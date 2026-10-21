# Mục lục bằng chứng

Các thư mục bàn giao cũ là lịch sử bất biến: không ghi logs/DB/manifests mới vào chúng, không sửa số liệu cũ theo audit mới. Trạng thái chờ audit trong report cũ không thay nguồn nghiệm thu về sau.

| Phạm vi | Bằng chứng |
| --- | --- |
| S01 Đợt 1 | [Bàn giao](s01-phase1/IMPLEMENTATION_REPORT.md) |
| S01 Đợt 2 / F1–F2 | [Bản sửa a3](s01-phase2/fixes-0.1.0a3/IMPLEMENTATION_REPORT.md) |
| S01 Đợt 3 / persistence | [Bàn giao](s01-phase3/IMPLEMENTATION_REPORT.md), [bản sửa a5](s01-phase3/fixes-0.1.0a5/IMPLEMENTATION_REPORT.md) |
| S01 Đợt 4 / CLI local a6 | [Bàn giao](s01-phase4/IMPLEMENTATION_REPORT.md), [nghiệm thu bên ngoài](/Users/macbookpro/.codex/.chatgpt-projects/g-p-68c38c8799f48191a101e19a975ca4f9/outputs/audits/s01-phase4-0.1.0a6/S01_ACCEPTANCE.json) |
| S02 Đợt 1 a1/a2 | [a1](s02-phase1/IMPLEMENTATION_REPORT.md), [a2](s02-phase1/fixes-0.1.0a2/IMPLEMENTATION_REPORT.md), [audit a2: S02-05 còn mở](/Users/macbookpro/.codex/.chatgpt-projects/g-p-68c38c8799f48191a101e19a975ca4f9/outputs/audits/s02-phase1-0.1.0a2-2026-10-19/AUDIT_REPORT.md) |
| Tổ chức layout 19/10/2026 | [Bàn giao mới](repository-layout/2026-10-19/IMPLEMENTATION_REPORT.md) — chờ audit |

Các report chứa đường dẫn cũ để tái hiện đúng bối cảnh, không chỉnh thành layout mới. Xem [README hiện hành](../README.md) và bảng old→new trong report layout. Wheel bàn giao ở `dist/` và `s02/dist/` giữ nguyên; rebuild và tests mới của layout chỉ nằm trong thư mục layout mới. DB synthetic trong evidence không dùng làm kho vận hành.

Đợt chạy sau chọn thư mục chưa tồn tại (`reports/<đợt-mới>/` hoặc thư mục kết quả ngoài checkout). Không dùng report “all green” để che suite S02-05 vẫn failed. Không có nghiệm thu S02 hoặc quyền triển khai Đợt 2 từ việc đổi thư mục.
