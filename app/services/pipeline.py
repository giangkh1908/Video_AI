"""Five-stage pipeline: script -> narrate -> render -> compose -> validate."""
import concurrent.futures
import importlib
import json
import logging
import shutil
import time
from datetime import datetime, timezone
from pathlib import Path

from app.core.config import settings
from app.core.models import ErrorInfo, JobErrorCode, JobStatus

log = logging.getLogger(__name__)
FAIL_CODE = {"scripting": JobErrorCode.SCRIPT_INVALID, "narrating": JobErrorCode.TTS_FAILED,
             "rendering": JobErrorCode.RENDER_FAILED, "compositing": JobErrorCode.COMPOSE_FAILED,
             "validating": JobErrorCode.QA_REJECTED}


class _BudgetExceeded(TimeoutError):
    """Remaining job budget ran out while blocked inside a subprocess call."""


def _svc():
    from app.services import job_service as svc
    return svc


def _set(job_id, status, detail):
    from app.core import state_machine as sm  # lazy: mirrors _svc(), avoids import cycles
    svc = _svc()
    job = svc.repo.get(job_id)
    if job is None:
        raise RuntimeError(f"unknown job {job_id}")
    try:
        sm.transition(job, status)  # ValueError on illegal edge: caller maps it, never silent
    except ValueError as exc:
        exc.pipeline_stage = status.value  # type: ignore[attr-defined]
        raise
    job.stage_detail = detail
    job.updated_at = datetime.now(timezone.utc)
    svc.repo.save(job)
    return job

def _stamp(svc, job_id, timings):
    job = svc.repo.get(job_id)
    if job is None:
        return None
    job.timings = {k: round(float(v), 3) for k, v in timings.items()}
    svc.repo.save(job)
    return job


def _fail(job_id, code, message, retryable, stage):
    svc = _svc()
    job = svc.repo.get(job_id)
    if job is None or job.status in (JobStatus.COMPLETED, JobStatus.FAILED):
        return job
    job.status = JobStatus.FAILED
    job.stage_detail = f"failed in {stage}" if stage else "failed"
    job.error = ErrorInfo(code=str(getattr(code, "value", code)), message=str(message)[:300], retryable=retryable, failed_stage=stage)
    job.updated_at = datetime.now(timezone.utc)
    svc.repo.save(job)
    log.warning("pipeline failed job_id=%s code=%s stage=%s", job_id, code, stage)
    return job


def _impl(module, names):
    mod = importlib.import_module(module)
    for name in names:
        obj = getattr(mod, name, None)
        if obj is not None:
            return obj() if isinstance(obj, type) else obj
    raise RuntimeError(f"no {names[0]} in {module}")


def _make_script(concept):
    if settings.script_provider == "llm":
        try:
            gen = _impl("app.providers.script_llm", ("LLMScriptProvider", "LlmScriptProvider"))
            out = gen.generate(concept)
            script, fb = out if isinstance(out, tuple) else (out, False)
            return script, fb, "llm"
        except Exception as exc:
            log.warning("llm script failed, using template: %s", exc)
    try:
        gen = _impl("app.providers.script_template", ("TemplateScriptProvider",))
        out = gen.generate(concept)
        script, fb = out if isinstance(out, tuple) else (out, False)
        return script, fb, "template"
    except Exception:
        mod = importlib.import_module("app.domain.canonical_templates")
        for name in (f"build_{concept.value.replace('-', '_')}", "build"):
            fn = getattr(mod, name, None)
            if callable(fn):
                try: return fn(), True, "template"
                except TypeError: return fn(concept), True, "template"
        raise RuntimeError("no canonical template available")

def _speak(text, voice, silent=False):
    which = "tts_silent" if silent or settings.tts_provider == "silent" else "tts_edge"
    provider = _impl(f"app.providers.{which}", ("EdgeTTSProvider", "SilentTTS", "TTSProvider", "synthesize"))
    return provider.synthesize(text, voice) if hasattr(provider, "synthesize") else provider(text, voice)


def _mp3_sec(path, words):
    try:
        from mutagen.mp3 import MP3
        return float(MP3(str(path)).info.length)
    except Exception:
        return max(1.0, words / 2.5)
