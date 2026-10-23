# Lanes và oracle

`packages/s02/tools/prepare_p2_tests.py` và `run_p2_checks.py` giữ nguyên byte so a1. Toàn tests/helpers có sẵn trước sửa giữ nguyên, kể cả `test_db2.py`, `p2_helpers.py`. Chỉ thêm `test_review_integrity.py` (34 ca sau parametrization). Full lane hiện hành có 454 ca a1 + 34 ca mới, chạy trong **một batch cho mỗi backend**.

Các fixtures/API adapters từ a1 tiếp tục áp dụng: nullable fields E1, config pins, receipt/wrapper, fault injection location và projection L1 trong bộ nhớ cho pure P1 oracle. [Mapping lịch sử a1](../2a-p2-0.3.0a1-2026-10-22/TEST_MAPPING.md) mô tả từng thay đổi; `ADAPTER.json` của mỗi run mới ghi input/output hashes và diff. `test-input-preservation.json` so chính xác hashes adapter output a1 với a2 trên tất cả files cũ. Không gọi đây là legacy-write tests nguyên trạng chạy trên E1.

| Nhóm | Setup/expectations | Kết quả dùng |
| --- | --- | --- |
| Baseline P1 a3 | Frozen corpus/helpers từ snapshot trước P2, wheel 0.2.0a3 riêng | p1-regression; 383/backend |
| Baseline Đợt 1 a3 | Frozen corpus, loại đúng sáu modules P1-only; wheel 0.1.0a3 riêng | legacy-regression; 217/backend |
| S01 a6 | Source tests nguyên byte, installed wheel a6 từ lock; process riêng | s01-regression; 986/backend |
| Sáu oracle P1 | Files audit nguyên byte, locator helpers; explicit baseline/P2 lanes | baseline-p1-oracles và audit-p1; 27/backend mỗi lane |
| Ba oracle P2 a1 | Nguyên byte `test_independent_p2.py`, `test_independent_review_contract.py`, `test_independent_persistence_v2.py` | before-* và audit-p2; 9 + 2 + 6/backend |
| Revocation gap P1 | Cùng original review-contract oracle, frozen helpers, wheel P1 riêng | before-p1-review-contract; 1 failed / 1 passed/backend |
| Regression Review mới | Fresh E1 và mixed fixture L1→E1; explicit SQL faults, API thật, hook lỗi transaction có sẵn | focused-review-02 (34/backend) và full-s02 |

Các negative mới kiểm cả `verify`, `heads`, `get_record`, `check_freshness`, trước write và sau mutation. Kiểm nguyên DB bytes sau reject/rollback, không chỉ exception; kiểm command vẫn prepared, record/Run chưa tồn tại, root cũ còn current. Controls request_changes root và successor revoked/re-request_changes có reopen. Deliberate timestamp ngược không ảnh hưởng tip; không dựa fixture hai Review duy nhất để nhận diện cycle hoặc fork.

Compatibility riêng: explicit owner L1 vẫn nhận root revoked theo behavior pin; owner E1 từ chối cùng payload. Full DB2 lựa chọn active review bằng toàn lịch sử L1+E1, DB1 vẫn dùng verifier legacy. So AST và hashes bổ trợ differential 413 outcomes, không tuyên bố chứng minh semantics trên mọi đầu vào.

Không sửa original oracle còn fail: xem [ORACLE_EXCEPTION.md](ORACLE_EXCEPTION.md). Không dùng file persistence không-v2 có lỗi API event_id. Không skip/xfail. Các mocks/SQL seeding/reviewer là synthetic; không migration production hoặc xác nhận người thật.
