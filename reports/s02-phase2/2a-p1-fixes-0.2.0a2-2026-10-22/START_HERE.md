# START HERE — bản sửa S02 2A-P1 0.2.0a2

Ngày 22/10/2026. **Đã sửa ba findings S02-2A-P1-01/02/03, chờ audit lại. Chưa nghiệm thu P1 và chưa ghi nhận auditor đóng findings.**

1. Wheel S02 duy nhất để audit/cài: [release/dacn_s02-0.2.0a2-py3-none-any.whl](release/dacn_s02-0.2.0a2-py3-none-any.whl), SHA-256 `fbdabdf9c837f5d2cf20632b7fcdaaa423f3d50f717090ef187994dcc333e943`. `build-01/` là build tự kiểm trước bàn giao, không phải wheel được chỉ định để audit. Wheel a1 và evidence cũ giữ nguyên.
2. Đọc [phản hồi từng finding](FINDING_RESPONSE.md), [kết quả kiểm thử](TEST_RESULTS.md), [cách tái lập](REPRODUCE.md), [AGENTS hiện hành](../../../AGENTS.md) và [API/giới hạn P1](../../../docs/S02_2A_P1_IMPLEMENTATION.md).
3. Đối chiếu [diff đúng trạng thái trước sửa](implementation.diff), [inventory trước](before-inventory.json), [bảo toàn sau sửa](protected-inventory.json), [oracle nguyên byte](oracle-preservation.json), [input release](release-inputs.json) và [rules bundle/hashes](rules-bundle.json).
4. Bằng chứng chạy: [baseline a1](baseline-audit/commands.json), [ba files audit trên release a2](release-audit-02/commands.json), [full regression](full-regression/commands.json), [instrumentation](full-regression/observations.json), [differential L1](differential-summary.json), [source–wheel–installed](package-evidence/manifest.json), [clean build](clean-build-comparison.json), [tổng hợp](execution-summary.json).
5. [MANIFEST](MANIFEST.json) niêm phong mọi file handoff trừ chính manifest. Kiểm actual repo với release-inputs trước audit; không lấy trạng thái snapshot thay hiện trạng repo.

Kết quả thực chạy: 12/12 tests audit, S02 344/344, S01 986/986 **trên mỗi backend C và Python**, không fail/error/skip. S02 gồm 307 tests giữ nguyên và 37 regression mới. Differential L1 khớp 413/413 outcomes với a3 trên cả hai backend. Đã tái hiện 5 fail/7 pass audit trên a1 trước sửa.

Scope vẫn chỉ P1 pure validators. L1 schema, E1 schema/registry, DB1/repository legacy, S01 a6, locks/dependencies và artifacts lịch sử giữ nguyên; 1278 file trước sửa được bảo toàn, sáu file hiện hữu thay đổi đúng phạm vi, thêm một file regression. Contract/profile/rules IDs giữ nguyên, hash code thực đổi theo artifact a2.

Tests chạy thật trên fixtures/DB tạm synthetic; mọi review input trong tests là synthetic, không phải người dùng xác nhận. Chưa chứng minh nghiệp vụ, E1 persistence, DB2, P2/P3, migration, 2C hoặc live; không mở operational store, không sửa dataset, không gọi LLM. Không mở rộng quyền từ kết quả này.
