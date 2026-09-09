"""Domain models — contract in docs/04-domain-jobs.md."""
from datetime import datetime, timezone
from enum import Enum
from typing import Annotated, Literal, Union

from pydantic import BaseModel, Field, field_validator


class ConceptId(str, Enum):
    PH_SCALE = "ph-scale"
    COVALENT_WHY = "covalent-why"
    IONIC_VS_COVALENT = "ionic-vs-covalent"


class JobStatus(str, Enum):
    QUEUED = "queued"
    SCRIPTING = "scripting"
    NARRATING = "narrating"
    RENDERING = "rendering"
    COMPOSITING = "compositing"
    VALIDATING = "validating"
    COMPLETED = "completed"
    FAILED = "failed"


class HttpErrorCode(str, Enum):
    UNSUPPORTED_CONCEPT = "UNSUPPORTED_CONCEPT"
    INVALID_REQUEST = "INVALID_REQUEST"
    JOB_NOT_FOUND = "JOB_NOT_FOUND"
    ARTIFACT_NOT_READY = "ARTIFACT_NOT_READY"
    RETRY_NOT_ALLOWED = "RETRY_NOT_ALLOWED"


class JobErrorCode(str, Enum):
    SCRIPT_INVALID = "SCRIPT_INVALID"
    TTS_FAILED = "TTS_FAILED"
    RENDER_FAILED = "RENDER_FAILED"
    COMPOSE_FAILED = "COMPOSE_FAILED"
    QA_REJECTED = "QA_REJECTED"
    PIPELINE_TIMEOUT = "PIPELINE_TIMEOUT"


class ErrorInfo(BaseModel):
    code: str
    message: str
    retryable: bool = True
    failed_stage: str | None = None


# --- Visual specs (Pydantic v2 discriminated union) ---
class PhScaleBar(BaseModel):
    type: Literal["ph-scale-bar"] = "ph-scale-bar"
    highlight: float | None = None


class AtomShare(BaseModel):
    type: Literal["atom-share"] = "atom-share"
    molecule: str = "H2"


class CompareTable(BaseModel):
    type: Literal["compare-table"] = "compare-table"
    rows: list[list[str]] = Field(default_factory=list)


class TitleCard(BaseModel):
    type: Literal["title-card"] = "title-card"
    subtitle: str | None = None


VisualSpec = Annotated[
    Union[PhScaleBar, AtomShare, CompareTable, TitleCard],
    Field(discriminator="type"),
]


class Scene(BaseModel):
    id: str
    title: str
    bullets: list[str]
    narration: str
    visual: VisualSpec
    duration_sec: float
    key_equation: str | None = None
    learning_objective: str | None = None

    @field_validator("title")
    @classmethod
    def _title_len(cls, v: str) -> str:
        assert len(v) <= 60, "title max 60 chars"
        return v

    @field_validator("bullets")
    @classmethod
    def _bullets(cls, v: list[str]) -> list[str]:
        assert 1 <= len(v) <= 3, "1-3 bullets"
        assert all(len(b) <= 80 for b in v), "bullet max 80 chars"
        return v

    @field_validator("narration")
    @classmethod
    def _narration_words(cls, v: str) -> str:
        n = len(v.split())
        assert 20 <= n <= 60, f"narration 20-60 words, got {n}"
        return v

    @field_validator("duration_sec")
    @classmethod
    def _duration(cls, v: float) -> float:
        assert 5.0 <= v <= 9.0, "scene 5-9s"
        return v


class ScriptIR(BaseModel):
    concept: ConceptId
    title: str
    scenes: list[Scene]
    style: Literal["clean-edu"] = "clean-edu"

    @field_validator("scenes")
    @classmethod
    def _scenes(cls, v: list[Scene]) -> list[Scene]:
        assert 4 <= len(v) <= 6, "4-6 scenes"
        assert len({s.id for s in v}) == len(v), "scene ids unique"
        total = sum(s.duration_sec for s in v)
        assert 28.0 <= total <= 45.0, f"total 28-45s, got {total}"
        return v


class Job(BaseModel):
    job_id: str
    concept: ConceptId
    status: JobStatus = JobStatus.QUEUED
    progress: int = 0
    stage_detail: str = "queued"
    attempt: int = 1
    idempotency_key: str | None = None
    artifact_path: str | None = None
    script: ScriptIR | None = None
    fallback_used: bool = False
    audio_degraded: bool = False
    error: ErrorInfo | None = None
    timings: dict[str, float] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
