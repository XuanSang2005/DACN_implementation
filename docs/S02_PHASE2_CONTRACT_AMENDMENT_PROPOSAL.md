# Addendum hẹp: application S01 cùng snapshot và kế thừa resolution

**Trạng thái: proposed — A1/A2 đã audit đạt ở mức thiết kế; chưa được duyệt implementation, schema/profile/migration còn cần chốt.**

Phiên bản addendum `s02-phase2-amendment/0.1.0-draft.2`, ngày 21/10/2026; đi cùng [kế hoạch Đợt 2 draft.3](S02_PHASE2_IMPLEMENTATION_PLAN_PROPOSAL.md). Đây là đề nghị thay hai nhóm quy tắc, **không phải contract thay thế draft.3**, không được đưa vào a3 bằng cách chỉ thêm orchestrator. G3 capture/G4 ledger vẫn là đề xuất độc lập, không được giải quyết hoặc triển khai bởi addendum này.

## 1. Căn cứ và phạm vi

**Kết luận hiện hành:** [audit draft.3 ngày 21/10/2026](/Users/macbookpro/.codex/.chatgpt-projects/g-p-68c38c8799f48191a101e19a975ca4f9/outputs/audits/s02-phase2-proposal-draft3-2026-10-21/AUDIT_REPORT.md) đóng A2-R1/R2 và S02-P2-02 ở mức thiết kế; A1/G2 giữ kết luận trước. Các mục 2–3 dưới đây giữ nguyên bytes đã audit. [Đề xuất schema/profile/migration 2A](S02_PHASE2_2A_SCHEMA_MIGRATION_PROPOSAL.md) là tài liệu mới riêng, chưa được audit hoặc duyệt implementation.

**Phản hồi audit draft.2:** [audit ngày 21/10/2026](/Users/macbookpro/.codex/.chatgpt-projects/g-p-68c38c8799f48191a101e19a975ca4f9/outputs/audits/s02-phase2-proposal-draft2-2026-10-21/AUDIT_REPORT.md) đóng S02-P2-01 ở mức thiết kế và xác nhận G2 đã rõ. Mục 2 A1 giữ nguyên bytes; lần sửa plan draft.3/addendum draft.2 đã xử lý riêng A2-R1/R2. Đó là trạng thái trước audit draft.3; kết luận hiện hành ở đoạn trên. Chưa có quyền implementation.

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

Thêm trường nullable `resolution_carry` vào Issue body, và status `resolution_pending_revalidation`. Đây là chứng cứ typed **nằm trong Issue successor bất biến**, tránh tạo một ứng dụng Answer mới hoặc hệ thống approval mới. Trường mới không phải Review, không cấp xác nhận nghiệp vụ/kiến trúc. Issue gốc trực tiếp có resolution_carry=null; Issue kế thừa có object non-null. A2-R2 bổ sung nhánh REPLACEMENT ở §3.6: trường nullable resolution_replacement và status resolution_replaced. Hai object carry/replacement loại trừ nhau; DIRECT có cả hai null, CARRY chỉ carry non-null, REPLACEMENT chỉ replacement non-null. Không chọn DIRECT chỉ vì carry=null.

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
| `evaluation` | `{method:structural_check|human_review,evaluator:Text,rule_version:Text,evidence_record_ids:ID[],reason:Text}`; method do code quản lý, evaluator thật (code version hoặc người review), không LLM tự nhận là user |

Các refs lịch sử trong object này có mục đích rõ: origin chứng minh application, from/base chứng minh tuyến kế thừa hiện hành, checks chứng minh điều kiện còn phù hợp. `Trace` của Issue mới vẫn trỏ source của Model hiện tại; `answer_ids` và `resolution_event_refs` giữ nguyên đầy đủ từ predecessor, không xoá hoặc đổi event để qua validator. `resolution` giữ diễn giải kết quả lịch sử; trạng thái và assessment nói liệu kết quả ấy dùng được hiện tại.

### 3.2 Invariants DIRECT/CARRY và phương pháp đánh giá

**DIRECT (resolution_carry=null, resolution_replacement=null):** giữ kiểm a3: every resolution_event_ref là application_applied, resolved_issue_id đúng chính Issue, Change.new_model_id đúng model Issue, backlinks đủ, Answer/current lineage đúng, Issue được chọn trong result set của T3 application. Không chấp nhận prepared/consent làm evidence giải quyết. Issue resolved không có Answer vẫn giữ source-only rule cũ; không dùng A2 để hợp thức hóa business resolution không bằng chứng.

