# CLAUDE.md — Growtrics Chemistry Video Request Service (Architecture Final)

> Merge từ `architect_agy.md` (pillars, fact invariants, storyboard, cost pitch)
> + `architect_claude.md` (state chuẩn, ScriptIR, visual guide, API v1, template-first).
> Version: 1.0-final | Ngày: 2026-09-09 | Trạng thái: Ready to implement

---

## 0. One-liner

> **API thật + Job async thật + MP4 thật. AI mock có chủ đích sau interface. Determinism đến từ Template + Schema validation, không đến từ may rủi của LLM.**

### Design Pillars (giữ từ agy)

1. **Reliability under Non-determinism:** kỹ thuật hóa mọi điểm chạm LLM/media, 4 Quality Gates + Fact Invariants + Deterministic Fallback.
2. **Cost-Quality Pareto:** chất lượng sư phạm sắc nét nhất ở chi phí rẻ nhất (hybrid: Template/LLM structured + Edge-TTS free + Pillow diagrams + FFmpeg → **~$0–0.001/video**).
3. **Clean Boundaries (Hexagonal):** cô lập API / Job Engine / Generation Providers / Persistence / Media Storage.
4. **Zero-Flaky Repeatability:** chạy 10/10 lần đều pass, không treo job, không video hỏng.

### Goals & Non-goals

| # | Yêu cầu đề | Cách đáp ứng |
|---|---|---|
| 1 | FastAPI backend | FastAPI + Pydantic v2, Python 3.11 |
| 2 | POST request video | `POST /api/v1/videos/requests` (202 Accepted) |
| 3 | Async flow | `BackgroundTasks` + `ThreadPoolExecutor(max_workers=2)`, poll status |
| 4 | List jobs | `GET /api/v1/jobs?status=&concept=&limit=&offset=` |
| 5 | Visible status | 7 trạng thái + progress 0-100 + `stage_detail` |
| 6 | Retrieve artifact | `GET /api/v1/videos/{id}` (metadata) + `GET .../file` (stream mp4, Range 206) |
| 7 | Visual + audio | Pillow 1280x720 frames + Edge-TTS narration + FFmpeg H.264/AAC |
| 8 | Boundary sạch | `API → Service → Providers/Store`, thay provider bằng env |
| 9 | 3 queries bắt buộc | Enum đóng + 3 templates curated + fact invariants |
| 10 | Mở rộng STEM | `concepts/registry.py`: thêm 1 class + 1 dòng đăng ký |

**Non-goals:** không auth, không DB thật, không Celery/Redis, không frontend, không diffusion photoreal, không websocket.

---

## 1. System Architecture

```text
                    ┌──────────────────────────────────────────────┐
                    │                  CLIENT                       │
                    │  curl / Postman / docs (poll, download mp4)   │
                    └──────────────┬───────────────▲───────────────┘
                                   │ POST          │ GET poll/download
                                   ▼               │
                    ┌──────────────────────────────────────────────┐
                    │               API LAYER (FastAPI)             │
                    │  routers: requests, jobs, videos, health     │
                    │  DTOs Pydantic, error mapping, Range serve    │
                    └──────────────┬───────────────────────────────┘
                                   │ JobCreate(concept)
                                   ▼
                    ┌──────────────────────────────────────────────┐
                    │         APPLICATION SERVICE (JobService)      │
                    │  - tạo job, state machine, idempotency        │
                    │  - dispatch worker, timeout 120s, retry       │
                    └──────────────┬───────────────────────────────┘
                                   │ run_pipeline(job_id)
                                   ▼
              ┌────────────────────────────────────────────────────────┐
              │              GENERATION PIPELINE (5 stages)               │
              │  [1.Script] → [2.Narrate] → [3.Render] → [4.Compose] →  │
              │  [5.Validate]                                           │
              │   ScriptProvider TTSProvider FrameRenderer Composer QA   │
              │   (template>LLM) (edge-tts>silent) (Pillow) (ffmpeg)     │
              └──────┬────────────┬───────────┬────────────┬────────────┘
                     │            │           │            │
                     ▼            ▼           ▼            ▼
              ┌──────────────┐ ┌──────────────────────────────────────────┐
              │ JOB STORE    │ │           ARTIFACT STORE                 │
              │ InMemory dict│ │  ./artifacts/{job_id}/                  │
              │ + lock (Repo │ │   video.mp4, script.json, audio_full.mp3,│
              │  interface)  │ │   thumb.jpg, pipeline.log.json           │
              └──────────────┘ └──────────────────────────────────────────┘
```

