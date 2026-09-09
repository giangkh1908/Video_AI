# 04 — Domain: Jobs & ScriptIR

## 4.1 Job model

```python
class JobStatus(str, Enum):
    QUEUED="queued"; SCRIPTING="scripting"; NARRATING="narrating"
    RENDERING="rendering"; COMPOSITING="compositing"
    VALIDATING="validating"; COMPLETED="completed"; FAILED="failed"

class ErrorInfo(BaseModel):
    code: str            # Job Execution Error only: SCRIPT_INVALID | TTS_FAILED | RENDER_FAILED | ...
                         # (HTTP errors như UNSUPPORTED_CONCEPT / JOB_NOT_FOUND thuộc namespace riêng, xem 03-api-spec §3.8)
    message: str         # human-readable, không stacktrace
    retryable: bool
    failed_stage: str | None

class Job(BaseModel):
    job_id: str          # "v_" + uuid8
    concept: ConceptId
    status: JobStatus
    progress: int        # 0-100
    stage_detail: str    # "rendering scene 3/5"
    attempt: int         # số lần retry pipeline, max 3
    idempotency_key: str | None
    artifact_path: str | None
    script: ScriptIR | None
    fallback_used: bool = False
    audio_degraded: bool = False
    error: ErrorInfo | None
    timings: dict[str, float] = {}
    created_at: datetime
    updated_at: datetime
```

## 4.2 State machine

```text
QUEUED → SCRIPTING → NARRATING → RENDERING → COMPOSITING → VALIDATING → COMPLETED
   │          │           │           │             │             │──→ FAILED
   └──────────┴───────────┴───────────┴─────────────┴─────────────→ FAILED (exception/timeout)
FAILED → QUEUED (via POST retry, attempt<3, retryable)
```

- Chỉ transitions trên được phép (`state_machine.py` enforce, trái → ValueError → 500 nội bộ, không lộ client).
- Progress map: scripting 0→20, narrating 20→40, rendering 40→75, compositing 75→90, validating 90→100.
- Terminal: `queued` 0, `completed` 100, `failed` giữ progress cuối (không reset).
- `fallback_used` / `audio_degraded` là flags, không phải status (fix lỗi agy diagram cũ).

## 4.3 ScriptIR — hợp đồng trung tâm

Mọi stage downstream chỉ đọc ScriptIR. LLM có bịa cũng không qua schema.

```python
from typing import Annotated, Union
from pydantic import Field

class ConceptId(str, Enum):
    PH_SCALE="ph-scale"; COVALENT_WHY="covalent-why"; IONIC_VS_COVALENT="ionic-vs-covalent"

class PhScaleBar(BaseModel):
    type: Literal["ph-scale-bar"] = "ph-scale-bar"
    highlight: float | None = None   # pH cần sáng lên, vd 7.0

class AtomShare(BaseModel):
    type: Literal["atom-share"] = "atom-share"
    molecule: str                    # "H2" | "O2" | "H2O"

class CompareTable(BaseModel):
    type: Literal["compare-table"] = "compare-table"
    rows: list[list[str]]            # 3-5 rows x 3 cols

class TitleCard(BaseModel):
    type: Literal["title-card"] = "title-card"
    subtitle: str | None = None

VisualSpec = Annotated[
    Union[PhScaleBar, AtomShare, CompareTable, TitleCard],
    Field(discriminator="type")
]  # Pydantic v2 discriminated union — bắt buộc để parse JSON theo field `type`

class Scene(BaseModel):
    id: str                          # "s1"
    title: str                       # max 60 chars
    bullets: list[str]               # 1-3 items, mỗi <=80 chars
    narration: str                   # 20-60 words
    visual: VisualSpec
    duration_sec: float              # 5-9

class ScriptIR(BaseModel):
    concept: ConceptId
    title: str
    scenes: list[Scene]              # 4-6, thực tế 5
    style: Literal["clean-edu"] = "clean-edu"
```

Validators (`models.py`):
- `scenes` 4–6, ids unique.
- Mỗi narration 20–60 words (đếm split).
- Mỗi duration 5–9s, tổng 28–45s.
- `est_audio = words/2.5`; nếu `|est_audio - duration| > 2` → pipeline auto-stretch duration (không reject, chỉ warn trong log).