**CARRY (object non-null):** không nới DIRECT thành “event thuộc một Issue bất kỳ cùng key”. Phải kiểm toàn chuỗi sau:

1. Origin là DIRECT resolved Issue hợp lệ, có Answer application thật trong lịch sử cùng session. Validate nguyên gốc bằng DIRECT, không sửa Issue/event/Change để đáp ứng Model mới.
2. From bằng supersedes_id và là Issue cùng key được **base_analysis_set_id** chọn tại expected base; from phải là origin hoặc carry nối về origin qua chuỗi hữu hạn không cycle, không fork từ predecessor lịch sử bỏ qua current. Mọi node cùng issue_key/session, Answer.issue_id nằm trên lineage tới origin. Không chỉ so chuỗi key.
3. `answer_ids` và `resolution_event_refs` của successor **bằng** predecessor; root evidence truy về origin, không thêm/xóa Answer/event trong phép carry. Origin/application không đổi. Apply Answer mới, nếu thực sự cần quyết định mới, phải là luồng riêng được cấp nghiệp vụ; không phải carry hoặc recovery lời cũ.
4. Model successor phải có parent=Model của from, Change khớp old/new, source contexts đúng; base set phải là head được CAS. Trên cùng Model chỉ cho Issue/set successor với change_id=null và base set hiện hành. Target Issue nằm trong result AnalysisSet cùng Model; không chọn Issue lịch sử thay nó. Giữ `changed_record_ids`, selection đủ key và affected closure.
5. Source checks cover basis nguồn đã dùng để resolve, gồm Trace nguồn/nguồn đã kiểm của interpretation và nguồn của affected thao tác/quy tắc/nghĩa vụ. Issue/from/origin và Answer refs được dereference để lập basis, không chỉ tin danh sách LLM chọn. Mọi from_ref phải đúng nguồn predecessor/basis lịch sử được chỉ rõ; to_ref thuộc nguồn Model đích. So exact values có kiểu, nhưng equal text/pointer chưa đủ cho semantic scope. Reorder tiêu chí không nối index; cần correspondence có căn cứ hoặc undetermined. Nguồn mới thêm nghĩa vụ liên quan cũng phải xét, không chỉ source_checks các nguồn cũ.
6. Scope evidence cover toàn affected/blocking và dependencies/Parts liên quan, kể cả phần tử mới ảnh hưởng; code tính reverse impact/closure và kiểm pairs không thiếu, không cắt action của Part. Common component không tự kéo cả model; thiếu graph/unknown scope không được suy độc lập.
7. Assessment/applicability và status của CARRY phải khớp bảng 3.3. REPLACEMENT có bảng riêng §3.6, không đánh assessment cũ thành applicable. Source/impact checks lặp khi mở kho; evidence IDs phải tồn tại và có đúng phiên bản liên quan. CAS trước publish bảo đảm đánh giá không stale. Không vì root resolved mà bỏ checks 5–6.

**A2-R1 — phương pháp kiểm tra khác kết luận tái sử dụng.** Đổi tên method đề xuất `structural_reuse` thành `structural_check`: code luôn được thực hiện kiểm tra trên nguồn hiện hành, kể cả snapshot đổi hoặc proof còn thiếu. Method nói ai/cách nào kiểm; `assessment` mới nói kết quả. Đây là sửa schema proposal, không rename dữ liệu đã lưu trong a3 (a3 chưa có field này).

