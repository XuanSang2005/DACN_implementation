# H2-A implementation report

## Căn cứ và phiên bản

HEAD trước sửa `67134fa6f3198282fed650d817d865b792228742`, index rỗng, worktree sạch theo [snapshot](/Users/macbookpro/.codex/.chatgpt-projects/g-p-68c38c8799f48191a101e19a975ca4f9/outputs/implementations/s02-2a-h2-a-0.6.0a1-2026-10-25/before.status.txt). Không reset hoặc sửa công việc ngoài phạm vi. Inventory trước sửa gồm 13.146 file hiện có (Git-visible và reports giữ trên đĩa); phạm vi chính xác trong [manifest](/Users/macbookpro/.codex/.chatgpt-projects/g-p-68c38c8799f48191a101e19a975ca4f9/outputs/implementations/s02-2a-h2-a-0.6.0a1-2026-10-25/before.inventory.json). Không tuyên bố bao phủ toàn filesystem/dataset.

Proposal giữ nguyên `s02-2a-h2/0.1.0-draft.2`, SHA `490ed4f0ce3b9979fb8e7c06ef5f1e1113183dcbd67c8a23d6ecdd3ce62d9dcd`. D01/D02 đã đóng ở mức thiết kế; người dùng chấp thuận D1–D4 và giao riêng H2-A. Package mới `0.6.0a1` để tách H1 a2. Canonical contract/profile/rules/DB2 không đổi; private H2 versions giữ draft.2. Schema/registry/dependencies/locks/S01 không sửa.

## Thay đổi thực thi

| File | Vị trí chính | Hành vi |
| --- | --- | --- |
| `h2_limits.py` | Limits:24, references:46, Budget:80 | Giới hạn chung invocation, đếm occurrences, slot chống tính đôi input, exact codec/lexical preguard |
| `h2_contracts.py` | SourceInventory:60, HoldSelector:109, BindingRequest:166 | Full obligation family/criteria; selectors bền với graph; closed pins |
| cùng file | AuthorityContext:214, Grant:227, ConstructionPermit:259, Evidence:294 | Trust context ngoài payload; typed input từ caller đã kiểm; evidence inspection/independence |
| `h2_graph.py` | ModelContext:42, closure:167, reverse_impact:259, impact:292 | Context Part + cả row; full discovered Part action_ids; context/causal uses tách riêng; base+candidate/removals |
| `h2_candidates.py` | schema:14, scope_request_hash:24, parse_candidate:44 | Closed unit candidate, all-inventory inspection, typed local/base read allowlist, scope/raw pins; không dựng Model |
| `h2_policy.py` | materialize:96, admit:211, assess_union:217 | Before/post coverage, nguồn/holds/authority, append rights, closure hợp cuối; guard_required khi union fail |

Các file ở `packages/s02/src/dacn_s02/`. Không sửa helper H1/L1 dùng chung. Candidate projection dùng bản copy schema H1; không thay schema H1/canonical. Metadata `pyproject.toml` và `__init__.py` đổi version/mô tả; toàn module H1, repository/DB2/CLI cũ giữ byte. Không có command H2 mới.

`h2_fixtures.py` và bốn `test_h2_*.py` là synthetic handwritten fixtures/test-only. Production không import test helpers. Expected sets/conditions viết độc lập trong assertions: A1/A2/A3/Parts/workflows, family/criterion source refs, holds và reason codes; không dùng closure/impact chính nó để dựng expected scopes.

## Controls trước/sau và các phản ví dụ

H2-A là chức năng mới; không dùng oracle H1 làm kết quả baseline partial-policy. Baseline H1 chỉ full scope. Trong test H2-A: chọn U+V trả V allowed, U held và global blocked; graph rỗng với unknown-global không cho V tiến; đầy đủ source basis + trusted grant cho V pre-Parts. Sharing C/R không kéo A1 sang V; explicit C/Actor blocker, Support A1 hoặc unknown thì V bị chặn. Part P12/P23 mở toàn A1/A2/A3 tới fixed point. Swap mapping nguồn/chuyển Part/thay membership/removed dependency làm đổi impact; set reorder/revision-only không tự làm stale semantic context.

