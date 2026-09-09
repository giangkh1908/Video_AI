"""Repeatability: 10 runs x 3 concepts pass Gate 4 thresholds + fact invariants.

Slow by design (parent decides when to run). Media assertions only run with
RUN_MEDIA=1; otherwise script + invariant loops run and media is skipped.
"""
import os

import pytest

pytestmark = pytest.mark.slow

CONCEPTS = ["ph-scale", "covalent-why", "ionic-vs-covalent"]
RUNS = 10
RUN_MEDIA = os.getenv("RUN_MEDIA", "0") == "1"


def _ffmpeg_present() -> bool:
    try:
        from pathlib import Path

        from imageio_ffmpeg import get_ffmpeg_exe

        return Path(get_ffmpeg_exe()).exists()
    except Exception:
        return False


def _generate(concept):
    from app.core.models import ConceptId
    from app.providers.script_template import TemplateScriptProvider

    return TemplateScriptProvider().generate(ConceptId(concept))


def test_scripts_pass_invariants_10x3():
    from app.core.models import ConceptId
    from app.domain.invariants import check

    try:
        _generate(CONCEPTS[0])
    except NotImplementedError:
        pytest.skip("script provider not implemented yet")
    for _ in range(RUNS):
        for concept in CONCEPTS:
            script = _generate(concept)
            # Gate-2 scope is narration+bullets ONLY (no title) — same join as
            # services/pipeline.py; including titles would false-pass here.
            text = " ".join(f"{' '.join(s.bullets)} {s.narration}" for s in script.scenes)
            missing = check(ConceptId(concept), text)
            assert not missing, f"{concept} missing {missing}"
            total = sum(s.duration_sec for s in script.scenes)
            assert 28.0 <= total <= 45.0, f"{concept} total {total}"
            for scene in script.scenes:
                est = len(scene.narration.split()) / 2.5
                assert 5.0 <= scene.duration_sec <= 9.0
                assert abs(est - scene.duration_sec) <= 2.0, scene.id


def test_gate4_thresholds_sane():
    from app.providers import qa_gate

    assert qa_gate.MIN_SIZE_BYTES == 200_000
    assert qa_gate.MIN_DURATION_SEC == 25.0
    assert qa_gate.MAX_DURATION_SEC == 60.0
    assert qa_gate.BRIGHTNESS_MIN == 15.0
    assert qa_gate.BRIGHTNESS_MAX == 240.0


@pytest.mark.skipif(not RUN_MEDIA, reason="set RUN_MEDIA=1 to render 30 videos")
def test_media_repeatability_10x3():
    if not _ffmpeg_present():
        pytest.skip("no ffmpeg binary")
    from app.services import job_service as svc
    from app.services.pipeline import run_pipeline

    for _ in range(RUNS):
        for concept in CONCEPTS:
            job = svc.create_job(concept)
            run_pipeline(job.job_id)
            done = svc.repo.get(job.job_id)
            assert done.status.value == "completed", done.error
