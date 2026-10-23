# Phản hồi S02-2A-P2-01/02

**Đã sửa, chờ audit lại.** Đối tượng mới `dacn-s02 0.3.0a2`, DB2. Không tự đóng findings hoặc nghiệm thu P2. Căn cứ: audit độc lập a1 ngày 23/10/2026, contract draft.3 §9, storage draft.2 §3, manifest schema/framing/mutable_baseline đã chốt. IDs/profile/rules/schema không thay đổi; đây là sửa thực thi điều kiện đã có.

## S02-2A-P2-01 — inventory và lineage active review

Nguyên nhân: `_check` chỉ kiểm các selection rows hiện có thuộc đúng bundle, không đối chiếu tập bundle có Review và đầu cuối toàn lịch sử. Selection mất/rewind vẫn qua read và làm CAS tin rằng bundle chưa có root.

Sửa ở `Repository._check_review_selection`, được `_check` DB2 gọi sau whole-graph verification. Gom toàn bộ Review L1+E1 theo bundle; tập selection phải bằng tập bundle có review. Kiểm predecessor cùng bundle, khác self, một root, mỗi parent tối đa một successor, toàn history liên thông không cycle, selection đúng tip duy nhất. Tip revoked vẫn được chọn; check_freshness tiếp tục từ chối revoked. Không sort timestamp, repair, viết lại record hoặc sửa manifest. Chuỗi hợp lệ có thời gian successor cũ hơn root được kiểm trong controls để chứng minh không phụ thuộc timestamp.

Cùng `_check` bảo vệ checked reads, đầu transaction sau BEGIN IMMEDIATE và sau mutation trước COMMIT. CAS ghi Review giữ nguyên, nên parent cũ/root thứ hai khi đã có selection không được ghi; post-mutation fault rollback nguyên DB bytes. Manifest baseline vẫn chỉ kiểm lịch sử, không thay current selection.

Trước sửa wheel a1: file audit selection 6 failed / 3 passed mỗi backend. Sau sửa: 8 passed / 1 failed mỗi backend; ca cuối bị chặn sớm tại checked heads ngoài khối raises của oracle. [Phản chứng và trace](ORACLE_EXCEPTION.md) công khai nguyên kết quả, không nới checked read để lấy 9/9. Regression mới kiểm missing/stale selection, fork, multiple roots, disconnected cycle/self-cycle, CAS rollback và post-mutation rollback trên fresh/mixed.

## S02-2A-P2-02 — revoked cần predecessor

Nguyên nhân: validator chỉ kiểm accepted scope rỗng cho revoked; root có supersedes null vượt CAS None==None. Đây là lỗi có từ trước: wheel P1 0.2.0a3 được tái hiện mới, 1 failed / 1 passed mỗi backend, giống a1. Không gán nhầm thành regression do DB2.

Sửa trong nhánh `kind=='review'` của `validate_record`, **chỉ khi authoritative owner profile E1**. Revoked cần supersedes khác null; predecessor phải tồn tại, kiểu Review, khác self và cùng bundle. Typed refs/session checks hiện có tiếp tục áp dụng. Root request_changes hợp lệ, successor revoked hợp lệ được lưu/reopen; root revoked bị từ chối toàn T3, không tạo record/Run và command vẫn prepared.

Sau sửa nguyên `test_independent_review_contract.py` đạt 2/2 mỗi backend. Negative pure validator mới phân biệt E1 reject với L1 vẫn giữ hành vi baseline, và kiểm self/missing/cross-bundle predecessor.

## Dispatch và compatibility

DB1 `_check_legacy` giữ nguyên AST, kể cả các khoảng trống review của baseline; bản sửa không phải công cụ repair hoặc vá semantics kho DB1. `validate_record` chỉ thêm nhánh E1; bỏ nhánh đó khi so AST thì bằng chính bản trước sửa. L1 schema/resources, DDL1/DDL2, registry và toàn logic A1/A2 khác giữ nguyên byte. DB2 current-selection check áp trên toàn inventory L1+E1, nhưng không sửa semantics payload L1: root revoked lịch sử thuộc L1 vẫn giữ khoảng trống validator baseline; normal DB2 writer chỉ tạo E1 và không tạo được root revoked mới. Không retroactively thêm field/approval vào lịch sử. Chi tiết [legacy-preservation.json](legacy-preservation.json), differential và baseline lanes chạy mới.

Vị trí file/dòng ở [code-locations.json](code-locations.json), diff so actual pre-edit state ở [implementation.diff](implementation.diff); hashes runtime thực ở [runtime-hashes.json](runtime-hashes.json). Các dữ liệu review đều synthetic, không chứng minh đã có người thật review hoặc có acceptance nghiệp vụ.
