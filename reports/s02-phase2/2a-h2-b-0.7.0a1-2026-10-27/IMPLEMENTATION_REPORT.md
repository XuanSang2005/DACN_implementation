# H2-B 0.7.0a1 — báo cáo implementer

Phạm vi người dùng giao ngày 27/10/2026: **chỉ H2-B scoped checkpoint mốc đầu**, theo H2 draft.2/D1–D4 đã chốt. Người viết là implementer; **chưa có audit độc lập hoặc nghiệm thu người dùng cho H2-B**. [API/CLI](../../../docs/S02_2A_H2_B_IMPLEMENTATION.md), [điểm vào bàn giao](START_HERE.md).

## Căn cứ và trạng thái trước sửa

HEAD thực tế `9d967d072b2d8c6d7a5d77ceda3670dfb979a456`, working tree sạch. Không lấy commit trước H2-A `67134fa…` làm HEAD. Snapshot/hash trước sửa gồm 338 file tracked/untracked không bị ignore; phạm vi inventory được ghi rõ, không tuyên bố hash toàn filesystem. H2-A wheel đã audit được kiểm SHA-256 `d4e824d66c3066c29d63792d60116c6e8596d96593037bc15f97ff5470ee08e2`.

Đã đọc AGENTS, proposal H2 draft.2, audit thiết kế, hướng dẫn H1/H2-A, audit H2-A a2/findings/erratum và đoạn LaTeX authoritative về làm rõ theo phạm vi. Proposal/evidence lịch sử giữ nguyên; các trạng thái “chờ phê duyệt” lịch sử không mở lại D1–D4.

## Thay đổi

| File mới | Trách nhiệm |
| --- | --- |
| `h2_authority.py` | LocalSyntheticAuthority, read/hash/closed codec, unique exact tuple, external context, deny/unavailable |
| `h2_checkpoint.py` | Metadata private, inventory/selectors, construction provenance, progress và correspondence normalization |
| `h2_store.py` | H2-only entry/parent publisher, T0 compare, raw/config, unique seal, whole-graph preflight, finalized promoted-plan lookup, result/raw checks |
| `h2_builders.py` | Append theo units, toàn rows/criteria, local handle allocations, Issue successors, genuine holds, task predicates, current-ref rebinding |
| `h2_service.py` | Preflight/authority/admit/build/union/guard/revalidate/derive/progress; publication qua repository CAS hiện có |
| `h2_cli.py` | Bảy scoped commands/preview và global authority flags, receipt-first semantics, input/usage handling |

Chỉ sửa payload cũ `cli.py` để dispatch H2 riêng và `__init__.py` để tăng version; pyproject tăng `0.7.0a1`/description. Giữ dependencies, H1 handlers, pure policy H2-A, L1, schemas, registry, DB2, A1/A2 và S01 nguyên byte. Thêm test helpers/worker/47 ca writer H2-B; các assertions/tests lịch sử nguyên byte. Các trang navigation hiện hành dẫn bàn giao mới với trạng thái chờ audit, không sửa biên bản cũ.

## Hành vi và bằng chứng

Source S01 synthetic được tiếp nhận bằng checked lookup và archive. Bootstrap riêng giữ supplied actors, toàn obligation rows, global/scoped construction tasks. Bốn mock đi qua projection/parser/builder thật; U giữ hold, V có progress riêng qua bước 4. Không biến Run blocked thành global completed hoặc accepted_scope; global mapping task chỉ resolved khi mọi row đủ predicate.

Authority do process caller cấp bên ngoài payload/DB. Mỗi pending invocation đọc lại control/hash; checks lặp trước seal và trong transaction trước publication. Binding ghim source, Model+AS, selectors, progress, retained basis, raw lengths/hashes, intent và bảng aliases. Denied/unavailable không tự tạo identity/plan/finalization mới. Finalized replay chỉ đọc outcome lịch sử, không đòi provider.

Union tính trên full candidate và base, gồm meaningful context/impact. Ngoài quyền ghi bị từ chối; thiếu proof/unknown/new hold trong hợp giữ Model cũ và công bố guard AS-only. Mỗi guard có root key/hash origin, finalized origin plan, failed input/context và current lineage. Guard không được đưa vào domain refs. Revalidation là command mới/current pair, không nhận candidate; giữ nguyên business/gap/global task IDs trên cùng Model. Guard thiếu proof giữ open, đủ proof tạo resolved successor; command mới mới được tiếp tục. Output cũ giữ nguyên stage/IDs; revalidation không tăng completed work.

Result assessment ghim base→result Model+AS, hashes, parent assessment, policy/diff/context và output refs. Current progress lấy từ unique finalized publisher của AS; không timestamp winner. Raw projection, allocated IDs và Records được đối chiếu lại khi đọc sealed plan; existing domain/mapping giữ nguyên ngoài current Issue refs và rows được phép điền.

Receipt/T0/seal/T3 và CAS dùng kho E1 hiện có. Race/kill/lost-ACK dùng OS processes và connections riêng, không mock writer. Hai backend dùng instrumentation encoder thật. Các trace và số đo **đã thực thi** xem [TEST_RESULTS](TEST_RESULTS.md); fixtures/analysis/approvals vẫn là **mock synthetic**, không kết quả LLM/nghiệp vụ.

## Giới hạn và nội dung auditor cần review

- Cùng checked snapshot/SourceContext, fresh E1, bước 1–4; không H1 bridge, sửa completed domain output, source switch, H2-C/H3, Answer/A2, LLM, renderer, migration operational/live.
- LocalSyntheticAuthority chứng minh exact invoker tuple và provenance phần mềm; không xác minh danh tính hoặc độc lập ngữ nghĩa thực tế. Các independence dispositions là test control được caller pin.
- Một Budget 30 giây cooperative mỗi invocation, cùng caps draft.2; không hard timeout syscalls hoặc cumulative CPU budget qua crashes. Không hạ assertions/skip hoặc tăng timeout để đạt.
- `requires_domain_edit_outside_h2` trong inspection reason là tín hiệu explicit/conservative của synthetic caller; code còn kiểm structural coverage của retained output. Đây không phải khả năng tự suy luận ngữ nghĩa rằng domain output cần sửa. Tín hiệu chỉ giữ terminal hold, không cấp quyền hay resolve business.
- Filesystem local ổn định/caller hợp tác; tests kill/lost-ACK không chứng minh power loss thật hoặc chống thay namespace ác ý đồng thời.
- Auditor cần đối chiếu raw→result, new/retained holds, guard origin/P_guard/current lineage, derived progress, provider recheck và CAS trên đúng wheel/hash. Implementer không tự đóng finding hoặc ghi nghiệm thu.

Không stage/commit/push, gửi việc sang chat khác, đổi automation hoặc sửa dataset/evidence lịch sử. Sau seal/AUDIT_READY, dừng sửa chờ audit.
