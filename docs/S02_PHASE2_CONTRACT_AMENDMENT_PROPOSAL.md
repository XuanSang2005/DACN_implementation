# Addendum hẹp: application S01 cùng snapshot và kế thừa resolution

**Trạng thái: proposed — đã phản hồi audit, chưa audit lại/chưa được duyệt implementation.**

Phiên bản addendum `s02-phase2-amendment/0.1.0-draft.1`, ngày 21/10/2026; đi cùng [kế hoạch Đợt 2 draft.2](S02_PHASE2_IMPLEMENTATION_PLAN_PROPOSAL.md). Đây là đề nghị thay hai nhóm quy tắc, **không phải contract thay thế draft.3**, không được đưa vào a3 bằng cách chỉ thêm orchestrator. G3 capture/G4 ledger vẫn là đề xuất độc lập, không được giải quyết hoặc triển khai bởi addendum này.

## 1. Căn cứ và phạm vi

[Audit draft.1](/Users/macbookpro/.codex/.chatgpt-projects/g-p-68c38c8799f48191a101e19a975ca4f9/outputs/audits/s02-phase2-proposal-draft1-2026-10-21/AUDIT_REPORT.md), [kết luận](/Users/macbookpro/.codex/.chatgpt-projects/g-p-68c38c8799f48191a101e19a975ca4f9/outputs/audits/s02-phase2-proposal-draft1-2026-10-21/AUDIT_RESULT.json) và probes [C](/Users/macbookpro/.codex/.chatgpt-projects/g-p-68c38c8799f48191a101e19a975ca4f9/outputs/audits/s02-phase2-proposal-draft1-2026-10-21/compatibility-c.json)/[Python](/Users/macbookpro/.codex/.chatgpt-projects/g-p-68c38c8799f48191a101e19a975ca4f9/outputs/audits/s02-phase2-proposal-draft1-2026-10-21/compatibility-python.json) xác nhận hai P1. Các probes là thực chạy **của auditor**, không được chạy lại trong lượt viết addendum. Nghiệm thu kỹ thuật Đợt 1 a3 giữ nguyên phạm vi lịch sử.

| Mục | Quy tắc draft.3/a3 hiện tại | Đề nghị thay có giới hạn |
| --- | --- | --- |
| A1 / S02-P2-01 | `application_selected_s01_result` trong [events.py](../packages/s02/src/dacn_s02/events.py) buộc changes_requirements dùng SourceContext của run quan sát và requirements_switch; `analysis_edit_source` giữ Context, `requirements_switch_snapshot` bắt snapshot khác trong [validation.py](../packages/s02/src/dacn_s02/validation.py) | Tách Context archive kết quả S01 khỏi Context của Model; so snapshot để chọn loại Change. Không nới hai invariant Change |
| A2 / S02-P2-02 | `issue_resolution_target/change` buộc event trực tiếp trỏ chính Issue/Model hiện tại; AnalysisSet chỉ chọn Issue cùng Model | Giữ kiểm trực tiếp tại Issue gốc; thêm chứng cứ kế thừa có kiểm lineage/ảnh hưởng tới Issue successor của Model hiện tại |

Các tên field/enum mới trong tài liệu này là **schema proposal**, chưa hợp schema a3. Chỉ ghi giả định contract version kế tiếp sau audit; không tự nâng `s02/0.1.0-draft.3`, package hoặc DB hiện hành.

## 2. A1 — application căn cứ snapshot, không căn cứ result_kind

### 2.1 Năm định danh phải tách

- `Mbase`: Model của expected base pair `(Mbase, ASbase)` đã pin trong operation; kiểm lại bằng CAS trước T3.
- `Cmodel = Mbase.source_context_id`; `Smodel = Cmodel.snapshot_id`: nguồn hiện hành của Model này, có thể là snapshot S01 cũ hơn head S01.
- `Robserved`: run S01 lấy từ s01_dispatch_intent/receipt và checked lookup, không lấy latest run.
- `Cobserved`: SourceContext archive của **Robserved**; `Sobserved` là snapshot trong envelope của run đó. Archive gồm envelope, raw input của run mới, origin source của snapshot, schema và hashes theo quy tắc nguồn hiện tại. Khi unchanged, raw của run mới và origin snapshot cũ có vai trò khác nhau.
- `Cresult`: Context làm nguồn của Model kết quả. Có thể bằng Cmodel dù Cobserved là một record khác. Không bỏ Cobserved khi Model không đổi snapshot.

