---
name: execution-planning
description: Use this skill when ordering multi-agent work, deciding sequential vs parallel execution, setting verification points, or handling agent failures. Triggers on "thứ tự chạy", "parallel hay sequential", "xử lý khi agent fail".
---

# Execution Planning: tối ưu cho xong việc, không tối ưu cho đông agent

## Lập plan

Xác định: tasks, dependencies, việc độc lập, specialist cần, điểm verify, điểm có thể fail.

## Song song

- Chỉ chạy song song task điều tra độc lập (VD: `scout` map kiến trúc + `scout` tìm feature tương tự → rồi mới implement).
- Không song song task có dependency chưa resolve. Không song song 2 task ghi cùng cây file (trừ khi có worktree/isolated workspace).
- Mặc định sequential khi tasks overlap file hoặc phụ thuộc output của nhau.

## Verify

Pipeline chuẩn cho việc implementation quan trọng:

```
investigate → implement → verify (test/build) → review → fix → final verification
```

Việc trivial bỏ bớt phase. Không coi message "done" của agent là verify — phải thấy test/lệnh chạy thật.

## Failure handling

1. Phân loại fail: môi trường, thiếu thông tin, hay implementation sai.
2. Chỉ retry khi khả năng recover được; đổi strategy khi retry 2 lần không thêm thông tin.
3. Đổi specialist khi agent hiện tại thiếu capability.
4. Giữ findings hữu ích từ attempt fail. Báo blocker trung thực khi không xong.

## Critical

Tránh delegation thừa, thực thi nối tiếp không cần thiết, và điều tra lặp lại. Thành công = task xong + verified, không phải số agent đã spawn.
