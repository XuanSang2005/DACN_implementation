# Audit lại 2A-H1 dacn-s02 0.5.0a2

Ngày 25/10/2026. **ĐẠT nghiệm thu kỹ thuật H1 trong phạm vi local/synthetic, fresh E1/full scope. S02-2A-H1-01 và S02-2A-H1-02 đóng. Không có finding implementation mới trong delta đã review.**

Mốc đã đạt là S01 synthetic + bốn mock qua handlers thật → draft Model/mapping/Issues, có checkpoint/reopen/resume/blocked và safety gate H1. Không nghiệm thu chất lượng nghiệp vụ, LLM, renderer, toàn bộ S02 hoặc H2/H3. [Biên bản máy đọc](/Users/macbookpro/.codex/.chatgpt-projects/g-p-68c38c8799f48191a101e19a975ca4f9/outputs/audits/s02-2a-h1-0.5.0a2-2026-10-25/S02_2A_H1_ACCEPTANCE.json).

## Candidate và bằng chứng bảo toàn

Wheel audit: [dacn_s02-0.5.0a2-py3-none-any.whl](/Users/macbookpro/.codex/.chatgpt-projects/g-p-68c38c8799f48191a101e19a975ca4f9/outputs/implementations/s02-2a-h1-fixes-0.5.0a2-2026-10-24/final/wheels/dacn_s02-0.5.0a2-py3-none-any.whl), SHA-256 `012a398d9c3aa3d085508bb8b2a60600a0c8f8211992f2bdd5396e8e618c4f11`. Repo `/Users/macbookpro/Documents/DACN_implementation`, HEAD `4c7e69719dbd1a6e4215cfd01764c6750962ee7f`; đọc AGENTS hiện hành và đối chiếu scope fix01/02 với proposal execution draft.2 đã audit thiết kế.

Môi trường mới từ locks/bundle pin, copy source kiểm hash; hai clean rebuilds; cài đúng ZIP bàn giao non-editable và collector chạy lại sau cài. Wheel a1 so a2 chỉ đổi bốn package files: `__init__.py`, `h1_candidates.py` (handler version), `h1_limits.py`, `h1_builders.py`. 29 package files còn lại giữ nguyên byte; không thêm/xóa payload file. METADATA đổi version đúng, WHEEL giữ nguyên.

Seal bàn giao **2.404 files** được hash lại. Inventory gốc **13.124 files**: 10 thay đổi đã khai báo, 13.114 còn lại nguyên byte; thêm test fixes và docs bàn giao. S01, locks, shared validators/profiles, L1/E1 canonical schemas/registry, repository/DB2, existing tests/conftest và evidence lịch sử giữ nguyên. Kiểm thêm 1.607 files audit a1 và 3.489 files implementation a1 nằm trong các output lịch sử. Kết thúc audit kiểm lại toàn bộ, repo/head/index/status không thay đổi bởi auditor. Xem `preservation.json`, `wheel-delta.json`, `final-preservation.json`.

## Đóng hai findings

| Finding | Mức độ trước sửa | Kết luận trên a2 | Bằng chứng |
| --- | --- | --- | --- |
| S02-2A-H1-01 | Trung bình | CLOSED | Đếm finding_handles/questions/finding_handle occurrences; đúng 50.000 nhận, 50.001 rejected trước linker/build. Ca xuyên suốt giữ raw, head không đổi, không result publication, reopen đúng |
| S02-2A-H1-02 | Trung bình | CLOSED | Mỗi unassigned-action gap tạo Issue analysis_omission DIRECT/key riêng, full hold; Issue được trích dẫn giữ nghĩa và lineage. Local/base/pending-mapping đều blocked, không prepare bước 4 |

**01:** [h1_limits.py:74](/Users/macbookpro/Documents/DACN_implementation/packages/s02/src/dacn_s02/h1_limits.py:74) thêm đếm string refs, giữ SourceRef atomic và không đếm declaration `handle/id` như ref. Defaults/candidate/limits/canonical versions giữ nguyên. V4 có ba controls đúng trần, ba parser negatives và một integration negative. Tests mới còn kiểm singular finding_handle, mixed refs và total result/current-Issue refs; không chỉ vá đúng một fixture audit.

