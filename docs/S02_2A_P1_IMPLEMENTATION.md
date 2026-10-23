# S02 2A-P1 — profiles và validators

Ngày 22/10/2026. Package `dacn-s02 0.2.0a3` đã được [nghiệm thu kỹ thuật P1 cấp thấp/local](/Users/macbookpro/.codex/.chatgpt-projects/g-p-68c38c8799f48191a101e19a975ca4f9/outputs/audits/s02-2a-p1-0.2.0a3-2026-10-22-223420/S02_2A_P1_ACCEPTANCE.json). Findings 01/02/03/04 đã đóng. Nội dung API dưới đây mô tả bản P1 đã nghiệm thu; giới hạn DB1/E1 trong bộ nhớ là trạng thái của bản ấy.

Người dùng đã giao riêng [P2 — DB2 và E1 persistence](S02_2A_P2_IMPLEMENTATION.md), target `0.3.0a1`; P2 chưa nghiệm thu. P3, migration, 2C và live chưa được giao. Bàn giao P1 cũ không bị sửa trạng thái lịch sử.

## Profile và dispatch

| Profile | Resource | Rules / contract | Quyền |
| --- | --- | --- | --- |
| L1 `s02-profile/legacy-a3` | `schemas/contract.json`, nguyên byte a3 | `s02-rules/legacy-a3`, `s02/0.1.0-draft.3` | Repository DB1 và low-level checks |
| E1 `s02-profile/a1a2-v1` | `schemas/profiles/a1a2-v1/contract.json` | `s02-rules/a1a2-v1`, `s02/0.1.0-draft.4` | Low-level validation trong bộ nhớ; chưa có writer |

Registry packaged có allowlist và hash thực; descriptor chính xác gồm profile_id/contract_version/rules_id/required_capabilities/schema_sha256. Hash registry ghim trong `profiles.py`. `Profile` frozen giữ schema/descriptor bytes; truy cập cây schema trả bản riêng, không dùng mutation global theo request. Unknown descriptor/profile/rules/capability/hash bị từ chối. Các resources chỉ local `$ref`. Semantic rules ID là nhãn phiên bản, không chứng minh thuật toán đúng; manifest bàn giao ghi hash từng module và hash bundle rules thực tế.

`shape(..., profile=...)`, `walk_schema(..., profile=...)`, `fields(..., profile=...)`, `typed_links(..., profile=...)` dùng cùng owner. Helpers legacy mặc định L1; alias `SCHEMA` luôn là L1. `validate_record(..., owner_profile=..., profile_map=...)` và `validate_operations(..., operation_profile_map=..., record_profile_map=...)` cần map đủ khi có E1; không suy metadata từ payload. Events/stages thừa kế operation, không có profile override trong JSON. Các module kiểm không sửa caller inputs.

Entry point thuần `profile_graph.validate_graph` yêu cầu explicit record/operation profiles và owners cho toàn graph, archive/staged bytes, commands/events. Trước dispatch profile/lineage, nó kiểm command map key bằng command_id và reserved_run_id duy nhất giữa mọi operations, kể cả prepared/unfinalized. Nó kiểm shape toàn bộ targets, session/typed links, archive/hash, record semantics, operations, uniqueness application trong graph, publication/lineage và inventory; records mới được công bố phải cùng profile operation, reused records giữ owner profile cũ. Graph mixed L1/E1 **trong bộ nhớ** không phải mixed store. Metadata profiles/owners phải do caller có thẩm quyền cung cấp; đây không phải endpoint trusted import/candidate hay bằng chứng nguồn đã được checked lookup chỉ từ file JSON.

`validate_record`/`validate_operations` là thành phần kiểm, không tự đầy đủ như whole-graph entry point. Caller phải cung cấp toàn graph đã kiểm shape/nguồn; không dùng kết quả của một helper thay whole-store validation, claim hoặc CAS. `check_base_pair` chỉ so cặp head được caller đưa vào; giao dịch CAS/claims vẫn do repository legacy hoặc P2 tương lai thực hiện. Không có token thành công P1 nào cấp quyền publish E1.

## Schema, required/nullability và typed refs

Mọi object mới đóng. Hai trường nullable ở Issue E1 **bắt buộc có key**. Không backfill L1. Bảng diff máy đọc nằm trong evidence `schema-changes.json`.

