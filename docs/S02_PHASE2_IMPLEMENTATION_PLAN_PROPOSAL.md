# Đề xuất S02 Đợt 2 — bước 1–4

**Trạng thái: proposed — A1/A2 đã audit đạt ở mức thiết kế, G2 đã rõ; schema/profile/migration 2A còn chờ audit, chưa được duyệt implementation.**

Phiên bản tài liệu: `s02-phase2-plan/0.1.0-draft.3`; ngày 21/10/2026. Astra chuẩn bị thiết kế; agent khác audit độc lập; người dùng quyết định phạm vi, nghiệp vụ và quyền dùng dữ liệu/ngân sách. Lượt này chỉ cập nhật AGENTS và viết tài liệu/ví dụ. Không viết code/tests, đổi package/schema/DB, cài dependencies, gọi LLM hoặc renderer. Các câu lệnh, schema candidate, giới hạn và kết quả mong đợi dưới đây đều là **đề xuất**, trừ những mục được ghi rõ đã có.

**Cập nhật trạng thái audit:** [audit draft.3 ngày 21/10/2026](/Users/macbookpro/.codex/.chatgpt-projects/g-p-68c38c8799f48191a101e19a975ca4f9/outputs/audits/s02-phase2-proposal-draft3-2026-10-21/AUDIT_REPORT.md) đóng S02-P2-02/A2-R1/R2 ở mức thiết kế; A1 tiếp tục đóng và G2 giữ kết luận đã rõ. Semantics đã review giữ nguyên. [Gói schema/profile/migration 2A mới](S02_PHASE2_2A_SCHEMA_MIGRATION_PROPOSAL.md) cụ thể hóa gate kỹ thuật còn lại; gói này chưa audit/chưa được duyệt code. Báo cáo phản hồi và manifests cũ giữ trạng thái lịch sử. Nghiệm thu Đợt 1 không mở rộng sang implementation Đợt 2.

## 1. Baseline, căn cứ và chênh lệch tài liệu

### 1.1 Đã chốt và đã nghiệm thu trong phạm vi nào

| Căn cứ | Trạng thái dùng trong đề xuất |
| --- | --- |
| [AGENTS](../AGENTS.md), [README](../README.md) | Layout `packages/s01`, `packages/s02`; state ngoài checkout; dataset chỉ đọc; không import production source chéo package |
| [Contract S01](S01_OUTPUT_CONTRACT_PROPOSAL.md) | Input `1.0.0`, output `0.1.0-draft.2`; package S01 `0.1.0a6` nghiệm thu kỹ thuật CLI local |
| [Contract S02](S02_OUTPUT_CONTRACT_PROPOSAL.md) | `s02/0.1.0-draft.3`; giữ nguyên semantics, chín bước; không thêm architectural drivers |
| [Kế hoạch tổng thể](S02_IMPLEMENTATION_PLAN_PROPOSAL.md) | `s02-plan/0.1.0-draft.3`; thiết kế đã review không đồng nghĩa model, ngân sách hoặc live pilot được duyệt |
| [Bàn giao a3](../reports/s02-phase1/fixes-0.1.0a3/IMPLEMENTATION_REPORT.md), [kết quả](../reports/s02-phase1/fixes-0.1.0a3/TEST_RESULTS.md), [tái lập](../reports/s02-phase1/fixes-0.1.0a3/REPRODUCE.md) | Bằng chứng implementation lịch sử; không sửa trạng thái tại thời điểm bàn giao |
| [Audit độc lập 21/10](/Users/macbookpro/.codex/.chatgpt-projects/g-p-68c38c8799f48191a101e19a975ca4f9/outputs/audits/s02-phase1-0.1.0a3-2026-10-21/AUDIT_REPORT.md) và [acceptance](/Users/macbookpro/.codex/.chatgpt-projects/g-p-68c38c8799f48191a101e19a975ca4f9/outputs/audits/s02-phase1-0.1.0a3-2026-10-21/S02_PHASE1_ACCEPTANCE.json) | S02 `0.1.0a3`, DB structure `1`, accepted technical Phase 1 local foundation. S02-05 và LAYOUT-01 đóng; S02-01–04 tiếp tục đóng |
| [Nguồn LaTeX](/Users/macbookpro/.codex/.chatgpt-projects/g-p-68c38c8799f48191a101e19a975ca4f9/output/pdf/DACN_Schema_Input_v1_Phong_Kham.tex) | Schema input 11/10, flow S02 cập nhật 18/10; nguồn chỉ đọc |

Acceptance **không** nghiệm thu toàn bộ S02, phân tích nghiệp vụ, chất lượng LLM, renderer, khả năng vận hành production hoặc cho phép triển khai Đợt 2. Audit ghi S01 986 và S02 217 tests/backend, cùng các kiểm chứng độc lập; đây là số liệu **trích từ audit**, không phải tests chạy trong lượt tài liệu này.

### 1.2 Kết quả đọc code và những điểm cần tránh hiểu nhầm

- [service.py](../packages/s02/src/dacn_s02/service.py) chỉ điều phối `start`: checked intake, archive và Run với `steps=[]`, chưa tạo Model. `mode=live` ở intake hiện tại **không chứng minh đã gọi LLM**; phải đọc attempts và config.
- [repository.py](../packages/s02/src/dacn_s02/repository.py) có prepare/events/staging/finalize, CAS hai head, checked lookup; [events.py](../packages/s02/src/dacn_s02/events.py) giới hạn **một dispatch, một response_received/command**. Retry nhiều lần phải được điều phối qua command liên kết hoặc thay invariant sau review, không nhét nhiều dispatch vào command hiện có.
- [validation.py](../packages/s02/src/dacn_s02/validation.py) yêu cầu inventory mọi requirement/criterion ngay cả Model trung gian; mapping rỗng phải `not_assessed` và có Issue. Issue phải trỏ Model có thật; đây là ràng buộc bootstrap cần xử lý, không được lưu Issue mồ côi.
- [scope.py](../packages/s02/src/dacn_s02/scope.py) có closure/reverse impact và gate `permitted_scope` nhận **accepted scope**. Gate này chặn khi bất kỳ mapping nào chưa assessed; không dùng nó như bộ lập lịch trước review bằng cách dựng review giả.
- README và các mục lục/bàn giao trước audit còn ghi “chờ audit”. Kết luận 21/10 thay thế thông tin trạng thái ấy, không thay bytes lịch sử. Lượt này chỉ sửa AGENTS theo quyền được giao. Một số `external_bindings` của [ví dụ draft.3](examples/s02/01-source-and-model.json) còn đường dẫn `../../../src/...` trước đổi layout; giữ nguyên lịch sử, ví dụ mới dùng đường dẫn hiện hành. Đây là chênh lệch đường dẫn/trạng thái, chưa phải bằng chứng mâu thuẫn semantics contract.
- Không sửa draft.3 để hợp thức hóa code. Những phần draft.3 chưa quy định đủ cho orchestrator nằm ở mục 11; chưa được xem là đã giải quyết chỉ vì nền tảng a3 được nghiệm thu. A1/A2 cần audit semantics/schema/compatibility riêng; G3 mở rộng capture và G4 ledger/version DB vẫn chờ thiết kế/audit riêng. Không tự coi draft.3 đã bao gồm các thay đổi này.

## 2. Phương án khuyến nghị và ranh giới sở hữu

Đề xuất xây orchestrator local tuần tự, bốn bộ xử lý bước thuần, adapter provider nhỏ, adapter S01 có receipt và bộ quản lý ngân sách bền vững. Reuse Python/SQLite/codec/validator/repository hiện tại. Mỗi lời gọi có một command/Attempt; kết quả từng bước công bố riêng bằng CAS, thay vì giữ một transaction qua cả bốn bước. Cách này dễ truy vết và resume; đổi lại nhiều Run/Model revisions hơn. Không thêm framework agents, KB, solver, renderer hoặc service web.

### 2.1 Candidate không phải canonical record

LLM chỉ đề xuất nội dung. Candidate nội bộ kế thừa mục 3 của kế hoạch tổng thể: code giữ `base_model_id`, `base_analysis_set_id`, `source_context_id`, `step`, `scope`; payload LLM được ghép vào envelope nội bộ sau khi đối chiếu pins. Nếu provider echo các trường pin, code chỉ so sánh, không cho chúng đổi base. Đề xuất format payload LLM riêng `s02-candidate/0.1.0-draft.1`, một schema cho từng bước, chưa phải contract được duyệt.

| Dữ liệu | Người tạo và kiểm soát |
| --- | --- |
| Local handles, tên, mô tả, rationale, lựa chọn nhóm/tách, câu hỏi, nguồn đề nghị, phần nghĩa vụ được thể hiện/còn thiếu | LLM đề xuất; code kiểm kiểu/refs; reviewer kiểm nghĩa. Các array theo từng bước được khai báo trong schema, không mở dict tùy ý |
| `origin` explicit/inferred, trạng thái cần làm rõ, ảnh hưởng dự kiến | LLM đề xuất cùng bằng chứng; không suy explicit từ pointer hợp lệ. Code không nâng inferred thành explicit/confirmed |
| Record ID, logical ID, timestamp, revision, parent, producer Run, hashes, source pins, AnalysisSet selection, trạng thái lỗi/CAS | Code tạo; LLM không được ghi trực tiếp |
| Snapshot S01, priority/null/criteria và thứ tự, actor supplied | Chỉ lấy nguồn đã checked; LLM không tái tạo bản authoritative hoặc điền unknowns |
| Answer text/respondent, consent, quyết định nghiệp vụ và review | Người dùng cung cấp qua thao tác riêng; LLM không tạo consent/review hoặc tự đóng Issue |

Payload chung đề xuất có `candidate_version`, `step`, `proposals`, `questions`, `unrepresented_source_refs`. `proposals` có shape cố định theo bước: 1 là findings; 2 là actors/actions/workflows/data/rules; 3 là components/responsibilities; 4 là mappings. Candidate mới dùng handle cục bộ, existing refs chỉ từ allowlist của base. Trùng handle, thiếu target, field lạ, duplicate JSON keys hoặc giá trị không round-trip exact: reject với raw bytes giữ nguyên. Không “sửa” chuỗi/ID/số để qua validator. JSON provider schema là projection, không dùng nguyên schema Record/metadata của kho.