**Dependency rule:** `API → Service → Providers/Store`. Providers không import FastAPI. Store không biết render. Thay Sora/ElevenLabs chỉ sửa `providers/`.

### Providers — Template-first (quyết định sống còn cho demo)

| Provider | Default (`USE_MOCK=true`) | Real (tương lai) | Đổi bằng |
|---|---|---|---|
| Script | `TemplateScriptProvider` từ `concepts/*.py` (0.1s, offline) | `LLMScriptProvider` (gpt-4o-mini / Claude Haiku + parse + validate) | `SCRIPT_PROVIDER=llm` |
| TTS | `EdgeTTSProvider` (free) → fallback `SilentTTS` | `ElevenLabsProvider` | `TTS_PROVIDER` |
| Render | `PillowRenderer` | `SoraProvider` | `RENDER_PROVIDER` |

Log mỗi job: `provider.script=template fallback_used=false attempt=1`.

---

## 2. Domain Models

```python
class ConceptId(str, Enum):
    PH_SCALE = "ph-scale"
    COVALENT_WHY = "covalent-why"
    IONIC_VS_COVALENT = "ionic-vs-covalent"

class JobStatus(str, Enum):
    QUEUED="queued"; SCRIPTING="scripting"; NARRATING="narrating"
    RENDERING="rendering"; COMPOSITING="compositing"
    VALIDATING="validating"; COMPLETED="completed"; FAILED="failed"

class Job(BaseModel):
    job_id: str
    concept: ConceptId
    status: JobStatus
    progress: int              # 0-100
    stage_detail: str          # "rendering scene 3/5"
    attempt: int
    idempotency_key: str | None
    artifact_path: str | None
    script: ScriptIR | None
    fallback_used: bool = False
    audio_degraded: bool = False
    error: ErrorInfo | None    # {code, message, retryable, failed_stage}
    timings: dict[str, float]
    created_at: datetime
    updated_at: datetime
```

### ScriptIR — hợp đồng trung tâm

```python
class Scene(BaseModel):
    id: str
    title: str                 # max 60 chars
    bullets: list[str]         # 1-3 items, mỗi <=80 chars
    narration: str             # 20-60 words
    visual: VisualSpec         # PhScaleBar | AtomShare | CompareTable | TitleCard
    duration_sec: float        # 5-9s
    key_equation: str | None = None        # optional (EduGen borrow)
    learning_objective: str | None = None  # optional (EduGen borrow)

class ScriptIR(BaseModel):
    concept: ConceptId
    title: str
    scenes: list[Scene]        # 4-6 scenes (thực tế dùng 5 cho đủ 30-40s)
    style: Literal["clean-edu"] = "clean-edu"
```

Validators: tổng duration 28-45s; `est_audio = words/2.5` phải nằm trong `duration ±2s` (lệch → auto-stretch); không scene trống.

---

## 3. Job Lifecycle (bản sửa từ agy)

```text
QUEUED → SCRIPTING → NARRATING → RENDERING → COMPOSITING → VALIDATING → COMPLETED
   │          │           │           │             │             │──→ FAILED (retryable? requeue : terminal)
   └──────────┴───────────┴───────────┴─────────────┴─────────────→ FAILED (exception/timeout)
FAILED → QUEUED (POST /api/v1/jobs/{id}/retry, max 3)
```

