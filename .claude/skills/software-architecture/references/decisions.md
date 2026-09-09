# Khi nào dùng pattern nào

Mỗi dòng: **chỉ dùng khi có triệu chứng đo được**. Không triệu chứng = chưa có vấn đề.

| Pattern | Chỉ dùng khi | Trả giá | Sai lầm phổ biến |
|---|---|---|---|
| Modular monolith | Mặc định mọi hệ mới | Enforce boundary bằng build | "Modular" chỉ là folder |
| Extract service | Cần cycle/deploy/scaling/ownership riêng + ops maturity | Network, eventual consistency | Tách theo org chart |
| API gateway | Nhiều client, cần auth/rate-limit 1 chỗ | Single point phải SRE-grade | Nhét business logic vào gateway |
| CQRS-lite | Query cần shape/index khác write | Sync 2 model | Bê full event sourcing cho CRUD |
| Event sourcing | Cần audit log thật / replay / temporal query | Snapshot, versioning event | Dùng vì "nghe hiện đại" |
| Transactional outbox | "Sửa DB + phát event" phải nguyên tử | Worker relay + consumer idempotent | 2PC tự chế |
| Saga | Workflow nhiều bước nhiều service, có bù trừ | Compensation complexity | Choreography cho logic rẽ nhánh phức tạp |
| Cache | Bottleneck đọc đo được + chịu stale | Invalidation, 2 nguồn sự thật | Cache trước khi đo |
| Circuit breaker | Dependency ngoài có thể chết | Cần fallback thật | Breaker không fallback |
| Retry + budget | Client gọi service autoscale | Burst nhân tải lúc sự cố | Retry 3 lần ở 5 tầng |
| Expand/contract | Mọi schema/API change nhiều version cùng chạy | Tồn tại 2 hình dạng 1 thời gian | ALTER phá binary cũ |
| Strangler fig | Thay hệ lớn đang chạy | 2 hệ song song + routing | Big-bang rewrite |
| Idempotency key | Mọi chỗ retry / user bấm đúp | Store key + response cũ | Không lock → race |

## Ba câu hỏi khi bị đề xuất công nghệ mới

1. Nó giải quyết triệu chứng đo được nào hôm nay?
2. Failure mode của nó, team đã vận hành lúc 3h sáng được chưa?
3. Bỏ nó thì tốn bao nhiêu — có giải pháp boring nào <20% chi phí?

## Design review: 8 câu bắt trả lời được

1. Quality attribute nào bắt buộc bằng số?
2. Dependency ngoài nào giết được hệ? Chết kiểu gì?
3. Rollback quyết định này tốn bao nhiêu?
4. Boundary nào enforce bằng máy, không bằng ý thức?
5. Chỗ nào dễ đổi nhất — quyết định đã đặt ở đó chưa?
6. Dữ liệu nào có 2 bản sao — ai thắng khi lệch?
7. On-call debug bằng dashboard/trace/log nào cụ thể?
8. Traffic ×10 cái gì gãy trước? ×100?