**02:** [h1_builders.py:101](/Users/macbookpro/Documents/DACN_implementation/packages/s02/src/dacn_s02/h1_builders.py:101) tạo hold riêng cho assignment gap, lấy source từ action hiện hành và nối trace tới current finding đúng phiên bản. Không biến nonblocking finding thành blocker chỉ bằng sửa record cũ; không cho dùng exemption của mapping task. V4 xác nhận ba nhánh local/base/pending-mapping sau reopen và ngăn prepare bước 4. Sáu regression Model-change/AS-only kiểm old Records nguyên byte, key/supersedes/current refs; hai gaps chung task vẫn giữ hold riêng. Fully assigned control vẫn completed đến bước 4, verification không chặn vẫn open.

## Oracle V3 và đính chính audit a1

**Lỗi tuple đúng là lỗi logger của auditor.** V3 đưa tuple từ Repository.heads() vào exact JSON encoder trước assertions xuyên suốt. Không sửa codec hoặc Repository API để cho logger pass. Báo cáo a1 đã phân loại nhầm một failure này thành production assertion failure; [đính chính riêng](/Users/macbookpro/.codex/.chatgpt-projects/g-p-68c38c8799f48191a101e19a975ca4f9/outputs/audits/s02-2a-h1-0.5.0a2-2026-10-25/AUDIT_ERRATUM_A1.md) giữ nguyên toàn bộ hồ sơ cũ.

V4 chỉ sửa **hai dòng ghi evidence**, chuyển head tuples thành lists. Input và mọi assertions nguyên nghĩa; AST assertions bằng nhau, diff/hashes tại [oracle-correction.json](/Users/macbookpro/.codex/.chatgpt-projects/g-p-68c38c8799f48191a101e19a975ca4f9/outputs/audits/s02-2a-h1-0.5.0a2-2026-10-25/oracle-correction.json), [diff V3 → V4](/Users/macbookpro/.codex/.chatgpt-projects/g-p-68c38c8799f48191a101e19a975ca4f9/outputs/audits/s02-2a-h1-0.5.0a2-2026-10-25/oracle-v3-v4.diff). V3 nguyên byte vẫn chạy riêng.

| Wheel và oracle — lượt chạy mới của auditor | C | Python | Phân loại |
| --- | --- | --- | --- |
| a1 + V3 | 4 pass, 6 fail | 4 pass, 6 fail | 5 production failures + 1 logger failure |
| a1 + V4 | 4 pass, 6 fail | 4 pass, 6 fail | Cả 6 là assertions của hai findings; integration fail completed thay vì rejected |
| a2 + V3 | 9 pass, 1 fail | 9 pass, 1 fail | Chỉ logger tuple nguyên bản |
| a2 + V4 | **10 pass** | **10 pass** | Tất cả assertions thực thi; không skip/xfail |

Baseline a1 được cài từ wheel a1 chính xác trong venv mới, không lấy source a2 rồi gắn nhãn baseline. Bản sửa làm V4 chuyển từ 6 failures sang 0; không có thay đổi production phục vụ logger. Oracle chính thức cho re-audit này là [test_independent_h1_v4.py](/Users/macbookpro/.codex/.chatgpt-projects/g-p-68c38c8799f48191a101e19a975ca4f9/outputs/audits/s02-2a-h1-0.5.0a2-2026-10-25/test_independent_h1_v4.py); V3 vẫn là evidence lịch sử.

## Kiểm thử độc lập mới

| Bộ kiểm | C | Python | Evidence |
| --- | --- | --- | --- |
| Full S02 | **769 pass** | **769 pass** | `full-checks/s02-*.xml` |
| H1 subset của full | 103 pass | 103 pass | 85 cũ + 18 fixes, không cộng lại coverage |
| Full S01 | **986 pass** | **986 pass** | `full-checks/s01/` |
| Sáu oracle P1 nguyên bản | 27 pass | 27 pass | `oracle-p1-six/` |
| P2 v2 + boundaries | 17 pass | 17 pass | `oracle-current-boundaries/` |
| P3 a3 boundaries | 4 pass | 4 pass | `oracle-current-boundaries/` |
| Bốn P3 bundle + CLI controls | 22 + 14 pass | 22 + 14 pass | `full-checks/p3-oracles/` |
| P2 gốc | 16 pass, 1 known setup failure | Tương tự | `oracle-p2-original/` |
| Differential L1 a3 → a2 | 413/413 bằng nhau | 413/413 bằng nhau | `differential-result.json` |

