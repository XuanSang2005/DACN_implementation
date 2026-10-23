# Mục lục bằng chứng

Trạng thái hiện hành 23/10/2026: P1 `0.2.0a3` và P2 `0.3.0a2` đã nghiệm thu kỹ thuật local; findings P1 01–04 và P2 01/02 đã đóng theo [audit P2 a2](/Users/macbookpro/.codex/.chatgpt-projects/g-p-68c38c8799f48191a101e19a975ca4f9/outputs/audits/s02-2a-p2-0.3.0a2-2026-10-23-015238/AUDIT_REPORT.md). Người dùng giao riêng [P3 migration local](../docs/S02_2A_P3_IMPLEMENTATION.md), `0.4.0a2`: **Đã sửa, chờ audit lại**. [Bàn giao mới](s02-phase2/2a-p3-fix01-0.4.0a2-2026-10-23/START_HERE.md). Chỉ thử trên kho synthetic/test; không migration operational, 2B/2C hoặc live. Bàn giao cũ giữ nguyên trạng thái lịch sử.

Các thư mục bàn giao cũ là lịch sử bất biến: không ghi logs/DB/manifests mới vào chúng, không sửa số liệu cũ theo audit mới. Trạng thái chờ audit trong report cũ không thay nguồn nghiệm thu về sau.

| Phạm vi | Bằng chứng |
| --- | --- |
| S01 Đợt 1 | [Bàn giao](s01-phase1/IMPLEMENTATION_REPORT.md) |
| S01 Đợt 2 / F1–F2 | [Bản sửa a3](s01-phase2/fixes-0.1.0a3/IMPLEMENTATION_REPORT.md) |
| S01 Đợt 3 / persistence | [Bàn giao](s01-phase3/IMPLEMENTATION_REPORT.md), [bản sửa a5](s01-phase3/fixes-0.1.0a5/IMPLEMENTATION_REPORT.md) |
| S01 Đợt 4 / CLI local a6 | [Bàn giao](s01-phase4/IMPLEMENTATION_REPORT.md), [nghiệm thu bên ngoài](/Users/macbookpro/.codex/.chatgpt-projects/g-p-68c38c8799f48191a101e19a975ca4f9/outputs/audits/s01-phase4-0.1.0a6/S01_ACCEPTANCE.json) |
| S02 Đợt 1 a1/a2 | [a1](s02-phase1/IMPLEMENTATION_REPORT.md), [a2](s02-phase1/fixes-0.1.0a2/IMPLEMENTATION_REPORT.md), [audit a2: S02-05 còn mở](/Users/macbookpro/.codex/.chatgpt-projects/g-p-68c38c8799f48191a101e19a975ca4f9/outputs/audits/s02-phase1-0.1.0a2-2026-10-19/AUDIT_REPORT.md) |
| S02 a3 / S02-05 và LAYOUT-01 | [Bản sửa a3](s02-phase1/fixes-0.1.0a3/IMPLEMENTATION_REPORT.md) — đã sửa, chờ audit; [kiểm thử](s02-phase1/fixes-0.1.0a3/TEST_RESULTS.md) |
| Tổ chức layout 19/10/2026 | [Bàn giao](repository-layout/2026-10-19/IMPLEMENTATION_REPORT.md), [audit: đạt mục tiêu, còn LAYOUT-01](/Users/macbookpro/.codex/.chatgpt-projects/g-p-68c38c8799f48191a101e19a975ca4f9/outputs/audits/repository-layout-2026-10-19/AUDIT_REPORT.md) |
| LAYOUT-01 / wrappers | [Bản sửa](repository-layout/fixes-LAYOUT-01-2026-10-19/IMPLEMENTATION_REPORT.md) — chờ audit lại |

Các report chứa đường dẫn cũ để tái hiện đúng bối cảnh, không chỉnh thành layout mới. Xem [README hiện hành](../README.md) và bảng old→new trong report layout. Wheel bàn giao ở `dist/` và `s02/dist/` giữ nguyên; rebuild và tests mới của layout chỉ nằm trong thư mục layout mới. DB synthetic trong evidence không dùng làm kho vận hành.

Đợt chạy sau chọn thư mục chưa tồn tại (`reports/<đợt-mới>/` hoặc thư mục kết quả ngoài checkout). Giữ kết quả S02-05 failed trên a2 như lịch sử; kết quả bản sửa phải có evidence riêng, không sửa assertions để làm xanh. Không có nghiệm thu S02 hoặc quyền triển khai Đợt 2 từ việc đổi thư mục hay tests pass.
