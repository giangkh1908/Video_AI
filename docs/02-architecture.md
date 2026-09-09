# 02 — System Architecture

## 2.1 Tổng quan layers

```text
CLIENT (curl) ──POST/GET──▶ API LAYER (FastAPI routers, DTOs, error mapping)
                              │ JobCreate(concept)
                              ▼
                    JOB SERVICE (orchestrator: state, idempotency, dispatch, timeout)
                              │ run_pipeline(job_id)
                              ▼
                    PIPELINE 5 stages: Script → Narrate → Render → Compose → Validate
                      │            │           │            │           │
                 ScriptProvider TTSProvider FrameRenderer Composer  QAGate
                      │            │           │            │           │
                      ▼            ▼           ▼            ▼           ▼
                 JOB STORE (InMemory dict + lock)   ARTIFACT STORE (./artifacts/{job_id}/)
```

**Dependency rule:** `API → Service → Providers/Store`. Providers không import FastAPI. Store không biết render.

## 2.2 Components & trách nhiệm

| Component | File | Trách nhiệm | Không được làm |
|---|---|---|---|
| API routers | `app/api/routes.py` | Parse, gọi service, map lỗi, serve file (Range) | Render, gọi FFmpeg trực tiếp |
| JobService | `app/services/job_service.py` | Tạo/get/list/retry job, transitions, idempotency, dedup | Vẽ frame, tổng hợp audio |
| Pipeline | `app/services/pipeline.py` | `run_pipeline(job_id)` tuần tự 5 stages, update progress, catch → FAILED | Định nghĩa HTTP |
| ScriptProvider | `app/providers/script_*.py` | concept → ScriptIR | Đọc HTTP, ghi file |
| TTSProvider | `app/providers/tts_*.py` | text → audio bytes | Quyết định duration scene |
| FrameRenderer | `app/providers/renderer_pillow.py` | ScriptIR → frames PNG | Gọi TTS |
| Composer | `app/providers/composer_ffmpeg.py` | frames+audio → MP4 | Validate khoa học |
| QAGate | `app/providers/qa_gate.py` | ffmpeg `-i` (parse stderr) + mutagen + image checks → pass/fail | Sửa script |
| JobRepository | `app/store/memory_repo.py` | save/get/list (Protocol, mai thay Postgres) | Biết MP4 |
| ArtifactStore | `app/store/local_artifacts.py` | put/path per job_id (Protocol, mai thay S3) | Biết Job status |

## 2.3 Sequence — happy path

```text
Client                API              JobService        Worker(pipeline)       Stores
  │ POST /requests      │                  │                    │                 │
  │────────────────────▶│ create_job()     │                    │                 │
  │                     │─────────────────▶│ save(QUEUED)       │                 │
  │                     │                  │───────────────────▶│                 │
  │ 202 {job_id}        │ dispatch BG      │                    │                 │
  │◀────────────────────│                  │                    │                 │
  │ GET /jobs/{id}      │                  │  SCRIPTING→...     │                 │
  │────────────────────▶│ get()            │  progress update   │                 │
  │◀── {rendering 62%}──│                  │───────────────────▶│ save each stage │
  │ ...poll...          │                  │  VALIDATING→COMPLETED                │
  │ GET /videos/{id}/file               │                    │  video.mp4 ready  │
  │────────────────────────────────────────────────────────────────▶│ serve mp4   │
```

## 2.4 Concurrency & runtime

- `BackgroundTasks + ThreadPoolExecutor(max_workers=2)`. Semaphore 2 render đồng thời, job thứ 3 chờ `QUEUED` → tránh OOM FFmpeg.
- Timeout toàn job 120s → `FAILED/PIPELINE_TIMEOUT`.
- `/ready` checks: ffmpeg binary + tts reachability + disk writable (disk <500MB → not ready).
- Evolution: thay `dispatch()` bằng `celery.send_task("run_pipeline")` — pipeline đã là hàm thuần `run_pipeline(job_id)` nên không sửa logic.
- Python 3.11, FastAPI (>=0.100, Starlette >=0.27 để FileResponse hỗ trợ Range 206) + Pydantic v2, Pillow, imageio-ffmpeg (lấy binary qua `imageio_ffmpeg.get_ffmpeg_exe()`, khỏi cài hệ thống), edge-tts, mutagen (đo duration mp3).
- Không dùng ffprobe: imageio-ffmpeg trên Windows chỉ bundle `ffmpeg.exe`, không có `ffprobe.exe`. Mọi metadata mp4 đo bằng `ffmpeg -i video.mp4` (parse stderr: `Duration:`, `Video: h264`, `Audio: aac`) + mutagen cho mp3.