**Khuyến nghị:** thêm `observed_source_context_id: ID|null` vào payload `application_applied`. Giữ nguyên `new_source_context_id` với nghĩa Cresult; không đổi ý nghĩa field cũ. Với changes_requirements, observed_source_context_id bắt buộc non-null trỏ Cobserved; với points_to_existing_source bắt buộc null, observation null và analysis_edit theo quy tắc cũ. Không thêm enum application mode: branch được code suy ra từ hai snapshot IDs có thẩm quyền, không tin nhãn do caller nhập.

Cobserved có thể đã archive hợp lệ trong session hoặc được tạo cùng T3. Sau checked lookup, lưu observation và bộ bytes archive vào staging của command trong transaction ngắn trước T3 (các purpose nguồn/schema đã có); profile adapter kiểm inventory/hash và envelope run/snapshot của bộ staging, lookup command/get_stage tìm lại đúng bộ này. Nếu CAS T3 thua, observation/staging vẫn còn dù Cobserved/Model mới chưa được publish. Recovery dựng lại Cobserved từ bộ đã kiểm hoặc đối soát cùng S01 run, không thay bằng latest head. Không công bố Context đáng tin nếu archive chưa verify. Không tái dùng Cmodel làm Cobserved chỉ vì cùng snapshot nếu nó không chứng minh đúng Robserved. SourceContext schema không cần field mới. `Run.source_context_id` vẫn là source pin của operation/base theo a3; `Run.result_model_id` dẫn tới Model dùng Cresult. Không đổi Run.source_context_id thành Cobserved rồi phá `run_intent_source`.

### 2.2 Quy tắc thay thế application_selected_s01_result

Sau khi verified archive/consent/observation, và **sau kiểm base pair còn hiện hành**:

| So sánh | Change và nguồn Model | Records/events công bố T3 |
| --- | --- | --- |
| Sobserved = Smodel | `analysis_edit`; Change.old_source_context_id = Change.new_source_context_id = Cmodel; Model mới dùng Cmodel; application.new_source_context_id=Cmodel | Cobserved + source artifacts nếu chưa có; Change chỉnh phân tích/Issue state, Model successor, resolved Issue cùng key/current lineage, AnalysisSet mới, Run + application_applied có observed_source_context_id=Cobserved và backlinks nguyên tử |
| Sobserved ≠ Smodel, cùng spec/store đã chọn | `requirements_switch`; Change.old_source_context_id=Cmodel, new=Cobserved; Model mới dùng Cobserved; application.new_source_context_id=Cobserved | Cùng bộ records ở trên, thêm inventory/source-impact/reanalysis tasks; không mang refs cũ sang theo index |
| Không có Answer application, chỉ intake lại run unchanged | Giữ quy tắc intake/no-op draft.3; không bắt Model revision mới | Archive/run nguồn, không dựng application chỉ vì đọc run mới |

`result_kind=unchanged` nghĩa input bằng **head S01 tại commit của run**, không nói Model S02 đang dùng snapshot nào. Ví dụ S02 dùng S1, S01 head S2, request base_revision=2 cho input S2 ⇒ run unchanged trả S2 ⇒ **requirements_switch S1→S2**. Ngược lại recovery vào base S02 mới đã dùng đúng Sobserved phải dùng nhánh cùng snapshot sau impact review/CAS mới. Không retarget operation cũ; nhánh được xác định trong command successor pin base mới.

Cùng snapshot vẫn có Model revision mới trong **application** để thể hiện thay đổi phân tích/Issue state và đáp ứng atomic Model/Change/AnalysisSet của a3. Đây không phải revision S01 dư. Nếu Answer không giải quyết current Issue thật sự thì giữ pending và không tạo application giả; việc run S01 validated không tự đủ để kết luận giải quyết.

### 2.3 Bằng chứng đầu vào bắt buộc

Không chỉ kiểm s01_result_observed tự khai báo. Checked lookup + archive phải chứng minh đồng thời:

