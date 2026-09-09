"""End-to-end: POST -> poll -> video metadata/file for 3 concepts (mocked pipeline)."""
import json

import pytest
from fastapi.testclient import TestClient

from app.core.models import ConceptId, JobStatus, Scene, ScriptIR, TitleCard
from app.main import create_app
from app.services import job_service as svc

CONCEPTS = ["ph-scale", "covalent-why", "ionic-vs-covalent"]


def _fake_script(concept: str) -> ScriptIR:
    scenes = [
        Scene(
            id=f"s{i + 1}", title=f"Scene {i + 1} about {concept}",
            bullets=[f"key point {i + 1}"],
            narration=" ".join(f"word{j}" for j in range(25)),
            visual=TitleCard(subtitle=f"part {i + 1}"), duration_sec=6.5,
        )
        for i in range(5)
    ]
    return ScriptIR(concept=ConceptId(concept), title=f"All about {concept}", scenes=scenes)


def _complete(job_id: str) -> None:
    job = svc.repo.get(job_id)
    job.script = _fake_script(job.concept.value)
    job.status = JobStatus.COMPLETED
    job.progress = 100
    job.stage_detail = "done"
    job.artifact_path = str(svc.artifact_store.path(job_id, "video.mp4"))
    job.timings = {"total": 1.0}
    svc.repo.save(job)
    svc.artifact_store.put(job_id, "video.mp4", b"fake-mp4" * 512)
    svc.artifact_store.put(job_id, "thumb.jpg", b"fake-jpg" * 64)
    svc.artifact_store.put(job_id, "script.json", job.script.model_dump_json(indent=2))
    svc.artifact_store.put(job_id, "subtitles.srt", "1\n00:00:00,000 --> 00:00:06,500\nx\n")
    svc.artifact_store.put(job_id, "pipeline.log.json", json.dumps({"duration_sec": 32.5}))


@pytest.fixture()
def client(monkeypatch, tmp_path):
    monkeypatch.setattr(svc, "_submit", _complete)
    monkeypatch.setattr(svc.artifact_store, "base", tmp_path)
    svc.repo._jobs.clear()
    svc.repo._by_idem.clear()
    svc._voices.clear()
    return TestClient(create_app())


@pytest.mark.parametrize("concept", CONCEPTS)
def test_post_poll_video_file(client, concept):
    created = client.post("/api/v1/videos/requests", json={"concept": concept})
    assert created.status_code == 202
    job_id = created.json()["job_id"]

    poll = client.get(f"/api/v1/jobs/{job_id}").json()
    assert poll["status"] == "completed"
    assert poll["progress"] == 100

    meta = client.get(f"/api/v1/videos/{job_id}").json()
    assert meta["status"] == "completed"
    assert meta["error"] is None
    assert meta["artifacts"]["video_url"] == f"/api/v1/videos/{job_id}/file"
    assert meta["artifacts"]["mime_type"] == "video/mp4"
    assert meta["artifacts"]["file_size_bytes"] > 0
    assert meta["artifacts"]["duration_seconds"] == 32.5
    assert meta["cost_breakdown"]["estimated_usd"] == 0.0
    assert len(meta["script"]["scenes"]) == 5

    data = client.get(f"/api/v1/videos/{job_id}/file")
    assert data.status_code == 200
    assert "video/mp4" in data.headers["content-type"]
    assert len(data.content) > 0