| Method | Assessment hợp lệ | Điều kiện và giới hạn |
| --- | --- | --- |
| structural_check | applicable | Cùng snapshot; basis values và toàn footprint/refs/actions/rules/Parts liên quan không đổi; predecessor applicable; không có phần tử mới/impact chưa xét; diff + reverse closure + source coverage đầy đủ theo rule version được audit. Chỉ đủ tất cả mới kết luận reuse |
| structural_check | undetermined | Được ghi sau kiểm tra ở **bất kỳ snapshot** nào khi ít nhất một điều kiện applicable chưa chứng minh được: snapshot đổi, nguồn/footprint đổi, thiếu proof, predecessor pending hoặc unknown impact. Ghi điều kiện thất bại và phần chưa biết; giữ hold. Không bắt có reviewer |
| structural_check | not_applicable | Không cho phép trong profile hẹp này: code ghi undetermined và chuyển đánh giá có người review, không tự kết luận quyền nghiệp vụ cũ hết hiệu lực |
| human_review | applicable | Người review thực đã xem basis nguồn, correspondence/impact đầy đủ và chứng minh kết quả cũ vẫn trả lời nghĩa vụ hiện tại. Cho phép khác snapshot hoặc predecessor undetermined; không tự cấp bởi LLM. Không áp dụng nhánh này để lật một kết luận not_applicable đã có: dùng §3.6 |
| human_review | undetermined | Review thực đã diễn ra nhưng người review ghi rõ chưa đủ căn cứ; vẫn chặn. Không dùng nhãn này nếu chưa có người review |
| human_review | not_applicable | Người review thực chỉ ra căn cứ nguồn/phạm vi khiến kết quả cũ không còn áp dụng; bảo toàn root, chuyển luồng thay thế §3.6 |

`evaluation.evaluator` của structural_check là code/rule version, reason ghi checks thiếu/thất bại; human_review là người thực hiện, reason là quyết định và căn cứ họ cung cấp qua thao tác người dùng, gắn đúng model/source/base set và evidence_record_ids. Code lưu nguyên quyết định, không tự điền tên người hoặc sinh câu “đã review”. Ví dụ dùng DEMO được ghi là giả định. Nếu không có human review thì không được chọn method này. Thiếu record/field bắt buộc, ref hỏng hoặc lineage sai vẫn reject; undetermined không hợp thức hóa graph lỗi. Proof còn thiếu phải được ghi rõ trong reason và giữ toàn phạm vi chưa chứng minh độc lập, không dựng chứng cứ giả để điền đủ bảng. Equal text/ID không đủ proof. Nguồn mới đổi quyền chưa đồng nghĩa code biết quyền đúng mới là gì. Quyết định tái dùng không thay consent S01 hoặc Review bước 9.

### 3.3 Trạng thái và phạm vi bị chặn

Bảng này chỉ áp dụng CARRY; REPLACEMENT có bảng riêng ở §3.6.

| Assessment | Issue.status | Hành vi |
| --- | --- | --- |
| applicable | resolved | Giữ resolution có hiệu lực trong scope đã chứng minh; không chuyển approval Model/Bundle cũ; reanalysis tasks khác vẫn pending nếu chưa có evidence |
| undetermined | resolution_pending_revalidation | Giữ application lịch sử; chặn scope cần kết quả này, tạo task đánh giá lại với căn cứ. Không tự hỏi lại cùng câu hỏi hoặc đổi thành open chỉ để qua validator |
| not_applicable | resolution_pending_revalidation | Ghi rõ kết quả cũ không đủ/không áp dụng ở nguồn hiện tại; chặn phạm vi ảnh hưởng cho đến có phân tích/quyết định thích hợp, không xóa evidence |

Unknown impact: affected/blocking enumerate tất cả phần tử/Parts có thể bị ảnh hưởng ở Model mới; khi chưa xác định được, enumerate toàn Model và giữ source-level hold mở rộng qua mọi lần graph lớn lên. Scope rỗng không biểu diễn unknown. `resolution_pending_revalidation` phải được tính là blocker trong admission, model/mapping state, current set và gate handoff; không lọt qua chỉ vì enum khác open. Part blocked có thể trỏ Issue này sau amendment; entity liên quan giữ needs_reanalysis với Change/task, không giả một câu hỏi nghiệp vụ mới.

Từ undetermined, khi có căn cứ xác nhận resolution cũ vẫn đúng, tạo CARRY successor applicable và AnalysisSet mới (hoặc Model/Change mới nếu sửa nội dung model), giữ origin/from lineage; **không thêm application_applied** cho Answer cũ. Từ not_applicable, không dùng chuyển này để xóa blocker: đi nhánh REPLACEMENT §3.6, giữ nguyên kết luận hết hiệu lực. Chỉ nếu thật sự phát sinh câu hỏi nghiệp vụ mới từ thay đổi nguồn mới thì người dùng nhận câu hỏi có lý do/nguồn mới; không sinh câu hỏi để lách unique. Không đánh tasks hoàn tất chỉ vì status Issue đổi; tasks hoàn tất cần evidence theo version riêng.

