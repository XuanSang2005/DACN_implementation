# H3-C — delta private continuation, draft.1

Ngày 01/11/2026 · **C-P01 PROPOSED — cần audit trước implementation phụ thuộc.** Đây là mốc contract của scope H3-C người dùng giao; chưa có C builders/result checker/writer hoặc wheel C. Không ghi C đã được audit/nghiệm thu. [Bàn giao và kết quả diagnostics](../reports/s02-phase2/2a-h3-c-contract-review-2026-11-01/START_HERE.md).

Căn cứ: [H3 draft.2 §3–7.1/E01–E24](S02_2A_H3_E1_HISTORY_DESIGN_PROPOSAL.md), [B-P01](S02_2A_H3_B_CHECKPOINT_CONTRACT_DELTA_PROPOSAL.md), [baseline B a2](../reports/s02-phase2/2a-h3-b-fix-0.10.0a2-2026-11-01/START_HERE.md) và audit B a2 ngày01/11. H3-A đã nghiệm thu pure; B a2 đạt audit delta, finding01 CLOSED. Audit a2 chỉ chạy7 ca/backend mới, không full regression a2. Quyền H3-C đến từ yêu cầu riêng hiện tại, không suy từ audit B.

Đã kiểm HEAD `9a1a44e8bebccda085604dc371b91c2db33b08f1`, snapshot457 files hiện có, giữ toàn working tree B chưa commit. Đã đọc nguồn LaTeX theo [EXTERNAL_REFERENCES](EXTERNAL_REFERENCES.md), dòng362–449: tiếp tục phần độc lập có căn cứ, giữ unresolved issues và kiểm toàn model. Không dùng dữ liệu phòng khám làm kết quả chạy. Các controls dưới đây đều local/synthetic.

## 1. Gate được xác định trên B a2 nguyên byte

| Điểm trong contract/checker hiện hành | Hệ quả cho C |
| --- | --- |
| `h3_checkpoint_contracts.validate`: Config/Binding chỉ adopt hoặc revalidate; candidate=null, goal khác build | Không thể cấp quyền Model bằng approval AS-only. Đổi mode ở caller vẫn bị `b_as_only_mode`; đây là giới hạn đúng của B, không finding B mới |
| `h3_checkpoint_checks.result/admission`: Model bằng nguyên base; result stages/outputs lấy từ verified parent/anchor | Không có result rule cấp **công việc mới** từ raw candidate. Không được điền output mới rồi gọi checker B như thể retained output |
| `h3_bindings.check_admission` A draft.2: whole progress bằng provenance projection; reader B nhận marker draft.3 | Relabel B parent thành A không giữ được semantics/result assessments. C cần bridge version riêng, giữ exact promoted B parent bytes; không backfill/reseal parent |
| H2 `scope_request_hash` nhận closed BindingRequest H2; H3 có history/registry/parent pins khác | Giữ shape candidate H2 không tự định nghĩa hash domain C. Cần chốt mapping scope request và read/write allowlist; không bỏ `scope_request_sha256` check |
| `verify_guard_origin` chỉ guard H2/key/predicate/plan H2. GuardOrigin H3 bắt buộc `origin_plan_sha256` nonnull | C cần guard riêng. Nếu copy nguyên origin object vào chính introducing plan, hash đầy đủ của plan lại bao gồm hash đang khai. Chưa có protocol định nghĩa pin lúc tạo để tránh chu kỳ này. Không đặt hash0, giả H2 guard hay bỏ kiểm để qua gate |

Các boundary checks giữ chức năng đúng của A/B/H2. **Không kết luận canonical A2 không biểu đạt được continuation.** Hai detached positive controls mới đã qua canonical validators: Model DIRECT→CARRY và Model REPLACEMENT complete structural continuation. Chúng không append domain output, không có C handler/writer, không thay proof raw fidelity hoặc safety C.

