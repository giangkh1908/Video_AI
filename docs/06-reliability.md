# 06 — Reliability: Gates, Invariants, QA, Failures

Mục tiêu: 10/10 runs pass. Không tin LLM, validate trước khi tốn render.

## 6.1 Gate 1 — Schema & Auto-Repair (scripting)

- Strip ```json fences, trailing commas → `json.loads` → Pydantic strict parse thành ScriptIR.
- Fail → retry LLM tối đa 2 lần, backoff 1s/2s, prompt kèm `str(ValidationError)` để self-correct.
- Vẫn fail → fallback `CanonicalTemplate` (biên tập tay, pass 100%), set `fallback_used=true`, log warn. Job tiếp tục, không fail.

## 6.2 Gate 2 — Fact Invariants (`domain/invariants.py`)

Check case-insensitive trên `narration + bullets` join:

- **ph-scale:** phải có range token (`0-14`/`0 to 14`/`0–14` — bare `0` + `14` rời nhau không tính), và (`7` hoặc `neutral`), và (`acid` hoặc `< 7`/`below 7`), và (`base`/`alkaline` hoặc `> 7`/`above 7`), và (`H+`/`H＋`/`hydrogen`) VÀ (`OH-`/`hydroxide`) (cả hai họ H/OH đều bắt buộc).
- **covalent-why:** phải có (`share`/`shared`/`sharing` VÀ `electron*`), và (`octet` hoặc `8 electrons`/`eight electrons`), và (`non-metal`/`nonmetal`), và (`stab`/`stable`/`stability` hoặc `energy`/`lower energy`).
- **ionic-vs-covalent:** phải có ((transfer-family) VÀ (shar-family)) VÀ ((ionic-pair) VÀ (covalent-pair)), trong đó transfer-family = (`transfer`/`donat`/`give`+`take`/`cation`+`anion`), shar-family = (`shar*`), ionic-pair = (bare `metal` khớp regex word-boundary `(?<!\w)(?<!non-)metal(?!\w)` + `non-metal`), covalent-pair = (`non-metal` + `non-metal` hoặc `both non-metal`). Bare `metal` nằm trong `non-metal` không tính.

Thiếu → reject script trước khi gọi TTS/render (tiết kiệm cost). LLM path retry, template path luôn pass (test `test_invariants.py` enforce).

## 6.3 Gate 3 — A/V Alignment (narrating)

- Đo `audio_sec` thực per scene bằng `mutagen` (`MP3(path).info.length`), không ước lượng chay.
- `scene_sec_final = clamp(audio_sec + 0.5 pad, 5.0, 9.0)`. Tổng ép 28–45s (nếu lệch, scale đều các scene).
- Render đúng số frames = `scene_sec_final × 24fps` → audio không bao giờ lệch hình.

## 6.4 Gate 4 — Artifact Integrity (validating, `qa_gate.py`)

Fail bất kỳ → `QA_REJECTED` (retryable) → retry pipeline 1 lần → vẫn fail → FAILED.

| Check | Threshold | Bằng gì (xem 02-architecture §2.4) |
|---|---|---|
| File tồn tại + size | >200KB | `os.path.getsize` |
| Duration | 25–60s | `ffmpeg -i` parse stderr `Duration:` |
| Audio stream | `has_audio_stream == true` | `ffmpeg -i` parse stderr `Audio: aac` + mutagen cross-check |
| Frame không đen/trắng | sample 3 frames/scene, mean brightness 15–240 | Pillow `ImageStat` |
| Text không tràn | `textbbox` width <90% canvas | Pillow `draw.textbbox` |
| Codec | video H.264, audio AAC, container mp4 | `ffmpeg -i` parse stderr `Video: h264` / `Audio: aac` |

## 6.5 Failure taxonomy (không stacktrace ra client)

Job Execution codes (namespace riêng với HTTP errors ở 03-api-spec §3.8):
`SCRIPT_INVALID, TTS_FAILED, RENDER_FAILED, COMPOSE_FAILED, QA_REJECTED, PIPELINE_TIMEOUT`.
(HTTP errors `UNSUPPORTED_CONCEPT, INVALID_REQUEST, JOB_NOT_FOUND, ARTIFACT_NOT_READY, RETRY_NOT_ALLOWED` không lưu vào Job.)

Mỗi FAILED có `{ code, message, retryable, failed_stage }`. Retryable=true → client được gọi retry (attempt<3). Timeout job 120s. Worker crash → BG task catch → FAILED chứ không treo `processing`.

## 6.6 Anti-flaky bổ sung

- `seed = hash(concept)` cho mọi jitter (vị trí dots, fade offset) → cùng concept cùng skeleton.
- Idempotency key 24h + dedup job đang chạy <60s → chống spam render trùng.
- `test_repeatability.py`: loop 10 lần × 3 concepts, assert pass Gate 4 + fact invariants mỗi lần.