Sau builder-fixture, append mapping độc lập có thể qua trong khi U vẫn hold; Part bridge A1/A2 khiến cả selected candidate `guard_required`, không truncation/publish. Source/context edit và successor headers sai bị reject. Old Issue/pending role không miễn unassigned action/gap; permit chỉ waiver construction được caller kiểm provenance, không đóng Issue hoặc cấp review.

Các controls raw hashes/base Model+AS/selectors, provider/version/control hash, missing/uninspected criterion, source family đầy đủ, exact metadata Decimal, payload trusted giả, malformed/limits/deadline giữ fail-closed. Đây là kiểm code bằng synthetic inputs, không đánh giá prose/nghiệp vụ thật.

## D1–D4 được thực hiện đến đâu

- D1: tuple/context/grant/evidence matching thuần; không LocalSyntheticAuthority đọc file, process restart hoặc authentication. Caller tự truyền decision tin cậy; JSON tự khai allow/trusted không có quyền.
- D2: source selectors/current Issue inventory và construction provenance predicate/union outcome thuần. Origin finalized Run/plan lookup, P_guard AS-only revalidation/lifecycle/progress publisher/CAS thuộc B; A không tạo/sửa Issue.
- D3: family toàn criteria, typed closed candidate/append-only guard; scoped-bootstrap/handlers pipeline chưa viết. H1 entry/CLI giữ nguyên.
- D4: caps/budget/serialization primitives và tests, không chứng minh I/O bounded của provider/seal. Deadline cooperative 30 giây/invocation; không timeout hard hay ngân sách cộng qua crash.

## Bảo toàn và giới hạn

[Preservation](/Users/macbookpro/.codex/.chatgpt-projects/g-p-68c38c8799f48191a101e19a975ca4f9/outputs/implementations/s02-2a-h2-a-0.6.0a1-2026-10-25/final/PRESERVATION.json) đối chiếu từng file trước sửa, HEAD/index và design-inputs. [Diff](/Users/macbookpro/.codex/.chatgpt-projects/g-p-68c38c8799f48191a101e19a975ca4f9/outputs/implementations/s02-2a-h2-a-0.6.0a1-2026-10-25/final/change.diff) gồm cả file mới; [package manifest](/Users/macbookpro/.codex/.chatgpt-projects/g-p-68c38c8799f48191a101e19a975ca4f9/outputs/implementations/s02-2a-h2-a-0.6.0a1-2026-10-25/final/package-evidence/manifest.json) kiểm source–wheel–installed và baseline version khác được chọn rõ. Hai build từ copy sạch khớp mọi entry; S01 rebuild bằng accepted a6. Differential L1 chạy nguyên script/fixture lịch sử trên hai interpreters, hai backend.

Chưa chứng minh raw candidate→Model builder fidelity, finalized code-task provenance, current Issue successor rebinding, progress integrity hoặc publication. ModelContext nhận projection caller đã checked, chỉ tự kiểm shape/local refs/source inventory; không whole-graph Run/Change/owner/history verifier. Caller hợp tác phải giữ context/index bất biến sau tạo. H2-B phải ghép candidate parse + admission + builder fidelity + union + whole-graph/CAS, không dùng từng hàm đơn lẻ để publish. Không thực hiện pipeline resume/concurrency/crash/lost-ACK/stale H2; regressions H1 chỉ bảo toàn nền tảng. Không làm H2-B/C/H3/2B/2C/LLM/renderer/live, operational migration hoặc dataset.

Kết quả và lỗi harness (nếu có) được ghi riêng tại [TEST_RESULTS](TEST_RESULTS.md), gồm cả development failures không xoá. **Đã triển khai H2-A, chờ audit độc lập.**
