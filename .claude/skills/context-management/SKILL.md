---
name: context-management
description: Use this skill when managing context budgets, handing off between agents, compacting long sessions, or deciding what information to keep vs discard. Triggers on "context đầy", "handoff", "compact", "tóm tắt session".
---

# Context Management: context là tài nguyên hữu hạn

## Ngân sách

Coi context window là tài nguyên tốn kém, hiệu năng thoái hóa khi phình (context rot). Đừng cố dùng hết budget chỉ vì còn chỗ.

Giữ lại: requirements, constraints, decisions, architecture, files đã đổi, errors, test results, agent findings, unresolved issues.

Vứt/tóm tắt: giải thích lặp, tool transcripts, nội dung file dư thừa, quyết định đã bị thay thế, kết quả điều tra không liên quan, output lớn tóm được bằng findings ngắn.

## Handoff (giao việc cho agent khác)

Chỉ truyền context đủ để làm task, không forward nguyên conversation. Một handoff gồm: Objective, Scope, findings liên quan, files liên quan, constraints, decisions trước đó, expected output, verification. Ưu tiên structured summary + file:line refs hơn paste nguyên file.

## Compaction (khi context gần đầy)

Trước khi compact, giữ lại 8 thứ: objective hiện tại, requirements, decisions quan trọng, kiến trúc liên quan, files đã đổi, verification status, outstanding problems, next actions.

Tuyệt đối không tóm tắt mất requirements, constraints, failures, unresolved issues. Dùng structured summary, không prose dài.

## Critical

Nén context không được làm mất thông tin quyết định. Thà compact sớm giữ 8 mục trên còn hơn để tràn rồi mất dấu.