def _fit(secs):
    """Clamp per-scene audio+pad into [5, 9]s, then fit the total into 28-45s.

    Scenes already pinned at the floor/ceiling cannot absorb more, so the
    over/under remainder goes only to unpinned scenes (water-filling).
    Proportional scaling + hard re-clamp instead converges to ~45.006 on
    inputs like [4, 20x5] and raises although [5, 8x5] = 45 is feasible.
    """
    fitted = [min(9.0, max(5.0, s + 0.5)) for s in secs]
    for _ in range(5):
        total = sum(fitted)
        if 28.0 <= total <= 45.0:
            return fitted
        remainder = (28.0 if total < 28.0 else 45.0) - total
        movable = [i for i, s in enumerate(fitted)
                   if (remainder > 0 and s < 9.0) or (remainder < 0 and s > 5.0)]
        if not movable:
            break
        share = remainder / len(movable)
        for i in movable:
            fitted[i] = min(9.0, max(5.0, fitted[i] + share))
    total = sum(fitted)
    if not 28.0 <= total <= 45.0:
        raise ValueError(f"cannot fit scene durations into 28-45s window (total={total:.2f})")
    return fitted


def _srt(scenes, durations):
    fmt = lambda ms: f"{ms // 3600000:02d}:{(ms // 60000) % 60:02d}:{(ms // 1000) % 60:02d},{ms % 1000:03d}"
    lines, t = [], 0.0
    for i, (scene, dur) in enumerate(zip(scenes, durations)):
        lines.append(f"{i + 1}\n{fmt(int(t * 1000))} --> {fmt(int((t + dur) * 1000))}\n{scene.title}\n{scene.narration}\n")
        t += dur
    return "\n".join(lines)


def _write_log(svc, job, timings, warnings, providers, duration):
    svc.artifact_store.put(job.job_id, "pipeline.log.json", json.dumps({
        "job_id": job.job_id, "concept": job.concept.value, "attempt": job.attempt, "status": job.status.value,
        "timings": timings, "warnings": warnings, "provider_script": providers[0], "provider_tts": providers[1],
        "fallback_used": job.fallback_used, "audio_degraded": job.audio_degraded, "duration_sec": duration}, indent=2))

def _bounded(call, budget, stage):
    """Run a blocking provider call under the job's remaining time budget.

    Narrate/render block inside TTS/Pillow just like compose blocks inside
    ffmpeg, so the same executor bound applies: on expiry the pipeline
    thread is released and the caller fails the job as PIPELINE_TIMEOUT.
    """
    if budget is not None and budget <= 0:
        raise _BudgetExceeded(f"no time budget left for {stage}")
    if budget is None:
        return call()
    pool = concurrent.futures.ThreadPoolExecutor(max_workers=1)
    try:
        future = pool.submit(call)
        try:
            return future.result(timeout=budget)
        except concurrent.futures.TimeoutError as exc:
            future.cancel()
            raise _BudgetExceeded(f"{stage} exceeded {budget:.1f}s budget") from exc
    finally:
        # wait=False: a hung call keeps its worker thread, but the pipeline
        # thread is released (compose runs outside the render semaphore).
        pool.shutdown(wait=False, cancel_futures=True)


def _compose_bounded(composer, by_scene, paths, job_dir, budget):
    """Run composer with the job's remaining time budget.

    compose() blocks inside ffmpeg, so the between-stage `expired` checks
    never fire while it hangs. Bounding it here frees the worker and lets
    the job fail as PIPELINE_TIMEOUT instead of stalling forever.
    """
    call = (lambda: composer.compose(by_scene, paths, job_dir)) if hasattr(composer, "compose") \
        else (lambda: composer(by_scene, paths, job_dir))
    return _bounded(call, budget, "compositing")


def run_pipeline(job_id: str) -> None:
    try:
        _run(job_id)
    except Exception as exc:
        stage = getattr(exc, "pipeline_stage", None)
        code = FAIL_CODE.get(stage, JobErrorCode.COMPOSE_FAILED)
        try: _fail(job_id, code, f"{type(exc).__name__}: {exc}", True, stage)
        except Exception: pass


