# 07 — Cost & Quality Analysis

## 7.1 Lựa chọn đã chốt: Modular Composite (Template + Pillow + Edge-TTS + FFmpeg)

| Hướng | Visual | Cost/30s video | Reliability/tốc độ | Quyết định |
|---|---|---|---|---|
| Video Gen AI (Runway/Sora/Luma) | Điện ảnh nhưng text/công thức méo | $0.5–2 | Thấp (3–5p, fail cao) | ❌ Loại: đắt + sai khoa học |
| Code-based Manim pure | Đẹp 3Blue1Brown | ~$0.001 (LLM) | Trung bình (dễ lỗi syntax runtime) | ⚠️ Không cho auto-pipeline |
| **Modular Composite (chọn)** | Diagrams sắc nét + voice tự nhiên + fade | **$0–0.001** | **Rất cao (>99.5%, <25s)** | ✅ |

## 7.2 Unit cost breakdown

| Hạng mục | Tài nguyên | Đơn giá | Cost/video |
|---|---|---|---|
| LLM script (chỉ khi `SCRIPT_PROVIDER=llm`) | ~800 in + 400 out (gpt-4o-mini) | $0.15/1M in, $0.60/1M out | ~$0.00036 |
| Fact validation | regex local | free | $0 |
| TTS Edge-TTS (~80 words) | neural voice | free | $0 |
| Pillow render (~0.5s CPU) | local | — | ~$0.00010 |
| FFmpeg compose (~3s CPU) | local | — | ~$0.00050 |
| **Tổng default (template)** | | | **$0** |
| **Tổng LLM opt-in** | | | **~$0.001** |

> Scale 100k videos/tháng: default ~$0 tiền provider (chỉ điện máy), LLM opt-in ~$96.

## 7.3 Tối ưu đã áp

- Cache audio theo `sha1(narration+voice)` + cache script theo concept → request trùng không tốn gì.
- `thumb.jpg` từ frame giữa để list nhanh, không cần đọc mp4.
- Cap duration 28–45s + 24fps 720p: đủ rõ trên mobile, file <10MB, render nhanh.
- Template-first: 99% traffic không chạm LLM bill.

## 7.4 Upgrade path (khi có tiền)

Template → LLM script (+$0.0004, đa dạng lời thoại) → ElevenLabs (+$0.05, giọng hay hơn) → Sora scenes (+$0.5–2, photoreal). Mỗi bước chỉ thay 1 provider file, API/job/QA giữ nguyên.