Full suites và V4 không skip/xfail, không chỉnh timeout. Ca migration `reservation_durable-cli` pass trong full mới trên cả hai backend: timeout ở audit a1 **không tái hiện**, chưa chứng minh nguyên nhân gốc; không dùng kết quả này viết lại failure cũ. P2 gốc vẫn lỗi setup heads() sau corruption trước pytest.raises đã được audit trước xác nhận; v2 và boundaries pass, không làm yếu checked reader.

Wrappers **339 pass**; layout và source–wheel–installed/METADATA/WHEEL/direct URL/pip check đạt. Hai rebuild khớp toàn 20 S01 entries với accepted a6 và 37 S02 entries với wheel a2. Mọi imports nằm trong venv installed. Các counts là lượt chạy auditor mới, không sao chép số implementer hoặc cộng suites giao nhau thành coverage độc nhất. [JUnit tổng hợp](/Users/macbookpro/.codex/.chatgpt-projects/g-p-68c38c8799f48191a101e19a975ca4f9/outputs/audits/s02-2a-h1-0.5.0a2-2026-10-25/junit-summary.json).

M1 chạy lại qua CLI/process mới trên cả C/Python: S01 intake → bootstrap → bốn mock → completed_steps1–4, sáu mapping rows, Model/Issues, progress/reopen/resume; session thiếu thông tin giữ blocked. S01 store bytes không đổi. Đây là **handlers production thực thi trên mock synthetic**; không phải LLM hoặc xác nhận nghiệp vụ. Evidence `m1-c/`, `m1-python/`.

## Safety và compatibility

103 H1 tests đã chạy lại, gồm receipt/T0/seal/T3 crash trước/sau COMMIT, lost ACK/unknown; hai preparers cùng/khác intent; hai resumers trước/sau seal; CAS Model và AS-head stale riêng; plan bindings/hash/version/nhiều plan/finalized outcome; lexical/resource guards, blocked, wrong refs; hot journal/cache spill, wrong receipt identity, migration reservation và progress read-only. Những guards này giữ semantics đã review ở a1; hai counterexamples mới đã được kiểm bằng V4.

Kiểm độc lập thêm trên **checkpoints a1 thật**, mỗi backend một bộ: finalized a1 từng nhận candidate 50.001 refs vẫn đọc đúng outcome lịch sử, không sửa hồi tố; cả prepared và sealed a1 bị a2 từ chối unsupported handler trước mutation/rebuild/finalize. Command/events/stages và DB bytes giữ nguyên. Đây là version pin `s02-2a-h1/0.5.0a2`, không migration/repair checkpoint. Xem `version-c/RESULT.json`, `version-python/RESULT.json` và `check_version_boundaries.py`.

L1 schema/helpers nguyên byte + differential a3; E1 owner-profile dispatch, A1 snapshot/source archive, A2 DIRECT/CARRY/REPLACEMENT, current/history refs, identity/unique/CAS được đối chiếu qua code invariants và oracle hồi quy. H1 entry vẫn giới hạn fresh/full scope, không tự nhận lịch sử Answer/Review/A2 của H3.

## Giới hạn và bước tiếp theo

Nghiệm thu này không chứng minh chất lượng phân tích nghiệp vụ/LLM, renderer, performance/SLA, real disk-full/power loss, adversarial namespace replacement hay stress ngoài matrix H1. H2 partial scope/G2 mở rộng, H3 lịch sử E1 và bước 5–9 cần phạm vi riêng; không mở operational/live.

**Đã hoàn tất mốc lớn: H1 đạt kỹ thuật local/synthetic, có thể chuẩn bị commit mốc này.** Cập nhật docs trạng thái hiện hành trỏ tới biên bản mới; giữ bàn giao/evidence cũ nguyên trạng. User quyết định commit/push. Auditor không sửa implementation, stage, commit, push hoặc bắt đầu H2/H3.