Diagnostics mới từ chính release B a2 non-editable, fresh venv/locks offline: **8 pass +1 failure harness mỗi backend**, C rồi Python. Failure do test mới dùng regex `scope_intent_fields` trên `str(S02Error)` trong khi H2 lưu reason trong `error.details`; không sửa/rerun để đổi failure thành pass. Probe riêng lưu structured error, không tính thành test pass. Xem [failures/limits](../reports/s02-phase2/2a-h3-c-contract-review-2026-11-01/FAILURES_AND_LIMITS.md). Không suy diagnostics thành C đã đạt gate.

## 2. Dispatch và entry đề nghị

Đề nghị C private Config/Plan/Admission/policy/work/authority/analysis **draft.4**, handler `s02-2a-h3-c/0.11.0a1`; package dự kiến `0.11.0a1` chỉ phát hành sau khi gate này được chốt và implementation được kiểm. Không phát hành/bump version trong lượt contract. Registry protocol draft.1, History/Anchor và numeric limits hiện hành giữ byte/semantics.

| Đối tượng | Marker/handler và trách nhiệm |
| --- | --- |
| H2 origin/anchor, H3-A input, B publisher | Dùng reader gốc đúng version. Unsupported/mixed version fail closed; không chuyển bytes sang draft.4 để đọc |
| C Config/Plan/Admission | `s02-h3-{config,plan,admission}/0.1.0-draft.4`; handler trên. C reader/checker riêng |
| C work/authority/analysis/policy | `s02-h3-work/0.1.0-draft.4`, `s02-h3-local-authority/0.1.0-draft.4`, `s02-h3-analysis/0.1.0-draft.4`, `s02-h3-history-policy/0.1.0-draft.4` |
| C parent metadata | Union đóng của **actual B Admission draft.3** hoặc **actual C Admission draft.4**, kiểm theo actual finalized/promoted parent. Shape union không cấp capability. Không chấp nhận A projection làm result parent |

API đề nghị `ContinuationService(settings, historical_reviews=ReviewTrustContext(...), authority=LocalSyntheticContinuationAuthority(...))`, với `inspect`, `prepare`, `step`, `revalidate`, `resume`, `report`. Không CLI. Tên/version ở đây là đề nghị để audit.

C `prepare` nhận mode=`step|revalidate`, step1..4, units không rỗng sorted/unique. Step goal=build, candidate bytes bắt buộc; revalidate goal=admission|retained_output, candidate=null. C không nhận adopt; entry arbitrary checked E1 đi qua **explicit B adopt**. C parent phải actual B/C publisher đúng current pair/source. C `anchor=null`; provenance đã pin trong verified parent chain. Existing output không anchor tiếp tục stage0/unassessed/held xuyên chuỗi; C không tái dựng stage từ appearance. Revalidate sau một C publication đi qua reader C; không gọi B reader với C bytes.

Semantic authority C là lane/version riêng. Approval B, A hoặc bare boolean không cấp quyền C, kể cả cùng pair/raw. External historical registry vẫn load trước mọi checked read, R all-store cố định khi pending; pin trong DB không là nguồn trust.

## 3. Delta shapes tối thiểu cần chốt

Giữ toàn canonical E1/L1 schema/registry/DB2 và fields của các Records. Private field sets B/A giữ cho lane cũ. Với draft.4 mới:

1. Config giữ field set hiện có; thay constants/mode gates ở §2, `parent_metadata` là union versioned kể trên, không nullable ở C, `anchor` chỉ null. Config/result assessments không ghi đè parent. Binding/Authority/Analysis giữ field set, dùng constants C và crosschecks §4.
2. Plan giữ field set hiện có, thêm required `candidate_projection`: null ở revalidate và raw rejection chưa có projection; nếu step dựng được projection thì object đóng ở bảng dưới. Batch/promotions vẫn chỉ chứa Records thực dự kiến publish; hypothetical discarded Model không phải canonical Record trong batch.
3. Admission giữ field set, nhưng `guards` cho phép legacy H2 GuardOrigin đã được B kiểm hoặc **CGuardOrigin** đóng. `tasks` chỉ tiếp nhận inherited H2 TaskOrigin đã có provenance; lượt C không tạo predicate/permit type mới. Findings/business holds mới không được dùng như construction permit. Việc resolve technical task được result checker kiểm riêng theo đúng predicate/unit/target step đã pin, không dùng ngoại lệ đó giải DIRECT nghiệp vụ.