### 3.4 Các resolver cần sửa tường minh sau khi được duyệt

Không chỉ sửa `issue_resolution_target`:

- Schema Issue: field/enum mới. DIRECT path giữ invariant cũ; CARRY/REPLACEMENT có validators riêng, không chạy direct event-target check lên Issue kế thừa/thay thế. Mỗi nhánh vẫn validate DIRECT root nguyên gốc. Method structural_check kiểm theo bảng §3.2; không còn structural_reuse trong extended profile mới.
- `validate_set`: vẫn chọn Issue.model_id đúng Model hiện hành. Trong CARRY, chỉ các field lịch sử **resolution_carry.origin_issue_id/from_issue_id/base_analysis_set_id** được resolve tới history với các checks 3.2; không bắt origin phải ở current set và cũng không bỏ kiểm current-selection cho các Issue refs khác.
- `validate_record` generic SourceRef/Scope/ElementRef: Trace thường vẫn pinned current Model. Riêng `resolution_carry.source_checks.from_ref`, `scope_check.from_scope` và element_pairs.from được kiểm theo predecessor/basis lịch sử; to refs theo Model hiện tại. Không nới mọi SourceRef để chấp nhận snapshot tùy ý.
- `validate_change`, set/head inventory và builders: giữ all current keys qua model switch, source-only root cần logic riêng chứ không giả Answer carry. Change.source_record_ids trỏ predecessor/evidence; **Change.application_event_refs rỗng cho carry thuần**. Event gốc thuộc Change áp dụng gốc, không thêm backlink giả vào Change phân tích sau.
- `scope`, pending state checks, Part blocked checks và task/admission readers: nhận status revalidation mới và propagation scope. Model pin Issue cũ được resolver theo key/current set xử lý như draft.3; không dùng status lịch sử để qua blocker hiện tại.
- Recovery/checked reads phải validate DIRECT root + CARRY/REPLACEMENT chain và chứng cứ đầy đủ, không chỉ validate shape object mới. §3.6 chỉ rõ thêm history refs, current target selection và gate status cần sửa; application_pending_issue của Answer vẫn chỉ nhận open/answered_pending_application ở **key mới**, không cho apply Answer cũ lên pending-revalidation.

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

### 3.6 A2-R2 — thay thế kết quả hết hiệu lực, giữ đủ keys và lịch sử

**Khuyến nghị:** không tạo DIRECT root mới trên key cũ bằng cách xóa Answer/event refs. Khi đã có CARRY `not_applicable`, giữ kết luận đó và tạo Issue **key mới cho quyết định/nghĩa vụ hiện tại** với lý do nguồn thay đổi. Ví dụ key cũ hỏi quyền nhân viên theo S2; key mới hỏi chính sách cấp quyền sau thay đổi S3. Đây là câu hỏi mới do thay đổi nghiệp vụ, không tự mở lại câu hỏi cũ để né unique. Nếu nguồn hiện hành đã rõ và chỉ thiếu phân tích, key mới là analysis_omission giải quyết bằng nguồn/kiểm tra; không hỏi người dùng lại nội dung đã có.

Old key luôn còn một successor được chọn trong AnalysisSet. Successor giữ nguyên `answer_ids`, `resolution_event_refs` và nội dung resolution lịch sử; chỉ thêm `resolution_replacement` để phân biệt “đã có lời giải thay thế cho nghĩa vụ hiện tại” với “lời giải cũ trở lại đúng”. `resolution_carry=null` ở nhánh này; bằng chứng carry not_applicable vẫn nằm nguyên trong `obsolete_issue_id`. Không tạo app cho key cũ.

`resolution_replacement` đề xuất là object sau (null ở DIRECT/CARRY):

