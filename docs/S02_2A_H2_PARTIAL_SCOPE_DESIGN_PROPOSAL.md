# 2A-H2 — giữ scope bị chặn, tiếp tục phần độc lập

Ngày 25/10/2026 · **s02-2a-h2/0.1.0-draft.2** · **Đã sửa thiết kế H2-D01/D02, chờ audit lại; chưa triển khai, chưa được giao code H2.**

Mốc đề nghị: cùng một snapshot S01 synthetic và một head Model/AnalysisSet, giữ nhóm nghĩa vụ thiếu thông tin bị chặn, cho nhóm độc lập có đủ căn cứ đi qua handlers 2→3→4; công bố Model đầy đủ và tiến độ theo scope, reopen/resume/ghép không bỏ holds. Mock/scope assessments synthetic không phải kết quả LLM hoặc xác nhận nghiệp vụ.

Delta draft.2 theo [audit draft.1](/Users/macbookpro/.codex/.chatgpt-projects/g-p-68c38c8799f48191a101e19a975ca4f9/outputs/audits/s02-2a-h2-design-draft1-2026-10-25/AUDIT_REPORT.md): cụ thể hóa D1–D4 thành **phương án được chọn trong proposal**, không còn placeholder provider/revalidation. Đây chưa phải người dùng phê duyệt thiết kế hoặc auditor đóng findings. [Bàn giao delta](../reports/s02-phase2/2a-h2-design-draft2-2026-10-25/START_HERE.md) giữ bản draft.1/diff/hashes riêng.

## 1. Căn cứ và hiện trạng thực tế