Luồng local: kiểm response transport → parse exact → kiểm candidate schema → kiểm source/handle/allowlist → lập bảng handle→ID một lần → dựng batch canonical → validate toàn graph/inventory/current Issues → CAS T3. Validation lỗi sớm khiến bước phụ thuộc `not_run` trong báo cáo điều phối, không thêm enum đó vào Run. Refusal/incomplete không đi vào parser candidate như kết quả thành công. Quy tắc không biểu diễn trong Structured Outputs vẫn do code kiểm.

Prompt được chia thành template version cho từng bước, cùng các khối cố định: vai trò/phạm vi bước, nguồn có delimiters như dữ liệu không đáng tin để điều khiển, inventory bắt buộc, current Issues/Answers đã áp dụng, base/handle allowlist, output candidate schema và checklist không suy quyền/không điền unknowns. Bước 1 yêu cầu chỉ ra thông tin đã có trước hỏi; bước 2 tách quyền xem/hủy và nhánh chưa rõ; bước 3 bắt buộc rationale/alternative/uncertainty; bước 4 đối chiếu toàn inventory và gap. Repair prompt thêm lỗi xác định được cùng capture gốc, không đổi nguồn hoặc quyền. Chỉ yêu cầu rationale thiết kế ngắn có nguồn, không yêu cầu/lưu chain-of-thought; không bật reasoning summaries/tool outputs ngoài nhu cầu. Prompt hash là bytes đã render cho từng Attempt; template version riêng giúp so sánh thay đổi, không bảo đảm model deterministic.

Canonical projection: findings → Issue + successor AnalysisSet; bước 2–4 → Model + Change + AnalysisSet + các Issue hiện hành; Run/Attempt/Artifacts do code. Không cấp Artifact chính thức có producer Run chưa tồn tại. Candidates chỉ nằm trong response/staging cho đến T3; không là endpoint nhập Record bất kỳ.

### 2.2 Identity, revision và evidence

- Record ID UUIDv4 theo generator/repository hiện hành. Logical IDs giữ khi cùng phần tử được sửa qua explicit edit; new handle được cấp mới; không nối lại identity bằng tên tương tự. Mapping row có một source obligation chính xác; criterion ref luôn snapshot + pointer, không nối index/text giữa revisions.
- Model mới là full state, parent revision +1 và Change; không ghi đè. Chỉ thay Issue của cùng Model thì tạo AnalysisSet successor; không bump Model chỉ vì có log. Issue successor giữ `issue_key`, `supersedes_id`, một current record/key; chuyển model phải tái gắn refs/scopes và giữ lineage, không bỏ các Issue đang mở. Riêng Issue resolved bằng Answer không được clone/rebind bằng a3; phải dùng A2 resolution_carry sau khi amendment được duyệt, giữ root application và đánh giá applicability hiện tại.
- `Trace` giữ source/Answer refs, origin, rationale, Issue IDs. Bằng chứng đáp ứng nghĩa vụ là nội dung obligation, trách nhiệm, thao tác/quy tắc và phần thiếu; refs chỉ chứng minh truy nguồn.
- Prompt template bytes + version/hash; prompt đã render bytes; config bytes + version/hash; request HTTP body chính xác; response HTTP body nguyên bytes, media type, byte length, SHA-256; headers allowlist không chứa Authorization. Hash là nhận diện bytes, không chứng minh nghĩa hoặc xác nhận của người dùng. Canonical JSON qua codec exact; raw response có thể không phải JSON.
- Config artifact đề xuất chứa `execution_origin=synthetic_mock|recorded_replay|provider_live|local_code`, template/candidate/adapter versions, source/base pair, limits, budget identity, provider/model/tier, tool policy và provenance replay. Đây là **nội dung blob đề xuất**, không thêm field vào Record. Prompt/request được pin tại T0 và reuse đúng artifact identity/producer khi hợp lệ.
- Contract Run chỉ có `live|replay`: synthetic mock dùng `replay` cùng marker rõ; không tạo enum `mock`. Recorded replay giữ hash/ID capture gốc, không giả một lời gọi mạng mới; usage lịch sử để trong provenance capture, không tính thành chi phí thực tế của replay. Attempt metadata phải khớp events của lượt hiện hành. Code-only bootstrap có attempts rỗng; live intake không được báo là live LLM.

## 3. Bootstrap và lưu tiến độ trước Model đầu tiên

Đề xuất cần review **G1**: sau `start` có SourceContext, code tạo một Model nền tối thiểu bằng command `work`, base pair null, scope null, config `local_code`, attempts rỗng. Giữ toàn bộ supplied actors và refs, các tập actions/workflows/data/rules/components/responsibilities/interfaces/dependencies rỗng; tạo một Mapping row/requirement và criterion từ inventory. Mỗi row `parts=[]`, `assessment=not_assessed`, liên kết Issue `kind=verification` nêu “chưa phân tích nghĩa vụ”, không giả câu hỏi nghiệp vụ. Một Issue công việc có thể phục vụ nhiều row nếu trace liệt kê đủ nguồn.

Model/Issue/AnalysisSet/Run/config Artifact cùng T3 để giải quyết refs vòng. AnalysisSet đầu revision 1 có affected inventory đúng Model; Issue affected/blocking chỉ chứa phần tử thật, không dùng scope rỗng với nghĩa toàn hệ thống. Unknown impact phải enumerate toàn Model/Parts hiện có theo draft.3, và tính lại khi Model có phần tử mới; không giữ affected rỗng để biểu diễn unknown. Không tuyên bố `ready` hoặc scope độc lập từ skeleton. Gate bắt buộc coi những nghĩa vụ chưa phân tích là **chưa biết ảnh hưởng**, chặn chấp nhận/bàn giao. Bootstrap là chuẩn bị đầu bước 1, không phải bước thứ mười hay hoạt động LLM.

Sau bootstrap, bước 1 lưu findings source-level vào Issue và raw response; khi chưa có actions/Parts, scope chưa thể chi tiết. Source-level holds nằm trong một manifest điều phối có version/hash ở config/response và được tái dựng từ inventory + current Issues; **không** là Review. Không chọn subset để né các holds chưa xác định. Bước 2 có thể tạo candidate tạm nhằm tìm phạm vi ảnh hưởng; chỉ công bố phần chưa rõ với trạng thái/Issue đúng, không gọi nó là kết quả nghiệp vụ đã giải quyết. Bước 4 phải chuyển mọi hold tới mapping/closure cụ thể hoặc giữ hold rộng; không mất blocker khi thêm phần tử.

Mỗi bước lưu một checkpoint canonical bằng T3. Failure trước T3 giữ head cũ và staging/outcome; resume đọc command/bytes cũ. Crash sau T3 lookup trả đúng records, không dựng lại IDs/timestamps. Rerun thực sự là command mới pin head pair hiện hành, Change/AnalysisSet successor và liên kết lần trước; không sửa checkpoint cũ. Nếu bootstrap hoặc bước nào chưa đủ các invariant intermediate, dừng phần publish và đưa gap đi audit, không nới validator.

## 4. Bước 1 — Kiểm tra ý nghĩa và làm rõ

**Input/gate:** SourceContext checked từ S01, snapshot/schema/envelope/raw source đã archive, Model nền + AnalysisSet hiện hành, inventory FR/NFR/constraints/criteria, previous Issues/Answers nếu có; quyền gửi đúng dữ liệu chỉ cần ở mode live. Source/base mismatch hoặc archive hỏng dừng trước dispatch.

**LLM:** soát từng nghĩa vụ tìm thiếu, mơ hồ, mâu thuẫn; trích nguồn và giải thích ảnh hưởng; phân loại đề nghị `business`, `quality_target`, `analysis_omission`, `design_choice`, `verification`. Trước đề nghị hỏi người dùng, đối chiếu snapshot, Answer đã áp dụng và Issues hiện hành. Thông tin đã có nhưng bị bỏ sót phải sửa phân tích với ref; không hỏi lại. Giá trị null/[] chỉ là tín hiệu xem xét, không tự kết luận mọi unknown chặn mọi bước.

**Code:** kiểm coverage lượt đọc bằng inventory, hợp lệ của refs, duplicate/lineage Issue và nguồn không bị lược mất; không chứng minh LLM đã đọc hiểu đầy đủ. Dựng Issue/AnalysisSet successor; unresolved phải ở current set. Nếu finding chỉ thay phân tích mà chưa đổi Model, giữ Model ID. Finding có scope chưa biết giữ source-level hold theo G1/G2; scope trống không có nghĩa không ảnh hưởng. Các open Issues giữ nguyên khi rerun không đề cập tới chúng; muốn resolved/withdrawn phải có lý do/bằng chứng và đúng protocol.

**Người dùng:** trả lời quyền, quy tắc, phạm vi, mục tiêu/ưu tiên chưa có. Design choice đưa review kỹ thuật; verification task giữ nghĩa vụ kiểm chứng, không yêu cầu người dùng bịa SLA. Ví dụ R4 đã giới hạn quyền xem, không suy ra quyền hủy ở R2; R3 là điều kiện thử, không tự biến thành peak production. R5 giữ constraint local và không gửi lịch hẹn ra ngoài.

**Output:** candidate findings → Issue có source Trace, affected/blocking cụ thể khi biết; AnalysisSet; Run `blocked` nếu còn holds ảnh hưởng, vẫn có thể lưu phân tích hợp lệ. Thiếu thông tin nghiệp vụ không phải lỗi JSON để “repair” model tự điền. Dừng scope phụ thuộc; tiếp tục phần khác chỉ khi có lý do độc lập dựa nguồn và kiểm closure. Nếu không xác định được phạm vi ảnh hưởng, chưa cho phần ấy qua gate.

**Chạy lại/stale:** Answer không tự đóng Issue; theo mục 8. Thay AnalysisSet trong lúc call làm kết quả stale dù Model không đổi; giữ raw, không gộp findings cũ vào set mới. Source đổi phải làm lại phát hiện vấn đề liên quan từ snapshot mới. Đợt 1 có Issue/Answer/set/invariants; còn thiếu prompt, coverage audit, question queue và scheduler/source-level hold.

## 5. Bước 2 — Actors/actions/workflows/operation–data–rule

**Input/gate:** snapshot đúng pin, kết quả bước 1 và current Issues, danh mục supplied actors nguyên nghĩa. Có thể phân tích nháp vùng đang bị hỏi để xác định ảnh hưởng; chỉ cho phần độc lập tiến tiếp khi các ràng buộc có thể áp dụng đã được xét. Không đồng nhất “có thể phân tích” với “đã được chấp nhận”.