| Status | % | Ý nghĩa |
|---|---|---|
| `queued` | 0 | Nằm hàng đợi (semaphore 2, job thứ 3 chờ) |
| `scripting` | 0→20 | `ScriptProvider.generate` + Gate 1+2 |
| `narrating` | 20→40 | TTS per scene + đo duration (Gate 3) |
| `rendering` | 40→75 | Pillow frames per scene |
| `compositing` | 75→90 | FFmpeg concat + fade |
| `validating` | 90→100 | QA Gate 4 (`ffmpeg -i` parse stderr, ffprobe-equivalent; ffprobe only if present) |
| `completed` | 100 | Serve được |
| `failed` | — | Kèm `error.code`, không bao giờ stacktrace |

> `fallback_used`, `audio_degraded` là **flag**, không phải status. Retry nội bộ LLM (tối đa 2) không lộ ra API.

---

## 4. Reliability — 4 Gates (merge agy + claude)

### Gate 1: Schema & Auto-Repair
- Strip markdown fences, trailing commas → Pydantic strict parse.
- Fail → retry LLM tối đa 2 với backoff 1s/2s (kèm Pydantic error trong prompt) → vẫn fail → **fallback Canonical Template (0.1s)**.

### Gate 2: Fact Invariants (giữ nguyên từ agy)
- **ph-scale:** phải có `0-14`, `7`/`neutral`, `acid`/`<7`, `base`/`alkaline`/`>7`, `H+`/`OH-`.
- **covalent-why:** phải có `shar* electron`, `octet`/8 electrons, `non-metal`, `stab*`/`energy`.
- **ionic-vs-covalent:** phải có `transfer` (cho-nhận, ion) vs `shar*` (dùng chung), `metal + non-metal` (ionic) vs `non-metal + non-metal` (covalent).
- Vi phạm → reject trước khi tốn TTS/render.

### Gate 3: A/V Alignment
- Đo `audio_duration` thực bằng mutagen per scene (`ffmpeg -i` parse stderr khi cần cross-check duration/audio-stream — ffprobe-equivalent; ffprobe only if present).
- `scene_duration = clamp(audio + 0.5s pad, 5s, 9s)`; tổng clamp 28-45s. Tránh 1 scene 15s phá timeline.

### Gate 4: Artifact Integrity (số chốt từ claude)
- `size >200KB`, `25s ≤ duration ≤60s`, `has_audio_stream == true` (`ffmpeg -i` parse stderr, ffprobe-equivalent; ffprobe only if present).
- Sample 3 frames/scene: mean brightness 15-240 (chống đen/trắng).
- `textbbox` <90% width (chống tràn chữ).
- Fail → `QA_REJECTED` (retryable) → retry pipeline 1 lần → vẫn fail → `FAILED`.

### Thêm: Idempotency, Dedup, Timeout, Errors
- `idempotency_key`: trùng key 24h → trả job cũ.
- Dedup: cùng concept đang chạy <60s → trả job đó.
- Timeout toàn job 120s → `PIPELINE_TIMEOUT`.
- Job codes (`ErrorInfo.code`, lưu trong Job): `SCRIPT_INVALID, TTS_FAILED, RENDER_FAILED, COMPOSE_FAILED, QA_REJECTED, PIPELINE_TIMEOUT`. Mỗi lỗi có `retryable: bool`.
- HTTP codes (request-level, không lưu vào Job — xem docs/03 §3.8): `UNSUPPORTED_CONCEPT, INVALID_REQUEST, JOB_NOT_FOUND, ARTIFACT_NOT_READY, RETRY_NOT_ALLOWED`.

---

## 5. Media Pipeline & Visual Spec

**Style chốt (từ claude):** 1280x720, nền `#0F172A`, accent `#22D3EE`, font DejaVu Sans Bold, subtitle trắng viền đen dưới. Motion: crossfade 0.4s + Ken Burns zoom nhẹ + marker di chuyển.

**Storyboard (giữ từ agy, chuẩn hóa 5 scenes để đủ duration):**

