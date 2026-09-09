# 08 — Project Structure & Execution Plan

## 8.1 Cây thư mục (target ~25 files)

```text
D:/test/
├── CLAUDE.md                    # architecture final (merge)
├── requirements.txt             # fastapi, uvicorn, pydantic, edge-tts, pillow, imageio-ffmpeg, mutagen
├── docs/                        # spec này (README + 01..08)
├── app/
│   ├── __init__.py
│   ├── main.py                  # create FastAPI app, include routers (serve file via routes file endpoint)
│   ├── api/routes.py            # POST requests, GET jobs, GET videos, retry, health/ready
│   ├── core/config.py           # env: USE_MOCK, SCRIPT/TTS/RENDER_PROVIDER, workers=2, timeout=120
│   ├── core/models.py           # ConceptId, JobStatus, Job, ScriptIR, Scene, VisualSpec, ErrorInfo
│   ├── core/state_machine.py    # ALLOWED_TRANSITIONS + transition(job, to)
│   ├── services/job_service.py  # create/get/list/retry, idempotency, dedup, dispatch BG
│   ├── services/pipeline.py     # run_pipeline: 5 stages + progress + timings + catch→FAILED
│   ├── providers/base.py        # Protocols: Script/TTS/FrameRenderer/Composer/QAGate
│   ├── providers/script_template.py  # TemplateScriptProvider (đọc concepts/*)
│   ├── providers/script_llm.py       # LLMScriptProvider opt-in (flag)
│   ├── providers/tts_edge.py         # EdgeTTSProvider
│   ├── providers/tts_silent.py       # SilentTTS fallback
│   ├── providers/renderer_pillow.py  # PillowRenderer (4 VisualSpec)
│   ├── providers/composer_ffmpeg.py  # FFmpeg concat + fade + AAC/H264
│   ├── providers/qa_gate.py          # Gate 4 checks
│   ├── domain/invariants.py          # Fact rules 3 topics (từ agy)
│   ├── domain/canonical_templates.py # fallback scripts 100% chuẩn (hoặc concepts/*)
│   ├── concepts/ph_scale.py          # build() -> ScriptIR (5 scenes)
│   ├── concepts/covalent_why.py
│   ├── concepts/ionic_vs_covalent.py
│   ├── concepts/registry.py          # CONCEPTS = {"ph-scale": ..., ...}
│   └── store/memory_repo.py          # InMemoryJobRepo + lock
│   └── store/local_artifacts.py      # LocalArtifactStore ./artifacts/{job_id}/
├── artifacts/                   # output runtime (gitignore, trừ 3 mp4 mẫu)
│   └── {job_id}/video.mp4, script.json, audio_full.mp3, thumb.jpg, pipeline.log.json
└── tests/
    ├── test_api.py              # 202, poll, list filter, 404, unsupported concept
    ├── test_invariants.py       # 3 topics pass/fail cases
    ├── test_qa.py               # size/duration/brightness/textbbox
    ├── test_repeatability.py    # 10x3 runs đều pass
    └── test_end_to_end.py       # POST→poll→download 3 queries
```

## 8.2 Trách nhiệm file (1 dòng/file)

Xem §2.2 trong `02-architecture.md`. Nguyên tắc: file nào cũng <250 dòng, hàm thuần dễ test, providers không import fastapi.

## 8.3 Conventions

- Python 3.11, Pydantic v2 (`model_validate`, discriminated union `Field(discriminator="type")`).
- Status/error codes chữ thường snake; ConceptId kebab (`ph-scale`).
- Mọi thời gian UTC ISO8601. `job_id = "v_" + uuid4().hex[:8]`.
- Log structured: `logger.info("stage", extra={"job_id":..., "stage":...})` + `pipeline.log.json` per job.
- Env: `SCRIPT_PROVIDER=template|llm`, `TTS_PROVIDER=edge|silent`, `MAX_WORKERS=2`, `JOB_TIMEOUT_SEC=120`, `ARTIFACT_DIR=./artifacts`.
- `/ready` checks: ffmpeg binary + tts reachability + disk writable (disk <500MB → not ready).
- Media params tập trung ở `core/config.py`: voice_rate, fps, resolution, crossfade, pads (không hardcode trong providers).

## 8.4 Thêm STEM topic mới (không sửa engine)

1. Tạo `app/concepts/photosynthesis.py` implement `build() -> ScriptIR`.
2. Thêm fact rules vào `domain/invariants.py`.
3. Đăng ký 1 dòng `registry.py` + thêm enum `ConceptId`. Xong.

## 8.5 Execution plan (spec-first)

1. **Core & domain:** `models.py`, `state_machine.py`, `invariants.py`, `canonical_templates.py` + tests invariants.
2. **Engines:** script/template → voice → visual → composite → qa_gate (test từng cái với script mẫu).
3. **Worker & API:** `job_service.py` + `pipeline.py` + `routes.py` + `main.py` (curl 3 queries pass).
4. **Repeatability:** `test_repeatability.py` 10×3 + fix flaky + render 3 mp4 mẫu vào `artifacts/` + viết DEMO.md.
