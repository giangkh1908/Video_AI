# 03 — API Specification

Base: `http://localhost:8000`. Version: `/api/v1`. JSON. Status chữ thường.

## 3.1 POST /api/v1/videos/requests → 202

```json
// request
{ "concept": "ph-scale", "voice": "en-US-AriaNeural", "idempotency_key": "opt-uuid" }
```
- `concept` enum: `ph-scale | covalent-why | ionic-vs-covalent`. Sai → 400.
- `voice` optional, default `en-US-AriaNeural`.
- `idempotency_key` optional: trùng trong 24h → trả job cũ (không render lại).
- Dedup: cùng concept đang chạy <60s → trả job đó (xem `06-reliability.md` §6.6).

```json
// 202 response
{ "job_id": "v_8f3a...", "status": "queued",
  "poll_url": "/api/v1/jobs/v_8f3a...", "estimated_sec": 25 }
```

## 3.2 GET /api/v1/jobs?status=&concept=&limit=&offset= → 200

```json
{ "total": 3, "limit": 20, "offset": 0,
  "jobs": [
    { "job_id": "v_8f3a...", "concept": "ph-scale", "status": "completed", "progress": 100, "updated_at": "..." }
  ] }
```

## 3.3 GET /api/v1/jobs/{job_id} → 200 | 404

Polling chính. Khi đang chạy:

```json
{ "job_id": "v_8f3a...", "concept": "ph-scale", "status": "rendering",
  "progress": 62, "stage_detail": "rendering scene 3/5", "attempt": 1,
  "fallback_used": false, "error": null, "timings": { "scripting": 0.1 } }
```

## 3.4 GET /api/v1/videos/{job_id} → 200 | 404

View artifact. Luôn 200 khi job tồn tại (kể cả chưa xong) để client poll cùng envelope:

```json
// khi đang render — artifacts: null, client poll tiếp qua poll_url
{
  "job_id": "v_8f3a...", "concept": "ph-scale", "status": "rendering", "progress": 62,
  "fallback_used": false, "audio_degraded": false,
  "artifacts": null,
  "poll_url": "/api/v1/jobs/v_8f3a...",
  "error": null
}
```

Metadata + artifact + cost + script khi completed (chứng minh khớp query):

```json
{
  "job_id": "v_8f3a...", "concept": "ph-scale", "status": "completed", "progress": 100,
  "fallback_used": false, "audio_degraded": false,
  "artifacts": {
    "video_url": "/api/v1/videos/v_8f3a.../file",
    "duration_seconds": 32.5, "file_size_bytes": 2458120, "mime_type": "video/mp4"
  },
  "cost_breakdown": { "estimated_usd": 0.0, "provider_script": "template", "provider_tts": "edge-tts" },
  "script": { "title": "...", "scenes": [ { "id": "s1", "title": "..." } ] },
  "error": null
}
```

Failed vẫn 200 với envelope:

```json
{ "status": "failed",
  "error": { "code": "TTS_FAILED", "message": "Edge-TTS unreachable after 2 retries",
             "retryable": true, "failed_stage": "narrating" } }
```

## 3.5 GET /api/v1/videos/{job_id}/file → 200 | 206 | 404 | 409

Serve bằng `FileResponse(path, media_type="video/mp4")` — Starlette >=0.27 (FastAPI >=0.100, pin trong requirements.txt) đã tự hỗ trợ `Accept-Ranges: bytes` và 206 Partial Content, không viết custom byte generator.
- Có `Range: bytes=` → 206 để tua trên browser.
- Job tồn tại nhưng chưa completed → `409 { code: ARTIFACT_NOT_READY }` (phân biệt với 404 job không tồn tại).
- Verify: `curl -H "Range: bytes=0-1023" -i .../file` phải thấy 206.

## 3.6 POST /api/v1/jobs/{job_id}/retry → 202 | 404 | 409

Chỉ khi `status=failed` và `retryable=true` và `attempt<3`. Chuyển về `queued`.

## 3.7 GET /health, GET /ready

- `/health` → `{ "ok": true }` (liveness).
- `/ready` → `{ "ffmpeg": true, "tts": true, "disk_free_mb": 1234 }`; fail nếu thiếu ffmpeg binary hoặc disk <500MB.

## 3.8 Errors — 2 namespaces riêng

**A. HTTP errors (request-level, trả HTTPException, không lưu vào Job):**

| HTTP | code | Khi nào |
|---|---|---|
| 400 | UNSUPPORTED_CONCEPT | concept ngoài enum, kèm `hint: [...]` |
| 400 | INVALID_REQUEST | thiếu field, Pydantic fail |
| 404 | JOB_NOT_FOUND | sai job_id |
| 409 | ARTIFACT_NOT_READY | job tồn tại nhưng file chưa xong (chỉ ở `GET .../file`) |
| 409 | RETRY_NOT_ALLOWED | job chưa fail / hết attempt |
| 500 | INTERNAL | không bao giờ lộ stacktrace |

**B. Job Execution errors (`ErrorInfo.code` trong Job record, trả HTTP 200 envelope `{status: failed}`):**
`SCRIPT_INVALID, TTS_FAILED, RENDER_FAILED, COMPOSE_FAILED, QA_REJECTED, PIPELINE_TIMEOUT`.
Chi tiết thresholds xem `06-reliability.md` §6.5. Khi code: đặt 2 Enum riêng `HttpErrorCode` vs `JobErrorCode` trong `routes.py` / `job_service.py` để tránh nhầm.

## 3.9 Curl demo

```bash
curl -X POST http://localhost:8000/api/v1/videos/requests \
  -H "Content-Type: application/json" -d '{"concept":"ph-scale"}'
curl http://localhost:8000/api/v1/jobs/v_8f3a...
curl "http://localhost:8000/api/v1/jobs?status=completed&limit=10"
curl http://localhost:8000/api/v1/videos/v_8f3a...
curl -O http://localhost:8000/api/v1/videos/v_8f3a.../file
```
