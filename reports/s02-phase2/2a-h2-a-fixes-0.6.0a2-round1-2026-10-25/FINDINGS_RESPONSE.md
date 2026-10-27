# Phản hồi audit H2-A a1 — vòng sửa 1

`dacn-s02 0.6.0a2`, source trước sửa là worktree a1 chưa commit tại HEAD `67134fa6f3198282fed650d817d865b792228742`, index rỗng. [Inventory](/Users/macbookpro/.codex/.chatgpt-projects/g-p-68c38c8799f48191a101e19a975ca4f9/outputs/implementations/s02-2a-h2-a-fixes-0.6.0a2-round1-2026-10-25/before.inventory.json), [status](/Users/macbookpro/.codex/.chatgpt-projects/g-p-68c38c8799f48191a101e19a975ca4f9/outputs/implementations/s02-2a-h2-a-fixes-0.6.0a2-round1-2026-10-25/before.status.txt). Mọi thay đổi có sẵn được giữ; không reset/stash/stage/commit/push. Snapshot trước sửa được đối chiếu toàn bộ với after.inventory của bàn giao a1. Version và wheel a1/evidence lịch sử không ghi đè.

Nguồn `user_manual`, dispatch `c7294c612cda66f6bd4bb45460b83cba80c8af8c2b77b91d9069310cc89c5eca`, vòng sửa 1. [Prompt](/Users/macbookpro/.codex/.chatgpt-projects/g-p-68c38c8799f48191a101e19a975ca4f9/outputs/coordination/h2-a/migration-new-session-2026-10-25/FIX_ROUND_1_NEW_SESSION.txt), [audit](/Users/macbookpro/.codex/.chatgpt-projects/g-p-68c38c8799f48191a101e19a975ca4f9/outputs/audits/s02-2a-h2-a-0.6.0a1-2026-10-25/AUDIT_REPORT.md). Không ghi state/counter; không tự đóng findings. Proposal draft.2/D1–D4 và các private version/rules IDs giữ nguyên; sửa cách thực thi các điều kiện đã chốt.

## S02-2A-H2-A-01

**Nguyên nhân:** `_evaluate` reclose cả U+V rồi phát tán `union.reasons` sang mọi unit, làm lỗi closure riêng U thành lý do chặn V. Dù direct blockers đã kiểm từng unit, NEEDS_REANALYSIS/SCOPE_UNDETERMINED vẫn lan sai.

**Sửa:** `packages/s02/src/dacn_s02/h2_policy.py:117` (`_evaluate`, vùng union gần dòng 198): giữ source seeds và footprint của toàn request để inspect; gate từng unit trước, rồi reclose hợp **eligible units** từ seeds gốc để kiểm quyền trước build. Không suy causal attribution bằng phép trừ tên reason. Chỉ gắn lỗi của hợp eligible vào các units ấy. Per-unit tests và unknown/business/source holds không bỏ.

**Trước/sau:** a1 U state needs_clarification/needs_reanalysis hoặc unknown Support U ⇒ U+V không có allowed unit. a2 trả U blocked, V allowed khi đủ inventory/independence/grant, global blocked giữ nguyên. Khi candidate đã dựng, `assess_union` vẫn atomic: selected unit nào fail thì toàn candidate held, không cắt lấy phần pass.

**Bằng chứng:** oracle v2 nguyên byte có ba ca sửa + controls V-only; regression mới mở rộng tới workflow state, giữ full footprint actions A1/A2 và unit reasons V rỗng; bridge/Support thật ảnh hưởng V vẫn chặn. Logs a1/a2 và JUnit ở [TEST_RESULTS](TEST_RESULTS.md).

## S02-2A-H2-A-02

**Nguyên nhân:** `assess_union` đã tính impact trên base/candidate nhưng chỉ dùng `source_changed`. Source mới V và read alias A1 bị hiểu thành quyền thay đổi nghĩa A1 ngoài request. JSON existing node không đổi chưa đủ chứng minh semantics không đổi.

**Sửa:** `h2_policy.py:228` (`assess_union`, meaningful gate cuối hàm): dùng causal uses/actions/active Parts của **cả delta.before và delta.after**, neo quyền tác động existing IDs vào closure của source units trên **base**. Post-closure không tự cấp quyền bằng Part/workflow bridge mới. Outside base write footprint ⇒ rejected (hoặc giữ guard_required khi post gate đã yêu cầu hold); meaningful impact chạm current hold hoặc undetermined ⇒ guard, không allowed toàn candidate.

New node được source-write kiểm riêng, không buộc mọi component mới phải đã có Part. Khi đối chiếu logical holds dùng causal uses/active Parts; context dùng chung không đổi không kéo mọi action. Blocker explicit trên Actor/component/Part vẫn áp dụng cả khi context đó không là causal use. ConstructionPermit chỉ được dùng trong predicate đã có, không tự tạo Review hay sửa immutable Records.

`h2_graph.py:259` (`reverse_impact`): membership action_ids của **changed/new Responsibility** cũng seed actions bị assign trước khi có Part trỏ nó. Chỉ reverse meaningful delta làm việc này; ordinary shared responsibility context không mở mọi actions. Cách sửa tránh chỉ nhận đúng NewRule fixture. Các đường removal dùng graph cũ, addition dùng graph mới; append-only vẫn từ chối edits/removal đã ngoài scope.

