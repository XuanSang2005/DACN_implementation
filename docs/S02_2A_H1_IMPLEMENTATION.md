# S02 2A-H1 — handlers 1–4 offline/synthetic

`dacn-s02 0.5.0a2`: **đã nghiệm thu kỹ thuật H1 local/synthetic, fresh E1/full scope**, H1-01/02 đóng theo [audit 25/10/2026](acceptance/s02-2a-h1-0.5.0a2-2026-10-25/AUDIT_REPORT.md) và [biên bản](acceptance/s02-2a-h1-0.5.0a2-2026-10-25/S02_2A_H1_ACCEPTANCE.json). [Proposal draft.2](S02_2A_STEPS_1_4_EXECUTION_DESIGN_PROPOSAL.md) và [bàn giao H1](../reports/s02-phase2/2a-h1-fixes-0.5.0a2-2026-10-25/START_HERE.md) giữ trạng thái lịch sử. Không nghiệm thu nghiệp vụ/LLM/renderer/toàn S02. [H2 draft.2](S02_2A_H2_PARTIAL_SCOPE_DESIGN_PROPOSAL.md) đã [đạt audit thiết kế](acceptance/s02-2a-h2-design-draft2-2026-10-25/README.md), D01/D02 đóng design-only; chưa code H2.

H1 nhận S01 a6 test store qua checked lookup của `start`, pin snapshot đã chọn, bootstrap rồi chạy một lượt bốn mock responses qua handlers thật. Đầu ra là draft Model, đầy đủ mapping requirement/criterion, Issues và checkpoints có raw/config/plan. Không phải kết quả LLM hoặc xác nhận nghiệp vụ. Baseline nghiệm thu P3 vẫn là `0.4.0a3`; H1 không mở H2/H3/2B/2C, renderer hoặc live.

Bản `0.5.0a2` sửa riêng S02-2A-H1-01/02; auditor đã đóng cả hai. Bộ đếm tính từng occurrence trong `finding_handles`, `questions`, `finding_handle`, SourceRef và typed refs; không tính handle khai báo, không đếm đôi SourceRef. Mỗi unassigned-action gap có Issue analysis_omission giữ hold riêng, truy vết action và current finding; không mượn miễn trừ pending-mapping, không mở partial continuation.

Auditor chạy mới full S02 **769 pass/backend**, S01 **986 pass/backend**, H1 subset 103 và V4 **10 pass/backend**. Đây là số audit độc lập, không phải tests của lượt tài liệu. V3 cũ vẫn 9 pass/1 logger tuple failure; [đính chính của auditor](acceptance/s02-2a-h1-0.5.0a2-2026-10-25/AUDIT_ERRATUM_A1.md) và V4 sửa logger riêng, assertions không đổi. Timeout a1 không tái hiện ở full audit a2; root cause timing chưa chứng minh. Giữ mọi failure/evidence cũ.

Handler pin tăng thành `s02-2a-h1/0.5.0a2`; contract/candidate/config/plan/limits và canonical profile IDs không đổi. Finalized a1 vẫn đọc outcome lịch sử, không reinterpret/repair; work a1 chưa finalized bị từ chối execution như version không hỗ trợ, không chạy lại hoặc thay plan bằng code mới. Caller muốn chạy candidate mới phải dùng luồng explicit mới trong phạm vi H1.

## Chạy luồng đầu tiên

Dùng wheel non-editable trong venv mới; cwd, state và receipts ngoài checkout/dataset, S01 và S02 ở hai thư mục riêng. Cấu hình giữ nguyên schema hiện hành:

```toml
state_dir = "s02"
[s01_stores]
synthetic = "s01/s01.sqlite3"
```

```sh
dacn-s02 --config local.toml init
dacn-s02 --config local.toml start --store-key synthetic \
  --s01-run-id <S01-run> --expect-snapshot <snapshot> --receipt intake.json
dacn-s02 --config local.toml bootstrap --from-receipt intake.json --receipt bootstrap.json
dacn-s02 --config local.toml analyze-step --from-receipt bootstrap.json \
  --step 1 --mock-response step1.json --expect-sha256 <sha256> --receipt step1.receipt.json
# Lặp analyze-step với step=2,3,4, from-receipt là checkpoint liền trước.
dacn-s02 --config local.toml resume --receipt step4.receipt.json
dacn-s02 --config local.toml progress --receipt step4.receipt.json
```