| Field | Kiểu và quy tắc |
| --- | --- |
| origin_issue_id | DIRECT Issue gốc, cùng root của obsolete_issue_id; chứng minh Answer/application cũ |
| obsolete_issue_id | CARRY Issue lịch sử có assessment=not_applicable do human_review; cố định cho chuỗi replacement này, truy lại đầy đủ checks/root |
| from_issue_id, base_analysis_set_id | Predecessor **current cùng key cũ**, bằng supersedes_id, được set base chọn; CAS trên cả Model/set |
| change_id | Change đúng parent/current Model khi đổi Model; null khi chỉ đổi Issue/set trên cùng Model |
| replacement_issue_id | Issue **current ở result AnalysisSet**, cùng Model/session, key khác; đại diện quyết định/nghĩa vụ mới. Không dùng Issue lịch sử hoặc chính key cũ |
| assessment | complete hoặc incomplete: nghĩa vụ hiện tại đã được thay thế đầy đủ hay chưa; không phải applicability của resolution cũ |
| obligation_checks | Mảng `{old_ref:SourceRef,current_ref:SourceRef|null,disposition:replaced|removed,evidence_record_ids:ID[],reason:Text}`; đối chiếu đủ basis/criteria/nghĩa vụ cũ và phát hiện nghĩa vụ mới. Removed cần căn cứ nguồn mới và quyết định người review, không suy từ việc LLM bỏ sót |
| scope_check | Cùng shape scope_check của carry: từ predecessor, tới Model hiện tại; cover toàn affected/blocking/Parts và reverse impact, không cắt action |
| evaluation | Cùng shape evaluation; method structural_check hoặc human_review, evaluator/rule/evidence/reason gắn đúng base, nguồn và phạm vi |

**Bảng transition của nhánh REPLACEMENT:**

| Tiền đề / kết quả | Record được chọn ở key cũ | Key mới / chặn |
| --- | --- | --- |
| Old carry not_applicable, chưa có quyết định thay thế | Giữ CARRY pending, hoặc successor REPLACEMENT incomplete khi đã tạo target | Target open/pending nếu có; old hold giữ nguyên, không tự withdraw |
| Đã có Answer mới nhưng chưa applied, chỉ prepared hoặc model chưa sửa | REPLACEMENT incomplete, status=resolution_pending_revalidation | Không release; unique Answer cũ vẫn applied=1, Answer mới applied=0 |
| Target resolved đúng nguồn/model, coverage và việc tái phân tích liên quan đã đủ, được người review xác nhận thay thế | REPLACEMENT complete, status=resolution_replaced, blocking rỗng | Giữ affected cho audit. Chỉ bỏ hold của key cũ, các blockers/tasks khác vẫn xét bình thường |
| Model tiếp theo chỉ thay phần độc lập | Tạo successor, target rebind theo current key/lineage; có proof coverage/closure đầy đủ thì structural_check được giữ complete | Không dùng target ID lịch sử. Nếu chưa chứng minh được thì incomplete + materialize lại hold |
| Target lại pending/hết hiệu lực, nguồn/scope thay đổi hoặc thiếu evidence | REPLACEMENT incomplete + resolution_pending_revalidation | Giữ obsolete root bất biến và blocker hiện tại; không đánh Answer cũ applicable |

**Điều kiện complete, kiểm nguyên tử trước publish và khi đọc lại:**

