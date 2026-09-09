---
name: clean-code
description: Use this skill when writing, modifying, reviewing, or refactoring source code in any language — naming, function boundaries, error handling, comments, abstraction choices, or module simplification. Triggers on "code này messy", "viết lại cho sạch", "review code", "refactor".
---

# Clean Code: giảm chi phí đọc và chi phí thay đổi

Mọi quy tắc dưới đây là phương tiện. Quy tắc nào làm 2 chi phí trên tăng thì bỏ.

## Ba câu lọc (chạy trước mọi quy tắc)

1. Người đọc tiếp theo có phải mở file khác / nhớ thứ không nằm ở đây mới hiểu không? → có = complexity ẩn, sửa.
2. Đổi đoạn này có buộc sửa nơi khác không? → có = information leakage, siết boundary.
3. Code đọc nhiều : sửa ít (parser, mapper, log format)? → chấp nhận hơi cryptic nếu có comment trỏ spec.

## Naming

- Tên nói **nó tồn tại để làm gì**, không phải nó là loại gì. Độ dài tỉ lệ scope.
- Cấm Hungarian (`m_`, `kFoo`), cấm hậu tố rỗng (`data`, `manager`, `utils`, `processor`).
- Bool đọc như khẳng định: `isReady`, `hasVoucher`. `temp`/`result` chỉ trong hàm ≤5 dòng.

## Function

- Ngắn theo nghĩa đọc hết 1 màn hình không cần cuộn để tin nó. Đừng chia để đạt số dòng.
- 0–2 tham số chuẩn; ≥3 thì hỏi "chúng có luôn đi cùng nhau không" → gom thành 1 kiểu.
- Flag argument là smell: tách `renderPlain`/`renderRich`, trừ khi 2 nhánh thật sự rối nhau.
- Không trộn 2 tầng trừu tượng trong 1 hàm. Guard clause thay vì lồng if (nest ≥3 = thiếu hàm).
- Quy tắc ba lần: trừu tượng hóa ở lần trùng thứ **ba**. DRY là về kiến thức quyết định, không phải text giống nhau.

## Comment

Chỉ viết thứ code không tự nói được, theo thứ tự: **vì sao** (trade-off + issue/ADR) → bất biến + hậu quả vi phạm → hợp đồng ẩn (owner, đơn vị, format, thứ tự chạy, nguồn hằng số) → side effect → TODO có chủ (`TODO(name, #id)`).
Không viết: diễn lại từng dòng, ASCII divider, code comment-out, `@author`, xin lỗi cho code mù mờ.

## Lỗi và state

- Fail fast với message nêu input + hợp đồng vi phạm + hệ quả. Không nuốt exception (buộc nuốt thì đặt tên thứ bị nuốt + lý do).
- Lỗi kỳ vọng → trả về giá trị; lỗi lập trình → ném. Không dùng exception điều khiển luồng.
- Tránh null ở API boundary. Immutable mặc định. Ghép thao tác phụ thuộc thời gian vào 1 hàm (diệt temporal coupling).

## Layout và module

- Package theo feature, không theo layer. Module sâu (interface nhỏ, hành vi nhiều).
- Không cho 2 module cùng biết 1 chi tiết nếu 1 bên không cần. File 1000 dòng của 1 khái niệm > 12 file vụn.

## Khi nào được phớt lờ

- Style guide repo thắng mọi quy tắc ở đây. Formatter/linter/CI lo thì không dạy lại.
- Code throwaway viết thẳng nhưng **đánh dấu**. Hot path khó đọc được nếu có comment trỏ benchmark.
- Không áp gu cá nhân lên file không liên quan task. Diff trộn refactor + behavior change → tách commit.

## Quy trình sửa code có sẵn

1. Khóa hành vi bằng test trước (characterization test, kể cả khi hành vi đang sai).
2. Sửa ở điểm gần nhất chứa quyết định đó. Một commit một chiều: hoặc refactor hoặc đổi hành vi.
3. Xóa code chết khi có bằng chứng (hết reference + CI xanh).

Chi tiết: [references/code-smells.md](references/code-smells.md)