1. Robserved = dispatch.s01_run_id = observation.s01_run_id = Cobserved.s01_run_id = envelope.run.run_id; Cobserved.store_key = dispatch.s01_store_key, alias gắn kho đã cấu hình, session/spec khớp. Snapshot = observation.snapshot_id = Cobserved.snapshot_id = envelope.snapshot.snapshot_id. SourceContext thuộc cùng session và verified archive.
2. Interpretation của application là đúng event đã chọn; consent.interpretation_event bằng event ấy; dispatch.consent_event bằng consent ứng dụng; observation.dispatch_event là dispatch này. Answer ID giống nhau xuyên chuỗi, refs chỉ đúng command/ancestors hợp lệ. Không thay interpretation changes_requirements thành points_to_existing_source vì thấy unchanged.
3. Staged full input bytes hash = consent.approved_input_sha256 = hash raw **run source** trong Cobserved; không so hash với origin source hoặc JSON serialization của snapshot. Metadata Artifact hash/length đúng BLOB. Request mode/spec/base trong checked S01 run/request bằng request được pin ở interpretation/dispatch. Phải giữ schema artifact và normalization profile S01; thiếu schema_version được thêm theo rule duy nhất. So normalized input với snapshot bằng comparator exact, không hash JSON để kết luận nghĩa bằng nhau.
4. Envelope validated và đúng contract/schema; source provenance/run↔origin identities giữ quy tắc a6. `Smodel` lấy qua Model base/Context đã checked, không nguồn do LLM nhập. Snapshot ID khác nhưng text giống vẫn là source switch; snapshot ID bằng nhưng archive có nội dung khác là corruption, từ chối.
5. Current Issue trong ASbase cùng issue_key và nằm trên lineage của Answer.issue_id; giải quyết đúng Issue successor, Change nguồn và application backlinks; unique applied/active claim/CAS/finalized-Run giữ nguyên.

`verify_archive` hiện kiểm raw→normalized snapshot; amendment bổ sung kiểm **raw run source→consent** và request chain trong application/checked-read, không coi helper hiện có đã làm đủ tất cả mục trên. Sai run, snapshot, raw hash, request base hoặc consent ⇒ reject toàn T3; không chọn nguồn thay thế để chữa. Raw/staging/observation lịch sử vẫn giữ; không publish Model hoặc đóng Issue.

### 2.4 State transitions và recovery

| Tình huống | Xử lý đề xuất | Điều không được làm |
| --- | --- | --- |
| Cùng snapshot, base pair còn đúng | Branch analysis_edit + Cmodel; Cobserved được archive và trỏ riêng; một application | Bỏ archive run mới; đổi Context Model chỉ để qua check |
| Khác snapshot, kể cả S01 unchanged | requirements_switch + Cobserved; reanalysis pending và current Issues đầy đủ | Chỉ kiểm result_kind để chọn analysis_edit |
| S01 commit, S02 chưa T3 | Lookup đúng receipt/run; đối chiếu chuỗi; archive/reuse Cobserved; tiếp tục operation cũ nếu base đúng | Submit S01 lại, đổi Answer/consent hoặc cấp run khác |
| M/AS đổi trước T3 | Stale outcome; không application. Successor sau explicit impact review/claim CAS lấy cặp base mới, reuse observation/consent cũ và tính lại snapshot branch | Auto merge/rebase hoặc đổi base của command cũ; dispatch S01 lần hai |
| Mất ACK T3 | Connection mới checked lookup command/application; trả đúng kết quả đã commit, kể cả hiện đã là lịch sử | Mark failed đè completed hoặc application thứ hai |
| Observation/hash/consent sai | Reject + giữ evidence lỗi; head/claim applied không tiến | “Sửa” event bất biến hoặc thay observation bằng head hiện hành |

S01 base đã consent có thể khác revision nguồn của Model S02 (ví dụ S02 S1, S01 head S2). Trước dispatch, người dùng phải xem **cả hai** cùng full proposed input và diff so với nguồn S02 lẫn base S01 nếu khác; không sửa request sau consent. Recovery sau commit không xin consent để commit lại. Nếu impact mới chưa đủ căn cứ thì giữ pending; không hủy sự thật S01 đã commit.