**LLM:** đề xuất action có initiator/actors, dữ liệu read/write, permission rules và business rules, workflow nodes/edges, guard, luồng chính/nhánh/ngoại lệ cùng nguồn. Phân biệt action nội bộ với tác nhân ngoài. Actor mới chỉ là discovered candidate với nguồn/rationale; nếu đó là quyết định nghiệp vụ thiếu thì tạo question và `needs_clarification`. Không bổ sung actor vào snapshot S01. Chấp nhận suy luận sau này không đổi origin inferred.

**Code:** giữ supplied actors đủ và ref đúng `/actors/i`; kiểm typed refs, action initiator ↔ actor_ids, permission rule kind, graph endpoints, entry, decision guards, read/write/rule/workflow refs. Bổ sung kiểm local dự kiến cho reachability/nhánh bỏ quên và reciprocal links nếu contract yêu cầu; không tự sinh guard hay thêm node để “vá graph”. Tự động phát hiện dữ liệu không có nguồn/Issue; không tự chứng nhận quyền dựa tên actor. Quy tắc bảo toàn nghĩa và quyền phải có human evaluation.

**Người dùng:** quyết định ai đặt/hủy, ngoại lệ, giới hạn phòng khám nếu nguồn thiếu. Trong clinic, action hủy có thể giữ `initiator=unknown`, `actor_ids=[]`, chưa có permission rule, Issue mở; không gán nhân viên hoặc bệnh nhân chỉ vì đã có quyền xem. Khi LLM đề xuất “Quản trị viên”, không tự chuyển thành supplied actor hay cấp quyền toàn hệ thống.

**Output/canonical:** Model revision chứa actors/actions/workflows/data/rules + Change; tạo Issue successors theo trạng thái và A2 cho resolution đã áp dụng (chưa hợp a3 nếu chưa amendment), AnalysisSet mới revision 1 cho model đó; mappings còn not_assessed có Issue. Candidate giữ main/alternative/exception paths; canonical Workflow dùng nodes/edges/branch_points, không thêm schema flow mới. Những thao tác chưa rõ giữ state và Trace.issue_ids; biết rằng nhiều action cùng chạm dữ liệu chỉ là căn cứ phân tích, chưa phải dependency.

**Dừng/rerun:** refs thiếu/graph sai → rejected technical candidate; missing permission → business Issue, không tự retry để đoán đáp án. Source/Answer thay đổi dùng reverse impact + semantic review, chạy lại phần sớm nhất ảnh hưởng, giữ evidence phần tái dùng. Đợt 1 có entity shapes/validators/closure; cần extraction prompt, candidate linker, builder Change, source-aware impact và regression quyền.

## 6. Bước 3 — Initial components

**Input/gate:** action/workflow/data/rule model đã kiểm; current Issues và phạm vi có thể tiếp tục; giữ nguyên blockers. Không yêu cầu đã hoàn tất bước 5–6 để bắt đầu nhóm trách nhiệm, nhưng không tuyên bố dependency/characteristic đã đánh giá.

**LLM:** nêu component purpose, trách nhiệm, actions/rules liên quan, lý do nhóm/tách, phương án thay thế và uncertainties. Đánh giá boundaries dựa hành vi và quy tắc phải giữ. Không mặc định actor/entity/action/FR là một component; cùng data không bắt buộc gộp. Ví dụ nhóm đặt/hủy với quản lý nhất quán lịch/slot chỉ là một phương án; tách trách nhiệm cũng có thể hợp lý nếu có căn cứ phối hợp.

**Code:** kiểm Component và Responsibility refs, inventory actions được phân công hoặc có gap; không cho endpoint deploy/style/microservice tùy ý lọt vào canonical schema. Assignment vào Responsibility của một component và danh sách action/rule phải resolve; source trace phải tồn tại. Uncertainty về chia nhóm giữ trong alternatives/uncertainties hoặc Issue design_choice, không ép trở thành câu hỏi nghiệp vụ. Không dùng số component làm tiêu chí chất lượng.

**Người dùng/reviewer:** xác nhận những yêu cầu nghiệp vụ thật sự mới; reviewer xem rationale/alternatives. Lượt này không tạo review accepted chỉ vì schema pass.

**Output:** Model + Change + current AnalysisSet; Component/Responsibility fields theo draft.3. Interfaces/dependencies chưa phân tích giữ rỗng/chưa đánh giá, không tự sinh protocol hoặc hướng dependency từ thứ tự workflow. Scope độc lập có thể có candidate components, scope phụ thuộc giữ draft/needs_clarification. Dừng nếu không đủ căn cứ phân nhóm cho scope, giữ gap và bằng chứng thay vì kết luận hoàn tất.

**Rerun:** thay actions/rules/nguồn hoặc group boundary thì cập nhật responsibility và đánh dấu mappings liên quan cần xét lại, không giữ coverage cũ tự động. Đợt 1 có schema/model revision; còn thiếu grouping prompt, alternative comparison và responsibility coverage check. Không triển khai đánh giá scalability/security/... trên phương án ở đây: đó là bước 6.

## 7. Bước 4 — Mapping nghĩa vụ đến trách nhiệm/components

**Input/gate:** current Model bước 3, inventory đầy đủ nguồn FR/NFR/constraints và mỗi criterion, current Issues; không loại requirement vì priority null/could. Inventory là nguồn của phép kiểm tổng thể, không do LLM tự lựa chọn.

**LLM:** phân rã nghĩa vụ thành Parts có obligation rõ; target components hoặc system, actions, primary/supporting responsibilities, covered_portion/remaining_gap. Criterion row là nghĩa vụ riêng ngay cả khi requirement text đã mapped. Nếu nghĩa vụ hỗn hợp, tách các phần có ý nghĩa trước review; không cắt Part chỉ để né blocker. Source hợp lệ chưa chứng minh trách nhiệm thể hiện đúng nghĩa vụ.

**Code:** một Mapping row cho mỗi pointer inventory, không trùng/thiếu; Parts ID unique, target system không action_ids, target components/proposed cần actions và primary responsibility; primary/supporting không giao nhau; blocked có Issue đang mở, unassigned/blocked có gap. Row chưa phân tích có `parts=[]`, `not_assessed`, Issue; không biến rỗng thành satisfied. Không tự ép NFR/constraint thành component riêng. Với R3/R5, có thể tách phần toàn hệ thống và phần trách nhiệm cụ thể nếu có nguồn; chưa chứng minh performance/local compliance bằng mapping.

Chạy closure tới fixed point: action → Parts liên quan → **toàn bộ actions của từng Part mới** → workflow/Support/dependencies/mappings rồi lặp. P1(A1), P12(A1,A2), A2 bị chặn ⇒ P1 chưa độc lập; không cắt P12 lúc xét gate. Không kéo mọi action vì cùng component/interface/responsibility. Union các scopes sau closure phải kiểm lại. Constraint chưa assessed có thể áp dụng toàn bộ nên chưa cấp phép scope; không bỏ qua vì không có Part.

**Người dùng/reviewer:** so sánh source text/criteria với obligation, trách nhiệm và gaps; xác nhận nghiệp vụ khi có câu hỏi; không có field auto `satisfied=true`. Output là đề xuất mapping, không nghiệm thu đáp ứng requirement.

**Output/canonical:** Model/Change/AnalysisSet checkpoint; mỗi Part assignment proposed/unassigned/blocked đúng draft.3. Hết bước 4 có thể là Run `blocked` với model cấu trúc hợp lệ và phần thiếu được báo. Chưa Bundle/Review/Handoff hoặc diagram; chưa chuyển S03. Rerun do thay component/criterion/Issue phải xét lại coverage và closure; source revision mới không nối criterion theo index. Đợt 1 có inventory/mapping validator/closure; còn thiếu decomposition prompt, mapping builder và báo cáo coverage cho review.

### 7.1 Admission từng bước — G2, không phải gate review

**“Nghĩa vụ đã được xét cho bước k”** là entry manifest điều phối của snapshot/base pair: source ref đã được đọc, thông tin cần cho bước kế tiếp được liệt kê, verdict `usable|held|not_relevant_with_reason`, evidence refs, current Issue IDs, lý do phạm vi ảnh hưởng và phần còn phải làm. Mỗi requirement **và từng criterion**, gồm constraints, phải có entry `inspected` hoặc `not_inspected`; not_inspected không cho suy độc lập. Manifest có version/hash/pin, không sửa input, không là Review. Code kiểm inventory/bindings; nghĩa của verdict phải có căn cứ và phương pháp review, không coi LLM trả usable là chứng minh nghiệp vụ đúng.

`Mapping.assessment=not_assessed` trước bước 4 nghĩa **chưa phân rã/gán Parts**, không nhất thiết thiếu thông tin để trích actions hoặc nhóm components. `Mapping.assessment=proposed` ở bước 4 nghĩa đã có đề xuất mapping, chưa chứng minh đủ nghĩa vụ/được chấp nhận. Hai assessment không tự chuyển cho nhau. Verification tasks “chưa dựng Parts, sẽ làm ở bước 4” không chặn chính công việc xây bước 2–3; business/constraint holds thật không được đổi tên thành verification để qua gate. Giữ inventory rows/Issue bắt buộc của Model intermediate, không tạo Parts giả.

| Bước | Được đọc/phân tích nháp | Được publish checkpoint | Được chuyển tiếp trong Đợt 2 | Người dùng review |
| --- | --- | --- | --- | --- |
| 1 | Nguồn checked, pin pair; đọc cả FR/NFR/constraints/criteria/unknowns | Findings/Issues đúng nguồn, inventory đầy đủ, holds/current set không bị giấu; CAS. Có thể Run blocked | Sang 2 cho scope đủ thông tin actor/hành vi/rules cần trích hoặc phần chứng minh không phụ thuộc hold; chưa đòi Parts. Held scope chỉ tiếp tục nháp để tìm câu hỏi/ảnh hưởng, không gán permission/rule chưa biết | Không tự cấp |
| 2 | Nguồn/holds bước 1; vùng held có thể tạo candidate unknown có nhãn | Typed actors/actions/workflows/data/rules đúng cấu trúc; facts/unknowns giữ, Issue successors/A2 đúng, inventory và propagation holds; CAS | Sang 3 khi footprint trách nhiệm/action/rule/data đủ để đề xuất boundaries và đã xét constraint có thể tác động. Không đòi Parts hoặc dependency analysis bước 5 hoàn tất | Không tự cấp |
| 3 | Thử grouping/alternatives trong scope; boundary vẫn là đề xuất | Components/responsibilities có căn cứ, gaps/uncertainties/holds hiện hành; Model/Change/set hợp lệ, A2 khi cần; CAS | Sang 4 khi có responsibility candidates để đối chiếu inventory; không đòi đã map. Phần chưa rõ được lập mapping unassigned/blocked để báo gap, không gọi là thiết kế đã giải quyết | Không tự cấp |
| 4 | Đọc từng obligation, đề nghị Parts/coverage/gaps | Full inventory, Parts/refs hợp lệ hoặc row not_assessed có Issue; closure fixed point, holds/A2, CAS; có thể Run blocked | Đóng checkpoint bước 4 kèm omissions; phần thiếu không gọi hoàn tất. Không tự chuyển quyền bước 5–9/S03; gate review/handoff vẫn chặn unassessed | Không tự cấp |

