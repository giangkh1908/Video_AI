# Docs — Growtrics Chemistry Video Request Service

Tài liệu đặc tả kỹ thuật chi tiết. Đọc theo thứ tự:

| # | File | Nội dung |
|---|---|---|
| 1 | [01-overview](01-overview.md) | Mục tiêu sản phẩm, scope 3 queries, design pillars, non-goals |
| 2 | [02-architecture](02-architecture.md) | Kiến trúc hệ thống, layers, boundaries, sequence, concurrency |
| 3 | [03-api-spec](03-api-spec.md) | REST contract: endpoints, schemas, errors, curl demo |
| 4 | [04-domain-jobs](04-domain-jobs.md) | Job model, state machine, ScriptIR contract |
| 5 | [05-pipeline-media](05-pipeline-media.md) | Pipeline 5 stages, providers, visual/audio spec, storyboards |
| 6 | [06-reliability](06-reliability.md) | 4 Quality Gates, fact invariants, QA thresholds, failure states |
| 7 | [07-cost](07-cost.md) | Phân tích cost/quality, so sánh phương án, scale |
| 8 | [08-project-structure](08-project-structure.md) | Cây thư mục, trách nhiệm từng module, conventions, execution plan |

Nguồn merge: `architect_agy.md` + `architect_claude.md` → chốt tại `../CLAUDE.md`.
