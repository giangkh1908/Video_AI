"""API contract tests: create/poll/list/404/400/retry/file states."""
import pytest
from fastapi.testclient import TestClient

from app.core.models import ConceptId, ErrorInfo, Job, JobStatus
from app.main import create_app
from app.services import job_service as svc


@pytest.fixture()
def client(monkeypatch):
    monkeypatch.setattr(svc, "_submit", lambda job_id: None)
    svc.repo._jobs.clear()
    svc.repo._by_idem.clear()
    svc._voices.clear()
    return TestClient(create_app())


def _failed_job() -> Job:
    job = Job(
        job_id="v_retry01", concept=ConceptId.PH_SCALE, status=JobStatus.FAILED,
        progress=40, stage_detail="failed in narrating", attempt=1,
        error=ErrorInfo(code="TTS_FAILED", message="tts down",
                        retryable=True, failed_stage="narrating"),
    )
    svc.repo.save(job)
    return job


def test_create_202_shape(client):
    r = client.post("/api/v1/videos/requests", json={"concept": "ph-scale"})
    assert r.status_code == 202
    body = r.json()
    assert body["job_id"].startswith("v_")
    assert body["status"] == "queued"
    assert body["poll_url"] == f"/api/v1/jobs/{body['job_id']}"
    assert body["estimated_sec"] == 25


def test_create_idempotent_same_key(client):
    a = client.post("/api/v1/videos/requests",
                    json={"concept": "ph-scale", "idempotency_key": "k-1"}).json()
    b = client.post("/api/v1/videos/requests",
                    json={"concept": "covalent-why", "idempotency_key": "k-1"}).json()
    assert a["job_id"] == b["job_id"]


def test_poll_shape(client):
    job_id = client.post("/api/v1/videos/requests", json={"concept": "ph-scale"}).json()["job_id"]
    body = client.get(f"/api/v1/jobs/{job_id}").json()
    assert body["concept"] == "ph-scale"
    assert body["progress"] == 0
    assert body["stage_detail"] == "queued"
    assert body["attempt"] == 1
    assert body["timings"] == {}
    assert body["error"] is None


def test_list_filters(client):
    for concept in ("ph-scale", "covalent-why", "ionic-vs-covalent"):
        assert client.post("/api/v1/videos/requests", json={"concept": concept}).status_code == 202
    all_jobs = client.get("/api/v1/jobs").json()
    assert all_jobs["total"] == 3
    filtered = client.get("/api/v1/jobs", params={"concept": "ph-scale"}).json()
    assert filtered["total"] == 1
    assert filtered["jobs"][0]["concept"] == "ph-scale"
    queued = client.get("/api/v1/jobs", params={"status": "queued"}).json()
    assert queued["total"] == 3
    page = client.get("/api/v1/jobs", params={"limit": 2, "offset": 1}).json()
    assert len(page["jobs"]) == 2 and page["offset"] == 1


def test_unknown_job_404(client):
    assert client.get("/api/v1/jobs/v_nope").status_code == 404
    assert client.get("/api/v1/jobs/v_nope").json()["detail"]["code"] == "JOB_NOT_FOUND"
    assert client.get("/api/v1/videos/v_nope").status_code == 404
    assert client.get("/api/v1/videos/v_nope/file").status_code == 404
    assert client.post("/api/v1/jobs/v_nope/retry").status_code == 404


def test_unsupported_concept_400(client):
    r = client.post("/api/v1/videos/requests", json={"concept": "photosynthesis"})
    assert r.status_code == 400
    body = r.json()["detail"]
    assert body["code"] == "UNSUPPORTED_CONCEPT"
    assert "ph-scale" in body["hint"]


def test_invalid_request_400(client):
    r = client.post("/api/v1/videos/requests", json={})
    assert r.status_code == 400
    assert r.json()["code"] == "INVALID_REQUEST"


def test_retry_not_allowed_when_running(client):
    job_id = client.post("/api/v1/videos/requests", json={"concept": "ph-scale"}).json()["job_id"]
    r = client.post(f"/api/v1/jobs/{job_id}/retry")
    assert r.status_code == 409
    assert r.json()["detail"]["code"] == "RETRY_NOT_ALLOWED"


def test_retry_success_requeues(client):
    _failed_job()
    r = client.post("/api/v1/jobs/v_retry01/retry")
    assert r.status_code == 202
    assert r.json()["status"] == "queued"
    assert r.json()["attempt"] == 2
    assert svc.repo.get("v_retry01").error is None


def test_file_409_when_not_ready(client):
    job_id = client.post("/api/v1/videos/requests", json={"concept": "ph-scale"}).json()["job_id"]
    r = client.get(f"/api/v1/videos/{job_id}/file")
    assert r.status_code == 409
    assert r.json()["detail"]["code"] == "ARTIFACT_NOT_READY"
    meta = client.get(f"/api/v1/videos/{job_id}").json()
    assert meta["artifacts"] is None
    assert meta["poll_url"] == f"/api/v1/jobs/{job_id}"


def test_health_root(client):
    assert client.get("/health").json() == {"ok": True}