Publish checkpoint xác nhận dữ liệu trung gian có cấu trúc/nguồn đúng, không xác nhận semantics đủ rõ. `advance(scope,k→k+1)` chỉ cho công việc bước tiếp, không là accepted_scope. Trước Parts: footprint dùng source inventory + actor/action/workflow/data/rule refs đã biết cùng lý do ảnh hưởng/độc lập; không lấy dependency/Support chưa phân tích làm proof. Khi có Parts/Support thì closure đầy đủ draft.3 bắt buộc. Unknown ảnh hưởng ⇒ hold rộng, không suy từ đồ thị rỗng. Không gọi permitted_scope với review giả hoặc sửa gate ấy để làm scheduler.

Mỗi hold có source basis, Issue identity, phạm vi logic (mọi thao tác hủy hoặc all-source-uses khi constraint chưa rõ), và tập phần tử/Parts hiện tại do code materialize. Trước publish, materialize lại **trên candidate Model**, xét phần tử mới, closure và union. Scope rỗng ở Model nền không xóa hold; source selector vẫn tồn tại. Không biết ảnh hưởng thì enumerate toàn graph hiện tại và giữ selector cho graph tương lai. A2 pending_revalidation cũng là hold; source/set đổi làm manifest stale.

### 7.2 Hai walkthrough admission minh họa, chưa chạy

**Nguồn đủ rõ (synthetic, không thay clinic):** R-task nêu nhân viên được tạo phiếu, đọc danh mục, lưu phiếu; criterion xác nhận dữ liệu bắt buộc, constraint ứng dụng/local database rõ. Không thiếu quyền/constraint cho bước 1–4. Bước 1 đánh từng obligation inspected/usable, Model vẫn mappings not_assessed. Bước 2 tạo action/rule/workflow đủ nguồn, mappings vẫn not_assessed. Bước 3 nhóm trách nhiệm có alternative, chưa Parts; admission không đòi output bước 4. Bước 4 tạo Parts đối chiếu; verification tasks mapping được xử lý với evidence. Model vẫn là đề xuất, local compliance chưa kiểm thực thi, không Review. Chỉ cần đủ thông tin cho nhiệm vụ từng bước, không bắt hoàn tất quality analysis bước 6.

**Constraint/quyền chưa rõ:** nguồn không cho biết ai được hủy hoặc constraint không xác định phạm vi dữ liệu cấm gửi. Bước 1 ghi hold/source selector; skeleton chưa action không có nghĩa độc lập. Bước 2 thêm cancel/read-history: hold quyền gắn cancel và phần phụ thuộc; hold constraint unknown gắn mọi source-uses gồm action mới. Bước 3 component/responsibility mới không loại hold; bước 4 Part có A1/A2 thì mở toàn action_ids và propagation lại. Có thể publish draft blocked, không tiến phần cần quyết định bằng cách gọi unknown là usable. Quyền rõ ở phần xem chỉ giúp tiếp tục nếu có căn cứ constraint không ảnh hưởng; constraint unknown toàn cục chưa cho scope độc lập. JSON 01 có hai traces admission này.

## 8. Clarification, consent, S01 update và recovery

### 8.1 State transitions đề xuất

| Tình huống | State/evidence và hành vi |
| --- | --- |
| Nhận câu trả lời | Command code-only (attempts rỗng) lưu Answer bất biến và outcome, cùng set successor nếu thay Issue; không nhận Record tùy ý từ CLI. Giữ text/respondent/recorded_by; Issue successor `answered_pending_application` nếu câu trả lời còn chờ áp dụng. `interpretation` ban đầu không sửa lại trong Answer |
| Answer chỉ nguồn đã có | Chọn `interpretation_selected: points_to_existing_source`, source refs phải resolve đúng snapshot và thật sự trả lời câu hỏi. Không gọi S01, consent_event và observation null ở application. T3 Model/Change analysis_edit + resolved Issue cùng issue_key/supersedes + current AnalysisSet + application_applied |
| Answer đổi requirements | `interpretation_selected: changes_requirements` pin full proposed input StageRef và request update spec/base. Lập diff; chờ consent đúng interpretation/hash/base, rồi mới S01 dispatch |
| Answer chưa rõ | Answer `needs_interpretation`; không tạo interpretation_selected sai enum. Hỏi câu bổ sung; Answer mới có supersedes_answer_id nếu sửa câu trả lời. Issue chưa resolved, chưa S01 dispatch/application |
| S01 validated, S02 chưa áp dụng | Lưu s01_result_observed từ checked lookup; intake đúng run/snapshot thành Cobserved archive; T3 theo A1 so Sobserved với Smodel, không chỉ result_kind. Áp dụng theo CAS. Crash thì recovery dùng lại run/event/bytes, không submit lại |
| S01 rejected/failed | Lưu observation đúng status, không source switch/resolve. Nếu cần sửa proposed input thì interpretation và consent mới; không thay hash cũ. Nhu cầu gửi lại được review riêng, không tự retry như transport |
| S01 outcome chưa rõ | Lookup đúng store + allocated run ID/receipt. Not_found/không đọc được không tự chứng minh chưa commit; giữ chưa rõ và không tạo revision mới bằng ID khác |
| Model hoặc AnalysisSet đổi lúc chờ Answer/consent | Answer vẫn nguyên; ứng dụng phải xét Issue hiện hành cùng key, base/source và impact mới. Finalize stale nếu base pair cũ; không chỉ kiểm Model |
| Hai application cùng Answer | Active claim CAS + unique applied của a3; một bên được áp dụng. Bên thua lookup application đã có, không tạo Answer clone để lách unique |

### 8.2 Trình bày và pin consent

Trước consent, người dùng xem **toàn bộ input S01 đề xuất**, diff theo field/array, unknowns và nội dung giữ nguyên, schema version, spec ID/base revision, snapshot nguồn và interpretation/explanation. Diff là trợ giúp; consent hash tính từ **bytes đầy đủ thực sự gửi** bằng codec exact, không từ chỉ phần diff. Consent record dùng respondent/text do người dùng cung cấp, interpretation EventRef và approved_input_sha256. Không có LLM-generated consent. Đổi interpretation, proposed bytes hoặc S01 base cần consent mới. Ghi quyết định consent gắn base Model/AnalysisSet trong command intent; source/base S01 nằm trong interpretation.

Có thể yêu cầu consent lại khi chỉ Model/AnalysisSet đổi: khuyến nghị trước S01 dispatch, đánh giá lại impact và trình lại base pair cho người dùng; không tái dùng consent âm thầm cho phạm vi mới. Sau S01 đã commit, không yêu cầu “consent lại để commit S01 lần nữa”; chỉ cần review phạm vi áp dụng/reanalysis trên cặp S02 mới. Nếu người dùng không đồng ý áp dụng thì giữ S01 revision đã tồn tại và S02 source cũ cùng Issue mở, không rollback lịch sử.

### 8.3 Cầu S01 và thứ tự effect

1. Claim Answer; checked current Issue trong AnalysisSet; pin cặp head, proposed bytes/request/interpretation/consent.
2. Dùng [S01 Service](../packages/s01/src/dacn_s01/service.py) `allocate_run_id()`; tạo receipt create-only bằng cơ chế [local_io](../packages/s01/src/dacn_s01/local_io.py) trước submit. S02 lưu s01_dispatch_intent cùng run ID/store key/request/input StageRef sau khi receipt đã bền vững. Không giữ transaction S02 khi ghi kho S01.
3. Gọi S01 `submit(..., run_id=ID)` đúng raw bytes/request. CLI S01 hiện **không** nhận run ID do caller cấp; không gọi CLI submit mù rồi mới biết ID. Adapter dùng API public từ wheel a6, không import source hoặc sửa S01. Nếu cần thêm public adapter surface, đưa audit trước, không chạm `_` internals để né giao thức.
4. S01 có thể validated/new_revision hoặc unchanged; kiểm envelope + `get_request` + raw source bằng checked lookup, đối chiếu hash/request đã consent. Intake archive đúng snapshot kết quả, không đọc head mới nhất thay thế.
5. T3 S02 CAS cặp base + active claim trước phân nhánh. Theo **amendment A1 đã đạt thiết kế, chưa được duyệt implementation**, archive Cobserved của run S01 mới dù snapshot trùng; application.observed_source_context_id trỏ archive đó. Nếu Sobserved bằng snapshot nguồn Model base: analysis_edit giữ đúng Cmodel; nếu khác: requirements_switch dùng Cobserved, **kể cả S01 result_kind=unchanged**. Model/Change/set/Issue/application/Run nguyên tử, Run giữ source pin của operation. Issue chỉ resolved khi cùng key/current lineage và backlinks đúng. a3 hiện từ chối nhánh cùng snapshot; không triển khai bằng orchestrator đơn thuần.

Hai kho không có transaction phân tán; S01 commit rồi S02 fail là state hợp lệ cần reconciliation. Kho đang không đọc được thì dừng, không ghi “failed” đè run đã commit. Đã có s01_dispatch_intent mà chưa có observation ⇒ tra đúng ID. Lookup absent vẫn không tự resend; chỉ operator xử lý khi có bằng chứng chưa gửi/không còn worker đang chạy và quyết định rõ, không chọn run ID mới ngầm. Giao thức này không hứa exactly-once API.

### 8.4 Source switch khác resolve và reanalysis