1. **ph-scale** — *Hiểu thang 0-14 đo H+/OH-, mốc 7 trung tính.*
   S1 Hook (title) → S2 thanh gradient đỏ→tím + marker 0→14 → S3 acid giàu H+ (pH<7) vs base giàu OH- (pH>7) + log 10x → S4 ví dụ: chanh/dạ dày 1-2, nước 7, xà phòng/tẩy 12-13 → S5 quiz.
2. **covalent-why** — *Liên kết để đạt octet bền + giảm thế năng.*
   S1 problem (phi kim thiếu e, năng lượng cao) → S2 sharing mechanism (2 mây e hòa vào cặp chung, vd H2/O2) → S3 octet callout → S4 outcome (giống khí hiếm, năng lượng cực tiểu) → S5 quiz.
3. **ionic-vs-covalent** — *Cho-nhận vs dùng chung.*
   S1 ionic (kim loại+phi kim, Na→Cl thành Na+/Cl-, lattice) → S2 covalent (phi kim+phi kim, H2O/CO2 dùng chung) → S3 split-screen so sánh → S4 comparison matrix (cơ chế, lực, ví dụ NaCl vs H2O) → S5 quiz.

**Audio:** Edge-TTS `en-US-AriaNeural`, rate -5%. Concat + pad 0.3s. Offline/fail 2 lần → `SilentTTS` (sine + subtitle), flag `audio_degraded=true`, job vẫn pass nếu visual OK. Cache audio theo `sha1(narration+voice)`.

**Compositing:** FFmpeg H.264 + AAC, `thumb.jpg` từ frame giữa.

---

## 6. Cost Breakdown (giữ pitch agy)

| Hạng mục | Tài nguyên | Cost/video |
|---|---|---|
| LLM script (chỉ khi `SCRIPT_PROVIDER=llm`) | ~800 in + 400 out (gpt-4o-mini) | ~$0.00036 |
| Fact check | regex local | $0 |
| TTS Edge-TTS | ~80 words | $0 |
| Pillow render | ~0.5s CPU | ~$0.00010 |
| FFmpeg compose | ~3s CPU | ~$0.00050 |
| **Tổng default (template)** | | **$0** |
| **Tổng với LLM opt-in** | | **~$0.001** |

So sánh: Sora/Runway $0.5-2/video + 3-5 phút + text hóa học méo → loại. Manim đẹp nhưng code dễ lỗi runtime → không chọn cho auto-pipeline.
**Scale 100k videos/tháng:** local ~$0 (điện máy), LLM opt-in ~$96.

---

## 7. API Contract (v1, merge)

```bash
POST /api/v1/videos/requests
GET  /api/v1/jobs?status=&concept=&limit=&offset=
GET  /api/v1/jobs/{job_id}
POST /api/v1/jobs/{job_id}/retry
GET  /api/v1/videos/{job_id}        # metadata + artifacts + cost + script
GET  /api/v1/videos/{job_id}/file   # mp4, hỗ trợ Range 206
GET  /health  GET /ready
```

```json
// POST /api/v1/videos/requests  → 202
{ "concept": "ph-scale", "voice": "en-US-AriaNeural", "idempotency_key": "opt-uuid" }
// →
{ "job_id": "v_8f3a...", "status": "queued",
  "poll_url": "/api/v1/jobs/v_8f3a...", "estimated_sec": 25 }

// GET /api/v1/videos/{id} (completed) → 200
{
  "job_id": "v_8f3a...", "concept": "ph-scale", "status": "completed",
  "progress": 100, "fallback_used": false, "audio_degraded": false,
  "artifacts": {
    "video_url": "/api/v1/videos/v_8f3a.../file",
    "duration_seconds": 32.5, "file_size_bytes": 2458120, "mime_type": "video/mp4"
  },
  "cost_breakdown": { "estimated_usd": 0.0, "provider_script": "template" },
  "error": null
}

// failed → 200 với status failed (không 500)
{ "status": "failed",
  "error": { "code": "TTS_FAILED", "message": "...", "retryable": true, "failed_stage": "narrating" } }
```