`resume` dùng raw/plan đã lưu, không cần file mock gốc. `progress` đọc lịch sử và phân biệt `result_pair`, `current_head`, `is_current`; không chạy handler. Output có Model, mappings, Issues/questions, holds, completed/next steps và refs/hashes. `completed` chỉ nói công việc code hoàn tất; `semantic_status=synthetic_draft_not_reviewed`. Lấy AnalysisSet bằng `show-record --id <result_pair[1]>`.

Mỗi lệnh tạo mới yêu cầu receipt chưa tồn tại. Nếu process chết sau receipt nhưng trước T0, checked absence cho `not_prepared/5`. Caller khai báo lại intent explicit trên chính receipt đó:

```sh
dacn-s02 --config local.toml prepare-work --receipt step1.receipt.json \
  --from-receipt bootstrap.json --step 1 --mock-response step1.json --expect-sha256 <sha256>
dacn-s02 --config local.toml resume --receipt step1.receipt.json
# Bootstrap dùng --step bootstrap và không có mock/hash flags.
```

`prepare-work` chỉ T0: `prepared/0`, chưa công bố Model. Receipt-only chưa pin input/parent/step; T0 commit đầu tiên xác lập intent. Cùng intent trả identity đã có, khác intent rejected/2, không overwrite receipt/raw. DB không đọc được trả unknown/3; không coi đó là absence để tạo lại công việc. `start` chưa finalized không được tiếp tục bằng H1.

| Điều kiện lệnh H1 | Exit |
| --- | --- |
| Completed/progress đọc được hoặc prepared | 0 |
| Rejected/blocked/stale/conflict, receipt sai binding | 2 |
| Failed, version không hỗ trợ, lookup/commit outcome unknown | 3 |
| File/receipt không tồn tại | 4 |
| Receipt hợp lệ, checked lookup xác nhận chưa có operation | 5 |
| Sai flags/cú pháp | 64 |

## Candidate và admission