`application_applied` chứng minh câu trả lời được áp dụng; `requirements_switch` chứng minh đổi snapshot; reevaluate completed cần evidence **cùng model mới**. Ba trạng thái không thay nhau. Sau switch, lập inventory mới; không copy SourceRef criterion theo index từ snapshot cũ. Matching requirement ID hỗ trợ xem diff nhưng không chứng minh nghĩa giữ nguyên. Code xác định structural impact, LLM/reviewer đánh giá ảnh hưởng nghĩa và phần tái dùng; affected elements `needs_reanalysis`, tasks pending từ bước sớm nhất. Tạo successor Issue/Trace/Parts sang nguồn mới với bằng chứng; Issue resolved bằng Answer bắt buộc A2 DIRECT/CARRY, không clone/rebind trần; không trộn output cũ vào model mới chỉ vì tên giống.

Nếu race sau S01 commit: finalization cũ thành stale, giữ observation; successor application theo claim_from/parent của a3 lấy base pair mới, reuse đúng Answer/dispatch/observation, **không dispatch S01 lần hai**. Nếu Issue hiện hành đã withdrawn/resolved theo quyết định khác, giữ Answer và source result lịch sử, yêu cầu xử lý xung đột thay vì giải quyết nhầm Issue.

### 8.5 A1/A2 trước continuation

[Addendum](S02_PHASE2_CONTRACT_AMENDMENT_PROPOSAL.md) đề xuất A1 tách Cmodel/Cobserved/Cresult, kiểm run/raw hash/consent/request; A2 giữ root application tại Q2/M2, successor Q3/M3 có resolution_carry và đánh applicability. `resolution_pending_revalidation` là status mới đề nghị, giữ Answer/event evidence, chặn scope cần kết quả cũ; không tự mở lại câu hỏi. Direct identity checks a3 vẫn giữ tại root. A2-R1 đổi method thành structural_check: được ghi undetermined khi thiếu proof; chỉ applicable cần đủ điều kiện. A2-R2 thêm resolution_replacement: kết luận cũ not_applicable giữ nguyên; key mới xử lý nghĩa vụ hiện tại, old-key successor chỉ resolution_replaced sau đủ evidence/reanalysis và review quan hệ thay thế. Không ứng dụng lại Answer cũ, không bỏ key khỏi set.

| Điểm rẽ | Quy tắc thay mô tả draft.1 |
| --- | --- |
| S01 unchanged, S02 cùng snapshot | analysis_edit giữ Cmodel + Cobserved evidence riêng; cần A1 |
| S01 unchanged, S02 snapshot cũ hơn | requirements_switch đến Sobserved; không bỏ source update vì result_kind |
| S01 commit → recovery → base pair mới | Giữ observation/consent/Answer; successor claim sau stale, so snapshot lại, không dispatch S01 mới |
| Resolved Q2/M2 → M3 | Root Q2/event không đổi; Q3/AS3 current, A2 applicable hoặc pending_revalidation; không application lần hai |
| Nguồn/rule liên quan đổi | Không auto applicable; source/impact review, hold/reanalysis, giữ evidence |
| CARRY undetermined, có proof mới | Review/kiểm tra theo matrix A2-R1; tạo successor applicable nếu đủ, không thêm application |
| CARRY not_applicable, có quyết định mới | Key mới xử lý nghĩa vụ hiện tại; old-key REPLACEMENT incomplete giữ hold, complete sau proof/reanalysis/review mới được resolution_replaced |
| Sai run/hash/consent/key/lineage/root event | Reject batch, không đổi head/đóng Issue |

A1/A2 phải kiểm ở finalize và checked read/reopen, không chỉ UI/orchestrator. Hoàn tất reanalysis cần evidence/task riêng; resolution applicable không truyền approval Model/Bundle.

## 9. Điều phối T0–T3, lỗi, retry và ngân sách

### 9.1 Thứ tự bền vững

| Mốc | Thao tác đề xuất | Crash/recovery |
| --- | --- | --- |
| Trước T0 | Đọc checked heads/source; chọn scope; cấp command/run/attempt IDs; receipt create-only; kiểm quyền dữ liệu, giới hạn và ngân sách | Receipt không có command thì kiểm đúng kho; không tự chạy lại bằng ID khác |
| T0 | prepare operation, pins, config/prompt/request bytes, prepared event; reservation ngân sách gắn command | Không có dispatch intent: explicit resume có thể gửi **đúng** request đã pin sau kiểm budget/base |
| T1 | Claim quyền dispatch một lần, commit dispatch_intent + reservation active; đóng transaction rồi mới HTTP | Có intent mà không có response durable ⇒ `dispatch_unknown`; không tự gửi lại |
| T2a (G3, cần amendment riêng) | Ghi response BLOB nguyên byte trước **mọi parse JSON**, cùng typed capture event đề xuất lưu HTTP status/headers/elapsed và StageRef | Crash sau T2a: có cả bytes và metadata transport để parse local, không resend hoặc bịa status |
| T2b | Parse outer HTTP envelope local, tạo response_received metadata + StageRef tới bytes T2a; metadata không đọc được để null; parse candidate sau capture | Một response_received/command; Attempt metadata phải bằng capture, không enrich âm thầm sau đó |
| T3 | Build batch/promotion manifest; checked graph, CAS Model+AnalysisSet và claim; Artifact+BLOB/Run/Attempt/Model/Change/set/events/head nguyên tử | Mất ACK commit: lookup command bằng connection mới. Finalized trả record cũ; stale chỉ giữ evidence/outcome, không model thành công |

**G3 là gap protocol cần audit riêng**, không phải khả năng đã hoàn thiện của a3. Contract hiện gộp bytes + metadata trong response_received, còn returned model/usage thường phải parse outer JSON mới biết. Để lưu raw trước mọi parse và vẫn phục hồi đủ metadata, đề nghị bổ sung event vận hành `response_bytes_captured` với payload `{response:StageRef,http_status,safe_headers,requested_model,elapsed_ms,complete_body:boolean}`. Bytes và event phải cùng T2a; T2b response_received trỏ đúng bytes và transport metadata, chỉ bổ sung metadata đọc được từ outer JSON. Chưa thêm enum/schema/event vào draft.3 hoặc code. Không dùng log.message hay config giả để giấu metadata transport. `get_stage`/staged_blobs hiện có là nền tảng nhưng chưa thay event mới; `_command` a3 vẫn trả dispatch_unknown trước response_received, không được báo rằng a3 đã hiểu T2a. Cần review semantics lookup và one-capture constraint khi amendment được duyệt. Nếu chưa duyệt G3, chưa implement nhánh live này.

`response_received` immutable, metadata null không được enrich âm thầm sau capture; receipt HTTP khác candidate parse thành công. Outer JSON không parse được: T2b giữ model/usage/id null, raw đầy đủ, Attempt invalid_output và Run rejected/failed theo loại lỗi, tuyệt đối không publish Model. Partial body có complete_body=false chỉ là bằng chứng transport bị cắt, chưa đủ để coi response hoàn tất; giữ unknown outcome và reservation, không auto resend. Header/status chưa nhận được thì giữ failure evidence theo giao thức lỗi được audit, không bịa HTTP 200.

Không write transaction qua mạng. Có dispatch_unknown thì canonical Attempt `unknown_outcome`, response/usage null nếu chưa có capture; command state chưa rõ không là status mới của Run. Lỗi kỹ thuật và mất thông tin nghiệp vụ tách biệt. Unknown cost giữ reservation, không mặc định 0. `failed/rejected/stale/interrupted` không có result Model/AnalysisSet; `blocked` chỉ có checkpoint nếu graph hợp lệ và blockers còn hiển thị. Kết quả completed của một bước không chứng nhận toàn bộ S02 hoàn tất.

### 9.2 Retry/repair bounded — các con số chưa được duyệt

Khuyến nghị pilot nhỏ hơn tổng kế hoạch cũ: một session có tối đa **12 dispatch tổng**, **2 content repair/bước**, **2 transport retry/lời gọi logic**, **180 giây deadline/lần**, **8.000 output tokens/lần**, **24.000 input tokens/lần** và **USD 5 tổng trần**. Đây là lựa chọn cần review D4, không mặc định bật live hay quyền chi. Tổng dispatch tính cả transport/repair; không nhân thành 12×3×3. Nếu nguồn không vừa context/budget thì dừng hoặc chia scope có quyết định và giữ dependencies, không truncate nguồn.

Retry transport chỉ khi chứng minh chưa gửi bytes hoặc response lỗi tường minh được chính sách cho phép; 429/5xx vẫn lưu response và chi phí chưa chắc chắn, không suy mọi lỗi HTTP là miễn phí. Sau timeout/disconnect kể từ T1 không chứng minh được no-send ⇒ unknown, không auto-retry. Backoff đề xuất 1s/4s có jitter, Retry-After tối đa 30s trong deadline/budget; quá thì dừng. Repair chỉ schema/refs/coverage lỗi xác định được, prompt giữ nguyên nguồn và lỗi, không yêu cầu model tự điền quyền/mục tiêu. Hai vòng không tiến triển cùng lỗi ⇒ giữ issues/needs review. Refusal không repair để vượt refusal.

Vì a3 chỉ một dispatch/command, mỗi retry được phép là child command mới có parent, config pin root budget/work identity, transport_attempt tăng; repair_round tăng riêng. Cùng response recovery là resume gốc, không tạo dispatch. Budget không reset bởi command mới, source switch, consent hoặc process restart. Cấp thêm ngân sách là quyết định riêng có record bằng chứng, không sửa hạn mức cũ.

**G4 cần thiết kế/audit trước live:** a3 chưa có ledger nguyên tử để enforce tổng cap xuyên command/process. Đề xuất bảng nội bộ budget account theo session/campaign root + immutable reservation/settlement events và unique dispatch binding, cùng DB S02, kiểm reserve + dispatch claim trong một transaction. Cần DB version mới/migration copy có backup và tests; không thêm bảng vào DB1 bị kiểm exact DDL, không tự đổi file schema trong lượt này. Mọi child/recovery tra root qua DB, không tin root do CLI tự nhập; new run không tạo tài khoản mới. Hai session trong cùng pilot dùng campaign cap chung, tránh reset bằng start mới. Điều phối một process không thay được atomic guard.

