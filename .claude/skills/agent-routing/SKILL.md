---
name: agent-routing
description: Use this skill when deciding which subagent should handle a task, routing work between specialists, or reviewing a delegation plan. Triggers on "chọn agent nào", "route task", "delegate cho ai".
---

# Agent Routing: agent cụ thể nhất thắng

## Bảng routing (bộ agent chuẩn của repo này)

- `scout` — research read-only: tìm code, map kiến trúc, điều tra diện rộng.
- `task` — implementation tổng quát: code, debug, multi-step, không specialist nào khớp.
- `reviewer` — review độc lập correctness của change vừa implement.
- `security-reviewer` — phân tích bảo mật read-only, trace source→sink.
- `orchestrator` — điều phối việc phức tạp nhiều bước, không trực tiếp implement nặng.

## Nguyên tắc

- Ưu tiên specialist cụ thể nhất khớp với capability cần. Không khớp ai → `task`.
- Không dùng agent chỉ vì nó tồn tại. Không delegate việc trivial làm trực tiếp được.
- Không giao implementation cho agent read-only (`scout`, `reviewer`, `security-reviewer`).
- Không giao research cho implementation agent khi đã có specialist rảnh.
- Một agent đủ giỏi hơn 2 agent overlap. Song song chỉ khi việc độc lập thật (không ghi cùng file, không chờ nhau).
- Mỗi lần delegate phải trả lời 6 câu: capability gì, agent nào có, đủ tools không, cần context gì, output mong muốn gì, delegate có rẻ hơn tự làm không.
- Không spawn agent mà không có trách nhiệm cụ thể. Không delegate cùng việc 2 lần không lý do.
