# Bàn giao S02-2A-P3-01 — 0.4.0a2

**Đã sửa, chờ audit lại.** Chưa đóng finding hoặc nghiệm thu P3.

Wheel duy nhất để audit: [dacn_s02-0.4.0a2-py3-none-any.whl](handoff-wheel/dacn_s02-0.4.0a2-py3-none-any.whl)

SHA-256: `7fbd0fb483989f7e57f53ee2b4545aa72b2efec07e36c9436401af55cd5d97ab`

- [Phản hồi finding, code/durability/race, kết quả và giới hạn](IMPLEMENTATION_REPORT.md)
- [Diff so trạng thái thực trước sửa](changes-handoff.patch), [inventory](input-inventory.json), [kiểm bảo toàn](preservation-handoff.json), [seals lịch sử](historical-seals-handoff.json)
- [Commands/cwd/exit codes/logs](command-index.json)
- [Tests/JUnit/log paths](test-results.json), [instrumentation](instrumentation.json), [baseline trước sửa](baseline-p3-oracles/), [hai oracle và controls sau sửa](handoff-focused/)
- [Full S02](handoff-full/), [S01](handoff-s01/), [differential L1](differential-summary.json), [helper hashes](helper-preservation.json)
- [Source–wheel–installed](handoff-package-evidence/), [rebuild](rebuild-comparison-handoff.json), [wheel diff a1→a2](wheel-a1-a2-diff-handoff.json), [pip check](handoff-pip-check.log)
- [Cách tái lập vào output mới](REPRODUCE.md), [release/hash inputs](handoff.json), [artifact hashes](ARTIFACT_HASHES.json), [seal](SEAL.json)

Kết quả mỗi backend: hai oracle P3 14 pass; regressions mới 34 pass; full S02 623 pass; S01 986 pass; P1 27 pass; P2 v2 17 pass. P2 nguyên bản giữ 16 pass + 1 lỗi setup đã biết; không sửa oracle hoặc xfail.

Reservation tồn tại độc lập SQLite, được fsync trước tạo target; init/copy dùng chung parent lock. Giữ fresh-init hợp lệ, inactive refusal và active idempotence. Partial a1 cũ không có marker/metadata phải giữ quarantine; không tự repair hoặc cleanup. Chỉ kiểm kho synthetic/test, không operational/live.

Các `dev*`/`final*`/`release-*`/`audit-*` là attempts trung gian được giữ nguyên; không phải wheel audit thay thế. Không suy tests pass thành kết luận auditor.

Kiểm seal bằng [verify_handoff.py](verify_handoff.py); thêm `--source` để đối chiếu checkout hiện tại với inputs của wheel bàn giao.