### 2.5 Phương án khác và trade-off

Khuyến nghị thêm một ref vì cần truy riêng nguồn Model và evidence run, giữ cả Change invariants. Đổi lại schema payload/application checker phải version, legacy decoder phải rõ.

Phương án khác: người dùng chọn interpretation mới points_to_existing_source sau một no-op đã được đối soát, giữ nguyên interpretation/consent/observation cũ. Cách này cần một quyết định phân loại lại tường minh và liên kết old chain; a3 chưa có đường giữ đầy đủ observation trong existing-source application (nhánh đó đòi null), nên **cũng cần amendment**, thêm thao tác và dễ làm mất lịch sử. Không chọn làm mặc định. Không chọn tạo revision S01 giả, nới requirements_switch cùng snapshot hoặc đổi nghĩa `new_source_context_id` thành archive.

## 3. A2 — bằng chứng Answer đã áp dụng và khả năng kế thừa resolution

### 3.1 Quyết định khuyến nghị

Giữ `application_applied` gốc, Answer, Issue resolved gốc, Change, Model/AnalysisSet gốc nguyên byte. Event luôn trỏ **Issue gốc tại Model áp dụng**, tuyệt đối không retarget sang Model sau. Unique một application/Answer vẫn là sự thật lịch sử toàn kho.

Thêm trường nullable `resolution_carry` vào Issue body, và status `resolution_pending_revalidation`. Đây là chứng cứ typed **nằm trong Issue successor bất biến**, tránh tạo một ứng dụng Answer mới hoặc hệ thống approval mới. Trường mới không phải Review, không cấp xác nhận nghiệp vụ/kiến trúc. Issue gốc trực tiếp có resolution_carry=null; Issue kế thừa có object non-null.

`resolution_carry` đề xuất:

| Field | Kiểu/ý nghĩa |
| --- | --- |
| `origin_issue_id` | ID Issue resolved gốc được application trực tiếp; giữ ổn định xuyên chuỗi |
| `from_issue_id` | ID Issue predecessor hiện hành được chọn ở base AnalysisSet; bằng supersedes_id |
| `base_analysis_set_id` | ID set đã pin khi đánh giá; chứa from_issue_id. Cùng model nếu chỉ revalidate analysis; model cha nếu tạo Model successor |
| `change_id` | Change ID của chuyển Model này; null khi chỉ Issue/set successor trên cùng Model |
| `assessment` | `applicable`, `undetermined`, `not_applicable` |
| `source_checks` | Mảng `{from_ref:SourceRef,to_ref:SourceRef|null,relation:equal_value|changed|removed,reason:Text}`; cover đủ nguồn phụ thuộc của resolution, không chọn bỏ nguồn thay đổi |
| `scope_check` | `{from_scope:Scope,to_scope:Scope,element_pairs:[{from:ElementRef,to:ElementRef|null,relation:unchanged|modified|removed,reason:Text}],reason:Text}`; gồm Parts nếu có. Null to chỉ removed có căn cứ, không tự có nghĩa hết nghĩa vụ |
| `evaluation` | `{method:structural_reuse|human_review,evaluator:Text,rule_version:Text,evidence_record_ids:ID[],reason:Text}`; method do code quản lý, evaluator thật (code version hoặc người review), không LLM tự nhận là user |

Các refs lịch sử trong object này có mục đích rõ: origin chứng minh application, from/base chứng minh tuyến kế thừa hiện hành, checks chứng minh điều kiện còn phù hợp. `Trace` của Issue mới vẫn trỏ source của Model hiện tại; `answer_ids` và `resolution_event_refs` giữ nguyên đầy đủ từ predecessor, không xoá hoặc đổi event để qua validator. `resolution` giữ diễn giải kết quả lịch sử; trạng thái và assessment nói liệu kết quả ấy dùng được hiện tại.

### 3.2 Invariants thay thế — hai nhánh tách biệt

