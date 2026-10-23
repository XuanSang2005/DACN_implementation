# START HERE — S02 2A-P1 0.2.0a3, sửa finding 04

Ngày 22/10/2026. **S02-2A-P1-04 đã sửa, chờ audit lại; P1 chưa nghiệm thu.** Auditor a2 đã đóng 01/02/03 trong phạm vi lỗi đã báo. Không tự ghi 04 đã đóng hoặc có quyền P2/P3.

1. Wheel S02 **duy nhất để audit**: [release/dacn_s02-0.2.0a3-py3-none-any.whl](release/dacn_s02-0.2.0a3-py3-none-any.whl), SHA-256 `678b6fdd6c54c221b162b60d519e8aaf92e9777fe5ef60a90fdf4f7f194b9117`. `build-01/` chỉ là candidate tự kiểm trước release; a1/a2 và evidence cũ giữ nguyên.
2. Đọc [phản hồi finding 04](FINDING_RESPONSE.md), [TEST_RESULTS](TEST_RESULTS.md), [REPRODUCE](REPRODUCE.md), [AGENTS](../../../AGENTS.md) và [hướng dẫn P1](../../../docs/S02_2A_P1_IMPLEMENTATION.md).
3. Đối chiếu [diff so actual state trước sửa](implementation.diff), [inventory trước](before-inventory.json), [bảo toàn sau](protected-inventory.json), [oracle/helper hashes](oracle-preservation.json), [release inputs](release-inputs.json), [rules/code hashes](rules-bundle.json).
4. Bằng chứng: [baseline a2](baseline-audit/commands.json), [năm oracle files trên release](release-audit/commands.json), [replay phản ví dụ](replay-summary.json), [full regressions](full-regression/commands.json), [instrumentation](full-regression/observations.json), [differential L1](differential-summary.json), [source–wheel–installed](package-evidence/manifest.json), [clean builds](clean-build-comparison.json), [tổng hợp execution](execution-summary.json).
5. [MANIFEST](MANIFEST.json) ghim mọi artifact handoff trừ chính manifest. Kiểm actual source/tests với release-inputs trước audit; bản snapshot không thay hiện trạng repo.

Đã chạy mới trên **mỗi backend C/Python**: hai files audit a2 10/10 pass; ba files audit a1 12/12 pass; full S02 **383/383**, full S01 **986/986**, không fail/error/skip. S02 gồm 344 tests trước sửa giữ nguyên + 39 regression mới. Hai graph lỗi bị reject đúng; các controls unchanged/review mới/hold pass. Trước sửa đã tái hiện 2 failures/backend trên wheel a2. Differential L1 khớp 413/413 outcomes với baseline S02 **0.1.0a3**.

Bảo toàn 1739 file trước sửa, không thiếu file. Chỉ năm file hiện hữu đổi trong phạm vi và thêm một test file; wheel chỉ đổi resolution.py, __init__ và METADATA version. L1/shared helper, schema L1/E1/registry, DB1/repository, S01 a6, locks/dependencies và artifacts lịch sử nguyên byte. Contract/profile/rules IDs giữ nguyên; hashes code thực cập nhật.

Kết quả là tests code trên fixtures/DB synthetic; review bindings trong tests không phải người thật xác nhận. Chưa chứng minh nghiệp vụ hoặc mapping đủ nghĩa; không E1 persistence, DB2, migration, P2/P3, CAS/claims mới, 2C/live. Không mở operational store, không sửa dataset, không gọi LLM/renderer.
