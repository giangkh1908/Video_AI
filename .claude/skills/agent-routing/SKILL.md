---
name: agent-routing
description: Use this skill when deciding which subagent should handle a task, routing work between specialists, or reviewing a delegation plan. Triggers on "chọn agent nào", "route task", "delegate cho ai".
---

# Agent Routing: agent cụ thể nhất thắng

## Bảng routing (bộ agent chuẩn của repo này)

- `scout` — research read-only: tìm code, map kiến trúc, điều tra diện rộng.
- `task` — worker duy nhất orchestrator được spawn, với 4 roles: PROPOSE (ra ý tưởng độc lập), CRITIQUE (chấm bài peer, chốt CONCEDE/HOLD), MERGE (chốt 1 final plan), IMPLEMENT (code, debug, multi-step + tự gọi reviewer trước khi trả).
- `reviewer` — review độc lập correctness của change vừa implement.
- `security-reviewer` — phân tích bảo mật read-only, trace source→sink.
- `orchestrator` — CHỈ điều phối `task` (roles PROPOSE/CRITIQUE/MERGE/IMPLEMENT), không spawn specialist trực tiếp, không trực tiếp implement nặng.

## Nguyên tắc

- Ưu tiên specialist cụ thể nhất khớp với capability cần. Không khớp ai → `task`.
- Không dùng agent chỉ vì nó tồn tại. Không delegate việc trivial làm trực tiếp được.
- Không giao implementation cho agent read-only (`scout`, `reviewer`, `security-reviewer`).
- Không giao research cho implementation agent khi đã có specialist rảnh.
- Một agent đủ giỏi hơn 2 agent overlap — NGOẠI LỆ: debate ý tưởng luôn cần 2 `task` PROPOSE độc lập + cross-CRITIQUE (đây là thiết kế, không phải overlap thừa). Song song chỉ khi việc độc lập thật (không ghi cùng file, không chờ nhau).
- Mỗi lần delegate phải trả lời 6 câu: capability gì, agent nào có, đủ tools không, cần context gì, output mong muốn gì, delegate có rẻ hơn tự làm không.
- Mỗi delegation cho `task` phải ghi rõ Role (PROPOSE / CRITIQUE / MERGE / IMPLEMENT + round).
- Không spawn agent mà không có trách nhiệm cụ thể. Không delegate cùng việc 2 lần không lý do.