| Vị trí | Thay đổi E1 | Required/nullability và refs |
| --- | --- | --- |
| `$id` | `urn:dacn:s02:0.1.0-draft.4` | L1 không đổi |
| `issueBody` | oneOf DIRECT/CARRY/REPLACEMENT | DIRECT: cả hai object null, status cũ; CARRY: carry object/replacement null; REPLACEMENT: carry null/replacement object |
| `resolution_carry` | Origin/from/base/change, assessment, source_checks, scope_check, evaluation | Tất cả required; change_id nullable; to_ref và element_pairs.to nullable khi removed |
| `resolution_replacement` | Origin/obsolete/from/base/change/current target, assessment, obligation_checks, scope_check, evaluation | Tất cả required; change_id và current_ref nullable theo nghĩa quy định |
| `ResolutionEvaluation` | method structural_check/human_review; evaluator/rule_version/evidence_record_ids/reason | Không nullable; không còn structural_reuse; metadata không xác thực người review |
| `application_applied.payload.observed_source_context_id` | Archive của run S01 quan sát, tách khỏi nguồn Model | Required nullable; changes_requirements phải non-null; existing-source phải null; typed source_context |
| `$defs.Export` E1 | false | Không mạo danh export draft.3 hoặc công bố mixed export v2 |

Ngoại lệ lịch sử chỉ ở carry origin/from/base; replacement origin/obsolete/from/base; `source_checks.from_ref`, `obligation_checks.old_ref`, `scope_check.from_scope`, `element_pairs.from`. Schema gắn `x-history` đúng các field ấy. Generic Trace/SourceRef, new/to side, Scope/ElementRef còn lại vẫn pinned current Model/snapshot; replacement target phải được result AnalysisSet chọn, cùng Model/session và khác key. `change_id` là Change chuyển Model này; null khi chỉ đổi Issue/set. Typed links vẫn giữ nguyên path/type, không biến history thành untyped ID.

## A1 cấp thấp

`observed_source.check_application_source` kiểm base Model/source và set; interpretation–consent–dispatch–observation–Answer; run/store/spec/snapshot/request; archive blob hashes/length, schema S01 và envelope; full staged raw **run source** khớp consent. S01 envelope a6 không có raw hash/length ở run.source: hash/length được lấy từ Artifact/BLOB thực, không bịa trường vào envelope. Raw được chuẩn hóa và đối chiếu snapshot bởi `verify_archive` a3; origin source và run source vẫn riêng khi source IDs khác.

Cùng snapshot: analysis_edit giữ Cmodel, event vẫn trỏ Cobserved riêng. Khác snapshot: requirements_switch dùng Cobserved, kể cả result_kind=unchanged. Cùng snapshot ID nhưng archive giá trị khác bị từ chối. Check recovery từ chối dispatch S01 mới khi ancestor đã có dispatch; không có hàm submit/resend trong production code P1. Các tests S01 thật chỉ tạo kho synthetic mới ngoài checkout.

## A2 và giới hạn chứng minh

DIRECT tách thành `validate_direct` giữ oracle a3; event phải trỏ chính root Issue/Model và backlinks. Whole graph bổ sung atomic selected result/current lineage qua events. L1 root được kiểm bằng profile L1, E1 root bằng E1. Carry/replacement không áp lại Answer hay thêm backlink event cũ vào Change mới.

CARRY kiểm chuỗi hữu hạn về DIRECT root, from=supersedes=current base selection, paired base/result publication, bảo toàn answer_ids/resolution_event_refs/resolution. Basis được lấy từ root/predecessor traces, Answers, interpretation nguồn và footprint của actions/rules/data/actors/Parts; requirement ref mở ra từng criterion. Footprint dùng closure và reverse impact, không mở mọi actions chỉ vì chung component. Pairs/correspondence có thể nhiều–nhiều; không nối criteria theo index xuyên snapshot. Structural applicable cần cùng snapshot, predecessor resolved/applicable, toàn proof/coverage và footprint không đổi. Thiếu proof giữ undetermined và đầy đủ hold; ref/lineage sai vẫn lỗi. Structural not_applicable bị từ chối. not_applicable không được lật trở lại applicable bằng carry.

REPLACEMENT giữ origin/obsolete lineage, current target khác key, không target-chain/cycle. Complete cần target DIRECT resolved hoặc CARRY applicable, coverage, current evidence và task completion/TaskAttestation đúng version; lần complete đầu cần human review evidence. Removed cần thay đổi nguồn có căn cứ và không được mâu thuẫn giá trị/criterion còn nguyên; structural continuation chỉ giữ complete đã có cùng snapshot/footprint/target meaning và proof. Target pending hoặc thiếu proof phải tạo incomplete với hold; lịch sử completed giữ nguyên. Validators từ chối current complete sai, không tự sửa record bất biến.

