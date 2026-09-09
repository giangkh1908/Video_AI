# Code Smells: triệu chứng → tên bệnh → hành động

Ngưỡng là tín hiệu nghi ngờ, không phải luật.

| Triệu chứng | Tên bệnh | Hành động |
|---|---|---|
| Đọc 3 file mới hiểu 1 hàm | Temporal coupling / middle man | Đưa quyết định về gần dữ liệu nó tác động |
| Sửa 1 requirement chạm 5 file | Shotgun surgery | Gom quyết định về 1 chỗ duy nhất |
| Hàm 3 dòng tên `getData()` trả 4 thứ | Shallow module | Gộp lại hoặc cho hợp đồng thật |
| `render(doc, true, false, 3)` | Flag arguments | Parameter object hoặc tách hàm theo biến thể |
| 2 chỗ giống nhau, định gộp | Trừu tượng sớm | Đợi lần thứ 3; check có đổi cùng lý do không |
| 2 chỗ khác nhau nhưng sửa cùng lúc | Trùng lặp thật | Gộp về 1 nguồn dù hình thức khác nhau |
| `utils.js` 800 hàm | Module không tên miền | Chia theo concept |
| if/else lồng ≥3 | Điều kiện chồng chất | Guard clause, predicate có tên, dispatch table |
| Comment diễn lại code | Comment thừa | Xóa; sửa code tới mức tự kể |
| Comment "đừng sửa chỗ này" | Hợp đồng không ai enforce | Viết test khóa bất biến đó |
| try/catch rỗng | Nuốt lỗi | Đặt tên thứ bị nuốt + lý do, hoặc để nổ |
| Magic value lặp nhiều file | 1 quyết định nhiều chủ | 1 hằng số có owner + nguồn (spec/RFC/issue) |
| Hàm `checkX()` có ghi file | Command-query violation | Tách `isX()` đọc / `ensureX()` ghi |
| PR 2000 dòng refactor + feature | Diff không đọc được | Tách commit: refactor thuần / behavior change |
| Không viết được test | Thiếu seam | DI / parameterise thứ đang hardcode |

## Đo thay vì cãi

```sh
git log --since=6.month --name-only --pretty=format: | sort | uniq -c | sort -rn | head -30
```

Ngưỡng nghi ngờ hay dùng: nest ≥3, >4 tham số, >1 file cho 1 quyết định, >1 màn hình cho 1 luồng đọc.
Ngưỡng không đáng tin: số dòng hàm/file, số class, "mọi thứ phải có interface".

## Khi không làm gì thêm

Code đúng, có test, không nằm trên đường task — chỉ "có thể khác đi" thì không đổi.
