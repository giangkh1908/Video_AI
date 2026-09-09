---
name: task-decomposition
description: Use this skill when breaking a complex request into executable subtasks, planning multi-step work, or delegating to subagents. Triggers on "plan this task", "break down", "chia nhỏ task", "lập kế hoạch thực hiện".
---

# Task Decomposition: tách để thực thi, không tách để mô tả

Mục tiêu duy nhất: biến 1 yêu cầu phức tạp thành tập **nhỏ nhất** các task có thể thực hiện độc lập.

## Nguyên tắc

- Hiểu mục tiêu thật của user trước khi tách. Phân biệt requirement với assumption tự thêm.
- Tách investigation khỏi implementation. Task nào cần đọc code trước thì là task research riêng.
- Mỗi task phải độc lập hiểu được: không task nào chỉ nhắc lại task cha.
- Ít task meaningful hơn nhiều task vụn. Việc nhỏ làm trực tiếp, đừng delegate.
- Mỗi task ghi rõ dependency và output kỳ vọng; không có dependency thì mới chạy song song được.

## Thủ tục

1. Xác định outcome cuối cùng + tiêu chí nghiệm thu (cái gì đo được khi xong).
2. Trích requirements, constraints显式; liệt kê unknowns cần investigation.
3. Tách thành tasks, mỗi task định nghĩa:
   - Objective (1 câu, động từ hành động)
   - Scope (file/module chạm vào + explicitly out-of-scope)
   - Context liên quan (file, quyết định trước — không forward cả conversation)
   - Dependencies (task nào phải xong trước)
   - Expected output (files đổi + báo cáo gì)
   - Verification (chạy test/lệnh gì để chứng minh xong)
4. Xóa task trùng lặp hoặc không có mục đích cụ thể.
5. Sắp xếp thứ tự thực thi, đánh dấu cặp nào chạy song song được (không overlap file ghi).

## Anti-pattern

- Outline khái niệm thay vì task thực thi được.
- Subtask không output ("tìm hiểu thêm về X" mà không nói tìm để trả lời câu nào).
- Chia song song 2 task cùng ghi 1 file.