**DIRECT (resolution_carry=null):** giữ kiểm a3: every resolution_event_ref là application_applied, resolved_issue_id đúng chính Issue, Change.new_model_id đúng model Issue, backlinks đủ, Answer/current lineage đúng, Issue được chọn trong result set của T3 application. Không chấp nhận prepared/consent làm evidence giải quyết. Issue resolved không có Answer vẫn giữ source-only rule cũ; không dùng A2 để hợp thức hóa business resolution không bằng chứng.

**CARRY (object non-null):** không nới DIRECT thành “event thuộc một Issue bất kỳ cùng key”. Phải kiểm toàn chuỗi sau:

1. Origin là DIRECT resolved Issue hợp lệ, có Answer application thật trong lịch sử cùng session. Validate nguyên gốc bằng DIRECT, không sửa Issue/event/Change để đáp ứng Model mới.
2. From bằng supersedes_id và là Issue cùng key được **base_analysis_set_id** chọn tại expected base; from phải là origin hoặc carry nối về origin qua chuỗi hữu hạn không cycle, không fork từ predecessor lịch sử bỏ qua current. Mọi node cùng issue_key/session, Answer.issue_id nằm trên lineage tới origin. Không chỉ so chuỗi key.
3. `answer_ids` và `resolution_event_refs` của successor **bằng** predecessor; root evidence truy về origin, không thêm/xóa Answer/event trong phép carry. Origin/application không đổi. Apply Answer mới, nếu thực sự cần quyết định mới, phải là luồng riêng được cấp nghiệp vụ; không phải carry hoặc recovery lời cũ.
4. Model successor phải có parent=Model của from, Change khớp old/new, source contexts đúng; base set phải là head được CAS. Trên cùng Model chỉ cho Issue/set successor với change_id=null và base set hiện hành. Target Issue nằm trong result AnalysisSet cùng Model; không chọn Issue lịch sử thay nó. Giữ `changed_record_ids`, selection đủ key và affected closure.
5. Source checks cover basis nguồn đã dùng để resolve, gồm Trace nguồn/nguồn đã kiểm của interpretation và nguồn của affected thao tác/quy tắc/nghĩa vụ. Issue/from/origin và Answer refs được dereference để lập basis, không chỉ tin danh sách LLM chọn. Mọi from_ref phải đúng nguồn predecessor/basis lịch sử được chỉ rõ; to_ref thuộc nguồn Model đích. So exact values có kiểu, nhưng equal text/pointer chưa đủ cho semantic scope. Reorder tiêu chí không nối index; cần correspondence có căn cứ hoặc undetermined. Nguồn mới thêm nghĩa vụ liên quan cũng phải xét, không chỉ source_checks các nguồn cũ.
6. Scope evidence cover toàn affected/blocking và dependencies/Parts liên quan, kể cả phần tử mới ảnh hưởng; code tính reverse impact/closure và kiểm pairs không thiếu, không cắt action của Part. Common component không tự kéo cả model; thiếu graph/unknown scope không được suy độc lập.
7. Assessment/applicability và status phải khớp bảng 3.3. Source/impact checks lặp khi mở kho; evidence IDs phải tồn tại và có đúng phiên bản liên quan. CAS trước publish bảo đảm đánh giá không stale. Không vì root resolved mà bỏ checks 5–6.

**Giới hạn của tự động đánh giá:** `structural_reuse` chỉ được chọn khi cùng snapshot, basis values không đổi, phạm vi liên quan/refs/actions/rules/Parts cùng nội dung, không có edit ảnh hưởng hoặc phần tử mới chưa xét, predecessor đang applicable, và code có proof diff/closure đầy đủ theo rule version đã audit. Same ID/text đơn thuần không là proof. Khác snapshot hoặc thay nội dung liên quan ⇒ mặc định undetermined; LLM có thể đề xuất tác động nhưng **human_review** cần xem source diff, scope correspondence và evidence trước khi đánh applicable. Review này chỉ đánh giá tái dùng resolution, không thay consent S01 hoặc Review bước 9. Nếu câu trả lời cũ rõ ràng mâu thuẫn nguồn mới, assessment=not_applicable với căn cứ; giữ unresolved effect, không tự đặt câu trả lời thay thế.

### 3.3 Trạng thái và phạm vi bị chặn

