---
name: ai-application
description: Use this skill when building or modifying LLM-backed features — prompt design, RAG/retrieval pipelines, agent context management, tool design, evals, hallucination or prompt-injection handling, model routing. Triggers on "RAG", "chatbot", "agent", "vector DB", "prompt", "eval model".
---

# AI Application: đơn giản trước, đo rồi mới thêm

Nguồn chuẩn: Anthropic *Building effective agents* — hệ thành công nhất dùng pattern đơn giản ghép được. Thêm tầng nào phải chứng minh bằng eval, không bằng cảm giác.

## Chọn hình thái: 4 nấc từ thấp lên

| Nấc | Dùng khi |
|---|---|
| Prompt tốt + few-shot | Kiến thức nằm trong model hoặc input user đưa |
| Long context + prompt caching | Kho < ~200K token, cần nhanh-rẻ (cache giảm cost tới ~90%) |
| RAG | Kho lớn hơn context, cần freshness / permission / citation |
| Fine-tune | Cần output shape/style ổn định (không phải để nhồi kiến thức — kiến thức thì RAG rẻ hơn) |

Agent (model tự quyết bước tiếp) chỉ khi **không đoán được số bước**. Luồng cố định → workflow code path định sẵn: rẻ, nhanh, debug được.

## Pipeline retrieval (thứ tự ưu tiên đã đo)

1. Chunk theo cấu trúc (heading/paragraph, giữ nguyên bảng + code block), 256–1024 token + overlap 10–20%. Không có size universal — đo trên eval của bạn.
2. Hybrid vector + BM25 (embedding bắt ngữ nghĩa, BM25 bắt identifier chính xác: mã lỗi, tên hàm, ID).
3. Rank fusion (RRF) + dedup. Contextual retrieval (prepend 50–100 token ngữ cảnh/chunk): −49% failed retrieval, ~$1/1M tokens.
4. Rerank top ~150 → 20: −67% failed retrieval, đổi latency lấy chất lượng. Top-K đưa vào prompt: 20 > 10 > 5, nhưng đo điểm bão hòa (lost in the middle).

## Prompt và tool (ACI)

- Tách data khỏi instruction bằng delimiter (`<document>`), ép trích nguồn từng khẳng định, cho phép trả lời "không có trong tài liệu".
- Tool design quan trọng hơn prompt: ít tool, tên + tham số tự giải thích, format gần tự nhiên (tránh bắt model đếm dòng/escape), lỗi trả về phải dạy cách sửa, side effect phải idempotent hoặc confirm.
- Context rot: compaction giữ decisions/constraints, note-taking ra file, sub-agent context riêng (~50K sạch/hướng), just-in-time retrieval bằng identifier.

## Eval và failure mode

- Không eval = không engineering. Golden set 20–50 câu hỏi thật + đáp án + nguồn. Tách metric retrieval (recall@k, MRR) khỏi generation (faithfulness, relevancy). LLM-judge có bias — randomise thứ tự, pairwise, hiệu chỉnh bằng người.
- Failure mode gặp là sửa ngay: retrieve top-K cả khi không có gì liên quan (thêm ngưỡng + lối "tôi không biết"), chunk cắt mất ngữ cảnh, semantic mù identifier (thêm BM25), index stale (`updated_at`), lọc ACL sau retrieve (phải pre-filter), prompt injection qua tài liệu (coi retrieved text là data, không phải instruction).