**Trước/sau:** new Rule nguồn V/action A1 của U held: a1 assessed/allowed V, a2 rejected/held. Rule chỉ A2 V tiếp tục allowed. New Responsibility áp A1/A2 có controls tương tự; shared component/responsibility không đổi không lan U; Part bridge mới không tự mở quyền.

**Bằng chứng:** oracle v2 giữ nguyên chuỗi closed parser → pre-admit → canonical Model semantic checks → impact → union. Test mới kiểm rule/RS memberships, base pin, Part bridge và atomic post outcome. Không provider I/O/builder/DB writer H2.

## S02-2A-H2-A-03

**Nguyên nhân:** base Model + current Issues có cap, candidate Model riêng có cap, nhưng aggregate candidate Model + current Issues bị bỏ. Footprint refs không thay mọi occurrence của full result.

**Sửa:** `h2_policy.py:65` (`_aggregate`) dùng đúng Budget.inspect trên `{model: full_model, current_issues: list(issues)}`; `_current` dùng cho base, `assess_union` dùng cho candidate ngay trước impact/outcome. Giữ cùng Budget, caps/default50000, exact codec và counters; không reset/charge lại input, không truncate.

**Bằng chứng hành vi:** default input 49.916 refs hợp lệ, candidate Model 49.618 + Issues 425 = 50.043 ⇒ `S02Error.error["code"] == "H2_LOCAL_LIMIT"`, reason refs, traceback qua `_aggregate(candidate, issues)`. Result 49.991 được allowed. Reduced cap190/result204 bị từ chối; cap204/result204 được allowed. Regression mới dùng literal expected aggregate204 và kiểm input counter không đổi; oracle exact examples replay ở [C](/Users/macbookpro/.codex/.chatgpt-projects/g-p-68c38c8799f48191a101e19a975ca4f9/outputs/implementations/s02-2a-h2-a-fixes-0.6.0a2-round1-2026-10-25/final/limits-replay-c.json), [Python](/Users/macbookpro/.codex/.chatgpt-projects/g-p-68c38c8799f48191a101e19a975ca4f9/outputs/implementations/s02-2a-h2-a-fixes-0.6.0a2-round1-2026-10-25/final/limits-replay-python.json), raw counts trong [logs](/Users/macbookpro/.codex/.chatgpt-projects/g-p-68c38c8799f48191a101e19a975ca4f9/outputs/implementations/s02-2a-h2-a-fixes-0.6.0a2-round1-2026-10-25/commands).

**Vấn đề oracle cần auditor xem xét:** `test_independent_h2_a_limits.py:35` dùng `error.value.code`. `S02Error` đã pin tại `packages/s02/src/dacn_s02/errors.py:6` chỉ có `.error`; CLI và tests hiện hành dùng `.error["code"]`. Hai case negative nay bắt đúng S02Error rồi thất bại tại accessor, thành **2 fail + 2 pass/backend**; đây không phải oracle pass. File/hash/assertions giữ nguyên. Không thêm alias vào API H1/L1 hoặc đổi h2_limits để đạt assertion này. Replay gọi nguyên `example` của oracle, **không thay test assertion**, ghi exception/error/traceback và source hash; chỉ là phản chứng diagnostic. Auditor quyết định erratum/đóng finding, implementer không tự quyết.

## Bảo toàn, phương pháp và phần chưa chứng minh

[Diff](/Users/macbookpro/.codex/.chatgpt-projects/g-p-68c38c8799f48191a101e19a975ca4f9/outputs/implementations/s02-2a-h2-a-fixes-0.6.0a2-round1-2026-10-25/final/change.diff) so đúng snapshot trước sửa a1, gồm cả files mới; không dùng Git HEAD làm baseline giả khi a1 chưa commit. [Preservation](/Users/macbookpro/.codex/.chatgpt-projects/g-p-68c38c8799f48191a101e19a975ca4f9/outputs/implementations/s02-2a-h2-a-fixes-0.6.0a2-round1-2026-10-25/final/PRESERVATION.json) kiểm file cũ, toàn H1/L1/DB2/S01/schema/registry/locks/tests cũ, proposal và a1 seal/evidence. Production chỉ sửa hai module H2 (policy/graph), metadata version; thêm một regression file. Chỉ navigation/API docs hiện hành cập nhật, handoff cũ nguyên byte. Một agent hỗ trợ review read-only, không sửa/chạy tests/build; root là implementer duy nhất.

Build/venvs/tests/backends chạy tuần tự; không dùng verifier mặc định đang chạy C/P song song. Bộ checks vẫn là E1 adapter và conftest/assertions hiện có. Tách baseline repro, development failures, final results và harness diagnostics; không báo counts lịch sử là kết quả mới. Full release evidence tại [TEST_RESULTS](TEST_RESULTS.md).

Chỉ pure scope policy, synthetic, cùng checked snapshot. Caller vẫn phải cung cấp checked source/history/provenance và external authority. Chưa có H2 CLI/provider file I/O/bootstrap/handlers/writer/progress/receipt/seal/CAS/revalidation publisher; chưa chứng minh H2 restart/concurrency/crash/lost ACK. H1 regression không là bằng chứng pipeline H2. Không H2-B/C/H3/2B/2C/LLM/renderer/live/dataset/operational/migration. **Đã sửa, chờ audit lại; chưa nghiệm thu.**