| Assessment | Issue.status | Hành vi |
| --- | --- | --- |
| applicable | resolved | Giữ resolution có hiệu lực trong scope đã chứng minh; không chuyển approval Model/Bundle cũ; reanalysis tasks khác vẫn pending nếu chưa có evidence |
| undetermined | resolution_pending_revalidation | Giữ application lịch sử; chặn scope cần kết quả này, tạo task đánh giá lại với căn cứ. Không tự hỏi lại cùng câu hỏi hoặc đổi thành open chỉ để qua validator |
| not_applicable | resolution_pending_revalidation | Ghi rõ kết quả cũ không đủ/không áp dụng ở nguồn hiện tại; chặn phạm vi ảnh hưởng cho đến có phân tích/quyết định thích hợp, không xóa evidence |

Unknown impact: affected/blocking enumerate tất cả phần tử/Parts có thể bị ảnh hưởng ở Model mới; khi chưa xác định được, enumerate toàn Model và giữ source-level hold mở rộng qua mọi lần graph lớn lên. Scope rỗng không biểu diễn unknown. `resolution_pending_revalidation` phải được tính là blocker trong admission, model/mapping state, current set và gate handoff; không lọt qua chỉ vì enum khác open. Part blocked có thể trỏ Issue này sau amendment; entity liên quan giữ needs_reanalysis với Change/task, không giả một câu hỏi nghiệp vụ mới.

Khi đánh giá lại có căn cứ, tạo Issue successor và AnalysisSet mới (hoặc Model/Change mới nếu sửa nội dung model), giữ origin/from lineage; **không thêm application_applied** cho Answer cũ. Chỉ nếu thật sự phát sinh câu hỏi nghiệp vụ mới từ thay đổi nguồn mới thì người dùng nhận câu hỏi có lý do/nguồn mới; không sinh câu hỏi để lách unique. Không đánh tasks hoàn tất chỉ vì status Issue đổi; tasks hoàn tất cần evidence theo version riêng.

### 3.4 Các resolver cần sửa tường minh sau khi được duyệt

Không chỉ sửa `issue_resolution_target`:

- Schema Issue: field/enum mới. DIRECT path giữ invariant cũ, CARRY path có validator riêng và lookup root chain.
- `validate_set`: vẫn chọn Issue.model_id đúng Model hiện hành. Chỉ các field lịch sử **resolution_carry.origin_issue_id/from_issue_id/base_analysis_set_id** được resolve tới history với các checks 3.2; không bắt origin phải ở current set và cũng không bỏ kiểm current-selection cho các Issue refs khác.
- `validate_record` generic SourceRef/Scope/ElementRef: Trace thường vẫn pinned current Model. Riêng `resolution_carry.source_checks.from_ref`, `scope_check.from_scope` và element_pairs.from được kiểm theo predecessor/basis lịch sử; to refs theo Model hiện tại. Không nới mọi SourceRef để chấp nhận snapshot tùy ý.
- `validate_change`, set/head inventory và builders: giữ all current keys qua model switch, source-only root cần logic riêng chứ không giả Answer carry. Change.source_record_ids trỏ predecessor/evidence; **Change.application_event_refs rỗng cho carry thuần**. Event gốc thuộc Change áp dụng gốc, không thêm backlink giả vào Change phân tích sau.
- `scope`, pending state checks, Part blocked checks và task/admission readers: nhận status revalidation mới và propagation scope. Model pin Issue cũ được resolver theo key/current set xử lý như draft.3; không dùng status lịch sử để qua blocker hiện tại.
- Recovery/checked reads phải validate DIRECT root + CARRY chain và chứng cứ đầy đủ, không chỉ validate shape object mới.

### 3.5 Ca cần chứng minh và phương án khác