1. Origin/obsolete/from đúng session, old issue_key và lineage; obsolete bằng from hoặc là ancestor của from và not_applicable đã có bằng chứng, không đổi text/status để tạo điều kiện. Successor giữ **bằng** answer_ids/resolution_event_refs của from. Root event vẫn trỏ root cũ, không backlink sang replacement Issue.
2. Result set chọn đúng một Issue/key: cả old successor lẫn target mới và các keys cũ khác đều có mặt, cùng Model. Target khác key, có lý do câu hỏi/nghĩa vụ mới gắn nguồn và hiện hành, không giả key khác để né claim. Target complete phải là DIRECT resolved hoặc CARRY applicable hợp lệ; không chấp nhận target là REPLACEMENT để tránh vòng/chains tự chứng minh. Kiểm cycle cả lineage và quan hệ thay thế; incomplete cũng không được trỏ vòng hoặc thiếu record.
3. Target đã giải quyết **toàn bộ** nghĩa vụ gây blocker cũ trong nguồn hiện tại. Obligation/scope checks phải cover text + từng criterion + rules/permissions/Parts và phần mới phát sinh; chỉ refs resolve hoặc đổi prose là không đủ. Target hẹp hơn ⇒ incomplete, giữ toàn vùng chưa chứng minh (không release một phần theo nhãn complete).
4. Việc áp dụng quyết định phải hiện trong Model/actions/rules/mapping thuộc scope; mọi task reanalysis liên quan được chứng minh bằng current-model evidence và TaskAttestation theo contract. Không mutate task/Change lịch sử thành done. Task ngoài scope chưa xong vẫn chặn phần tương ứng. Khi source đổi, source switch và reanalysis completion là hai việc khác nhau.
5. **Lần complete đầu tiên** hoặc source/scope/target meaning thay đổi cần human_review thật về quan hệ thay thế, với source diff, target resolution, coverage và task evidence. Đây là review chuyển nghĩa vụ, không Model Review bước 9; có thể nhận cùng thao tác người dùng trả lời nhưng chỉ ghi complete sau khi model/evidence đã hình thành và họ đã xem đúng bản. Structural_check được ghi incomplete bất cứ khi nào; chỉ được giữ complete từ predecessor complete trên cùng snapshot với target còn resolved/applicable, nghĩa/footprint không đổi và proof đầy đủ. Human_review chưa đủ căn cứ cũng trả incomplete. Không giả human_review để tự hoàn tất.
6. Chỉ complete mới có status=resolution_replaced và blocking rỗng; incomplete có status=resolution_pending_revalidation và hold đầy đủ theo impact. Bảng CARRY §3.3 không áp lên REPLACEMENT. Admission/closure/current-key resolver phải hiểu ba nhánh; không bỏ blocker chỉ vì status không phải open. Thất bại CAS/kiểm tra ⇒ không publish successor/set/head mới.

**Answer mới và nguồn mới:** tạo `Answer_new.issue_id=target_pending`, key mới; `supersedes_answer_id=null` khi khác key (không vi phạm answer_lineage bằng cách trỏ Answer cũ). Application hiện có chỉ nhận target open/answered_pending_application, tạo target DIRECT resolved, Model/Change/set và event mới đúng target. Unique tính **theo từng Answer**: Answer_old vẫn một application, Answer_new tối đa một application. Bảo toàn kiểm application_pending_issue/current-key/backlinks/claim; không mở rộng nó để apply lên old revalidation Issue. Nếu Answer_new đổi requirements, vẫn full input/diff/consent + checked S01 theo A1; không dùng human review replacement thay consent. Nếu chỉ nguồn đã có, dùng points_to_existing_source. Nếu không cần Answer vì nghĩa vụ đã rõ, target resolved source-only cần trace/evidence thật và human review quan hệ thay thế; không tạo Answer/event giả.

**Thứ tự và recovery:** có thể (a) atomic T3 ứng dụng Answer mới và publish old successor incomplete; sau khi người review xem evidence, một command mới CAS cùng Model/AnalysisSet tạo old successor complete, hoặc (b) publish complete cùng T3 chỉ nếu người review đã xem/pin đúng toàn candidate/hash/base và mọi proof hoàn tất. Khuyến nghị (a) cho local đầu tiên. Khi thêm key mới hoặc đổi Model, old key vẫn giữ hold trong mọi checkpoint trung gian. Nếu S01 đã commit, recovery lookup đúng run như A1, không resend. Nếu T3 application mới đã commit nhưng replacement review chưa xong: lookup application_new, giữ incomplete, chỉ tiếp tục review; không apply Answer_new lần hai. Mất ACK sau complete: lookup đúng command/records. Hai reviewers/publishers cạnh tranh: một CAS thắng, bên còn lại stale, không rebase ngầm. Hai applications cùng Answer_new: unique/claim như cũ, không có đường khác qua retirement.

**Kế thừa sau replacement:** mỗi successor kiểm lại target current/model/lineage và proof; obsolete/root vẫn cố định và giữ not_applicable ở lịch sử. Nếu target bị thay bởi một quyết định/key khác, không auto follow; explicit new replacement proof phải nối lịch sử target trước, đầy đủ coverage và human review. Target không còn đủ chứng cứ ⇒ incomplete/hold, không quay về coi resolution cũ đúng. Khi một nghĩa vụ bị bỏ khỏi source, complete cũng cần chứng cứ loại bỏ và human review; không tự xoá key khỏi AnalysisSet.

