---
name: software-architecture
description: Use this skill when choosing or changing system architecture — monolith vs services, module boundaries, data consistency, API contracts, retries, migrations, observability, or writing ADRs. Triggers on "thiết kế kiến trúc", "tách service", "viết ADR", "chọn tech".
---

# Software Architecture: quyết định đắt thì thiết kế kỹ, còn lại sửa tuỳ ý

Kiến trúc = những quyết định **tốn kém để thay đổi**. Việc của skill này là nhận ra quyết định nào thuộc nhóm đó.

## Trước khi chọn

- Phân loại cửa 1 chiều / 2 chiều: 2 chiều → quyết nhanh, phủ quyết bằng quyết định sau; 1 chiều → ADR + cân nhắc công khai.
- Đếm innovation tokens: mỗi hệ chịu được ~3 lựa chọn non trẻ. Còn lại dùng boring tech vì failure mode đã biết.
- Viết quality attribute thành số trước (p99, throughput, RTO/RPO, team mấy người). Không số = chưa có yêu cầu.
- Đừng thiết kế cho quy mô chưa có. Đa số hệ không bao giờ chạm giới hạn distributed giải quyết, nhưng trả chi phí vận hành ngay ngày đầu.

## Monolith hay distributed

Mặc định: **modular monolith**, tách khi đo thấy đau. Điều kiện cần trước service riêng: provision server trong vài giờ, deploy pipeline vài giờ, đã có monitoring + alerting, team chịu trách nhiệm end-to-end. Thiếu 1 trong 4 → microservices phóng đại vấn đề thành khủng hoảng.
Dấu hiệu tách 1 phần: xung đột deploy, khác scaling, khác owner, cần isolation lỗi. Mỗi lần tách phải mua được 1 trong đó.

## Ranh giới và phụ thuộc

- Vẽ trước khi code (context map / C4 mức 2). Không bản vẽ = không biết ranh giới nào bị xuyên.
- Chiều phụ thuộc 1 hướng vào domain core; domain không import framework/DB/HTTP.
- Boundary là chỗ dữ liệu đi qua, không phải chỗ có folder. Enforce bằng build (import lint), không trông chờ review.
- Đã distributed thì DB riêng mỗi service. Shared schema = distributed monolith.

## Dữ liệu và consistency

- Một nguồn sự thật cho mỗi dữ liệu; bản sao khai báo độ trễ tối đa + ai sửa khi lệch.
- Idempotency key ở mọi chỗ có retry. At-least-once + idempotent handler là mặc định thực tế.
- Eventual consistency phải đặt tên ở API (endpoint nào stale, bao lâu).
- Migration không downtime: expand/contract (thêm mới → viết cả hai → backfill → đọc mới → dọn cũ).
- Retry chỉ cho idempotent request, có jitter + retry budget. Timeout ở caller ngắn hơn SLA callee.

## Hợp đồng và vận hành

- API có consumer là hợp đồng 1 chiều: thêm field an toàn, đổi/xóa cần cycle + deprecation.
- Lỗi theo chuẩn máy đọc ổn định (RFC 9457 Problem Details).
- SLO/error budget trước khi thêm tính năng reliability. Alert không runbook thì tắt.
- Graceful shutdown là 1 feature. Dependency ngoài nào chết cũng phải trả lời được: hệ chết kiểu gì, user thấy gì.

## Diễn tiến hệ cũ

- Thay hệ lớn: strangler fig từng slice + kill-switch, không big-bang.
- Rewrite mặc định là không (mất tri thức bug-fix tích lũy). Chỉ khi: có test suite đáng tin của hệ cũ + hệ cũ không vá được + cam kết đóng băng tính năng.
- Quyết định 1 chiều → ADR (Context số liệu / Decision 1 câu / Consequences được-mất). ADR chỉ bị thay bằng ADR mới, không sửa lịch sử.

Chi tiết pattern: [references/decisions.md](references/decisions.md)
