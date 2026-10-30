# Mục lục bằng chứng

S02 P3 **0.4.0a3 đã nghiệm thu kỹ thuật local/synthetic**, findings P3 01/02 đã đóng theo [audit](../docs/acceptance/P3_AUDIT_REPORT.md) và [biên bản](../docs/acceptance/S02_2A_P3_ACCEPTANCE.json). S01/Đợt 1/P1/P2 giữ phạm vi nghiệm thu cũ. Không có nghiệm thu toàn S02/nghiệp vụ/LLM/live hoặc quyền operational/cutover.

**H1 0.5.0a2 đã nghiệm thu kỹ thuật local/synthetic**, H1-01/02 đóng theo [audit 25/10](../docs/acceptance/s02-2a-h1-0.5.0a2-2026-10-25/AUDIT_REPORT.md) và [biên bản](../docs/acceptance/s02-2a-h1-0.5.0a2-2026-10-25/S02_2A_H1_ACCEPTANCE.json). [Bàn giao H1](s02-phase2/2a-h1-fixes-0.5.0a2-2026-10-25/START_HERE.md) giữ nguyên trạng thái lịch sử. **[H2 draft.2 đã đạt audit thiết kế](../docs/acceptance/s02-2a-h2-design-draft2-2026-10-25/README.md)**, D01/D02 đóng design-only; [bàn giao delta](s02-phase2/2a-h2-design-draft2-2026-10-25/START_HERE.md) giữ lịch sử. **H2-A 0.6.0a2 đã được người dùng nghiệm thu kỹ thuật pure policy local/synthetic ngày 26/10**; findings 01/02/03 đóng theo [audit và biên bản](../docs/acceptance/s02-2a-h2-a-0.6.0a2-round1-2026-10-26/README.md). **H2-B 0.7.0a2 đã đóng findings01/02; [V01](/Users/macbookpro/.codex/.chatgpt-projects/g-p-68c38c8799f48191a101e19a975ca4f9/outputs/audits/s02-2a-h2-b-v01-0.7.0a2-2026-10-29/AUDIT_REPORT.md) xác minh an toàn deadline/recovery. Full lịch sử vẫn C959/959, Python958/959.** Người dùng đã biết giới hạn này và giao riêng **[H2-C merge/revalidation/stress](../docs/S02_2A_H2_C_IMPLEMENTATION.md)** ngày29/10; [bàn giao implementer](s02-phase2/2a-h2-c-0.8.0a1-2026-10-29/START_HERE.md) giữ trạng thái lịch sử. **H2-C `0.8.0a1` đã được người dùng nghiệm thu kỹ thuật local/synthetic ngày 29/10 theo [audit và biên bản](../docs/acceptance/s02-2a-h2-c-0.8.0a1-2026-10-29/README.md)**. Auditor tự chạy **18+2 ca/backend**, full S02 **977/977** và S01 **986/986/backend** là supporting evidence của implementer, không phải full audit chạy mới. AS-only race dùng presealed plans ở T3; recovery từ failed DB thật không bảo đảm liveness mọi contention. H2-B V01/full lịch sử giữ nguyên. **[H3 draft.2](../docs/S02_2A_H3_E1_HISTORY_DESIGN_PROPOSAL.md) đã đạt audit thiết kế; D1–D5 được chấp thuận, chỉ H3-A được giao, chưa nghiệm thu implementation**; 2B/2C/LLM/renderer/live/operational migration/cutover vẫn ngoài phạm vi, chưa nghiệm thu toàn S02.