Trước gửi reserve upper bound theo token ceiling và bảng giá pin (gồm cache write/context/tier). Nếu chưa xác định được upper bound token/charge thì **không gửi live**; byte count không tự coi là tokenizer. Ưu tiên một counter/provider preflight được kiểm chứng hoặc chặn với conservative bound đã review; dependency tokenizer nếu cần phải đề xuất riêng và kiểm đúng model. Usage trả về settle actual known charge; thiếu usage/cache detail giữ reservation và cost null. Không giải phóng reservation unknown chỉ vì timeout. Tổng spent + unresolved reservations + proposed maximum phải trong cap. Guard local không chứng nhận hóa đơn provider không vượt vì lỗi counter/tariff; đối soát hóa đơn thuộc pilot.

## 10. Stack, adapter và cách chạy dự kiến

### 10.1 Khuyến nghị kỹ thuật

Giữ CPython **3.13.16 có GIL**, SQLite **3.53.1**, codec exact S01 và jsonschema **4.26.0** theo baseline đã audit; không đổi locks/runtime để viết proposal. Tests sau này dùng pytest/tooling đã có. Không ORM, schema coercion hoặc dict parse qua float. Candidate và canonical checks dùng validator S02 riêng, W29, bool khác number, missing khác null; codec phát hiện duplicate keys trước mất dữ liệu và kiểm Unicode round-trip. Không dùng validator profile S01 cho model S02.

Adapter đề xuất Responses REST không streaming qua `urllib.request/ssl`, serialize request chính xác và capture bytes; không thêm SDK trong bản đầu. Trade-off: ít dependencies/retry ngầm, nhưng phải tự kiểm HTTP status/deadline/body cap/headers/usage và phân loại no-send/unknown. SDK Python là lựa chọn thay thế cần chứng minh giữ raw trước parse, số exact và vô hiệu retry ngoài ledger; **chưa chọn phiên bản SDK/chưa xác minh cấu hình SDK**. Không dùng SDK convenience parse như nguồn authoritative.

Provider/model ứng viên cần review: OpenAI `gpt-6.1-sol`, `reasoning.effort=medium`, tier Standard (`default`), text-only, tools rỗng; `store=false`, không background/conversation/previous_response_id, không truncation ngầm. Model local là phương án nếu tài liệu không được phép gửi đi, nhưng chưa chọn runtime/model hoặc đo chất lượng/phần cứng. Không tự fallback cloud/local/model khác sau lỗi. Chỉ thử dữ liệu synthetic/được cấp quyền, không dữ liệu lịch hẹn thật; R5 và quyền gửi tài liệu thiết kế phải được xem riêng, không suy consent S01 là consent gửi provider.

Đã đọc tài liệu chính thức qua **OpenAI Docs ngày 21/10/2026**:

