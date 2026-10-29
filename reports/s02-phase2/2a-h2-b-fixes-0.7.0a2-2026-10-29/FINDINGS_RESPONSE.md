# Phản hồi implementer — H2-B 0.7.0a2

Chỉ sửa S02-2A-H2-B-01/02. Trạng thái: **đã sửa để audit lại, chưa có kết luận đóng finding của auditor**. [Căn cứ audit](/Users/macbookpro/.codex/.chatgpt-projects/g-p-68c38c8799f48191a101e19a975ca4f9/outputs/audits/s02-2a-h2-b-0.7.0a1-2026-10-28/AUDIT_REPORT.md), [harness notes gốc](/Users/macbookpro/.codex/.chatgpt-projects/g-p-68c38c8799f48191a101e19a975ca4f9/outputs/audits/s02-2a-h2-b-0.7.0a1-2026-10-28/HARNESS_NOTES.md), [mô tả bản sửa](../../../docs/S02_2A_H2_B_FIXES_0_7_0a2.md).

| Finding | Thay đổi và invariant kiểm |
| --- | --- |
| 01 — Issue mới nguồn U chặn physical V | Full candidate/new Issues/selectors bounds và binding; source+physical closure trên candidate/base; selected/retained domain output và reverse impact đều được kiểm trước seal. Guard-only không publish Model/Change/Parts và không tăng stage. Unresolved/progress đối chiếu physical blockers; sealed result/T3 có invariant không completed selected output còn blocker thật. |
| 02 — singleton construction task chặn batch | `_building_task` đối chiếu nguyên permit của từng task với unit set gốc và coverage của batch. `valid_for` không đổi và không mở rộng unit set/key. Một command/một Model/Change/CAS; tasks ngoài batch và business/gap/guard giữ gate/predicate. |

Delta pure H2-A: `h2_policy.py` thêm adapter call semantics cho task đã kiểm provenance; `h2_contracts.py` thêm lựa chọn input/result lane khi parse selector dẫn xuất, default cũ giữ nguyên. H2-B thay `h2_checkpoint.py`, `h2_service.py`, `h2_store.py`; version tại init/pyproject. Không sửa H1/L1/S01/A1/A2/canonical schemas/registry/DB2/locks hoặc code/tests/oracle lịch sử khác.

Hai oracle chính chạy nguyên byte: `test_independent_publication_gate.py` và `test_independent_h2_b_v2.py`. a1 exact wheel được cài mới từ SHA đã audit, tái hiện 4 fail/3 pass mỗi backend. Kết quả a2 và regression/full/package mới ghi tại [TEST_RESULTS](TEST_RESULTS.md); không lấy số đếm cũ làm kết quả mới.

Regression repo thêm riêng, không đổi assertions cũ. Kiểm effects đã persist/reopen, không chỉ status response; giữ controls U-held/V-independent, affected context, batch độc lập và negative task/role/kind. Lượt focused đầu phát hiện implementation chặn quá rộng khi coi source inspection bước 1 là retained domain output; giữ failure và sửa scope bảo vệ, không nới assertion. Một regression kiểm derived result selectors không cộng lại input counters; result aggregate vẫn chịu caps.

Auditor cần xác nhận lại hai findings trên đúng wheel/hash được START_HERE chỉ định, xem raw→guard/result correspondence, full Issues/closure/impact, task provenance, union/CAS và safety hồi quy. Người dùng quyết định nghiệm thu cuối cùng. Không tự ghi findings CLOSED/accepted.