**Phạm vi sửa validator/schema sau duyệt:** thêm field/status REPLACEMENT và nhánh discriminator theo hai object; typed history refs origin/obsolete/from/base cùng old side của checks được resolve lịch sử có kiểm; replacement_issue_id bắt buộc current trong result set. Generic issue refs khác giữ nguyên. Run/Change khi chỉ review set không tạo application; khi apply Answer mới Change.application_event_refs chỉ chứa event **mới**, event cũ vẫn thuộc Change cũ. Model/Part/task readers nhận resolution_replaced chỉ khi proof complete, revalidation luôn blocker. Extended schemas/profile phải bắt cả hai nullable fields; history thiếu field dùng legacy profile, không backfill bytes. Không sửa contract draft.3 trong lượt này.

Phương án khác là root DIRECT mới cùng issue_key, tách active/historical Answer/event arrays. Không chọn vì phải đổi identity của các trường evidence hiện có và application target semantics rộng hơn. Nhánh replacement giữ root cũ và current-key selection nhưng thêm một field/trạng thái cùng proof coverage; đánh đổi này cần audit. [JSON 07](examples/s02-phase2/07-resolution-replacement.json) minh họa đầy đủ các checkpoint; đây chưa là ứng dụng đã chạy.

## 4. Version, lịch sử và migration đề xuất

**Chưa thực thi migration hoặc đổi version.** Sau audit mới chốt contract/package/DB profile mới, tách với draft.3/a3. Đề xuất DB format mới có capability/profile marker để reader a3 từ chối kho chứa extended payloads, không diễn giải chúng như DB1. Nếu G4 về sau cũng đổi DB thì cần migration order cụ thể, không mặc nhiên gộp hai migrations chưa thiết kế.

Khuyến nghị compatibility reader có **hai schema profiles rõ ràng**. Legacy payload thiếu observed_source_context_id hoặc resolution_carry được kiểm bằng rules draft.3 nguyên trạng; không insert mặc định vào bytes lịch sử. Extended application phải có field mới, extended Issue phải có cả resolution_carry và resolution_replacement (cả hai null cho DIRECT), không cho payload lai thiếu field rồi tự đoán. Legacy root application hợp lệ có thể là origin của carry mới sau full DIRECT validation; thiếu/sai evidence thì reject, không backfill approval.

Migration đề xuất trên **bản sao mới**, explicit người dùng chọn, verify DB1 bằng a3 trước, giữ records/events/blobs/IDs/timestamps/hashes/receipt links/unique applied và links lịch sử nguyên byte; chỉ metadata cấu trúc/profile mới nếu đã được audit. Không tự sửa DB cũ, không reset/cập nhật Answer/Issue cũ. Readers mới cần kiểm mixed history theo profile, materialize/verify typed links mới chỉ cho records mới, và gate unknown status fail closed. Rollback vận hành về kho DB1 cũ chỉ an toàn nếu không mất writes mới; không hứa downgrade tự động. Chi tiết DDL/backup/reopen/migration fault thuộc batch sau có quyền implementation, phải review trước khi chạy.

## 5. Bảo vệ giữ nguyên và quyết định còn chờ

Giữ Answer/events/records bất biến; current Issue key + lineage; root event target/model/backlinks; AnalysisSet cùng Model, một current/key; unique application/Answer và active claim; paired CAS; Run failed/rejected/stale không publish; exact source/request/consent chain; không transaction xuyên S01/S02; lookup recovery không resend; requirements_switch snapshot khác; analysis_edit giữ Context; source refs không nối index xuyên revision; admission khác Review.

A1 đã đóng ở mức thiết kế theo audit draft.2; phần 2 được giữ nguyên. A2-R1/R2 và S02-P2-02 đã đóng ở mức thiết kế theo audit draft.3; không yêu cầu sửa lại semantics. Cần audit gói schema/profile/version/compatibility/migration cụ thể trước persistence/carry. Người dùng quyết định cho phép semantics amendment, migration scope và batch implementation; chưa có quyết định ấy. Ví dụ [05](examples/s02-phase2/05-unchanged-application.json) và [06](examples/s02-phase2/06-resolved-issue-carry-forward.json) là projections dùng field mới **không hợp a3**, có positive/negative expectations để audit. [Bảng phản hồi draft.3](S02_PHASE2_DRAFT3_AUDIT_RESPONSE.md) không tự ghi findings đã đóng.