| Ca | Kết quả kỳ vọng sau amendment; chưa chạy |
| --- | --- |
| Answer áp dụng tại M2 rồi tạo M3 | Q2/event/Answer nguyên byte; Q3 supersedes Q2, origin Q2, carry proof và AS3 chọn Q3; application count=1 |
| Chỉ sửa phần độc lập | Structural proof diff + closure + source coverage đầy đủ ⇒ applicable, không auto mang Review cũ |
| Nguồn mới đổi quyền/rule liên quan | requirements_switch; Q mới pending_revalidation, giữ root evidence và Answer; blockers/reanalysis còn, không auto resolved |
| Key đúng nhưng bỏ qua predecessor hoặc root khác | Reject; cùng key không đủ identity |
| Event trỏ Issue khác/Answer khác hoặc event prepared | Reject bằng DIRECT/root checks; không carry evidence giả |
| Hai ứng dụng cùng Answer | Unique/claim CAS như a3: tối đa một event; bên thua lookup, không tạo carry để giả một application chưa có |
| Recovery lặp | Đọc cùng application/records hoặc resume đúng command; không tăng count, không đổi clocks/hashes |
| Carry CAS thua race Model hoặc set | Stale; giữ evidence, không công bố Q/Model/set mới; explicit reevaluation trên base mới |

Phương án thay thế: tách một record Resolution toàn cục rồi cho Issue trỏ tới nó. Có ưu điểm root identity riêng, nhưng thêm loại record/selection/migration và phải tái thể hiện toàn bộ evidence đã lưu; không cần cho hai finding hiện tại. Phương án chỉ giữ Q2 trong AS3 vi phạm current Model; xóa Answer/event hoặc tạo application thứ hai làm sai lịch sử, không chấp nhận. Inline carry giảm abstraction nhưng cần parser/validator/history refs rõ như 3.4; không phải vài dòng clone/rebind.

## 4. Version, lịch sử và migration đề xuất

**Chưa thực thi migration hoặc đổi version.** Sau audit mới chốt contract/package/DB profile mới, tách với draft.3/a3. Đề xuất DB format mới có capability/profile marker để reader a3 từ chối kho chứa extended payloads, không diễn giải chúng như DB1. Nếu G4 về sau cũng đổi DB thì cần migration order cụ thể, không mặc nhiên gộp hai migrations chưa thiết kế.

Khuyến nghị compatibility reader có **hai schema profiles rõ ràng**. Legacy payload thiếu observed_source_context_id hoặc resolution_carry được kiểm bằng rules draft.3 nguyên trạng; không insert mặc định vào bytes lịch sử. Extended application phải có field mới, extended Issue phải có resolution_carry (null cho DIRECT), không cho payload lai thiếu field rồi tự đoán. Legacy root application hợp lệ có thể là origin của carry mới sau full DIRECT validation; thiếu/sai evidence thì reject, không backfill approval.

Migration đề xuất trên **bản sao mới**, explicit người dùng chọn, verify DB1 bằng a3 trước, giữ records/events/blobs/IDs/timestamps/hashes/receipt links/unique applied và links lịch sử nguyên byte; chỉ metadata cấu trúc/profile mới nếu đã được audit. Không tự sửa DB cũ, không reset/cập nhật Answer/Issue cũ. Readers mới cần kiểm mixed history theo profile, materialize/verify typed links mới chỉ cho records mới, và gate unknown status fail closed. Rollback vận hành về kho DB1 cũ chỉ an toàn nếu không mất writes mới; không hứa downgrade tự động. Chi tiết DDL/backup/reopen/migration fault thuộc batch sau có quyền implementation, phải review trước khi chạy.

## 5. Bảo vệ giữ nguyên và quyết định còn chờ

Giữ Answer/events/records bất biến; current Issue key + lineage; root event target/model/backlinks; AnalysisSet cùng Model, một current/key; unique application/Answer và active claim; paired CAS; Run failed/rejected/stale không publish; exact source/request/consent chain; không transaction xuyên S01/S02; lookup recovery không resend; requirements_switch snapshot khác; analysis_edit giữ Context; source refs không nối index xuyên revision; admission khác Review.

Cần auditor review A1 field/branch/archival proof, A2 status/carry shape/history exceptions/blocker propagation, negative oracles và compatibility profile. Người dùng quyết định cho phép semantics amendment, migration scope và batch implementation; chưa có quyết định ấy. Ví dụ [05](examples/s02-phase2/05-unchanged-application.json) và [06](examples/s02-phase2/06-resolved-issue-carry-forward.json) là projections dùng field mới **không hợp a3**, có positive/negative expectations để audit. [Bảng phản hồi](S02_PHASE2_DRAFT2_AUDIT_RESPONSE.md) không tự ghi findings đã đóng.
