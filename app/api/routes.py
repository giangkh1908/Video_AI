"""REST API: requests / jobs / videos / health — contract docs/03-api-spec.md."""
import json
import shutil
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel

from app.core.config import settings
from app.core.models import ConceptId, JobStatus
from app.services import job_service as svc
from app.services.job_service import JobNotFound, RetryNotAllowed, UnsupportedConcept

router = APIRouter()
root_router = APIRouter()

ESTIMATED_SEC = 25
CONCEPT_HINT = [c.value for c in ConceptId]


class VideoRequest(BaseModel):
    concept: str
    voice: str = "en-US-AriaNeural"
    idempotency_key: str | None = None


def _error(status: int, code: str, message: str, hint=None):
    detail = {"code": code, "message": message}
    if hint is not None:
        detail["hint"] = hint
    raise HTTPException(status_code=status, detail=detail)


def _poll(job) -> dict:
    return {
        "job_id": job.job_id, "concept": job.concept.value, "status": job.status.value,
        "progress": job.progress, "stage_detail": job.stage_detail, "attempt": job.attempt,
        "fallback_used": job.fallback_used, "audio_degraded": job.audio_degraded,
        "error": job.error.model_dump() if job.error else None,
        "timings": job.timings,
        "created_at": job.created_at.isoformat(), "updated_at": job.updated_at.isoformat(),
    }


def _require(job_id: str):
    job = svc.get_job(job_id)
    if job is None:
        _error(404, "JOB_NOT_FOUND", f"unknown job {job_id}")
    return job


def _logged_duration(job_id: str) -> float:
    try:
        log = json.loads(svc.artifact_store.path(job_id, "pipeline.log.json").read_text())
        return float(log.get("duration_sec", 0) or 0)
    except Exception:
        return 0.0


@router.post("/videos/requests", status_code=202)
def create_video(body: VideoRequest, background: BackgroundTasks):
    try:
        job = svc.create_job(body.concept, body.voice, body.idempotency_key, background)
    except UnsupportedConcept as exc:
        _error(400, "UNSUPPORTED_CONCEPT", f"unsupported concept {exc.concept}", exc.hint)
    return {
        "job_id": job.job_id, "status": job.status.value,
        "poll_url": f"/api/v1/jobs/{job.job_id}", "estimated_sec": ESTIMATED_SEC,
    }


@router.get("/jobs")
def list_jobs(status: str | None = None, concept: str | None = None,
              limit: int = 20, offset: int = 0):
    status_id, concept_id = None, None
    if status is not None:
        try:
            status_id = JobStatus(status)
        except ValueError:
            _error(400, "INVALID_REQUEST", f"unknown status {status}")
    if concept is not None:
        try:
            concept_id = ConceptId(concept)
        except ValueError:
            _error(400, "UNSUPPORTED_CONCEPT", f"unsupported concept {concept}", CONCEPT_HINT)
    # Echo the EFFECTIVE window: JobService clamps limit to [1, 100] and
    # floors offset at 0, so mirror that here instead of echoing the raw
    # query (which would promise a wider page than the service returns).
    limit, offset = max(1, min(int(limit), 100)), max(0, int(offset))
    total, jobs = svc.list_jobs(status_id, concept_id, limit, offset)
    return {
        "total": total, "limit": limit, "offset": offset,
        "jobs": [{
            "job_id": j.job_id, "concept": j.concept.value, "status": j.status.value,
            "progress": j.progress, "updated_at": j.updated_at.isoformat(),
        } for j in jobs],
    }


@router.get("/jobs/{job_id}")
def poll_job(job_id: str):
    return _poll(_require(job_id))


@router.post("/jobs/{job_id}/retry", status_code=202)
def retry_job(job_id: str, background: BackgroundTasks):
    try:
        job = svc.retry_job(job_id, background)
    except JobNotFound:
        _error(404, "JOB_NOT_FOUND", f"unknown job {job_id}")
    except RetryNotAllowed as exc:
        _error(409, "RETRY_NOT_ALLOWED", exc.reason)
    return {
        "job_id": job.job_id, "status": job.status.value,
        "poll_url": f"/api/v1/jobs/{job.job_id}", "attempt": job.attempt,
    }


@router.get("/videos/{job_id}")
def video_meta(job_id: str):
    job = _require(job_id)
    base = {
        "job_id": job.job_id, "concept": job.concept.value, "status": job.status.value,
        "progress": job.progress, "fallback_used": job.fallback_used,
        "audio_degraded": job.audio_degraded,
        "poll_url": f"/api/v1/jobs/{job.job_id}",
        "error": job.error.model_dump() if job.error else None,
    }
    if job.status != JobStatus.COMPLETED:
        return {**base, "artifacts": None}
    video = Path(job.artifact_path) if job.artifact_path else svc.artifact_store.path(job_id, "video.mp4")
    file_ready = video.exists()
    # A completed job whose file was deleted must not claim size 0 (while
    # /file correctly 409s): report presence honestly with size null.
    size = video.stat().st_size if file_ready else None
    return {**base, "file_ready": file_ready, "artifacts": {
        "video_url": f"/api/v1/videos/{job_id}/file",
        "duration_seconds": _logged_duration(job_id),
        "file_size_bytes": size, "mime_type": "video/mp4",
    }, "cost_breakdown": {
        "estimated_usd": 0.0,
        "provider_script": "template-fallback" if job.fallback_used else "template",
        "provider_tts": "silent" if job.audio_degraded else "edge-tts",
    }, "script": job.script.model_dump() if job.script else None}


@router.get("/videos/{job_id}/file")
def video_file(job_id: str):
    job = svc.get_job(job_id)
    if job is None:
        _error(404, "JOB_NOT_FOUND", f"unknown job {job_id}")
    if job.status != JobStatus.COMPLETED:
        _error(409, "ARTIFACT_NOT_READY", f"job {job_id} is {job.status.value}")
    video = Path(job.artifact_path) if job.artifact_path else svc.artifact_store.path(job_id, "video.mp4")
    if not video.exists():
        _error(409, "ARTIFACT_NOT_READY", f"artifact for {job_id} not ready")
    return FileResponse(str(video), media_type="video/mp4", filename=f"{job_id}.mp4")


@root_router.get("/health")
@router.get("/health")
def health() -> dict:
    return {"ok": True}


@root_router.get("/ready")
@router.get("/ready")
def ready():
    try:
        from imageio_ffmpeg import get_ffmpeg_exe

        ffmpeg_ok = Path(get_ffmpeg_exe()).exists()
    except Exception:
        ffmpeg_ok = False
    base = Path(settings.artifact_dir)
    base.mkdir(parents=True, exist_ok=True)
    import os

    writable = os.access(base, os.W_OK)
    try:
        free_mb = shutil.disk_usage(base).free // (1024 * 1024)
    except Exception:
        free_mb = 0
    try:
        import edge_tts  # noqa: F401

        tts_ok = True
    except Exception:
        tts_ok = settings.tts_provider == "silent"
    body = {"ffmpeg": ffmpeg_ok, "tts": tts_ok, "disk_free_mb": free_mb}
    if not ffmpeg_ok or not writable or free_mb < 500:
        return JSONResponse(status_code=503, content=body)
    return body
