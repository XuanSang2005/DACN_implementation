# Mapping oracle và lanes

Tests/helpers lịch sử trong `packages/s02/tests` không bị sửa; bản trước công việc ở `before/`. Wheels baseline giữ nguyên. Lượt baseline chạy trên copies chỉ đổi vị trí workspace/docs, không sửa assertions. S01 chạy process và conftest riêng. DB thử nghiệm đều synthetic.

| Nhóm/case gốc | Lane baseline | Lane P2 và căn cứ thay setup/API |
| --- | --- | --- |
| 217 tests Đợt 1 | `legacy-regression`, wheel 0.1.0a3 | Nằm trong corpus 383 đã adapt; DB2 writer E1 thay DB1 theo storage §3–5 |
| 383 tests P1 a3 | `p1-regression`, wheel 0.2.0a3 | `audit-p2-regression`: giữ tests; khai báo hai fields Issue và observed_source_context_id cho fixture E1 |
| S01 986 tests | `p1-regression` và `audit-s01`, wheel S01 a6 | Nguyên tests; không import source chéo, không đổi S01 |
| Issue fixture/application | L1 không có fields mới | `helpers.issue` thêm hai null bắt buộc; `application_batch` existing-source thêm observed=null. Runtime không tự thêm |
| Pure P1 graph + sáu files audit | Root L1 từ DB1, nguyên helper files | Tạo root DB2/E1 rồi projection L1 **trong bộ nhớ** cho pure oracle; strip đúng fields mới, giữ events/records/bytes còn lại. Đây không phải L1 writer hoặc migration. Audits vẫn nguyên bytes/assertions |
| `test_repository_cannot_write_e1_issue` | Giữ nguyên và pass trên DB1 | Đổi fixture thành payload Issue L1, tên oracle `cannot_write_l1_issue`; vẫn phải raise, head không tiến, record không tồn tại. Đường E1 hợp lệ được kiểm riêng |
| CLI show-record | Bare payload baseline | Chỉ truy cập `result.record.type` theo wrapper mới, không bỏ assertion loại record |
| Receipt prepared lookup | s02/1 + state_dir | s02/2 + authoritative store_id; negative path/identity/old-receipt guards riêng. Không bỏ path binding |
| Config staged positive | Config bytes baseline | Thêm profile/contract/rules bằng config E1 fixture đã được tạo, giữ synthetic_config khác để kiểm pins; negative identity/promotion/rollback assertions giữ nguyên |
| Deliberate corrupt-history fixtures | Bypass legacy record/operation gate khi seed | Bypass đúng whole-graph gate mới chỉ trong test context; restore trước reopen. Với config pin, patch đúng reference profile_graph.validate_operations. Không bypass ở production |
| Docs shape test | Relative workspace docs | Adapter chỉ định vị docs thật; vẫn assert 33 records và inventory |
| CAS/claims/races/fault/kill | Nguyên tests DB1 baseline | Cùng assertions và IPC/barriers/process workers, đổi fixtures E1 như trên; encoder workers thực được đo |
| Manifest/storage mới | Không có trong baseline | `test_db2.py`/`p2_helpers.py`, schema/framing đã được người dùng chốt. Seed SQL rõ là synthetic; không public migrate |

Tool sinh lane: `packages/s02/tools/prepare_p2_tests.py`. Mỗi lượt `run_p2_checks.py` lưu `ADAPTER.json` chứa SHA-256 từng input/output và diff đầy đủ; không có skip/xfail. Các assertions chỉ thay đường truy cập wrapper của CLI; oracle writer đổi loại payload bị cấm do yêu cầu E1-only. Các negative/schema/identity/raw/rollback assertions còn lại giữ nguyên.

Nhóm DB2 được bổ sung positive review/claim lineage trong khi full batch đang chạy. Vì vậy kết quả cuối lấy **383 cases ngoài test_db2** từ full batch và **toàn bộ 71 cases test_db2 hiện hành** từ `audit-db2-final-02`; không cộng hai lần 69 cases DB2 cũ trong full batch. `execution-summary.json` kiểm hashes các files còn lại bằng nhau, liệt kê counts/logs và corpus cuối 454 cases/backend khi tất cả đạt. Các files audit và 2 graph replay được ghim riêng trong `oracle-inputs.json`, `replay-inputs.json`, kiểm lại sau chạy.

Các lượt discovery thất bại được giữ logs: DDL thử nghiệm đặt cột sau table constraint, adapter fault injection chưa chuyển gate, harness resolve symlink Python khỏi venv và lỗi đường copy fixture. Không dùng các lượt đó làm kết quả release. Bản có manifest đầy đủ và wheel audit được xác định duy nhất trong START_HERE.