| `candidate_projection` field — đều required | Kiểu/invariant đề nghị |
| --- | --- |
| candidate_sha256 | Hash exact candidate bytes đã pin T0; không hash JSON serialize lại |
| local_bindings | Map handle→typed Alias; unique identity/type và deterministic correspondence với raw handles, kể cả workflow members/findings/Parts; không caller canonical IDs |
| pre_successor_model | Record Model hoặc null. Step1=null; steps2–4 là full code-built candidate trước typed current-Issue rebind. Chỉ private reconstruction evidence, không tự cấp graph validity hoặc publication |
| pre_successor_model_sha256 | `digest(pre_successor_model)` hoặc null đúng lúc Model null |

ID allocation được lấy tường minh từ sealed batch/projection: model/change/set, successor theo từng base current key và handles mới. Checker kiểm unique/fresh so T0, reserved Run/plan Artifact khác mọi allocation, exact times và typed raw→projection→result reconstruction. Không lấy arbitrary status/proof body trong plan làm đầu vào builder. Findings mới có key code-owned `h3.finding.` + `digest([command_id,step,handle])`; guard có key `h3.guard.` + SHA256 ASCII command. Không dùng key/prefix như bằng chứng origin.

**CGuardOrigin** giữ các fields `issue_id, issue_key, origin_command_id, root_issue_id, source_context_id, base_pair, failed_candidate_sha256, failed_analysis_sha256, predicate, origin_plan_sha256`, thêm required `version='s02-h3-guard-origin/0.1.0-draft.1'` và `origin_plan_artifact_id:ID`. Chỉ C variant cho `origin_plan_sha256:Hash|null`; legacy variant vẫn Hash nonnull.

Ở introducing C plan: hash=null, origin_command bằng own command, Artifact ID bằng allocation.plan_artifact_id, root nằm đúng batch/base Model và candidate_outcome=guard_only. Exact finalized promotions/plan bytes/result checker xác minh origin; không cần hash chính object đang chứa nó. Lệnh sau **đọc** introducing Artifact ấy từ actual finalized event và kiểm SHA thực; result guard origin của lệnh sau pin SHA nonnull. Config parent vẫn giữ nguyên introducing metadata null, không sửa bytes cũ. Hash null ở inherited origin, Artifact khác introducing plan, giả predecessor/key/predicate hoặc thiếu finalized event đều reject. C reader dùng visited/shared depth Budget và không tự gọi lại chính publisher để cấp origin capability. Predicate C duy nhất ở lượt này đề nghị `h3.continuation_union/1`.

Đây là thay đổi contract cần audit, không phải authorization để nới `verify_guard_origin`/schemas A/B. H2 guards vẫn qua đúng verifier H2/B. C guard không xử lý Answer/A2 resolution, không tạo target/decision; guard revalidation chỉ kiểm lại retained/base context và failed projection đã pin, không tự publish discarded Model.

## 4. Binding/raw/progress semantics đề nghị

### 4.1 Intent và candidate projection

Binding C giữ whole T0 history/registry/source/archive/base Model+AS SHA, actual parent progress hash và retained-assessment hashes. `current_selectors_sha256` pin toàn current selectors từ **verified parent**, không selectors raw tự khai. Parent Plan/Artifact/Run/config được reader kiểm từ actual publication, không chỉ metadata bằng hash.

Định nghĩa `read_write_intent_sha256 = digest({mode,step,unit_ids,goal,aliases_sha256,current_selectors_sha256,progress_before_sha256,read_context_ids,write_source_refs})`. Units/IDs sorted unique; aliases/selectors/progress dùng exact codec hiện hành. `write_source_refs` là đầy đủ requirement family + criteria của selected units. `read_context_ids` do code lập từ fixed-point closure của selected source uses cộng retained outputs và their closure/reverse-impact trên base; có typed workflow members/current Issues cần dùng. Unknown read/impact không tự cấp membership. Mỗi input occurrence vẫn tính shared caps, không deduplicate để giảm Budget.