- [LaTeX authoritative](EXTERNAL_REFERENCES.md), mục làm rõ theo phạm vi, dòng 366–392: chờ phần phụ thuộc, tiếp tục phần độc lập, xét ảnh hưởng trực tiếp/gián tiếp và kiểm toàn model khi ghép. Đã đọc nguồn local.
- [Plan Đợt2 §7.1 G2](S02_PHASE2_IMPLEMENTATION_PLAN_PROPOSAL.md#71-admission-từng-bước--g2-không-phải-gate-review): inventory trước Parts, source-level holds, publish khác advance, không dùng gate review làm scheduler.
- [Execution draft.2 §7](S02_2A_STEPS_1_4_EXECUTION_DESIGN_PROPOSAL.md#7-mốc-nghiệm-thu-và-các-đợt-nhỏ-đề-nghị): H2 partial/G2 và stress; H3 lịch sử Answer/CARRY/REPLACEMENT tách riêng.
- [H1 a2 đã nghiệm thu local/synthetic](acceptance/s02-2a-h1-0.5.0a2-2026-10-25/AUDIT_REPORT.md): H1-01/02 đóng, safety là baseline bắt buộc. Nghiệm thu H1 không cấp quyền code H2.

| Đã có trong code | H2 còn cần viết sau audit/phạm vi riêng |
| --- | --- |
| h1_candidates: projection đóng, typed handles, exact codec/source inventory | Candidate theo unit; quyền đọc/ghi, không nhận scope mock tự khai làm authority |
| h1_builders: một lượt full scope, holds enumerate toàn Model | Selectors/holds khi graph lớn; builders áp delta vào full Model |
| h1_store.parent_context: parent completed, step/global completed_steps tuyến tính | Entry H2 nhận parent blocked có căn cứ và progress từng unit; không sửa H1 gate |
| scope.closure: mọi action_ids của Part, workflows/Support tới fixed point; reverse_impact bảo thủ | Adapter G2 trước Parts, context index Part–mapping row–source và lặp reverse impact/closure |
| permitted_scope là gate review, đòi mapping proposed/review pins | Không gọi với Review giả hoặc nới gate để lập lịch |
| DB2/receipt/T0/seal/T3/CAS/hot journal/Issue lineage | Private manifests/progress ghim config/plan hiện có, không DDL/claims mới |

closure trả ACTION_WITHOUT_PART trước bước4; reverse_impact không tự biết mọi quan hệ nguồn/mapping row. Helper có sẵn chưa phải admission scheduler hoặc bằng chứng độc lập ngữ nghĩa.

## 2. Phạm vi và đơn vị công việc đề nghị

H2 đầu **local/synthetic, cùng SourceContext/snapshot, fresh E1**, chỉ bước1–4. Đơn vị ban đầu là một requirement family: requirement FR/NFR/constraint và toàn bộ criteria của nó; mỗi criterion vẫn có inventory entry riêng. Không chia row/Part để lập lịch. Dùng snapshot+pointer, không tên/ID prefix hoặc nối index giữa revisions.

D3 chọn **scoped-bootstrap riêng cho H2**, nhận finalized receipt intake S02 start của source đã checked, chỉ khi session fresh/chưa có Model. Hoãn bridge từ H1 bootstrap; H1 prepared/sealed/blocked/finalized không là entry H2. Bootstrap H2 chỉ supplied actors/full inventory/code tasks, không cấp independence. Không thay handler của command cũ.

Mỗi cặp (unit, bước) chỉ dựng một kết quả; bước sau được bổ sung output vào Model successor. Không sửa kết quả của cặp đã hoàn tất, remove/reparent Part đã có, đổi source, apply Answer hoặc tạo Review/consent/A2 history. Bước4 được điền Parts/assessment vào row not_assessed thuộc quyền ghi, không thay row proposed đã có hoặc sửa Model Record cũ. Các ca chỉnh lại phân tích đã công bố dừng tường minh, cần phạm vi riêng; H3/2B/2C/bước5–9/LLM/renderer/live không thuộc H2.

**Advance là quyền làm bước kế trên scope, không phải accepted_scope.** Còn hold ở U thì Run toàn checkpoint có thể blocked dù V vừa dựng hợp lệ. Progress V tách biệt; không ghi global completed_steps1–4 như toàn model đã xong. Hết thời gian/giới hạn không làm U resolved/usable.

## 3. Contracts đề nghị

Các tên/fields là **đề xuất private có version**, chưa là schema canonical phát hành. Object đóng/required; exact codec/typed refs; chỉ chuẩn hóa set để hash, không đổi thứ tự criteria/workflow. H1-01 tiếp tục tính ref occurrences, không unique handles.

| Contract / version đề nghị | Required content / authority |
| --- | --- |
| ScopeRequest — s02-h2-work/0.1.0-draft.2 | Store/session/parent/command; source_context/snapshot/archive hash; expected Model+AS; step; unit IDs/requested source refs; read-context IDs; raw hashes/lengths; handler/scope-rules/limits versions. Unit IDs code-owned, không canonical Records |
| HoldSelector — s02-h2-hold/0.1.0-draft.2 | Current Issue ID/key; nguồn; target step; selector kind/refs; impact_known; evidence binding; code-task role hoặc null. Kinds hữu hạn: obligation_families, explicit_uses, all_source_uses. Unknown ⇒ all_source_uses |
| ScopeAnalysisEvidence — s02-h2-analysis/0.1.0-draft.2 | ID/version; source/base pair+hashes; current Issue/selector hash; step; obligations đã xét; facts/rules/constraints đã đọc; direct/reflected uses; independence pairs+lý do/source evidence; limitations; provenance/trusted caller binding. Candidate không cấp authority |
| H2Candidate — s02-h2-candidate/0.1.0-draft.2 | Version, step, request hash/unit IDs; proposals theo closed H1 projection; questions; inspection đủ toàn inventory; unrepresented_source_refs. Proposals chỉ cho write set, ngoài đó là context đọc |
| AdmissionManifest — s02-h2-admission/0.1.0-draft.2 | Source/base/result pins; một entry mỗi obligation/criterion; holds/selectors/current Issues; progress; read/write sets; direct/closed/reverse footprints; Part↔row↔source context; basis/provenance; exclusions/reasons; input/policy hashes; advanceable units. Code dựng/kiểm |
| ScopedProgress trong plan | Mỗi unit: stage outputs/IDs, assessment_state, latest checked pair, work_completed_through, needs_revalidation, unresolved keys, next_tasks/blocked reasons; quyền bước kế suy từ manifest hiện hành. Không biến scope rỗng thành completed |
| H2 config/plan format mới — D3 | Một primary config T0 pin raw StageRefs candidate/analysis (candidate=null khi revalidate; cả hai=null khi bootstrap), selectors/intent/limits/provider context; raw bytes riêng giữ nguyên. Plan gồm allocations/batch/promotions/admission/progress/guard-only outcome. Không CLI-supplied plan hoặc self-hash Artifact |

Selector giữ nguồn logic cho graph tương lai; materialized physical Scope không thay selector. Missing/uninspected rows, kể cả constraints và criteria, luôn ở toàn inventory. Mapping.not_assessed nói chưa dựng mapping, không tự chứng minh thiếu/đủ thông tin.

### 3.1 D1 — adapter authority local/synthetic cụ thể (H2-D01)

Code chứng minh refs/coverage/version/closure, không chứng minh prose không có nghĩa vụ ẩn. Mỗi hold→independent unit cần basis đã xét đủ nghĩa vụ có thể áp dụng, kể cả ngoài unit. Thiếu edges, candidate khai usable/trusted hoặc tên reviewer đều không đủ. ScopeAnalysisEvidence không là Review, Answer, consent hoặc A2 applicability.

**Chọn adapter builtin `LocalSyntheticAuthority`**, interface API `authorize(BindingRequest) -> AuthorityDecision`. Production chỉ cài parser/tuple matcher generic; test caller dựng approvals/expected scopes riêng, không import fixture/helper vào production. Không plugin loader/import theo tên module, network, LLM hoặc authentication service. Caller hợp tác, sở hữu kho synthetic/test và trust context local; adapter không chứng minh danh tính người thật hoặc tự xác minh nội dung là synthetic. Mọi output ghi synthetic_not_business_confirmation.

Trust context do **invoker tin cậy cấp trực tiếp lúc mở process**, tách khỏi `--config` kho S02, candidate, analysis, receipt và config/plan trong DB:

~~~text
dacn-s02 --config /test/s02.toml \
  --h2-authority-file /test/control/approvals-v1.json \
  --expect-h2-authority-sha256 <SHA từ invoker> \
  scoped-resume --receipt /test/work.json
~~~

Đây là CLI **dự kiến, chưa tồn tại**. Resume chỉ nhận receipt làm work input; hai global authority flags là trust context của process, không thay candidate/evidence/units. API tương đương nhận `authority=LocalSyntheticAuthority(path, expected_sha256)` từ caller, không lấy expected SHA từ DB hay file approvals để khởi tạo trust. Invoker tự chọn flags là ranh giới tin cậy local, không cơ chế chống caller ác ý. Copy authority fields vào candidate/config không cấp authority.

File control read-only/exact codec, object đóng: `format=s02-h2-local-authority/0.1.0-draft.2`, `provider_id`, `provider_version=local-synthetic/1`, `purpose=synthetic_test_only`, `approvals[]`; mỗi approval gồm `binding`, `decision=allow|deny`, `reason` nonempty. Không wildcard, regex, timestamp winner hoặc default allow. Trùng binding, format/version lạ, hash không khớp hoặc file không đọc được ⇒ lỗi authority/3. Một binding khớp duy nhất allow mới được dùng; deny hoặc không có entry khớp ⇒ denied/2. File không chứa semantic verdict thay ScopeAnalysisEvidence; chỉ caller quyết định đã kiểm basis synthetic nào.

**BindingRequest đóng**, so exact normalized sets (không bỏ duplicate đầu vào):

| Trường bắt buộc | Ý nghĩa ghim |
| --- | --- |
| purpose, provider_id/version, policy_version | Local synthetic; `s02-h2-scope-rules/0.1.0-draft.2`; không đổi owner profile |
| store_id, session_id, source_context_id, snapshot_id, archive_sha256 | Đúng checked source/store; không dựa tên path |
| base_model_id/hash, base_analysis_set_id/hash | Cặp đầy đủ, không chỉ Model |
| operation=step\|revalidate, goal, step, unit_ids | `goal=build\|admission\|retained_output`, selected family và toàn criteria |
| current_selectors_sha256, progress_before_sha256, retained_assessment_hashes | Toàn current hold selectors và progress/basis được tái dùng, kể cả ngoài unit |
| read_write_intent_sha256, candidate_sha256/length hoặc null/0, analysis_sha256/length | Đúng raw work intent; revalidate không candidate. Hashes không tự chứng minh semantics |
| guard_keys/current_guard_ids (set), assessment_policy_version | Revalidate đúng guard/current lineage; step không được lách guard đang mở |

Binding key SHA-256 trên exact encoding của tuple. AuthorityDecision đóng gồm status=allow|deny|unavailable|invalid, binding_key, provider identity/version/control SHA (null khi chưa đọc được), reason nonempty; allow/deny có đủ pins. Unavailable/invalid⇒3; allow/deny⇒kiểm binding và xử lý theo bảng dưới. Không bắt exception rồi default allow. Random command/Run IDs và times không thuộc approval tuple để hai preparers cùng logical intent dùng một approval, vẫn bị CAS/identity invariants kiểm. Chuẩn hóa sets chỉ để bind sau khi đã kiểm unique; order criteria/workflow và raw bytes giữ nguyên.

**Trình tự authority/effects:**

1. Read-only checked identity/source/current metadata, byte lengths/hashes và selectors/progress trên base; không parse candidate/analysis trước T0. Parse file control có bounds riêng (§6.2), xây tuple từ request/code-owned metadata. Authority allow **trước tạo receipt/T0/staging** cho work semantic. `scoped-bootstrap` code-only là ngoại lệ rõ: không analysis/provider/independence, vẫn toàn safety H1.
2. T0 tạo/so toàn intent trong transaction; pin context identity/version/control SHA cùng raw StageRefs. Authority object/key chỉ pin, không là bằng chứng tự xác thực cho process sau. Candidate+analysis parse/build sau T0. Evidence nội dung thiếu inventory/basis vẫn held/guard dù tuple được allow.
3. Mỗi process prepare/execute/resume chưa finalized phải tự mở lại provider bằng flags/API tin cậy, kiểm đúng original context SHA và authorize tuple đã pin. Kiểm lại trước seal và ngay trước T3 publication; không chỉ dựa allow đã lưu trong plan. File control mỗi phiên bản bất biến; thêm approvals cho command mới ⇒ file mới/SHA mới, giữ file cũ cho pending commands.
4. Nếu đã seal: dùng nguyên IDs/plan, verify binding/plan/result correspondence; không build plan khác khi provider unavailable/deny. Checked absence trả5 trước khi đòi provider, vì chưa execute work. Receipt-only chưa prepare cần `prepare-scope-work` với full original/new explicit intent và context như H1; checked absence=5 khác unknown=3.
5. Finalized progress đọc checked Run/plan/promotions không cần provider, chỉ báo outcome lịch sử + current pair/is_current, không cấp eligibility mới. Finalized resume trả outcome gốc (blocked→2), không gọi provider để viết lại lịch sử.

| Thiếu/sai gì | Outcome và effects |
| --- | --- |
| Thiếu context, provider unreadable/unavailable/quá budget, original provider/hash/version sai | 3; chưa prepare thì không receipt/T0; đã prepare/seal thì giữ operation/raw/plan nguyên, không finalize/domain publication |
| File hợp lệ, tuple sai evidence/base/units/selector/policy hoặc explicit deny | 2; cùng quy tắc không effects, không tự cấp identity khác; current head thay thì CAS còn kiểm riêng |
| Analysis/raw trong DB sai hash, nhiều plan/khác version | Integrity/unsupported3; không sửa bytes hoặc hỏi provider để hợp thức hóa corruption |
| Truyền analysis/candidate mới cho scoped-resume | Usage64 trước effects; muốn đổi input cần command mới, current pair và approval mới |
| Provider chỉ có allow cũ khi current source/base/selector/progress đổi | Không có exact allow→2; không tìm ancestor approval. Đối với work đã pin base cũ, đúng allow cũ vẫn cần CAS và có thể finalized stale/2 |

Missing một trong hai global flags là usage64; cả hai vắng cho semantic work là authority_unavailable/3. Không silently fallback. Nếu file đổi sau seal/giữa checks: SHA mismatch3, không giữ grant chỉ vì đã từng allow. Stable local filesystem/caller hợp tác như H1; không hứa chống thay namespace ác ý đồng thời hoặc hard I/O timeout.

### 3.2 Quyền ghi và inventory toàn Model

- Bước1 thêm Issues/AS, không sửa S01; supplied actors giữ đủ/đúng nguồn.
- Bước2 thêm actors candidate/actions/workflows/data/rules của units đã pin. Base ngoài quyền ghi giữ nội dung/IDs; context refs có allowlist đúng kiểu. Namespace handles có unit, tránh hai mock local handle trùng.
- Bước3 thêm components/responsibilities trong write set. Mọi action hiện có phải assigned, có gap Issue thật hoặc pending-construction task/hold đúng unit/provenance. “Ngoài request” không cho bỏ action khỏi đối soát toàn Model.
- Bước4 điền đầy đủ các row được chọn còn not_assessed trong Model successor; giữ row ID/source binding, code cấp Parts IDs. Rows held/chưa làm vẫn not_assessed+Issue; không import model fragment làm full Model.
- Nếu cần, code tạo scoped tasks “chưa chạy bước3/4”. Exemption phải đúng key/predicate/version và **công việc đang dựng**, không waived ở gate review. Genuine unassigned gap sau candidate bước3 có hold riêng như H1 a2; không đổi nhãn thành pending work, không mượn old Issue/pending-mapping.

Bootstrap mapping task toàn Model giữ nguyên predicate: chỉ resolved khi mọi row có Parts/assessment proposed. V xong bước4 không giải quyết task toàn cục nếu U còn not_assessed. Scoped progress chỉ ghi việc của V; không thu hẹp Issue cũ, đổi status/key hoặc dùng tiến độ này để miễn review gate.

## 4. Xác định ảnh hưởng và advance

Trên cùng M/AS: I là inventory nguồn, H là holds/current Issues, S là units request, C(M,S) là closed footprint, W là delta thực được phép ghi. Chỉ advance khi source/base/evidence current, mỗi obligation có disposition, tasks cần thiết đã xét và C(M,S) không chạm blocking uses của H cho nhiệm vụ ấy.

### 4.1 Trước Parts

1. Xuất I từ checked snapshot; không bỏ null/[], nguồn, priority hoặc criterion.
2. Đối chiếu từng hold với toàn I; materialize từ traces, actors/actions/rules/data/workflows và basis ngữ nghĩa. Chưa biết uses ⇒ toàn graph hiện có + all_source_uses cho graph tương lai.
3. Vùng held chỉ giữ unknown/draft để chỉ ra câu hỏi, không tự gán permission/actor/rule thiếu. Phần có căn cứ độc lập mới advance.
4. ACTION_WITHOUT_PART trước bước4 là output chưa dựng, không proof độc lập và không đòi toàn bước2–3 có Parts. G2 adapter dùng inventory/basis; không sửa closure/permitted_scope để bỏ lỗi review.
5. Xét shared facts/data/rules. Cùng dữ liệu không tự tạo Dependency; dependencies bước5 chưa được phân tích không có nghĩa không phụ thuộc.

### 4.2 Có Parts/workflows/Support — fixed point

Nhận graph đã validate cấu trúc. Dùng closure hiện có và adapter G2:

    seed source uses/actions/Parts
      → mọi Part chạm một use
      → TOÀN BỘ action_ids của TỪNG Part vừa phát hiện
      → rules/workflows và mọi reachable branch
      → actual Support.required_action_ids/mappings liên quan
      → reverse impact từ delta có nghĩa
      → lặp trên hợp kết quả tới khi không còn tăng

Không chỉ mở seed Part hoặc bỏ action/Part cuối để né blocker. Shared component/interface/responsibility chỉ là context, **không tự kéo mọi action của chúng**. Context vẫn thuộc basis; chính nghĩa/rule/boundary đó đổi thì xét lại uses có căn cứ, không so JSON node đơn lẻ.

H2 đầu đi mọi reachable branch, không chọn nhánh để né hold. Support required_action_ids=null, branch/impact không rõ hoặc mất ref ⇒ undetermined, không advance. Không invent Dependency/Support để có proof. Đầu vào ngoài capability entry phải bị từ chối tường minh.

### 4.3 Blocking uses khác context, không bỏ qua current blocker

Issue.affected có thể gồm context; Issue.blocking giữ uses/Parts cần hold, là subset của affected. New H2 Issue scopes phải phản ánh selectors/basis; không ghi component chung thành blocker rồi âm thầm bỏ khi gate. Current Issue thực sự blocking component/actor/rule mà thiếu căn cứ thu hẹp vẫn giữ bảo thủ.

Hai actions chung component không tự phụ thuộc; Part chứa cả hai, workflow nối chúng, rule/actual Support cần action kia thì phải đi theo. Constraint applicable-to-system luôn tham gia; constraint chưa rõ applicability ⇒ all_source_uses dù chưa có system Part.

### 4.4 Context index, reverse impact và giữ lại tiến độ

Index H2 riêng giữ **Part payload + mapping row identity/source_ref/assessment/issue links/membership**, cùng relations thuộc basis. Swap mapping sources, reparent Part, thêm bridge hoặc đổi responsibility membership có thể đổi footprint dù Part/component JSON giữ nguyên. Tập source refs tổng không đủ.

Tính delta có nghĩa trên **base lẫn candidate**, xét quan hệ cũ bị xóa và mới thêm; reverse impact rồi closure/union lại tới fixed point. Reorder sets/revision pin đơn thuần không tự đổi nghĩa; criteria/workflow order không được coi là set. Một lần reverse_impact chưa phải toàn thuật toán G2.

Pair đổi làm evidence/progress trước stale. Chỉ dựng **derived assessment** nếu cùng nguồn, correspondence basis/context đầy đủ, changed/reverse footprint không tác động scope, current authority approve đúng retained basis hashes và post-merge checks pass. Ghi from/to pair, parent assessment, diff/context hashes theo §5.3; không giả human review. Thiếu proof/context đổi có nghĩa ⇒ needs_revalidation/guard. `scoped-revalidate` đánh giá output cũ mà không dựng lại output; cần sửa domain output thì terminal/out_of_scope trong H2 (§5.2), không âm thầm copy done.

## 5. Ghép và công bố

Không có head riêng cho scope. Ghép là áp delta vào **full current Model** trên base pair đã pin, kiểm toàn graph/current selection, CAS cặp head như H1.

~~~mermaid
flowchart LR
  B[Checked source và full Model AS] --> P[Pin request raw basis tại T0]
  P --> A[Admission và dựng delta]
  A --> U[Ghép full candidate và kiểm union]
  U -->|đủ proof| S[Seal một plan]
  U -->|ảnh hưởng chưa rõ| G[Guard AS-only giữ hold]
  U -->|sai refs hoặc quyền ghi| R[Rejected giữ raw]
  S --> T[T3 whole graph check và CAS]
  G --> T
  T --> O[Run outcome và progress từng unit]
~~~

Trước seal/T3 phải: rematerialize mọi selector trên candidate có phần tử mới; tính C(M,S1∪S2) lại (không cộng cờ pass); giữ full inventory/criteria; kiểm W/context/source correspondence; giữ mọi current key/hold/task predicate; validate Model/Change/AS/profile/refs; đối chiếu progress với result pair. Ngoài W chỉ có rebind code-owned do Model/Issue successors, không sửa nội dung.

**D2 chọn fail-closed:** sai schema/ref/ngoài quyền ghi ⇒ rejected, giữ raw, không domain publication. Candidate hợp cấu trúc nhưng bridge/impact chưa đủ ⇒ không publish candidate Model; seal **guard-only AS successor** trên base, thêm guard kỹ thuật theo §5.1, Run blocked, không tăng completed work. Không trỏ guard base tới candidate IDs chưa tồn tại; dùng source selectors/surviving IDs. Lưu guard lỗi/commit unknown vẫn theo H1, không tự sửa plan. Guard không cố ý là dead end: chỉ command AS-only riêng §5.2 được revalidate, không thay input của resume.

Không tự cắt lại candidate khi chỉ một phần request đủ điều kiện; caller gửi command mới có scope/input tường minh. Partial continuation là chọn đơn vị trước build, không truncate mock/criteria/Part/holds.

Run còn semantic hold/unrepresented/technical work ngoài unit ⇒ blocked/exit2 dù S có output hợp lệ; result phân biệt work_completed_through(S), unresolved(U), next_tasks. Không gán user_accepted; bước4 chưa tự mở bước5–9/S03.

### 5.1 Guard/task có provenance và vòng đời riêng (H2-D02)

Guard root do code cấp `issue_key=h2.guard.<sha256(origin_command_id ASCII)>`, canonical `kind=analysis_omission`, `status=open`, DIRECT với carry/replacement=null. Key dài73 ký tự, không nối command ID tùy dài để vượt ID cap128. Private plan origin ghi command/Run, guard root/current IDs+key, source/base pins, failed candidate/analysis hashes, policy, selector, reason code, impacted units và predicate `h2.merge_assessment/1`. Phải đối soát origin finalized guard-only Run, artifacts/hash và toàn current lineage; prefix/kind/candidate tự nhận không đủ để nhận là guard kỹ thuật. Collision/provenance hỏng⇒integrity3, không cấp key khác để giấu lỗi.

Guard chỉ tham chiếu AS và private manifest/progress; **không đưa guard ID vào Model/mapping/Part trace hoặc candidate domain aliases**. Vì vậy xử lý guard trên cùng Model được AS-only; input đòi ghi guard vào domain graph bị rejected. Technical source refs không rỗng, giữ original refs và bổ sung basis khi footprint tăng. Unknown→all_source_uses; mọi physical Scope do code materialize, blocking⊆affected. Trong bước chưa có Parts vẫn giữ selector để chặn uses tương lai.

| Loại/state | Transition được phép và predicate |
| --- | --- |
| Scoped construction task open | Đúng origin/role+unit+step+policy, chỉ task “chưa chạy builder” của stage đang dựng được admission loại khỏi business gate; predicate tự nó chưa resolved |
| Task step3→resolved | Handler đúng unit đã account mọi action: assigned hoặc genuine gap có Issue hold riêng; task chỉ chứng minh đã dựng/đối soát, gap vẫn chặn |
| Task mapping(unit)→resolved | Mọi requirement+criterion row của unit có Parts/assessment proposed; mọi gap vẫn có current Issue. Global bootstrap mapping task chỉ resolved khi predicate này đúng cho **toàn inventory** |
| Guard open, evidence chưa đủ | scoped-revalidate tạo open successor cùng key; selector/affected/blocking giữ hoặc mở rộng theo impact, không thu nhỏ để đủ; resolution=null. Progress held/needs_revalidation, không domain edit |
| Guard open, P_guard đủ (§5.2) | Resolved successor cùng key trên current Model; blocking rỗng, affected/source basis giữ; AS mới vẫn chọn key resolved, không xóa guard |
| Guard resolved, Model/AS mới | Revalidate/derived-check đúng pair. Nếu proof thiếu, open successor cùng key/current lineage; không phục hồi cờ eligible cũ hoặc tạo A2 carry |
| Business hold/genuine gap/global mapping task chưa đủ predicate | Không thuộc quyền resolve của scoped-revalidate; giữ status/key/predicate/scopes, chỉ code-owned current-ref rebinding nếu Model successor |

Global mapping task không chặn chính builder bước4 trên unit đã admitted chỉ vì builder đang tạo Parts, nhưng vẫn open/global blocked khi chưa đủ toàn inventory. Exemption admission này ghim role/predicate/provenance, không miễn business/gap/guard cùng kind và không miễn gate review hoặc tự cho bước kế.

Mọi thay đổi Issue tạo ID mới, supersedes=current ID, cùng issue_key/model hiện hành; Records cũ không sửa. AS giữ đủ current keys, kể cả resolved. Trên AS-only, business/gap/global tasks giữ **chính IDs/bytes**; scoped tasks chỉ được resolve ở đúng builder predicate, không vì evidence gọi “technical”. Trên Model successor, tạo/rebind successors chuẩn, không thay nghĩa business holds. Không dùng status A2 resolution_pending_revalidation cho progress private.

### 5.2 Command revalidation và predicate khép kín

Chọn `scoped-revalidate` với **command/receipt mới** trên expected current Model+AS, explicit units/guard keys, `goal=admission|retained_output`, step, analysis raw+SHA và external authority. Không nhận candidate/domain delta. Goal admission đánh giá quyền thử bước chưa làm sau khi có prerequisite outputs; goal retained_output yêu cầu output stage đó đã tồn tại và đánh giá lại nguyên output ấy. Không sửa output của cặp (unit,bước) đã hoàn tất; đánh giá lại không phải lần build thứ hai.

`P_guard(G,E,M,AS)` chỉ true khi đồng thời:

1. G có provenance/predicate/lineage H2 guard chuẩn, current trong AS; E và authority tuple pin **current** pair/source/progress/selectors, đúng tất cả guard keys cần xử lý. Goal/step hợp với progress/prerequisites.
2. E xét đủ mọi obligation/use trong selector của G, inventory toàn cục kể cả constraints/criteria và failure context/delta hash gốc. Không resolve một guard bằng coverage của subset request. Mọi use có disposition có căn cứ: độc lập cho nhiệm vụ này hoặc held bởi **business/gap/task riêng vẫn tồn tại và có scope đúng**; không còn unknown về chính phép kiểm ảnh hưởng kỹ thuật của G. Business applicability unknown toàn cục không cho V advance.
3. Rematerialize selectors; closure/reverse/union/context Part–row–source trên current graph và context delta gốc. Không dùng candidate bị chặn chưa publish làm graph hiện hành. Báo rõ bỏ candidate cũ; resolved guard **không authorize** replay/publish candidate đó.
4. Retained domain outputs, nếu có, giữ nội dung/local IDs/source association; Records cũ nguyên byte. Nếu Model successor chỉ rebind revision/current Issue refs do code, diff phải chứng minh đúng phần rebind, đáp ứng structural/coverage/policy và không cần domain edit. Mọi progress muốn coi current có result correspondence §5.3. Không tăng work_completed_through.
5. Predicate kiểm đủ chính guard, source-only technical reason có nonempty source refs và private assessment. Không Answer/application/Review/A2 record. Canonical DIRECT resolved giữ source-only rule đã pin; schema hợp lệ riêng không là bằng chứng P_guard.

P_guard true⇒resolved successor với resolution mô tả code checked technical assessment, trace.source_refs đủ, answer_ids=[], resolution_event_refs=[], carry/replacement=null. P_guard false vì proof thiếu⇒open successor với selector giữ/mở rộng và reasons. **Cả hai** publish AS successor + assessment/progress + Run/artifacts qua T3 CAS; không Model/Change/domain output. Command lặp đúng receipt trả cùng outcome/IDs; command mới dù proof lặp vẫn là phép đánh giá explicit, không background retry. New AS giúp progress có một publisher rõ, không chọn theo timestamp.

Nếu cần đổi action/rule/responsibility/Part/mapping proposed/source hoặc trả lời business để hợp thức hóa output: outcome blocked/2 với reason `requires_domain_edit_outside_h2`, guard vẫn open, progress terminal_out_of_scope cho H2. Không promised recovery/sửa output trong H2; cần scope H3/đợt thích hợp riêng. Goal retained_output nhưng output chưa có hoặc cố build lại completed pair⇒rejected/2, không AS publication.

Revalidate có thể resolved guard kỹ thuật nhưng V vẫn `assessed_held` vì business/gap thật; giữ đủ blockers, không miễn chúng vì kind giống nhau. Khi V được admit, tạo **scoped-step command mới**, raw/approval mới trên AS vừa publish; old blocked command finalized không đổi. Không resolve global mapping task khi U còn not_assessed.

### 5.3 Progress và bind assessment vào result pair

Progress nằm trong private sealed plan, không Record/schema/head mới. Current progress lấy từ **unique finalized H2 publisher**: finalized event promote đúng plan Artifact, plan.batch.records chứa đúng AS record hiện hành và plan.batch.head đúng cặp, actual Records/Run outcome chứng minh batch đã publish (không stale/rejected). Kiểm hashes/parent progress chain; promotions chỉ dành cho Artifacts, không gọi AS là Artifact; không chọn Run có timestamp mới nhất hoặc chỉ cùng result_pair. AS hiện hành từ entry khác/thiếu hoặc nhiều publisher⇒unsupported/integrity3 trước H2 effects.

| assessment_state | Output/work history | Quyền đi tiếp |
| --- | --- | --- |
| pending | Chưa có output stage | Chỉ prerequisite/admission có proof mới cho build |
| current | Output đúng current pair hoặc admission checked | Chỉ selected scope không chạm business/gap/guard blockers; không accepted_scope |
| assessed_held | Technical assessment đủ nhưng business/gap/task còn liên quan | Không advance phần bị chặn; scope độc lập khác vẫn xét riêng |
| needs_revalidation | Work completed lịch sử giữ; output chưa có proof current | Không dùng làm prerequisite usable cho bước kế, phải revalidate |
| terminal_out_of_scope | Output cần domain edit hoặc source switch | Không build lại/release trong H2; unresolved/guard giữ |

Mọi progress needs_revalidation phải trỏ ít nhất một current technical guard có provenance, không chỉ cờ private vô căn cứ. Guard-only trước build giữ completed_through cũ; retained-output invalidation giữ danh sách output gốc/IDs nhưng needs_revalidation. Revalidate thành công chỉ đổi assessment_state/current pins/eligible_next; không tăng stage. Global Run vẫn blocked/2 khi U hoặc global technical work còn hold, dù V current/được admit. Read-only progress/0 trình last_checked_eligibility gắn pair/Run và eligibility_authorized_in_process=false; không giả quyền hiện hành hoặc completed toàn Run. Chỉ execution với tuple/authority hiện tại mới cấp admission cho work đó.

**Không vòng hash:** analysis input pin base pair, không phải caller đoán result IDs. Sau allocation, code tạo assessment trong plan với input binding key, base→result pair, hashes canonical Model/AS result, parent assessment/hash, policy, diff/context correspondence và output refs. Model/AS không chứa hash của assessment/plan đó; plan không nhúng hash Artifact của chính nó. Provider authorize base facts + exact inputs + policy/correspondence rule, **không** tự approve một result tùy ý: code chỉ derive result assessment nếu transition đúng §4/§5, whole graph và P_guard checks pass. T3 kiểm lại result pair/authority/CAS; mismatch⇒không publish. Current pair đổi sau đó chỉ được giữ progress bằng derived proof đủ hoặc explicit revalidate mới.

## 6. Resume/concurrency/crash, CLI và limits

- D3 chọn H2 opt-in config/plan/handler dispatch riêng (`s02-h2-config/0.1.0-draft.2`, `s02-h2-plan/0.1.0-draft.2`; handler package version chốt lúc được giao code). E1 owner dispatch tường minh; không canonical schema/registry/DB2/S01/locks mới. WorkRequest.scope=null **không là full permission**; private selector/intents code-checked authoritative cho scheduler.
- Receipt s02/2 create-only trước T0; receipt-only không pin input. Checked absence⇒not_prepared/5; unknown⇒3. Explicit prepare trên receipt ấy, không cấp identity khác.
- T0 checked BEGIN IMMEDIATE absent/existing+compare toàn logical intent trong một transaction: mode/goal/step/units/read-write selectors, pair/source, candidate+analysis raw hashes, one primary config, authority context, policy/limits/progress/guard IDs. Cùng intent giữ reserved Run/raw/config; khác intent rejected/2, không lấy ID/time của preparer thua làm identity mới. Các raw StageArtifacts có mặt theo mode dùng staging hiện có, không thêm bảng hoặc primary config thứ hai.
- Seal transaction kiểm 0/1/nhiều plan; bind allocations/IDs/times/admission/assessment/guard batch. Chỉ một plan hợp lệ được dùng nguyên. Không rebuild/reject-plan thay thế sau seal vì deadline/provider unavailable/head khác.
- Hai workers dù disjoint cùng base chỉ một T3 CAS thắng; bên thua finalized stale/2, chỉ artifacts/Run, không AS/guard/domain dự kiến. AS-only revalidate cũng CAS cả Model+AS; thiếu provider trước finalize thì chưa execute/finalize, không coi là stale đã commit. Caller muốn resubmit cần command/current pair/input/approval mới, không auto rebase/resend.
- Finalized dùng checked Run/event/promotions/actual pair; thiếu/hỏng metadata/version⇒fail closed, không timestamp/repair. Đọc lịch sử không đòi old base còn head, không biến lịch sử thành current eligibility.
- Kế thừa receipt/T0/seal/T3 trước/sau COMMIT, kill/lost ACK/unknown, identity, hot journal, reservation và progress read-only; toàn safety ngay writer H2-B, kể cả guard-only/revalidation/union correctness.

### 6.1 D3 — CLI/exit codes cụ thể, chưa implement

Global authority flags ở §3.1 dùng cho mọi semantic command chưa finalized; store `--config` hiện có không được thêm Settings keys. Mọi create command đòi receipt mới; expected-pair phải bằng checked parent/current pair, không auto lấy head khác khi caller pin cũ.

| Lệnh dự kiến | Work input / hành vi |
| --- | --- |
| scoped-bootstrap | --from-receipt finalized intake, --receipt mới; code-only fresh H2, không H1 bridge/provider |
| scope-plan | --from-receipt current H2, --step, --unit; read-only preview/last_checked_eligibility, eligibility_authorized_in_process=false; không authorize tuple mới, prepare luôn kiểm full inputs/binding |
| scoped-step | --from-receipt current, --expect-model/--expect-analysis-set, --step, --unit lặp, --mock-response/--expect-sha256, --analysis/--expect-analysis-sha256, --receipt mới; goal=build |
| scoped-revalidate | Cùng parent/pair, --goal admission\|retained_output, --step, --unit, --guard-key lặp, --analysis/--expect-analysis-sha256, --receipt mới; không --mock-response/candidate |
| prepare-scope-work | --receipt cũ checked absence, --mode bootstrap\|step\|revalidate và full mode-specific intent như trên; chỉ T0 prepared/0 |
| scoped-resume | --receipt; chỉ input đã pin và external process authority; finalized đọc original outcome |
| scoped-progress | --receipt; read-only, lịch sử/current/head và assessment/holds; finalized không cần authority |

Codes: 0 completed command/đọc progress/prepared; 2 rejected/denied/blocked/stale/conflict; 3 failure/unknown/unsupported/integrity/provider unavailable; 4 file/receipt not_found (authority file thiếu là3); 5 checked valid receipt chưa có operation; 64 usage/flags không phù hợp mode. Business held và missing proof hợp lệ để tạo guard là blocked/2; provider deny trước work là denied/2 không publication. Provider unavailable không tự finalize failed Run. Guard/revalidate AS commit có thể work complete nhưng global blocked/2.

### 6.2 D4 — bounds và cách đếm, không reset theo unit/vòng

Chọn policy H2 local riêng `s02-h2-local-limits/0.1.0-draft.2`, kế thừa trần H1, không sửa h1_limits/legacy verifier. 1 MiB=1.048.576 bytes. Không flags nới/reset, không Settings mới.

| Đối tượng | Trần/cách đo |
| --- | --- |
| Work raw | candidate+analysis **cộng** ≤1MiB đúng bytes đọc; revalidate candidate=null/0. Mỗi command tối đa1 candidate, auto-repair0 |
| Authority control | ≤1MiB bytes, đọc/hash/parse local bounded; approvals lookup exact, không network/cache authority từ DB |
| Request+candidate+analysis+provider decoded inputs | Depth≤64, string UTF-8≤64KiB, tổng values≤100.000 (object/list/scalar mỗi occurrence; keys không values), không reset khi chuyển input/unit |
| References input | Tổng occurrence≤50.000 cho request/selectors/candidate/analysis/control-file bindings, không deduplicate. SourceRef hoặc typed handle atomic=1, không đếm snapshot_id bên trong lần nữa. *_id strings, *_ids arrays, finding_handle(s)/questions dùng H1 rule; thêm issue_key/guard_keys/unit-key progress maps, explicit unit-pair endpoints và retained assessment refs theo closed H2 fields. Declared new output id/handle, hashes/version/time không ref. Unknown field bị reject, không bỏ qua |
| Serialized config / plan | ≤2MiB / ≤16MiB **exact encoded bytes**, kể cả raw StageRefs/pins/escapes/metadata. Analysis raw riêng, không nhét raw string để vượt string cap; không chỉ đo decoded prose |
| Result Model+current Issues / manifest+progress+assessment | Mỗi aggregate≤50.000 ref occurrences bằng cùng counter H2 cho private fields; Model/Issues vẫn phải qua H1 bounds hiện hành. Manifest/assessment JSON values/string/depth cùng caps, toàn progress/guards trong plan bytes bound; số units≤source families≤1.000 obligations gồm criteria |
| Graph | Entities≤2.000; workflow nodes≤2.000/edges≤4.000; Parts≤4.000; findings≤500/candidate, current Issues kể cả resolved≤2.000 như H1 |
| Compute | Một Budget 30 giây monotonic **mỗi invocation**, bắt đầu trước provider/preflight, dùng chung qua input parsing/provider hash+lookup/closure/reverse/union/all units/plan checks; check theo chunk/worklist và trước/sau exact codec/callback. Không tạo Budget mới mỗi unit/phase/fixed-point round |

Fixed point dùng worklist trên domain hữu hạn (inventory/element/node/Part/Issue/selector-use IDs), chỉ enqueue khi tập tăng; cache theo exact pair/policy trong invocation, không clear visited để lặp vô hạn. Bounds/timeout gặp ở bất kỳ vòng nào không là proof fixed point. Deadline cooperative như H1, không preempt syscall; provider I/O/SQLite wait có thể vượt wall time, khi trở về kiểm lại và không publish bằng budget đã hết. Không quảng cáo hard timeout.

Trước T0, quá raw/authority/input-preflight cap⇒không prepare; sau T0 parse/compute/result cap⇒giữ raw, nếu chưa seal có thể seal rejection nhỏ/finalize rejected/2 theo H1. Provider authority/budget unavailable⇒3, không tự tạo semantic rejection. Sau seal, deadline/binding thiếu không thay plan/finalize theo input khác, resume invocation mới có Budget mới nhưng nguyên raw/plan/limits; không hứa cumulative CPU budget qua crashes. T3 vẫn kiểm authority/CAS/graph; không được nhờ đã seal mà miễn check. Trần result/plan vi phạm là fail closed, không truncate collections/evidence/Parts.

Safety B tối thiểu2 independent processes cho prepare/resume/CAS/lost ACK. Stress C chốt đề nghị4 workers và ≥20 explicit checkpoints trong bounds, không auto iterations. Correctness union/bridge/revalidation **phải có ngay B**; C chỉ mở rộng tải/stress, không làm gate đầu an toàn muộn hơn.

## 7. Invariants cho oracle độc lập

| ID | Bất biến |
| --- | --- |
| I1 | Snapshot/archive/pointers, supplied actors, unknowns/priority/criteria và toàn inventory không mất |
| I2 | Mọi current Issue key kể cả resolved giữ; Model đổi tạo successors/current refs đúng; không nhập H3 history |
| I3 | Source selector sống qua graph rỗng/lớn; unknown applicability không bằng không ảnh hưởng |
| I4 | Mọi Part phát hiện mở hết action_ids; workflow/Support/reverse closure lặp và kiểm hợp cuối |
| I5 | Không kéo mọi action vì context chung; không bỏ causal/source evidence để làm scope nhỏ |
| I6 | Độc lập từng phần không suy độc lập sau merge; xét Part–row–source và target context |
| I7 | Ngoài W giữ nội dung/IDs, rebind có provenance; không drop row/cắt Part/đổi scope né blocker |
| I8 | Gap có hold riêng; code-task exemption không do candidate/kind/alias; pending work khác genuine gap |
| I9 | Progress trên pair/basis đã kiểm; giữ done qua merge cần derived proof, không release semantics |
| I10 | Một authoritative head pair/plan/final Run; receipt/raw/identity/CAS/resume H1 không suy yếu |
| I11 | Selected work done, global blocked, chưa review là thông tin khác nhau; không Run enum mới |
| I12 | Trust/version/limits/integrity unknown fail closed; không tự tạo Review/Answer/consent/quyền live |
| I13 | Provider allow từ process context ngoài payload; missing/deny/version/hash không dùng grant DB làm fallback |
| I14 | Revalidate chỉ technical guard có full provenance/P_guard, không business/gap/global-task exemption |
| I15 | Revalidate không tăng completed stage/sửa output; result assessment bind từ base qua code-owned transition, current progress có unique AS publisher |

## 8. Phản ví dụ và controls dự kiến — chưa chạy

Expected scopes lập riêng từ fixture/source, không gọi chính helper đang test để tính kỳ vọng.

| Case | Expected |
| --- | --- |
| R-cancel thiếu quyền, R-view đủ facts/không phụ thuộc cancel | Cancel held; view qua2→3→4 nếu basis đủ; toàn Run blocked |
| Hai actions chung C, không rule/workflow/Part/Support cần nhau | Không kéo action kia chỉ vì C; đổi nghĩa C sau đó phải xét lại basis |
| P1(A1), P12(A1,A2), A2 held | Seed P1 chạm P12, mở A2 ⇒ không advance. Thêm P23(A2,A3) kiểm lặp tiếp |
| S1/S2 riêng có proof, union thêm bridge tới held A3 | Recompute union; guard-only blocked, không publish Model/cờ done cũ |
| Constraint unknown khi chưa action, sau đó thêm action | all_source_uses bắt action mới; graph rỗng không cấp independent |
| Same Part JSON/tổng nguồn, swap sources hai rows hoặc reparent | Context changed, không structural reuse; entry append-only từ chối edit |
| Chỉ reorder sets/revision pins | Có thể derived proof giữ progress; không bỏ order criteria/workflow |
| New use thuộc selector cũ, Support required_action_ids=null | Rematerialize; unknown held, không dùng thiếu edge làm proof |
| Requirement có Parts, criterion chưa xét; bỏ NFR/constraint vì priority | Inventory fail/hold, không local-complete family sai |
| Gap trỏ old nonblocking Issue/pending-mapping, hai gaps chung task | Hold riêng từng gap, current lineage, không mượn exemption |
| AS-only đổi Issue/assessment khi worker đang chạy | Stale dù Model không đổi, raw/command giữ, không merge |
| Foreign snapshot/ID hoặc ghi held unit bằng read-context alias | Rejected; quyền đọc không thành quyền ghi |
| Concurrent same/different scope intent, resumers, crash/lost ACK | Ma trận H1 đủ scoped paths, một plan/Run, unknown khác absence |

### 8.1 Traces đề nghị đóng H2-D01 — kỳ vọng, chưa chạy

| Trace | Expected outcome/effects |
| --- | --- |
| Allow đúng tuple/context; prepare→seal→kill trước T3; process mới chỉ receipt+external flags cũ | Re-authorize exact tuple, dùng nguyên operation/Run/raw/config/plan/allocations; T3 publish tối đa1; fresh process progress đối soát đúng pair |
| Thiếu provider ở prepare / ở sealed resume | 3; trường hợp đầu không receipt/T0, trường hợp sau toàn prepared state giữ; không plan/identity mới |
| Provider file hợp lệ nhưng sai base/AS/unit/selector/analysis hash/policy entry | Denied2 trước effects/publication; không chọn entry ancestor/wildcard hoặc semantic trusted=true |
| Sai provider version/file SHA, file thay sau seal | 3; không dùng allow đã lưu, không mutate/finalize; phục hồi **file gốc** và retry cùng receipt mới tiếp tục |
| Analysis DB bytes thay hoặc truyền --analysis mới cho resume | Integrity3 hoặc usage64; không reinterpret plan. Candidate JSON tự khai allow không cấp authority |
| Đã finalized blocked, provider unavailable; read progress/resume | Progress0 chỉ historical/current status; resume trả blocked2 gốc, không mutate hoặc ghi lại permission |
| Approvals boundary/50.000 refs vs50.001, nhiều units/fixed-point/provider cùng deadline | Đúng trần vẫn chạy nếu mọi check khác đủ; vượt tổng bị từ chối/3 theo phase, không reset counter/budget để qua |

### 8.2 Traces đề nghị đóng H2-D02 — kỳ vọng, chưa chạy

1. **Guard→thiếu proof:** U business-held; build V phát hiện impact chưa rõ, candidate Model không publish. AS1 chọn G(open)+U và progress V chưa tăng. `scoped-revalidate` E1 được authorize nhưng coverage thiếu ⇒ AS2/G1(open,supersedes=G), V held; U chính ID/status trên cùng Model, raw cũ nguyên.
2. **Guard→đủ proof→V tiếp tục:** E2 trên current M/AS2 xét đủ selector, held U có scope riêng và chứng minh V không phụ thuộc; P_guard đủ. AS3/G2 resolved(supersedes=G1), current selection giữ U+G2, Model không đổi, V admission current nhưng completed stage chưa tăng. New scoped-step/current tuple tạo V output hợp lệ; U vẫn hold, global mapping task chưa resolved nếu U rows not_assessed; global Run blocked2. Candidate bị chặn trước đây không được auto publish.
3. **Output cũ→needs_revalidation:** V đã xong bước3; candidate ở scope khác làm lộ thiếu căn cứ về context của V, nên chỉ publish guard-only AS, không Model candidate. Output IDs/bytes giữ, guard/progress needs_revalidation; goal retained_output đủ structural+semantic basis⇒AS-only/current assessment, V không bị build bước3 lần hai. Nếu cần đổi responsibility/action/Part⇒terminal_out_of_scope/2, guard open, không domain edit.
4. **Giả exemption:** business Issue/genuine unassigned gap/global mapping task cùng kind/prefix giả hoặc một guard không đủ provenance; scoped-revalidate không được resolve, invalid target rejected2 (corrupt provenance3); exact business/gap/current refs và predicate giữ nguyên.
5. **Durability/CAS:** lặp revalidate cùng receipt sau lost ACK⇒cùng AS/Issue/Run; kill trước/sau seal/T3⇒0/1 publication. Một writer đổi **chỉ AS**⇒bên cũ stale2, không publish resolved successor/assessment dự kiến. Provider unavailable trên sealed revalidation⇒3, có thể tiếp tục sau cấp lại đúng context, không rebuild plan.

Các traces dùng oracle expected inventories/sets do auditor/caller độc lập lập, không gọi cùng scope helper để sinh kỳ vọng. Scenarios là synthetic software expectations, không kết quả đã đo hoặc xác nhận business.

## 9. Tiêu chí nghiệm thu implementation đề nghị

1. S01 test store+mock scoped responses qua handlers thật, ≥2 families: held U và V độc lập tới4; đủ rows/criteria/Issues/unknowns, reopen/resume. Không canonical fixture import thay handlers.
2. Trước/sau Parts, graph lớn và merge có selectors/basis/footprint/closure/reasons/hash; kiểm I1–I15, mọi positive/negative §8/§8.1/§8.2; có unknown-global path thực sự không advance và independent path thực sự tiến.
3. Holds/tasks/current selection đúng sau Model-change/AS-only; giữ gaps. Không user confirmation. Chạy H1-01/02/V4 và oracle mapping-context P1, không hạ expectations.
4. **Toàn safety ngay entry H2 đầu có effects:** C/Python factory instrumentation, process/connection riêng; prepare/resumers races; stale Model/AS; guard-only/normal rollback; kill/lostACK/unknown T0/seal/T3; finalized authority, corrupted/multiple plans/hot journal identity.
5. Full S02/S01 phù hợp; oracle P1/P2/P3/H1 nguyên hash/assertions (known harness fail báo riêng), differential L1 a3; wheel non-editable ngoài source, source–wheel–installed/METADATA/WHEEL/direct URL, clean copied builds, locks nguyên.
6. Logs/cwd/env/exit/JUnit, độc lập expected scopes, inventory/diff/hashes/giới hạn. Báo riêng timeout, không sửa timeout/skip/xfail/retry để viết lại full outcome. Chỉ kiểm phần mềm synthetic, chưa semantic quality/LLM/live.

## 10. Các đợt nhỏ cần giao riêng sau audit

| Đợt đề nghị | Deliverable / gate |
| --- | --- |
| H2-A: pure scope policy | Contracts/selectors/context index/impact/admission trước/sau Parts + fixtures §8, chưa command ghi DB. D1–D4 dùng phương án cụ thể draft.2 sau audit/người dùng duyệt; pure tests chưa là pipeline |
| H2-B: scoped checkpoint mốc đầu | Fresh2 families → held U, V tới4; builders/progress/CLI/provider/revalidate/guard-only/T0/seal/T3, toàn union/bridge/derived-proof correctness §8. **Toàn safety của writer bắt buộc ngay B** |
| H2-C: merge/revalidation/stress | Nhiều units/checkpoints trong limits, new bridges/context negatives/derived trace/explicit stale resubmission. 4 workers/≥20 checkpoints theo D4; không dời correctness/safety của B sang C |

Không batch nào tự bao gồm H3/Answer/application/LLM/renderer. Mỗi đợt cần giao implementation riêng; version package/handler phát hành chốt khi có scope code. Lượt này không phát hành wheel.

## 11. D1–D4: phương án cụ thể draft.2, chờ phê duyệt

| ID | Đã chọn trong proposal để audit, chưa là quyết định của người dùng | Tham chiếu/gate |
| --- | --- | --- |
| D1 | LocalSyntheticAuthority builtin; external invocation flags/API+immutable approvals hash; exact tuple/rebind mỗi process và trước publication, finalized đọc lịch sử | §3.1/§8.1, gate H2-D01 |
| D2 | Guard-only AS; scoped-revalidate AS-only/new command, P_guard/current lineage, assessment-only retained output; domain edit là terminal H2 | §5.1–5.3/§8.2, gate H2-D02 |
| D3 | Families/toàn criteria, fresh same-source/H2 bootstrap riêng, hoãn bridge H1; private scope=null không cấp permission; modes/CLI/dispatch riêng; không auto rebase | §2/§6.1; không cần lựa chọn H1 bridge để đạt mốc |
| D4 | H1 caps + tổng work raw1MiB/control1MiB, counters evidence/selectors/serialized bytes, một Budget chung invocation; C4workers/≥20checkpoints, B correctness+safety ngay đầu | §6.2, boundary/provider/worklist traces |

**Gate yêu cầu auditor xem xét đóng từng finding ở mức thiết kế:**

- **H2-D01:** adapter/CLI/API+trust boundary và tuple không mơ hồ; trace positive prepare→seal→restart→resume dùng nguyên identities/plan; mọi negatives §8.1 có exit/effects cụ thể, authority không đến từ payload/DB; provider labels synthetic. Lượt này chỉ walkthrough tài liệu; kiểm thực chạy phải có ngay H2-B nếu được giao.
- **H2-D02:** các transition/predicate task/guard/progress đủ cả giữ hold, resolve kỹ thuật với U vẫn blocked và retained-output assessment/terminal; current lineage/source-only reason/CAS/result derivation rõ; repeat/lost ACK/stale AS không thêm publication. Các traces §8.2 và union/bridge correctness là gate B, không hoãn C.

Còn cần **audit lại draft.2 và người dùng chấp thuận các phương án D1–D4, sau đó giao riêng implementation từng đợt**; chưa coi findings đóng hoặc H2 đủ quyền code. Authentication/evidence persistence nghiệp vụ thật, bridge H1/history/A2, sửa domain output/source switch/H3 và operational/live vẫn ngoài scope. Nếu implementation buộc đổi canonical schema/DB2/A2 semantics, dừng và nêu xung đột review riêng; không tự mở contract.
