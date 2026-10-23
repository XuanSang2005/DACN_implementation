# Mục lục bằng chứng

S02 P3 **0.4.0a3 đã nghiệm thu kỹ thuật local/synthetic**, findings P3 01/02 đã đóng theo [audit](../docs/acceptance/P3_AUDIT_REPORT.md) và [biên bản](../docs/acceptance/S02_2A_P3_ACCEPTANCE.json). S01/Đợt 1/P1/P2 giữ phạm vi nghiệm thu cũ. Không có nghiệm thu toàn S02/nghiệp vụ/LLM/live hoặc quyền operational/cutover.

| Mốc | Bàn giao bất biến |
| --- | --- |
| S01 CLI local a6 | [Đợt 4](s01-phase4/IMPLEMENTATION_REPORT.md), [acceptance](../docs/acceptance/S01_ACCEPTANCE.json) |
| S02 Đợt 1 a3 | [Bàn giao](s02-phase1/fixes-0.1.0a3/IMPLEMENTATION_REPORT.md), [acceptance](../docs/acceptance/S02_PHASE1_ACCEPTANCE.json) |
| S02 P1 a3 | [Bàn giao](s02-phase2/2a-p1-fix04-0.2.0a3-2026-10-22/START_HERE.md) |
| S02 P2 a2 | [Bàn giao](s02-phase2/2a-p2-fixes-0.3.0a2-2026-10-23/START_HERE.md) |
| P3 a1 | [Bàn giao ban đầu](s02-phase2/2a-p3-0.4.0a1-2026-10-23/START_HERE.md) |
| P3 a2 / fix 01 | [Bàn giao](s02-phase2/2a-p3-fix01-0.4.0a2-2026-10-23/START_HERE.md) |
| P3 a3 / fix 02 | [Wheel/hash/diff/logs](s02-phase2/2a-p3-fix02-0.4.0a3-2026-10-23/START_HERE.md) |
| Layout 19/10 | [Bàn giao](repository-layout/2026-10-19/IMPLEMENTATION_REPORT.md), [fix wrappers](repository-layout/fixes-LAYOUT-01-2026-10-19/IMPLEMENTATION_REPORT.md) |
| Cleanup GitHub riêng | [Kết quả trước/sau](../docs/GITHUB_CLEANUP_2026-10-23.md), [archive/restore](../docs/ARTIFACTS.md) |

Reports Markdown ngoài copied snapshots và CLI regression viết tay của P3 a3 tiếp tục được track. Raw logs/JUnit/DB/wheels/inventories và snapshots `before`/`originals` đã archive trước khi ngừng tracking; không xóa hoặc thay bytes bản gốc. Các link raw artifacts trong report lịch sử cần archive hoặc bản local đang giữ; không biến chúng thành kết quả mới. Nội dung “chờ audit” trong report phản ánh thời điểm bàn giao, trạng thái hiện hành lấy từ acceptance ở trên.

Archive và inventory SHA-256 được pin ở [artifacts](../artifacts/README.md); restore ra thư mục mới ngoài checkout. Bundle bootstrap nhỏ hơn, độc lập với raw reports; không cần tải toàn evidence để build/test. Không ghi logs/DB mới vào thư mục lịch sử hoặc dùng DB bằng chứng làm state vận hành. Chọn output mới ngoài checkout cho mọi lần kiểm tiếp theo.
