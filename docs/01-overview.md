# 01 — Overview & Scope

## 1.1 Bối cảnh sản phẩm

Growtrics xây dựng trải nghiệm học tập AI-native. Slice đầu tiên là **backend video request service** cho môn Hóa học:

- Learner gửi concept cần giải thích.
- Backend xử lý như **video-generation job bất đồng bộ** (không cần instant, latency 15–30s chấp nhận được).
- Client poll trạng thái, khi xong tải/mở MP4 có **hình + tiếng** như video giáo dục ngắn bình thường.

Không frontend. Demo bằng curl / Postman / Swagger UI.

## 1.2 Scope bắt buộc (3 queries)

| Concept ID | Learner query | Mục tiêu giáo dục |
|---|---|---|
| `ph-scale` | How does the pH scale work? | Hiểu thang 0–14 đo nồng độ H+/OH-, mốc 7 trung tính, log 10x |
| `covalent-why` | Why do atoms form covalent bonds? | Hiểu nguyên tử share electron để đạt octet bền + giảm thế năng |
| `ionic-vs-covalent` | What is the difference between ionic and covalent bonding? | Phân biệt cho-nhận (metal+non-metal, NaCl) vs dùng chung (non-metal+non-metal, H2O) |

Ngoài 3 concept → `400 UNSUPPORTED_CONCEPT`. Không nhận topic tự do (quyết định reliability, xem §06).

## 1.3 Design Pillars

1. **Reliability under Non-determinism** — mọi điểm chạm LLM/media đều có gate, retry, fallback.
2. **Cost-Quality Pareto** — đẹp nhất ở giá rẻ nhất: Template/LLM-structured + Edge-TTS free + Pillow + FFmpeg → $0–0.001/video.
3. **Clean Boundaries (Hexagonal)** — API / Job Engine / Providers / Store tách rời, thay provider bằng env.
4. **Zero-Flaky Repeatability** — 10/10 runs pass, không treo, không video hỏng.

## 1.4 Non-goals

Không auth, không DB thật, không Celery/Redis, không diffusion photoreal (Sora/Runway), không websocket/webhook, không frontend.

## 1.5 Thành công đo bằng gì

- 3 queries chạy end-to-end qua curl, ra MP4 xem được, nội dung khớp query.
- Cùng concept request 3 lần → 3 video đều pass QA.
- Code <30 files, boundary rõ, README giải thích được cost + chỗ cắm provider thật.