Bản a2 tách scope của task khỏi hold của replacement. Evidence phải current-model và phủ scope task; evidence A1 không bị buộc phủ hold A1/A2. Task Model cũ được vận chuyển qua từng cạnh Model bằng element_pairs trong chuỗi resolution đã validate, giữ đủ mọi đích khi split và ID cũ còn tồn tại. Không có correspondence, có removal hoặc thiếu coverage thì không được khai complete; giữ incomplete/hold. Không suy correspondence chỉ từ ID bằng nhau, không sửa task lịch sử. P1 chưa có cơ chế attestation riêng cho task bị xóa hoặc correspondence ngoài chuỗi resolution này; các trường hợp ấy không đủ chứng cứ để release.

Structural continuation kiểm riêng affected/blocking và footprint của target predecessor/successor: cùng tập thành viên (không phụ thuộc thứ tự), exact values và impact đã biểu diễn, cho phép đổi model pin qua lineage hợp lệ. Target đổi phạm vi/giá trị cần incomplete hoặc human review mới ghim đúng graph, cùng mọi điều kiện complete còn lại. Không dùng scope_unchanged của replacement làm bằng chứng cho target.

Bản a3 bổ sung comparison index riêng E1: mỗi Part được so cùng mapping row chứa nó (ID, source_ref, assessment, issue_ids và tập Part IDs). `_scope_proof` dùng identity này cho điều kiện unchanged và tập thay đổi đưa vào reverse impact; target footprint dùng cùng index. Giữ nguyên `validation.index_model`, closure và toàn logic L1. Hoán đổi nguồn hoặc reparent Part không còn bị che bởi cùng Part JSON/tập source refs tổng.

Thứ tự rows/Parts, issue IDs và các danh sách ID dạng tập trong Part không mang nghĩa cho phép so này; không sửa arrays nguồn, criterion order hoặc workflow order. Model revision pin được xử lý như trước. Nhãn pair unchanged vẫn kiểm payload Part, còn structural release cần cả ngữ cảnh mapping không đổi; thay ngữ cảnh có thể giữ undetermined/incomplete với full hold hoặc đi human review mới ghim graph cùng mọi coverage checks hiện hành. Không có thay đổi contract/profile/rules ID, schema hoặc writer.

`HumanReviewEvidence` là input **ngoài payload** cho low-level verifier, ghim reviewer/assessment và digest graph phụ thuộc bất biến mà họ xem. Không có UI/record/persistence/authentication protocol mới trong P1. Caller không được lấy metadata do LLM sinh làm input tin cậy này. Việc đối chiếu digest chỉ chứng minh binding, **không chứng minh có người thật review**, tính đúng nghiệp vụ, đủ nghĩa vụ ngữ nghĩa hay chất lượng phân tích. Fixtures dùng `SYNTHETIC REVIEWER`, không phải người dùng xác nhận. P2/2C cần thiết kế adapter/persistence tương ứng trong phạm vi được giao riêng.

Scope proof bảo thủ: unknown impact/support không đủ để release. Structural checks đối chiếu graph/values đã biểu diễn; không chứng minh graph không thiếu dependencies/permissions. Task evidence kiểm refs/current-model/scope và attestation; người review phải kiểm nội dung phù hợp bước/nghĩa vụ. Không có LLM đánh giá ngữ nghĩa, renderer hoặc benchmark trong bằng chứng P1.

## Fixtures và lane kiểm chứng

Suite a3 giữ nguyên files/assertions; lane wheel a3 riêng và lane package P1 dùng repository L1 nguyên hành vi. Không chuyển fixtures cũ thành E1 để báo legacy pass. Fixtures mới ở `profile_fixtures.py` dựng canonical graph từ root L1 thực, thêm E1 rõ ràng trong bộ nhớ; JSON canonical mẫu bàn giao là validation fixtures, không export/import production.

| Oracle cũ | Oracle E1 / lý do |
| --- | --- |
| Issue a3 không có carry/replacement | E1 DIRECT thêm đúng hai key null; L1 vẫn từ chối keys mới |
| application a3 không observed context | E1 existing-source thêm null; A1 changes-requirements thêm observed archive có checked S01 fixture |
| Direct event trỏ root | Carry/replacement giữ root và kiểm lineage/proof riêng; không retarget event |
| Model/set/apply/recovery/CAS/claims tests | Chạy nguyên trên DB1; P1 không hứa E1 persistence/race/durability |
| Closure Part nhiều actions | Thuật toán cũ giữ nguyên; gate E1 thêm status pending_revalidation là blocker |
| Docs projections | Không dùng làm canonical export; generator test mới lưu full graph, bytes và profile maps |

Bàn giao và kết quả chạy mới: [START_HERE](../reports/s02-phase2/2a-p1-fix04-0.2.0a3-2026-10-22/START_HERE.md). Không dùng số tests cũ thay kết quả này.