Giữ projection **shape/version H2 candidate draft.2**; ở C, field `scope_request_sha256` phải **bằng read_write_intent_sha256 C** theo định nghĩa trên. Đây là delta semantic hash domain tường minh; không gọi `h2_candidates.scope_request_hash(CBinding)` và không đổi nghĩa H2 callers. Candidate SHA/length và Analysis SHA/length được hash từ raw bytes riêng sau khi intent có sẵn, tránh chu kỳ scope hash/raw SHA. Authority final tuple pin tất cả. Node/Edge locators được adapter type-check rồi map sang WorkflowNode/WorkflowEdge ở private C metadata; không sửa raw hoặc H2 canonical aliases.

Raw candidate và analysis được stage/promote nguyên byte kể cả blocked/rejected; C result checker dựng lại projection với sealed allocations, so đúng nội dung, order và unknowns. Không dùng raw claim làm canonical CARRY/REPLACEMENT proof hoặc sửa raw để khớp builder.

### 4.2 Stage provenance, append-only và successors

Step chỉ được xét cho công việc chưa xong: unit requested có verified stage=step−1, prerequisites/current assessment phù hợp. No-anchor unit có actual outputs không được build đè dù stage0. Unit chưa có output có thể bắt đầu step1 với đầy đủ inspection/authority/independence. Stage1 thêm findings/AS, không Model; steps2–4 dùng Model/Change/AS và **mọi** current Issue successor cần thiết, không cắt một key/row/Part để publish.

Pure C builders phải tạo đúng bảng H3 §3.2: DIRECT Answer/applied→CARRY; source-only không giả Answer; CARRY pending không auto applicable; not_applicable không carry tiếp; chỉ dùng target khác key đã current, không sinh target mới; complete REPLACEMENT chỉ continuation đủ checks, thiếu thì incomplete/full hold hoặc guard trên base nếu successor không hợp lệ. Supersedes luôn base current. Root/origin/obsolete/from/Answer/event refs giữ đúng role, current refs chỉ typed allowlist. Change analysis_edit/cùng source, `application_event_refs=[]`, source_record_ids chứa actual predecessors/evidence; no new application/claim/decision/TaskAttestation/Validation.

Result stage tăng **đúng một** cho selected unit chỉ khi step candidate được whole-union accept và raw-to-result fidelity đạt. Mỗi Output mới pin actual command/raw SHA, exact output IDs/typed aliases, full source family. Existing Outputs giữ origin command/raw/source; chỉ current Issue IDs/aliases được transport theo key và exact typed proof. Stage/provenance và eligibility giữ riêng: toàn Run có thể blocked do U trong khi V thực sự tiến; không dùng status completed để suy usability hoặc user acceptance. Guard/revalidate/adopt/rejected/stale không tăng stage. Output rỗng ở step1 hợp lệ khi thực inspection đầy đủ và không finding, không nghĩa là được bỏ kiểm raw/source inventory.

Retained payload/IDs/row source, assessment, Part membership, row Issue context đều phải giữ qua current-ref projection. So nghĩa theo đúng set/order contract; workflow/criteria order giữ nguyên. Tính base/candidate forward closure, reverse impact, Part-all-actions fixed point và **union selected + retained + new findings/transitions** trước quyết định. Shared component đơn thuần không bridge; bridge thật kéo U blocker sang V bỏ toàn candidate, chỉ guard AS trên base khi hợp lệ. Unknown hold luôn rematerialize trên toàn inventory/graph mới; không scope rỗng=độc lập. Parent unknown selector không được thu hẹp chỉ bởi prose hoặc independence label; cần kiểm đầy đủ canonical scope/source/meaning/correspondence theo H3 §3.3–4, không đủ giữ hold.

### 4.3 Result assessment và reader

Giữ hash payload source/context/diff/closure và parent-assessment từ B-P01; recompute trên **actual C result pair/Records**. `proof_sha256` payload C = payload B-P01 cộng required `candidate_projection_sha256` (digest projection hoặc null) và `candidate_sha256` (raw SHA hoặc null). Stage inventory là **proven new + retained** sau fidelity/transition/union, không từ caller metadata. Parent hash lấy actual B/C parent assessment, không projection đã xóa assessment. Không hash chính result assessment hay plan vào proof.

