"""Local artifact store: ./artifacts/{job_id}/video.mp4, script.json, ..."""
from pathlib import Path

from app.core.config import settings

KINDS = (
    "video.mp4",
    "audio_full.mp3",
    "script.json",
    "thumb.jpg",
    "pipeline.log.json",
    "subtitles.srt",
)


class LocalArtifactStore:
    def __init__(self, base: str | None = None) -> None:
        self.base = Path(base or settings.artifact_dir)

    def job_dir(self, job_id: str) -> Path:
        d = self.base / job_id
        d.mkdir(parents=True, exist_ok=True)
        return d

    def path(self, job_id: str, kind: str) -> Path:
        return self.job_dir(job_id) / kind

    def put(self, job_id: str, kind: str, data: bytes | str) -> Path:
        p = self.path(job_id, kind)
        if isinstance(data, str):
            p.write_text(data, encoding="utf-8")
        else:
            p.write_bytes(data)
        return p