Projection riêng có version `s02-2a-candidate/0.1.0-draft.1`; schema được dựng detached từ E1 trong `h1_candidates.py`, không đăng ký profile mới. Object đóng/required, typed handles, không canonical ID. Xem contract từng bước ở [proposal §3](S02_2A_STEPS_1_4_EXECUTION_DESIGN_PROPOSAL.md#3-contract-candidate-đề-nghị) và schema thực thi `h1_candidates.schema(step)`.

- Bước 1: findings/questions/inspection; không nhận Answer, consent hoặc thay snapshot.
- Bước 2: actors/actions/workflows/data/rules; giữ actors supplied và nguồn. Không suy quyền/actor từ tên. Unknown initiator giữ `needs_clarification` và Issue `analysis_omission`: đọc nguồn trước khi hỏi nghiệp vụ.
- Bước 3: components/responsibilities/unassigned actions; không sinh interface/dependency/công nghệ.
- Bước 4: đúng một row cho mỗi requirement và từng criterion. Part đề xuất có refs đúng kiểu; system Part không action. Null coverage/gap và nghĩa vụ chưa thể hiện giữ Issue/hold, không tuyên bố satisfied.

Alias supplied actor là `supplied-actor.<index>` trong snapshot cố định. Alias công bố thông thường `stepN.<handle>`; nếu vượt 128 ký tự dùng `stepN-long.<sha256(handle ASCII)>`, namespace riêng và kiểm trùng. CLI trả `next_aliases`; candidate dùng đúng alias có kiểu đó, không nối theo tên.

H1 chỉ fresh E1 session, full scope, một lượt 1→4. Hold còn liên quan bước kế thì dừng blocked sau checkpoint; không chạy phần độc lập theo H2. Bootstrap task chờ mapping là task kỹ thuật ghim key/predicate do code tạo. Chỉ code kết thúc task này khi mọi row có Parts/assessment proposed; không có nghĩa đã đáp ứng nghĩa vụ nghiệp vụ. Không miễn gate chỉ dựa vào kind verification. Current Issues gồm cả key resolved; Model đổi thì tạo successors/current scopes, không sửa lịch sử.

## Prepare, seal và phục hồi

`h1_store.WorkStore` dùng transaction/graph check/finalize/CAS hiện có, không đổi repository/DDL/schema/registry. Prepare kiểm absent/existing và insert/so toàn intent trong cùng checked `BEGIN IMMEDIATE`. Primary config duy nhất và raw ở T0 trước parse; reserved Run/started_at được pin. Marker `s02_2a_work_config`, config version draft.1; handler version `s02-2a-h1/0.5.0a2`.

Seal kiểm chưa finalized trong transaction: 0 plan thì lưu một bản; 1 plan hợp lệ thì dùng nguyên allocations/bytes; nhiều plan/version/bindings/hash sai thì failed, không repair hoặc chọn theo timestamp. Marker `s02_2a_work_plan`, plan version draft.1. Plan append sau T0; không nằm trong prepared config pins và không nhúng metadata/hash Artifact của chính nó. T3 promote raw/config/plan, Run và batch cùng CAS cặp Model/AS. Stale chỉ lưu artifacts/Run, không công bố domain IDs dự kiến. Outcome sau finalize lấy từ Run/event, không từ plan/log mới hơn.

Test cache spill phát hiện SQLite read-only không tự rollback được hot journal sau kill trước seal commit. `h1_recovery.py` thực hiện riêng cho resume/prepare-work H1: kiểm receipt và store identity, exact DB2/registry/fresh active, journal magic, DB/journal là regular unaliased files, từ chối migration reservation; sau đó để SQLite rollback bằng lock chuẩn và kiểm lại toàn graph. Không có SQL sửa row/init/migration/activation. View immutable chỉ đọc identity/registry/activation, không dùng Records/head/eligibility từ view ấy. Progress và DB1 checked readers giữ read-only. Hỗ trợ filesystem local ổn định/caller hợp tác; chưa chứng minh chống thay namespace ác ý đồng thời hoặc power loss thật.

## Limits đã pin cho H1

`s02-2a-local-limits/0.1.0-draft.1`, pin resolved values/hash ở config/plan; không có flags nới/reset khi resume. Đây là trần local synthetic, không benchmark hay giới hạn mới của validator lịch sử.

| Loại | Trần |
| --- | --- |
| Raw / primary config / plan | 1 / 2 / 16 MiB encoded bytes |
| JSON depth / values / decoded string | 64 / 100.000 / 64 KiB UTF-8 |
| Obligations / total Model entities | 1.000 / 2.000 |
| Total workflow nodes / edges / Parts | 2.000 / 4.000 / 4.000 |
| Findings/candidate / current Issues kể cả resolved | 500 / 2.000 |
| Ref occurrences candidate/result Model+current Issues | 50.000 |
| Compute trước seal / candidate / auto-repair | 30 giây cooperative / 1 / 0 |

Raw/hash/inventory quá trần trước T0 không prepare/raw bị cắt. Vi phạm sau T0 giữ raw/config, seal rejection nhỏ và finalize rejected nếu persistence khả dụng. Deadline không gồm file/SQLite waits và không là hard timeout cho syscall/hàm nguyên khối. Plan thành công đã seal không bị thay vì caller khác hết deadline. Các limits không áp vào L1/E1 validators chung.

## Kiểm và tái lập

[START_HERE](../reports/s02-phase2/2a-h1-fixes-0.5.0a2-2026-10-25/START_HERE.md) trỏ JUnit, instrumentation, mốc CLI mẫu, crash/race/lost-ACK và source–wheel–installed. Đầu ra mới luôn dùng thư mục mới ngoài checkout. Production không import test helpers; driver/test fixtures nằm riêng, mock không phải dữ liệu đánh giá độc lập hoặc phân tích nghiệp vụ thật.