Đề nghị pure APIs `ContinuationVerifier.config(...)`, `result(...)`, `published(command)` và `check_continuation_result(...)`. `published` version-dispatch B parents bằng nguyên B verifier; C parents bằng C verifier theo oldest-first chain. Result checker phải canonical-check whole detached projected graph có introducing operation/Run/finalized event, so exact batch/projection/metadata/outcome/pins. Tiếp đó promoted publisher reader phải chấp nhận chính bytes ấy, và next-command Config phải kiểm được parent ấy. Capability từ dict/dataclass tự khai, parent metadata relabel, omitted unit, null result assessment hoặc hash tự khai đều reject.

## 5. Gates trước writer và safety sau gate contract

Chưa có kết quả G-C/S-C trong lượt này. Auditor review C-P01 trước code phụ thuộc; sau chốt delta, triển khai pure trước writer theo thứ tự:

| Gate | Bằng chứng bắt buộc trước writer |
| --- | --- |
| G-C1 | Closed schemas/version rejection và exact B→C parent bridge; C authority riêng, B approval không cấp Model; raw bytes/hash domain/read allowlist đúng |
| G-C2 | Typed builders/proofs canonical: DIRECT→CARRY, multihop/pending, source-only, not_applicable target/no-target, complete/incomplete REPLACEMENT, task predicates. False proof reject khác missing coverage giữ hold; không nới canonical validators |
| G-C3 | Actual detached projected Model+A2 result checker → promoted publisher reader → next C step/revalidate config; thêm guard own Artifact/null hash → inherited actual SHA, no recursion/hash cycle. Parent B bytes giữ nguyên |
| G-C4 | Base/candidate retained outputs và whole-union controls: Part–row–source swaps, true bridge, shared-component control, unknown-global graph growth/no-anchor outputs; raw projection tái dựng và output/source/Issue correspondence đúng |

Chỉ sau G-C1–4 mới writer C T0→một seal→paired T3, giữ command/plan/allocations/times qua reopen/resume/lost ACK, không implicit rebase. Cần toàn **S1–S6 §7.1 trên Model+A2 thật**, bao gồm concurrent prepare/resume/seal DIRECT→CARRY và REPLACEMENT, both head-change opponents, mọi phase fault/rollback/kill/lost ACK/unknown, all-store historical registry missing/tamper/restore và từng effects class pending/complete/incomplete/guard/rejection. B-AS pass không thay chúng. Coverage [matrix](../reports/s02-phase2/2a-h3-c-contract-review-2026-11-01/COVERAGE_MATRIX.md) ghi từng gate hiện **NOT RUN C**; không hoãn sang D.

Khi wheel C cuối ổn định mới full regression cần thiết **một lần**, một job nặng C rồi Python, concurrency chỉ trong race tests; không retry/skip/tăng caps hoặc giảm assertions để đổi failure thành pass. Fresh offline/non-editable/S01 payload/source–wheel–installed và toàn commands/logs/JUnit/readbacks/failures/seal theo yêu cầu người dùng. CLI/four-worker stress D/live ngoài scope.

## 6. Quyết định cần review

**C-P01:** chấp thuận hoặc sửa delta §2–4: draft.4/bridge actual B→C, C exact authority/hash domain, candidate_projection raw fidelity, C guard origin pin không self-hash, stage advancement/result assessment/publisher chain. Có schema snapshot đề nghị trong evidence root để audit fields chính xác; nó không được dùng bởi package/writer hiện hành và không thay canonical schema/registry.

Điểm dừng này thực hiện gate người dùng: “Nếu cần đổi nghĩa contract đã chốt, bàn giao delta cần audit trước phần implementation phụ thuộc; không nới validators để vượt gate.” Chưa phát hành C wheel hoặc gắn C AUDIT_READY implementation; marker bàn giao có scope **CONTRACT_DELTA_ONLY**. Không tự nghiệm thu C hoặc mở H3-D. Sau audit và quyết định của người dùng mới tiếp tục code phụ thuộc C-P01; các findings A/B đã đóng và evidence/oracles lịch sử giữ nguyên.