def _run(job_id: str) -> None:
    # current_stage lets the run_pipeline catch-all attribute gap failures
    # (stamp/store/srt/log, raised outside the per-stage tries) to the stage
    # in flight instead of COMPOSE_FAILED/None.
    current_stage = "scripting"
    try:
        svc = _svc()
        job = svc.repo.get(job_id)
        if job is None:
            return
        start = time.monotonic()
        timings, warnings, providers = {}, [], ["template", "edge-tts"]
        expired = lambda stage: (  # noqa: E731
            _fail(job_id, JobErrorCode.PIPELINE_TIMEOUT,
                  f"job exceeded {settings.job_timeout_sec}s before {stage}", True, stage)
            if (time.monotonic() - start) > settings.job_timeout_sec else None) is not None
        t0 = time.monotonic()
        try:
            _set(job_id, JobStatus.SCRIPTING, "generating script")
            script, fallback_used, name = _make_script(job.concept)
            providers[0] = name
            from app.domain.invariants import check as check_facts
            text = " ".join(f"{' '.join(s.bullets)} {s.narration}" for s in script.scenes)
            missing = check_facts(job.concept, text)
            if missing:
                raise ValueError(f"fact invariants missing: {missing}")
            for scene in script.scenes:
                if abs(len(scene.narration.split()) / 2.5 - scene.duration_sec) > 2:
                    warnings.append(f"auto-stretch {scene.id}")
            job = svc.repo.get(job_id)
            job.script, job.fallback_used = script, fallback_used
            svc.repo.save(job)
        except Exception as exc:
            _fail(job_id, FAIL_CODE["scripting"], f"{type(exc).__name__}: {exc}", True, "scripting")
            return
        timings["scripting"] = time.monotonic() - t0
        _stamp(svc, job_id, timings)
        if expired("scripting"):
            return
        t0 = time.monotonic()
        try:
            current_stage = "narrating"
            _set(job_id, JobStatus.NARRATING, "synthesizing narration")
            job = svc.repo.get(job_id)
            voice, job_dir = svc.voice_for(job_id), svc.artifact_store.job_dir(job_id)
            raw, paths = [], []
            for idx, scene in enumerate(job.script.scenes):
                # Bound each TTS call by the remaining job budget: a hung
                # Edge-TTS (30s x 5 scenes) must not hold the worker past 120s.
                def remaining():
                    return settings.job_timeout_sec - (time.monotonic() - start)
                try:
                    data = _bounded(lambda s=scene: _speak(s.narration, voice), remaining(), "narrating")
                except _BudgetExceeded:
                    raise
                except Exception as first_exc:
                    log.warning("primary TTS failed scene %d attempt 1/2: %s", idx, first_exc)
                    time.sleep(1)  # backoff before the single retry
                    try:
                        data = _bounded(lambda s=scene: _speak(s.narration, voice), remaining(), "narrating")
                    except _BudgetExceeded:
                        raise
                    except Exception as second_exc:
                        log.warning("primary TTS failed scene %d attempt 2/2, silent fallback: %s", idx, second_exc)
                        data = _bounded(lambda s=scene: _speak(s.narration, voice, silent=True), remaining(), "narrating")
                        job.audio_degraded = True
                paths.append(job_dir / f"scene_{idx}.mp3")
                paths[-1].write_bytes(bytes(data))
                raw.append(_mp3_sec(paths[-1], len(scene.narration.split())))
            try:
                fitted = _fit(raw)
            except ValueError as exc:
                # Unfittable timeline is a script problem, not a TTS problem.
                _fail(job_id, FAIL_CODE["scripting"], f"{type(exc).__name__}: {exc}", True, "scripting")
                return
        except _BudgetExceeded as exc:
            _fail(job_id, JobErrorCode.PIPELINE_TIMEOUT, f"{type(exc).__name__}: {exc}", True, "narrating")
            return
        except Exception as exc:
            _fail(job_id, FAIL_CODE["narrating"], f"{type(exc).__name__}: {exc}", True, "narrating")
            return
        timings["narrating"] = time.monotonic() - t0
        if settings.tts_provider == "silent":
            job.audio_degraded = True
        # Persist flags before _stamp: the repo stores deep copies, so _stamp's
        # re-read would load a stale copy (audio_degraded=False) and bury this.
        svc.repo.save(job)
        providers[1] = "silent" if job.audio_degraded else "edge-tts"
        _stamp(svc, job_id, timings)
        if expired("narrating"):
            return
        t0 = time.monotonic()
        try:
            current_stage = "rendering"
            _set(job_id, JobStatus.RENDERING, f"rendering scene 0/{len(job.script.scenes)}")
            try:
                from app.services.job_service import RENDER_SEMAPHORE as sem
            except Exception:
                import threading as _th
                sem = _th.Semaphore(2)
            with sem:
                renderer = _impl("app.providers.renderer_pillow", ("PillowRenderer", "Renderer"))
                frames = job_dir / "frames"
                frames.mkdir(parents=True, exist_ok=True)
                by_scene, total_scenes = [], len(job.script.scenes)
                for i, s in enumerate(job.script.scenes):
                    # Rendering is CPU-bound with no inner deadline, so check
                    # the job budget every scene instead of only between stages.
                    if (time.monotonic() - start) > settings.job_timeout_sec:
                        raise _BudgetExceeded(f"rendering exceeded {settings.job_timeout_sec}s budget")
                    by_scene.append([Path(p) for p in renderer.render_scene(s, i, frames)])
                    job = svc.repo.get(job_id)
                    job.progress, job.stage_detail = 75, f"rendering scene {i + 1}/{total_scenes}"
                    svc.repo.save(job)
        except _BudgetExceeded as exc:
            _fail(job_id, JobErrorCode.PIPELINE_TIMEOUT, f"{type(exc).__name__}: {exc}", True, "rendering")
            return
        except Exception as exc:
            _fail(job_id, FAIL_CODE["rendering"], f"{type(exc).__name__}: {exc}", True, "rendering")
            return
        timings["rendering"] = time.monotonic() - t0
        _stamp(svc, job_id, timings)
        if expired("rendering"):
            return
        t0 = time.monotonic()
        try:
            current_stage = "compositing"
            _set(job_id, JobStatus.COMPOSITING, "compositing video")
            paths = [job_dir / f"scene_{i}.mp3" for i in range(len(job.script.scenes))]
            composer = _impl("app.providers.composer_ffmpeg", ("Composer", "FFmpegComposer", "compose"))
            budget = settings.job_timeout_sec - (time.monotonic() - start)
            result = _compose_bounded(composer, by_scene, paths, job_dir, budget)
            video = Path(result["video_path"])
            thumb = Path(result["thumb_path"]) if result.get("thumb_path") else job_dir / "thumb.jpg"
            if not thumb.exists():
                flats = [p for group in by_scene for p in group]
                if flats:
                    shutil.copy(flats[len(flats) // 2], thumb)
            job = svc.repo.get(job_id)
            job.artifact_path = str(video)
            svc.repo.save(job)
            svc.artifact_store.put(job_id, "script.json", job.script.model_dump_json(indent=2))
            svc.artifact_store.put(job_id, "subtitles.srt", _srt(job.script.scenes, fitted))
            duration = float(result.get("duration_sec") or sum(fitted))
            _write_log(svc, job, timings, warnings, providers, duration)
        except _BudgetExceeded as exc:
            _fail(job_id, JobErrorCode.PIPELINE_TIMEOUT, f"{type(exc).__name__}: {exc}", True, "compositing")
            return
        except Exception as exc:
            _fail(job_id, FAIL_CODE["compositing"], f"{type(exc).__name__}: {exc}", True, "compositing")
            return
        timings["compositing"] = time.monotonic() - t0
        _stamp(svc, job_id, timings)
        t0 = time.monotonic()
        try:
            current_stage = "validating"
            _set(job_id, JobStatus.VALIDATING, "validating artifact")
            qa = _impl("app.providers.qa_gate", ("QAGate", "QualityGate", "validate"))
            check = (lambda v: qa.validate(v)) if hasattr(qa, "validate") else qa
            if not bool(check(video).get("passed", False)):
                warnings.append("qa first pass failed, retrying compose once")
                budget = settings.job_timeout_sec - (time.monotonic() - start)
                result = _compose_bounded(composer, by_scene, paths, job_dir, budget)
                video = Path(result["video_path"])
                if not bool(check(video).get("passed", False)):
                    _fail(job_id, FAIL_CODE["validating"], "QA checks failed", True, "validating")
                    return
        except _BudgetExceeded as exc:
            _fail(job_id, JobErrorCode.PIPELINE_TIMEOUT, f"{type(exc).__name__}: {exc}", True, "validating")
            return
        except Exception as exc:
            _fail(job_id, FAIL_CODE["validating"], f"{type(exc).__name__}: {exc}", True, "validating")
            return
        timings["validating"] = time.monotonic() - t0
        try:
            job = _set(job_id, JobStatus.COMPLETED, "done")
        except Exception as exc:
            _fail(job_id, FAIL_CODE["validating"], f"{type(exc).__name__}: {exc}", True, "validating")
            return
        timings["total"] = time.monotonic() - start
        _stamp(svc, job_id, timings)
        job = svc.repo.get(job_id)
        _write_log(svc, job, timings, warnings, providers, duration)
    except Exception as exc:
        # Gap failure outside the per-stage tries (stamp/store/srt/log):
        # keep an explicit stage tag so the run_pipeline catch-all maps the
        # right code; only genuinely untagged errors fall back to
        # COMPOSE_FAILED/None there.
        if getattr(exc, "pipeline_stage", None) is None:
            exc.pipeline_stage = current_stage  # type: ignore[attr-defined]
        raise