Concept lạ → `400 { code: UNSUPPORTED_CONCEPT, hint: ["ph-scale", ...] }`. Job không thấy → `404`.

---

## 8. Store, Observability, Project Structure

```python
class JobRepository(Protocol):
    def save(self, job: Job) -> None: ...
    def get(self, job_id: str) -> Job | None: ...
    def list(self, status=None, concept=None, limit=20, offset=0) -> list[Job]: ...

class ArtifactStore(Protocol):
    def put(self, job_id: str, kind: str, data: bytes) -> Path: ...
    def path(self, job_id: str, kind: str) -> Path: ...
```

Triển khai: `InMemoryJobRepo(threading.Lock)` + `LocalArtifactStore(./artifacts/{job_id}/video.mp4, script.json, audio_full.mp3, thumb.jpg, pipeline.log.json)`.

- Concurrency: semaphore 2 render cùng lúc.
- Logs: `pipeline.log.json` (timings, provider, attempt) + console `job_id=... stage=...`.
- `/ready` check ffmpeg + tts + disk.

```text
app/
  main.py
  api/routes.py
  core/models.py          # Job, ScriptIR, Scene, VisualSpec, ErrorInfo
  core/config.py          # USE_MOCK, workers, timeouts
  core/state_machine.py   # transitions hợp lệ
  services/job_service.py
  services/pipeline.py
  providers/base.py       # Protocols
  providers/script_template.py
  providers/script_llm.py # opt-in
  providers/tts_edge.py + tts_silent.py
  providers/renderer_pillow.py
  providers/composer_ffmpeg.py
  providers/qa_gate.py
  domain/invariants.py    # (từ agy) Fact rules
  domain/canonical_templates.py  # fallback 100% chuẩn
  concepts/ph_scale.py + covalent_why.py + ionic_vs_covalent.py + registry.py
  store/memory_repo.py + local_artifacts.py
artifacts/  tests/test_api.py + test_invariants.py + test_repeatability.py + test_end_to_end.py
README.md  COST.md  DEMO.md
```

---

## 9. Extensibility

Thêm topic mới (vd photosynthesis): tạo `concepts/photosynthesis.py: build() -> ScriptIR` + 1 dòng `registry["photosynthesis"] = ...` + thêm enum + invariants. Không đụng API/engine/QA.

---

## 10. Demo Flow

```bash
curl -X POST http://localhost:8000/api/v1/videos/requests \
  -H "Content-Type: application/json" -d '{"concept":"ph-scale"}'
curl http://localhost:8000/api/v1/jobs/v_8f3a...
curl "http://localhost:8000/api/v1/jobs?status=completed&limit=10"
curl http://localhost:8000/api/v1/videos/v_8f3a...
curl -O http://localhost:8000/api/v1/videos/v_8f3a.../file
```

Repeatability: request 3 lần `ph-scale` → 3 video đều pass Gate 4.

---

## 11. Tradeoffs (ADRs)

1. **Enum đóng 3 concepts** — đảm bảo đúng kiến thức + pass 100%. Mở rộng rõ ràng.
2. **Template-first, LLM opt-in** — offline demo được, $0, deterministic.
3. **Pillow thay diffusion** — hy sinh photoreal, giữ diagram chuẩn + rẻ.
4. **Polling thay webhook** — đề bảo latency không quan trọng, dễ curl.
5. **In-memory + local disk** — đề cho phép, migrate qua Repo/Store interface.

## 12. Execution Plan

1. Core & schemas (`models.py`, `invariants.py`, `canonical_templates.py`).
2. Engines (`script`, `voice`, `visual`, `composite` + `qa_gate`).
3. Worker & API (`job_service`, `pipeline`, `routes`).
4. Repeatability: `test_repeatability.py` chạy 10 lần x 3 concepts, check size/duration/audio/brightness.