| Mốc | Bàn giao bất biến |
| --- | --- |
| S01 CLI local a6 | [Đợt 4](s01-phase4/IMPLEMENTATION_REPORT.md), [acceptance](../docs/acceptance/S01_ACCEPTANCE.json) |
| S02 Đợt 1 a3 | [Bàn giao](s02-phase1/fixes-0.1.0a3/IMPLEMENTATION_REPORT.md), [acceptance](../docs/acceptance/S02_PHASE1_ACCEPTANCE.json) |
| S02 P1 a3 | [Bàn giao](s02-phase2/2a-p1-fix04-0.2.0a3-2026-10-22/START_HERE.md) |
| S02 P2 a2 | [Bàn giao](s02-phase2/2a-p2-fixes-0.3.0a2-2026-10-23/START_HERE.md) |
| P3 a1 | [Bàn giao ban đầu](s02-phase2/2a-p3-0.4.0a1-2026-10-23/START_HERE.md) |
| P3 a2 / fix 01 | [Bàn giao](s02-phase2/2a-p3-fix01-0.4.0a2-2026-10-23/START_HERE.md) |
| P3 a3 / fix 02 | [Wheel/hash/diff/logs](s02-phase2/2a-p3-fix02-0.4.0a3-2026-10-23/START_HERE.md) |
| H1 design draft.2 | [Bàn giao thiết kế lịch sử](s02-phase2/2a-h1-design-draft2-2026-10-23/START_HERE.md); audit đạt 24/10, nguồn trong bàn giao H1 |
| H1 0.5.0a2 | [Bàn giao lịch sử](s02-phase2/2a-h1-fixes-0.5.0a2-2026-10-25/START_HERE.md), [nghiệm thu H1](../docs/acceptance/s02-2a-h1-0.5.0a2-2026-10-25/S02_2A_H1_ACCEPTANCE.json) |
| H2 design draft.1 | [Bàn giao lịch sử](s02-phase2/2a-h2-design-draft1-2026-10-25/START_HERE.md), giữ nguyên evidence; audit yêu cầu bổ sung D01/D02 |
| H2 design draft.2 | [Bàn giao lịch sử](s02-phase2/2a-h2-design-draft2-2026-10-25/START_HERE.md), [audit thiết kế đạt](../docs/acceptance/s02-2a-h2-design-draft2-2026-10-25/README.md), chưa implementation |
| H2-A 0.6.0a1 | [Bàn giao lịch sử](s02-phase2/2a-h2-a-0.6.0a1-2026-10-25/START_HERE.md); findings 01/02/03 dẫn tới vòng sửa 1 |
| H2-A 0.6.0a2 | [Bàn giao vòng sửa 1 lịch sử](s02-phase2/2a-h2-a-fixes-0.6.0a2-round1-2026-10-25/START_HERE.md), [nghiệm thu pure policy](../docs/acceptance/s02-2a-h2-a-0.6.0a2-round1-2026-10-26/S02_2A_H2_A_ACCEPTANCE.json) |
| H2-B fixes 0.7.0a2 | [Bàn giao lịch sử](s02-phase2/2a-h2-b-fixes-0.7.0a2-2026-10-29/START_HERE.md); findings01/02 đã đóng, V01 giữ giới hạn full lịch sử |
| H2-C 0.8.0a1 | [Bàn giao merge/revalidation/stress](s02-phase2/2a-h2-c-0.8.0a1-2026-10-29/START_HERE.md); [đã nghiệm thu local/synthetic](../docs/acceptance/s02-2a-h2-c-0.8.0a1-2026-10-29/README.md), evidence lịch sử giữ nguyên |
| H3-A fixes 0.9.0a2 | [Bàn giao sửa riêng ba findings](s02-phase2/2a-h3-a-fixes-0.9.0a2-2026-10-30/START_HERE.md); đã bàn giao để audit lại, chưa nghiệm thu |
| H3-A a1 (lịch sử) | [Bàn giao pure contracts/history policy](s02-phase2/2a-h3-a-0.9.0a1-2026-10-29/START_HERE.md); CHANGES REQUIRED theo audit a1, ba findings OPEN, chưa nghiệm thu |
| H3 design draft.2 / sửa D01–D02 | [Bàn giao docs-only lịch sử](s02-phase2/2a-h3-design-draft2-2026-10-29/START_HERE.md) giữ trạng thái lúc bàn giao; hiện [đạt audit thiết kế, D01/D02 đóng design-only](../docs/acceptance/s02-2a-h3-design-draft2-2026-10-29/README.md), D1–D5 được người dùng chấp thuận |
| H2-C acceptance + H3 design draft.1 | [Bàn giao docs-only lịch sử](s02-phase2/h2-c-acceptance-h3-design-draft1-2026-10-29/START_HERE.md) giữ trạng thái lúc bàn giao; thiết kế hiện hành là draft.2 theo biên bản trên |
| H2-B 0.7.0a1 | [Bàn giao lịch sử](s02-phase2/2a-h2-b-0.7.0a1-2026-10-27/START_HERE.md); audit 28/10 CHANGES REQUIRED, findings 01/02 mở |
| Mốc nghiệm thu H2-A | [Danh sách commit, diff và kiểm bảo toàn](s02-phase2/h2-a-acceptance-commit-2026-10-26/START_HERE.md); chưa stage/commit/push |
| Mốc H1 + thiết kế H2 | [Trạng thái/commit cục bộ](s02-phase2/h1-h2-design-commit-2026-10-25/START_HERE.md); chưa push hoặc H2-A |
| Layout 19/10 | [Bàn giao](repository-layout/2026-10-19/IMPLEMENTATION_REPORT.md), [fix wrappers](repository-layout/fixes-LAYOUT-01-2026-10-19/IMPLEMENTATION_REPORT.md) |
| Cleanup GitHub riêng | [Kết quả trước/sau](../docs/GITHUB_CLEANUP_2026-10-23.md), [archive/restore](../docs/ARTIFACTS.md) |

Reports Markdown ngoài copied snapshots và CLI regression viết tay của P3 a3 tiếp tục được track. Raw logs/JUnit/DB/wheels/inventories và snapshots `before`/`originals` đã archive trước khi ngừng tracking; không xóa hoặc thay bytes bản gốc. Các link raw artifacts trong report lịch sử cần archive hoặc bản local đang giữ; không biến chúng thành kết quả mới. Nội dung “chờ audit” trong report phản ánh thời điểm bàn giao, trạng thái hiện hành lấy từ acceptance ở trên.

Archive và inventory SHA-256 được pin ở [artifacts](../artifacts/README.md); restore ra thư mục mới ngoài checkout. Bundle bootstrap nhỏ hơn, độc lập với raw reports; không cần tải toàn evidence để build/test. Không ghi logs/DB mới vào thư mục lịch sử hoặc dùng DB bằng chứng làm state vận hành. Chọn output mới ngoài checkout cho mọi lần kiểm tiếp theo.