| Nguồn trực tiếp | Xác minh và giới hạn |
| --- | --- |
| [GPT-6.1 Sol](https://developers.openai.com/api/docs/models/gpt-6.1-sol) | Công bố Responses, structured_outputs và reasoning medium; trang chỉ liệt kê snapshot `gpt-6.1-sol`, không tự bịa dated snapshot. Khả năng công bố chưa chứng minh account access/chất lượng DACN |
| [Structured Outputs](https://developers.openai.com/api/docs/guides/structured-outputs#supported-schemas) | Subset JSON Schema; root object, required fields và additionalProperties false. Schema projection candidate cần kiểm riêng; không gửi whole contract với custom formats rồi bỏ invariant cho vừa provider |
| [Pricing](https://developers.openai.com/api/docs/pricing) | Standard short-context Sol: input USD 2, output 10, cached input 0.10, cache write 30m 2.50, 12h 5 mỗi 1M tokens. Không chỉ input+output; long-context/tier/region có hệ số. Đây là giá tham khảo ngày đọc, chưa chi phí đo |
| [Responses data controls](https://developers.openai.com/api/docs/guides/your-data#v1responses) | store=false không phải cam kết zero retention; caching/data controls và quyền tổ chức cần kiểm trước pilot. Không lấy receipt local thay bảo đảm retention provider |

Chưa xác minh bằng request thật: API quyền tài khoản, payload schema từng bước, tên trường usage/cache trả về, deadline/network behavior, upper bound token counter, chất lượng tiếng Việt, latency và chi phí. Không có benchmark/model thắng được kết luận. Trước live phải pin adapter/tariff/schema, thử tương thích với synthetic có quyền và audit G3–G5; không tự áp mức giá ngày 18/10 của kế hoạch cũ mãi mãi.

### 10.2 Walkthrough CLI — không có lệnh nào được chạy ở lượt này

Các đường dẫn `/tmp/dacn-phase2-demo/...` chỉ là placeholder vùng thử riêng ngoài checkout/dataset; config và input phải được người thực hiện chuẩn bị. Input clinic dùng ví dụ hiện có, không phải dữ liệu bệnh nhân. `PY` dưới đây là interpreter của môi trường **wheel cài non-editable**, không source tree. Không có yêu cầu cài môi trường trong lượt tài liệu này.

**Đã có trong CLI a6/a3** (đọc [S01 CLI](../packages/s01/src/dacn_s01/cli.py), [S02 CLI](../packages/s02/src/dacn_s02/cli.py)):

```sh
"$PY" -m dacn_s01 --state-dir /tmp/dacn-phase2-demo/s01 init
"$PY" -m dacn_s01 --state-dir /tmp/dacn-phase2-demo/s01 submit --mode create --input /tmp/dacn-phase2-demo/clinic.json --receipt /tmp/dacn-phase2-demo/create.receipt.json
"$PY" -m dacn_s01 show-run --receipt /tmp/dacn-phase2-demo/create.receipt.json
"$PY" -m dacn_s02 --config /tmp/dacn-phase2-demo/s02.toml init
"$PY" -m dacn_s02 --config /tmp/dacn-phase2-demo/s02.toml start --store-key clinic --s01-run-id RUN_FROM_LOOKUP --expect-snapshot SNAPSHOT_FROM_LOOKUP --receipt /tmp/dacn-phase2-demo/start.receipt.json
"$PY" -m dacn_s02 --config /tmp/dacn-phase2-demo/s02.toml show-command --receipt /tmp/dacn-phase2-demo/start.receipt.json
```

Config S02 ánh xạ `clinic` tới kho S01, giữ state/output allowroots ngoài checkout theo a3. Chép IDs **từ checked lookup thực tế**, không ID minh họa. Receipt và JSON stdout tách log stderr. Các lệnh lookup không tạo run/revision. `start` chỉ intake, không bước 1–4.

**Giao diện mới đề xuất — CHƯA TỒN TẠI, chưa chạy:**

```sh
"$PY" -m dacn_s02 --config DEMO_CONFIG analyze --session SESSION --steps 1 --mode replay --capture FIXTURE --receipt STEP1_RECEIPT
"$PY" -m dacn_s02 --config DEMO_CONFIG questions --session SESSION
"$PY" -m dacn_s02 --config DEMO_CONFIG answer --issue ISSUE --text-file ANSWER_TEXT --respondent USER --receipt ANSWER_RECEIPT
"$PY" -m dacn_s02 --config DEMO_CONFIG interpret-answer --answer ANSWER --receipt INTERPRET_RECEIPT
"$PY" -m dacn_s02 --config DEMO_CONFIG show-proposed-input --interpretation EVENT_REF
"$PY" -m dacn_s02 --config DEMO_CONFIG consent --interpretation EVENT_REF --input-sha256 DISPLAYED_HASH --respondent USER --text-file CONSENT_TEXT --receipt CONSENT_RECEIPT
"$PY" -m dacn_s02 --config DEMO_CONFIG apply-answer --answer ANSWER --consent CONSENT_REF --receipt APPLY_RECEIPT
"$PY" -m dacn_s02 --config DEMO_CONFIG recover --receipt APPLY_RECEIPT
"$PY" -m dacn_s02 --config DEMO_CONFIG analyze --session SESSION --steps 2,3,4 --mode replay --capture FIXTURE --receipt NEXT_RECEIPT
```

`consent` chỉ ở nhánh changes_requirements; existing-source không giả consent; ambiguous Answer quay lại questions. `analyze` tự pin head pair và xuất manifest scope/holds trước chạy, không nhận arbitrary canonical records. Live tương lai cần lựa chọn tường minh mode/provider/model, data grant và budget account, không default live. Recover S01-committed/S02-not-applied chỉ lookup allocated run rồi apply theo claim/CAS; recover dispatch_unknown không resend. Lệnh read-only xuất status/IDs/blockers, log riêng; đề xuất giữ codes 0 kết thúc lệnh, 2 rejected, 3 failure/unknown, 4 not_found, 64 usage và thêm code 5 cho blocked cần review CLI. Không coi exit 0 là business accepted. Chỉ chốt flags/exit schema sau audit D5.

## 11. Ma trận kế thừa và các gap cần audit riêng

| Nhu cầu | Code hiện có | Phần còn thiếu | Thay đổi dự kiến | Kiểm thử | Bằng chứng |
| --- | --- | --- | --- | --- | --- |
| Checked S01 intake | s01_adapter.intake/verify_archive; Service.start | Update có consent/receipt | adapter clarification qua public S01 API | S01 commit rồi kill S02; unchanged; sai store/hash | receipts, raw source/hash, observation, snapshot IDs |
| Parse/refs | codec_boundary; validation.shape/validate_record | candidate schema/handles/prompt projection | candidates + builders từng bước | duplicate/Decimal/Unicode/foreign handles | bytes fixture, expected error/ref inventory |
| Bootstrap/checkpoints | prepare/finalize, full Model/set invariant | Skeleton/pending source holds | orchestrator bootstrap + inventory tasks | initial atomic cycle; crash, incomplete mapping | batch manifest/head trước sau |
| LLM lifecycle | events/staged_blobs/promotions | adapter, capture trước parse, resume | transport + scheduler T0–T3 | network fake socket, unknown/capture/replay | event timeline, call counter, raw hashes |
| Budget/retry | one dispatch per command | root ledger, atomic cap, counter/tariff | G4 internal persistence design + migration | hai process reserve, restarts/new-run | ledger, cap oracle độc lập |
| Steps 1–4 | schemas/entities/Issue/Mapping | prompts, candidates, linking/coverage | bốn pure handlers | semantic fixtures + golden invariants | inventory omissions/parts, source diff |
| Scope tiến tiếp | closure/reverse_impact/permitted_scope | admission trước review | G2 scheduler, không nới review gate | P12 nhiều actions, unassessed constraint | fixed-point trace, holds/exclusions |
| Answer/application | events.py; application_heads; unique applied | UX interpretation/consent và S01 orchestration | clarification service/CLI | stale set, same Answer race, key mismatch | exact EventRefs, applied unique, head pair |
| Audit/CLI | init/start/show; tools runners/collector | analyze/questions/answer/recover & evidence | CLI mỏng, versioned plan/config blobs | subprocess ngoài source, stderr/stdout | argv/exit/logs/wheel payload hashes |

Các liên kết code gốc ở mục 1; chi tiết kiểm thử ở mục 12. Những đề xuất sau **không sửa draft.3 tại chỗ**:

| ID | Gap/quyết định cần review | Khuyến nghị, trade-off và phần bị chặn |
| --- | --- | --- |
| G1 | Bootstrap/source holds | Audit draft.1 đã probe skeleton tối thiểu được a3 chấp nhận; chưa chứng minh full inventory/scheduler. Còn review profile mục 3/7.1, không thêm actor/obligation |
| G2 | Gate review không dùng làm admission analysis | Thiết kế admission đã được audit làm rõ; nội dung mục 7 giữ nguyên. Chưa nghiệm thu scheduler/thuật toán scope implementation |
| G3 | Raw trước mọi parse nhưng capture hiện tại cần metadata từ outer JSON; mock/replay profile chưa cụ thể | Đề nghị amendment vận hành response_bytes_captured + transport metadata nguyên tử theo mục 9.1, rồi response_received. Không sửa draft.3 trong lượt này. Audit amendment/schema/lookup state trước nhánh capture; replay ghi origin, không nói provider đã nhận |
| G4 | Ngân sách/dispatch ownership xuyên command chưa có; DB1 exact DDL | Ledger và atomic reservations/dispatch claim, DB version/migration riêng, cap gốc xuyên session pilot. Bắt buộc trước live; không dùng log text làm accounting authority |
| G5 | Usage draft.3 chỉ input/cached/output/cost/price_source, chưa diễn tả mọi cache-write bucket | Giữ nguyên Usage, raw HTTP lưu đủ, chi tiết hóa đơn/tariff trong config/evidence blob; unknown cost null và giữ reservation. Nếu cần bucket có cấu trúc public thì audit contract amendment. Không tính thiếu phí để đạt cap |
| G6 | Consent/stale orchestration + hai incompatibilities P1 | Cần A1 source/archive separation và A2 carry, không chỉ thêm orchestrator; exact full bytes/base/hash, no resend |
| A1 / S02-P2-01 | Semantics đã đóng ở mức thiết kế, a3 chưa hỗ trợ | Addendum mục 2 giữ nguyên; schema/profile/checker implementation theo gói 2A mới còn cần review |
| A2 / S02-P2-02 | A2-R1/R2 đóng ở mức thiết kế theo audit draft.3 | Giữ nguyên semantics; gói schema/profile/version, compatibility/migration 2A còn cần review trước persistence/carry |

D1 cần người dùng giao implementation sau audit proposal **và A1/A2/profile/migration phần liên quan**; D2 chốt G1/G2/candidate profile; D3 chốt provider/model/adapter/data permission; D4 chốt ledger/DB migration/token counter/budget/limits; D5 chốt UX/CLI/consent/recovery; D6 chốt semantic dataset/rubric/reviewer/held-out policy. Có thể duyệt offline batches trước live, nhưng phải ghi phạm vi riêng, không suy cho phép cả Đợt 2 từ một batch.

## 12. Kế hoạch kiểm thử phần mềm (chưa viết/chạy)

Fixture nhỏ synthetic và kho tạm riêng; không dùng dataset vận hành hoặc sửa audit cũ. Oracle là source bytes, inventory được lập độc lập, expected event/state transitions và queries từ connection mới, không chỉ gọi lại hàm đang test để tính kỳ vọng.

| Nhóm | Dữ liệu/cách kiểm | Kết quả mong đợi và evidence |
| --- | --- | --- |
| Unit parser/candidate | duplicate keys trước dict, huge int/Decimal, bool/number, missing/null, W29/ngoài W, surrogate Unicode biên; prompt injection dưới dạng dữ liệu nguồn | Giữ nguyên raw; reject có kiểm soát, không trim/coerce, không cho source text điều khiển consent/DB. Cả backend C/Python có instrumentation |
| Unit từng bước | case có thông tin sẵn vs thiếu; xem≠hủy; actor mới; workflow branch; alternatives; compound requirement/criterion | Không thêm quyền/priority/actor supplied; source omission chỉ rõ; inventory/handle errors đúng; multiple valid partitions không fail theo tên |
| Contract canonical | batches Model/Change/set/Issue/Answer/Event, duplicate/foreign refs, old issues omitted, resolved bằng prepared, sai issue_key/current set, attempt/config mismatch | Giữ regressions S02-01–05; full graph kiểm fail, head không đổi, raw evidence còn; success không auto Review/Handoff |
| Scope | all năm kiểu unassessed/unknown support/pending reanalysis/open issue/stale set; P1/P12(A1,A2) blocked A2; union chỉ lộ blocker khi ghép | Không bỏ constraint/criteria rỗng, mở toàn actions của Part đến fixed point, không kéo tất cả chỉ vì chung component; có membership/reason trace |
| A2-R1 method × assessment | Cùng snapshot đủ/thiếu proof; khác snapshot chưa/có human review | Code structural_check ghi undetermined hợp lệ; applicable thiếu proof và human review giả reject; JSON 06 chỉ oracle tĩnh |
| A2-R2 replacement lifecycle | Old not_applicable → key mới → Answer_new/S01 nếu cần → app mới → incomplete → review/complete; source-only variant | Old evidence/count không đổi; current cả hai keys; complete cần full coverage/task evidence; sai lineage/key/current target/prose-only/stale/recovery không release/app lần hai. JSON 07 dự kiến, chưa chạy |
| A1 application | Same snapshot/archive run mới; unchanged nhưng S02 cũ; recovery/race M/AS; sai raw/request/hash/consent/run/snapshot | Positive commit thật đúng Context/Change, applied=1; negative rollback/head giữ. Ví dụ 05 là oracle dự kiến |
| A2 carry | M2→M3, independent edit, source đổi, sai key/lineage/root, thiếu impact proof, bỏ current Issue | Applicable hoặc pending đúng, history/root không đổi, không app thứ hai; reopen kiểm chain; negatives reject. Ví dụ 06 chưa chạy |
| Admission G2 | Nguồn rõ đi 1→4 không Parts trước bước 4; unknown constraint/quyền giữ hold khi graph lớn | Per-step manifest khác Mapping.assessment; checkpoint blocked không accepted; không vòng phụ thuộc |
| Checkpoints/versions | bootstrap rồi 1→2→3→4; đóng/mở DB từng lượt; source reorder/criterion sửa; duplicate command/IDs/clock lùi | Full inventory, origin/provenance giữ; revision/set links đúng, không tái dùng criterion index; lookup không đổi timestamp |
| Replay/capture | mock byte fixtures hợp lệ/refusal/incomplete/non-JSON/HTTP error/partial body, sentinel provider không cho gọi | T2a raw durable trước parse; resume capture không tăng call counter; mock/replay không giả chi phí/model thực; candidate fail không model success |
| Retry/budget | presend error vs timeout sau dispatch, repair lỗi lặp, child command/new run/restart/source switch | Không resend unknown, tổng dispatch/repair không reset; reservation unknown không release; không đủ counter/rate thì không live |
| CAS và claim thực | Hai process, hai connection cùng DB, Event/barrier/IPC có deadline, không dùng sleep làm bằng chứng | Hai model publishers chỉ một; set đổi cũng stale; log không stale; cùng Answer chỉ một applied; hai budget reserves không vượt cap. Ghi timeline PID/command/head/ledger cuối |
| Crash/recovery thực | Kill process sau T0/T1/T2a/T2b, trước/sau T3, S01 trước/sau commit, trước observation và trước application | Mở connection mới kiểm event/bytes/heads; không resend captured/unknown; S01 không tạo revision dư; matched run/receipt đúng |
| Storage fault | Inject lỗi từng insert/commit; actual SQLite lock; receipt publish fail; unknown commit ACK | Atomic rollback hoặc checked reconciliation, không overwrite lịch sử; unknown khác conflict. Fault injection, lock và kill báo riêng |
| End-to-end CLI | Wheel sạch non-editable, cwd ngoài source; analyze/replay/questions/answer/consent/recover; sai config/receipt/hash/store | stdout JSON/stderr logs, IDs và status đúng, no arbitrary record import, no overwrite, guards checkout/dataset giữ |

Giữ toàn suite S01/S02 hiện có và audit regressions, không skip/nới assertions để đạt. Dùng workspace runner với process riêng/package/backend; không import production source vào sys.path. S02 phase2 expected counts chưa biết. Trước bàn giao chạy package verification source–wheel–installed, dependency check, protected hash diff, concurrent timelines/fault evidence. Không lấy số tests thay invariants. Các fault synthetic/kill không chứng minh mất điện, disk-full, filesystem/network production hoặc exactly-once provider.

## 13. Kế hoạch đánh giá ngữ nghĩa (chưa có kết quả)

Chưa có corpus development/held-out được cấp quyền, người chấm được phân công hay ngưỡng nghiệm thu. Clinic trong docs đã dùng thiết kế nhiều lần nên **chỉ development/minh họa**, không held-out độc lập. Proposed synthetic fixtures kiểm phần mềm không phải dữ liệu nghiệp vụ thực hoặc bằng chứng LLM giỏi.

Đề xuất đầu tiên để review: 6 case development và 6 case held-out, tách theo **dự án/nguồn nghiệp vụ** trước tuning, không split theo từng FR của cùng dự án; variants/câu trả lời của cùng case cùng split. Mỗi nhóm có mơ hồ quyền, actor mới, branches/exceptions, compound obligations, NFR/constraint toàn hệ thống và partial clarification. Danh sách case/hash/version/provenance, quyền dùng và ngày freeze được lưu trước pilot. Nếu không đủ corpus thì ghi thiếu và chưa kết luận tổng quát. Mức số case này thay đề xuất tổng thể cho pilot bước 1–4, chưa được duyệt.

Hai người review độc lập: reviewer kỹ thuật và người hiểu nghiệp vụ (người dùng chỉ định); agent audit xem phương pháp/evidence, không tự được tính là xác nhận nghiệp vụ. Chấm nguồn ẩn tên model khi có thể; ghi disagreement và lý do adjudication, không chỉ lấy trung bình. LLM tự chấm chỉ là hỗ trợ tìm vấn đề, không oracle duy nhất.

| Trục rubric đề xuất | Cách xem bằng chứng |
| --- | --- |
| Trung thực với nguồn | Mỗi khẳng định về quyền/rule/actor/condition có source/Answer hoặc nhãn inferred/unknown; đếm unsupported claims và độ nghiêm trọng |
| Làm rõ đúng vấn đề | Không hỏi lại thông tin đã có; câu hỏi giải quyết quyết định thực; scope blocker và phần độc lập có căn cứ |
| Actions/workflows/data/rules | Đủ hành vi/nhánh/ngoại lệ liên quan; read/write/rules có rationale; không suy quyền từ hành vi khác |
| Nhóm trách nhiệm | Cohesion, ranh giới/quy tắc phải giữ, alternatives/trade-offs; chấp nhận nhiều partition hợp lý, không so tên/số components |
| Coverage nghĩa vụ | Reviewer đối chiếu từng FR/NFR/constraint/criterion với Parts; phân biệt link có thật và phần nghĩa vụ thực sự được thể hiện |
| Sửa sau Answer/source change | Không mất unknown/issues, không tái dùng evidence stale, phân biệt resolve/switch/reanalysis |

Thang đề xuất 0–3 cho từng trục kèm lý do cụ thể, cộng danh sách critical errors (ví dụ tự cấp quyền, biến giả định thành xác nhận). Hiệu chỉnh rubric/ngưỡng bằng development và chấm thử chung trước khi freeze; chỉ người dùng/auditor chốt ngưỡng đạt. Không đặt con số pass tùy ý rồi gọi kết quả nghiệm thu. Báo raw counts, lỗi nghiêm trọng, disagreement và phân bố từng trục, không giấu lỗi quyền bằng điểm tổng.

Chỉ sau cấp quyền pilot mới chạy model ứng viên; đề xuất 2 repetitions/case để quan sát biến thiên, cùng prompt/config/budget, không tuyên bố seed cho deterministic. Nếu thử model đối chứng phải chốt model/chi phí và phạm vi trên development; không tự chạy Astra hoặc thêm model. Held-out chỉ dùng sau freeze prompts/model/limits/rubric; nếu xem để sửa thì công khai đã dùng và retire khỏi held-out. Đánh giá ablation đầy đủ operation–data/dependency/characteristics vẫn là kế hoạch sau, chưa lấy flow giản lược thay production chín bước.

## 14. Các batch implementation dự kiến và bàn giao audit

Tất cả batch dưới đây **chưa được giao implementation**. Cây file là dự kiến trong `packages/s02/`; không tạo chúng ở lượt này. Không thêm package common hoặc đổi S01 a6.

| Batch / dependencies | Phạm vi file dự kiến | Điều kiện hoàn thành và bằng chứng audit |
| --- | --- | --- |
| 2A — D1 + G1/G2 + **A2 đã đạt thiết kế; schema profile/migration** còn cần audit/duyệt trước builder carry | candidates/analysis_steps/orchestrator, typed Issue/validators/resolvers theo A2; tests dự kiến | Pure handlers có thể tách sub-scope không lưu carry nếu người dùng giao riêng, nhưng không gọi 2A đủ/ready trước A2. Bootstrap, admission không vòng, M2→M3 carry/pending, A2-R1 matrix + A2-R2 replacement lifecycle, negative identity/source proof; offline synthetic |
| 2B — sau nền 2A; **G3/G4/G5 và migration design riêng** được duyệt | transport/replay/capture/budget nếu được giao sau này | Tính A1/A2 profile vào migration order; không gộp migrations ngầm. Mock không chứng minh live; T0–T3/ledger/capture còn chờ audit, không triển khai lượt này |
| 2C — sau 2A với A2; **A1 + G6 + compatibility/version/migration được audit/duyệt** | clarification, S01 adapter, application validators/schema/profile, CLI/receipt | A2-R1/R2 đã đạt thiết kế; profile/checker/migration và quyền code phần phụ thuộc vẫn cần chốt; đủ pending→reuse và not_applicable→replacement, giữ application count từng Answer. Same-snapshot và khác-snapshot/unchanged phải hoàn thành thật; consent mismatch fail; recovery no resend, same Answer race, carry sau apply. Không chỉ thêm lời gọi vào a3 |
| 2D — sau 2A/2B/2C được audit trong phạm vi giao | E2E CLI/replay/evidence, không renderer | Full flow A1/A2/G2, regressions/reopen/CAS, installed wheel/hashes. G3/G4 chưa duyệt chỉ cho sub-scope offline riêng, không coi 2D đầy đủ |
| 2E — sau 2D + D3/D4/D6 + G3/G4/G5 và quyền live riêng | Adapter/config/corpus/rubric khi được giao | A1/A2 audit không cấp quyền model/dữ liệu/chi phí. Chưa ready code/live; chốt giới hạn/compatibility trước pilot |

Mỗi batch có report mới dự kiến dưới `reports/s02-phase2/<batch-version>/`: scope/changes/reasons; argv/cwd/exit/log thực; runtime/SQLite/deps; wheel/payload/source hashes; protected baseline/final diff; raw/candidate/canonical pins; concurrency/fault/recovery; hạn chế và câu hỏi audit. Không ghi reports lịch sử hoặc dataset. Phân biệt planned/mock/replay/live, tests phần mềm/semantic evaluation và nhân sự xác nhận. Trước bước 5–9 cần quyết định phạm vi tiếp theo, không mở rộng tự động.

Tiêu chí hoàn thành phần mềm Đợt 2 đề xuất: bốn bước có checkpoints nguồn đúng; unknown/holds không mất; clarification/application phục hồi đúng; CAS/bytes/budget invariants có bằng chứng; CLI/tài liệu và wheel cài sạch tái lập được; audit không còn lỗi chặn trong phạm vi đã giao. Đây không tự nghiệm thu thiết kế nghiệp vụ, LLM, renderer hoặc toàn S02. Live chưa được cấp quyền thì bàn giao offline và ghi **live/semantic evaluation chưa thực hiện**, không giả kết quả để đóng toàn bộ Đợt 2.

## 15. Ví dụ minh họa và kiểm tra tĩnh lượt tài liệu

Sáu file minh họa hiện hành có wrapper `illustration`, `contract_version`, `proposal_version` và bindings file/JSON Pointer. Đây là **kịch bản và projections minh họa chưa thực thi**, không phải export hoàn chỉnh có thể import vào repository. Các symbol model/command/event là tên dự kiến trong scenario, không IDs đã lookup. Field projection/candidate/proposed state không được lẫn với schema canonical Record. Chỗ trích canonical fields ghi rõ loại; kết quả “expected” chỉ là kỳ vọng thiết kế.

1. [01-clinic-steps-1-4.json](examples/s02-phase2/01-clinic-steps-1-4.json): nguồn clinic hiện có, inventory 15 obligations và progression; quyền/unknowns còn mở, không chứng minh đáp ứng p95.
2. [02-cancel-permission-and-new-actor.json](examples/s02-phase2/02-cancel-permission-and-new-actor.json): không suy quyền hủy từ R4; actor mới là đề xuất cần làm rõ; hai nhánh độc lập.
3. [03-consent-and-s01-recovery.json](examples/s02-phase2/03-consent-and-s01-recovery.json): Answer/consent **giả định**, full proposed S01 input, exact UTF-8 payload/hash, diff/base và mất phản hồi S02 sau S01 commit; không gửi lại S01.
4. [04-stale-and-dispatch-unknown.json](examples/s02-phase2/04-stale-and-dispatch-unknown.json): hai lịch khác nhau: đã capture nhưng stale; dispatch chưa rõ không capture. Không trộn unknown cost thành zero hoặc stale thành successful model.

5. [05-unchanged-application.json](examples/s02-phase2/05-unchanged-application.json): A1 cùng/khác snapshot, archive, recovery/stale/negatives; fields mới chưa hợp a3.
6. [06-resolved-issue-carry-forward.json](examples/s02-phase2/06-resolved-issue-carry-forward.json): A2 root application, carry lineage/proof, pending revalidation và race/recovery negatives.

[STATIC_CHECKS.json](examples/s02-phase2/STATIC_CHECKS.json) giữ nguyên bằng chứng **draft.1**, không dùng hashes ấy để khẳng định files hiện hành vẫn như cũ. [STATIC_CHECKS_DRAFT2.json](examples/s02-phase2/STATIC_CHECKS_DRAFT2.json) giữ kết quả lịch sử draft.2: JSON strict/duplicate keys, bindings/JSON Pointers, payload byte length/hash/consent, local Markdown links, baseline hashes và phạm vi loại trừ. Không import package để validate Model, không chạy application tests/LLM/renderer. Vì examples là projections, việc đọc JSON và resolve refs **không phải** chứng nhận đáp ứng schema/invariants của full canonical graph. Quyền implement và những gap mục 11 còn chờ review.

### Bổ sung audit draft.3 — chỉ A2-R1/R2

Ví dụ [07-resolution-replacement.json](examples/s02-phase2/07-resolution-replacement.json) thể hiện đường ra khỏi pending sau quyết định mới, cùng các ca âm/race/recovery dự kiến. [STATIC_CHECKS_DRAFT3.json](examples/s02-phase2/STATIC_CHECKS_DRAFT3.json) là bằng chứng tĩnh mới; hai manifests draft.1/draft.2 và báo cáo phản hồi draft.2 giữ nguyên. A1 đã đạt thiết kế không có nghĩa a3 đã hỗ trợ; G3/G4 và quyền implementation vẫn cần quyết định riêng.

### Trạng thái sau audit draft.3 và gate kỹ thuật 2A

A1/A2-R1/R2 đã đạt ở mức thiết kế, không sửa lại các semantics đó. [Đề xuất kỹ thuật 2A](S02_PHASE2_2A_SCHEMA_MIGRATION_PROPOSAL.md) có version riêng `s02-2a-storage-plan/0.1.0-draft.1`: L1/E1 profile, DB2/copy migration, activation/receipt và tests dự kiến. Phương án E1 gộp low-level checks A1+A2 trong 2A là lựa chọn cần duyệt về batch; không đưa orchestration 2C hoặc G3/G4 vào scope ngầm. Chưa có schema/DB/package version mới được phát hành.
