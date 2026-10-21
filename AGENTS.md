# Hướng dẫn làm việc — DACN implementation

## Phạm vi và căn cứ

- Implement và đánh giá S01–S02 trước khi tiếp tục chốt S03. Không mở rộng phạm vi khi chưa có quyết định của người dùng.
- S01 bản `0.1.0a6` đã có nghiệm thu kỹ thuật trong phạm vi CLI local. S02 `0.1.0a3` đã được **nghiệm thu kỹ thuật Đợt 1 — nền tảng và CLI local** theo [biên bản ngày 21/10/2026](/Users/macbookpro/.codex/.chatgpt-projects/g-p-68c38c8799f48191a101e19a975ca4f9/outputs/audits/s02-phase1-0.1.0a3-2026-10-21/S02_PHASE1_ACCEPTANCE.json). Công việc hiện tại chỉ là **cập nhật hướng dẫn và đề xuất S02 Đợt 2 — bước 1–4; chưa được duyệt implementation**. Chưa nghiệm thu toàn bộ S02, chất lượng phân tích nghiệp vụ, LLM hoặc renderer. Mỗi đợt code cần phạm vi người dùng giao riêng; kết luận audit không cấp quyền triển khai Đợt 2 hoặc gọi LLM thật.
- Nguồn thiết kế: [DACN_Schema_Input_v1_Phong_Kham.tex](/Users/macbookpro/.codex/.chatgpt-projects/g-p-68c38c8799f48191a101e19a975ca4f9/output/pdf/DACN_Schema_Input_v1_Phong_Kham.tex). Bản PDF cùng thư mục, cùng tên gốc là bản đối chiếu.
- Căn cứ đã chốt: schema input **1.0.0**, ngày **11/10/2026**; flow S02 cập nhật **18/10/2026**, gồm thao tác–dữ liệu/dependencies/tình huống (14/10), làm rõ theo phạm vi (15/10), architectural characteristics (17/10) và quy trình bước 8.1–8.5 (18/10). Ưu tiên nguồn LaTeX; nếu không truy cập được thì báo rõ, không dựng lại đặc tả từ trí nhớ.
- Phân biệt trong báo cáo và artifacts: **đã thực thi**, **mock/minh họa**, **kế hoạch đánh giá**, **kết quả đo thực tế**. Ví dụ phòng khám trong tài liệu là minh họa, không phải kết quả chạy hay xác nhận của người dùng.
- Phân biệt quyết định đã chốt với đề xuất cần review. Contract đầu ra và chi tiết triển khai chưa chốt phải được ghi rõ, đưa ra review trước khi dùng làm căn cứ implementation. Khi có mâu thuẫn với tài liệu, nêu điểm mâu thuẫn để giải quyết; không âm thầm sửa nghĩa đặc tả.

## Phân vai và bằng chứng

- **Astra:** đề xuất thiết kế kỹ thuật, implement, kiểm thử và cung cấp bằng chứng.
- **Agent audit:** đối chiếu đặc tả, review code, kiểm tra phương pháp và kết quả đánh giá.
- **Người dùng:** quyết định phạm vi và xác nhận thông tin nghiệp vụ.
- Không ghi nhận thay đổi là đã được audit hoặc người dùng xác nhận nếu chưa có kết quả tương ứng. Gắn kết quả review/xác nhận với đúng phiên bản và phạm vi được xem xét; kiểm tra của code/LLM không thay xác nhận nghiệp vụ.

## Layout workspace và thao tác hiện hành

- Code/config/tests/tooling hiện hành nằm tại `packages/s01/` và `packages/s02/`; namespaces/distributions vẫn là `dacn_s01`/`dacn-s01` và `dacn_s02`/`dacn-s02`. Không import chéo từ source; cài wheel non-editable và giữ dependency S02 → S01.
- Root `pyproject.toml` chỉ là cấu hình workspace, không build package S01. Giữ file này cùng `AGENTS.md` ở root để guard S02 nhận diện checkout kể cả khi chạy từ cwd bên ngoài. Operational state và dataset nằm ngoài checkout.
- Theo [audit a3 ngày 21/10/2026](/Users/macbookpro/.codex/.chatgpt-projects/g-p-68c38c8799f48191a101e19a975ca4f9/outputs/audits/s02-phase1-0.1.0a3-2026-10-21/AUDIT_REPORT.md), **S02-05 và LAYOUT-01 đã đóng; S02-01–04 tiếp tục đóng**. Baseline S01 `0.1.0a6`, S02 `0.1.0a3`, contract S02 draft.3, DB structure `1`. Lượt đề xuất Đợt 2 chỉ sửa trạng thái/phạm vi trong AGENTS và tạo tài liệu/ví dụ mới; giữ production source/tests/schema/locks, dependencies, version và artifacts lịch sử. [Bàn giao a3](reports/s02-phase1/fixes-0.1.0a3/IMPLEMENTATION_REPORT.md) giữ nguyên trạng thái tại thời điểm bàn giao; README còn ghi chờ audit, khi xác định nghiệm thu dùng kết luận và biên bản ngày 21/10 ở trên.
- Hướng dẫn hiện hành ở [README](README.md), [mục lục docs](docs/README.md) và [mục lục reports](reports/README.md). Tài liệu/contract/examples/báo cáo cũ giữ nguyên vị trí, nội dung và trạng thái lịch sử; đường dẫn cũ trong chúng không phải lệnh hiện hành.
- `tools/` cấp workspace chỉ phục vụ build/check/collect/layout. Runner và collector từng package ở `packages/<stage>/tools/`; entry point gọi workspace tooling. Scripts riêng cho đợt cũ nằm trong `tools/legacy/` của package, không chạy trực tiếp trên layout mới.
- Bootstrap chung dùng **một** `tools/requirements-tools.lock` (uv đã pin), runtime/wheelhouse giữ tại `.runtime/`, `.tools/`. Locks của từng package không thay đổi. Root `.venv`, `s02/.venv`, `dist`, `s02/dist` giữ vị trí cũ vì là môi trường/wheel lịch sử; không di chuyển venv hoặc ghi đè wheel bàn giao.
- Tạo venv kiểm chứng mới từ locks. Build ra thư mục mới; đối chiếu đầy đủ payload source → wheel → installed, không ép hash ZIP rebuild bằng ZIP lịch sử. S02 lock pin wheel S01 lịch sử: cài lock từ `dist/` rồi cài lại wheel S01 rebuild cùng version chỉ sau khi chứng minh payload bằng nhau; giữ bằng chứng bước thay wheel.
- Collector kiểm source = wheel = installed cùng phiên bản. Baseline khác phiên bản được chọn rõ bằng `--baseline-wheel s02=<wheel a2>` và ghi inventory/hash/diff a2 → a3 riêng, không ép payload a3 bằng a2. Cùng phiên bản vẫn bắt buộc payload/METADATA/WHEEL bằng baseline. Wrappers cố định package qua tham số nội bộ, không nhận selector CLI hoặc viết tắt; workspace tooling giữ `--package s01|s02|all` đầy đủ.
- `tools/run_checks.py --package all --report-dir <thư mục chưa tồn tại>` chạy S01 và S02 bằng **process riêng**, mỗi backend C/Python riêng; không gộp conftest hoặc bỏ instrumentation. Test helpers có thể thêm vào sys.path, production source thì không. Audit ngoài giữ nguyên assertions/file; adapter chỉ chỉ đường helpers mới.
- Mọi đầu ra kiểm mới vào thư mục mới, không ghi báo cáo cũ. Handoff layout tại `reports/repository-layout/2026-10-19/`; dữ liệu inventory, mappings, diffs và lệnh hoàn tác phải tránh ghi đè công việc phát sinh sau đợt này.

## Ranh giới codebase và dataset

- Repository implementation phải tách khỏi repository/thư mục dataset. Nếu chưa rõ vị trí implementation, hỏi trước khi tạo file; không chọn vị trí trong dataset.
- Dataset là tài nguyên bên ngoài, mặc định chỉ đọc. Không sửa, di chuyển, xóa hoặc tái tạo dataset từ repository implementation; không sao chép toàn bộ dataset vào codebase.
- Kết nối dữ liệu bằng cấu hình đường dẫn; không hardcode đường dẫn máy cá nhân trong logic. Đường dẫn tài liệu ở trên chỉ là tham chiếu thiết kế.
- Phân biệt rõ dữ liệu nguồn, test fixtures, đầu ra chạy thử và kết quả đánh giá bằng vị trí lưu và thông tin nguồn. Không ghi đầu ra vào dataset hoặc trình bày fixture/mock như dữ liệu nguồn.

## Contract S01 đã chốt

- Tiếp nhận các trường bắt buộc: `title`, `context`, `actors`, `functional_requirements`, `non_functional_requirements`, `constraints`, `design_preferences`, `operating_conditions`.
- `actors` có ít nhất một vai trò, không trùng tên; FR có ít nhất một phần tử. NFR và constraints có thể là `[]`, nhưng S02 vẫn phải kiểm tra tính đầy đủ.
- FR/NFR có `id`, `text`, `priority`, `acceptance_criteria`. ID là chuỗi không rỗng, không có khoảng trắng đầu/cuối, ổn định và duy nhất trên cả FR/NFR/constraints; không bắt buộc prefix. `text` không được null, rỗng hoặc chỉ có khoảng trắng.
- FR/NFR có priority `must`, `should`, `could` hoặc `null`; constraint bắt buộc `must`. Không tự gán priority. `acceptance_criteria` là danh sách giữ nguyên thứ tự; `[]` khi chưa cung cấp và chuyển S02 làm rõ.
- Các trường tùy chọn `title`, `group` của requirement là chuỗi không rỗng hoặc `null`; `details` có thể chứa `trigger`, `data`, `business_rules`, `exceptions` dạng chuỗi hoặc `null`.
- Constraint có cấu trúc tương tự requirement; có thể thêm object `constraint` với `kind` là chuỗi không rỗng và `value` là giá trị JSON hoặc `null`. `text` và tiêu chí nghiệm thu vẫn là nguồn nghĩa vụ chuẩn.
- `design_preferences.metric_priorities` chứa đủ, đúng một lần mỗi metric: `response_time_p95`, `sustainable_throughput`, `cpu_utilisation`, `scaling_gain`; thứ tự từ ưu tiên cao đến thấp do người dùng chọn. Không dùng thứ tự này để xếp hạng toàn bộ NFR hoặc bỏ qua constraint.
- `operating_conditions` giữ đủ sáu trường dạng chuỗi mô tả hoặc `null`: `critical_scenarios`, `expected_load`, `peak_load`, `data_volume`, `growth`, `resource_budget`. Giữ nguyên đơn vị và điều kiện gốc; phân biệt tải kiểm thử với tải vận hành.
- `project_details` tùy chọn gồm `scope_exclusions`, `external_systems`, `data_context`, dạng chuỗi mô tả hoặc `null`.
- `schema_version` là phiên bản định dạng; input cũ thiếu trường này được hiểu là `1.0.0`. Không đồng nhất schema version với revision của đặc tả người dùng.
- Bảo toàn nội dung, ID, priority, tiêu chí và thứ tự tiêu chí, nguồn, thông tin chưa biết. `null` là chưa biết; `[]` là chưa có phần tử được cung cấp. Không thay thông tin chưa biết bằng chuỗi rỗng hoặc số 0. Báo trường ngoài schema để xử lý, không âm thầm bỏ qua.
- Định danh đặc tả, revision và nguồn tách khỏi dữ liệu người dùng phải nhập. S01 hiện theo output contract `0.1.0-draft.2` và baseline nghiệm thu bên dưới. Nếu gom FR/NFR/constraints thành danh sách nội bộ, giữ loại, nội dung và nguồn gốc.
- Validation cấu trúc không chứng minh requirements đủ rõ, đúng nghiệp vụ, đã được xác nhận hoặc sẵn sàng benchmark. Không tự bổ sung nghĩa vụ nghiệp vụ.

## Baseline S01 và tiếp nhận sang S02

- Baseline nghiệm thu: package `0.1.0a6`, input schema `1.0.0`, output contract `0.1.0-draft.2`, DB structure `1`; CPython 3.13.16 có GIL, SQLite 3.53.1 trên macOS arm64/filesystem local. Không tự đổi contract hoặc dependencies của baseline trong đợt chuẩn bị S02.
- Căn cứ trạng thái: [S01_ACCEPTANCE.json](/Users/macbookpro/.codex/.chatgpt-projects/g-p-68c38c8799f48191a101e19a975ca4f9/outputs/audits/s01-phase4-0.1.0a6/S01_ACCEPTANCE.json). Proposal/báo cáo bàn giao cũ giữ trạng thái lịch sử của chúng; nghiệm thu kỹ thuật không xác nhận nghiệp vụ hoặc S02.
- S02 phải lấy nguồn qua lookup được kiểm tra, giữ đúng snapshot và version; không chỉ tin boolean handoff hoặc file JSON tự nhận validated. Không thay snapshot được chọn bằng head mới nhất.
- Criterion source ref tính từ snapshot.input, gồm snapshot_id và JSON Pointer; không nối lại index giữa revisions. Khi unchanged, nguồn của run mới khác origin_source_id của snapshot cũ; giữ đúng vai trò từng nguồn.
- Codec/schema/envelope checks không thay trusted lookup, và validation S01 không chứng minh requirements đủ rõ. Không dùng validator profile riêng của input S01 như validator tùy ý cho model S02.

## Flow S02 đã chốt — đúng chín bước

Đầu vào là requirements chuẩn hóa từ S01, kèm tiêu chí, ID, nguồn, phiên bản và thông tin chưa biết. Xét trực tiếp FR, NFR và constraints; **không tạo bước hoặc đầu ra architectural drivers**.

1. **Kiểm tra ý nghĩa và làm rõ requirements.** LLM tìm thiếu sót, mơ hồ, mâu thuẫn; code kiểm tra tham chiếu; người dùng trả lời nghiệp vụ. Giữ vấn đề/câu hỏi, requirement nguồn, phạm vi ảnh hưởng và snapshot sau làm rõ. Có thể tiếp tục phần không phụ thuộc câu trả lời; phần bị ảnh hưởng giữ trạng thái chưa rõ.
2. **Xác định actors, actions, workflows và thao tác–dữ liệu.** Mỗi thao tác có actor/hành vi, dữ liệu đọc/ghi, quy tắc phải giữ, workflow và nguồn. Giữ actors đã cung cấp; actor mới phát hiện cần nguồn và xử lý làm rõ phù hợp, không sửa snapshot S01. Phân biệt nguồn `explicit`/`inferred` với trạng thái `needs clarification` và trạng thái review; suy luận được chấp nhận vẫn giữ nguồn suy luận. Không tự gán quyền hoặc biến hành vi nội bộ thành actor bên ngoài. Mô hình thao tác–dữ liệu sinh trong S02, không thêm trường bắt buộc vào input S01.
3. **Identify Initial Components.** Đề xuất partitioning theo domain/trách nhiệm kỹ thuật, dựa trên actors/actions, workflows và thao tác–dữ liệu–quy tắc. Ứng viên có ID, tên, mục đích, trách nhiệm, liên kết, lý do nhóm/tách và điểm chưa chắc chắn. Cùng dữ liệu/quy tắc là căn cứ cân nhắc, không bắt buộc gộp. Không ánh xạ máy móc entity/action/requirement thành component; component chưa phải microservice hay đơn vị triển khai độc lập.
4. **Assign Requirements to Components.** Đối chiếu từng requirement và từng acceptance criterion với trách nhiệm, component chính/phối hợp hoặc phạm vi toàn hệ thống. Cho phép mapping nhiều–nhiều; báo nghĩa vụ chưa được thể hiện. Không ép NFR/constraint thành component riêng.
5. **Analyze Roles, Responsibilities and Interactions.** Xem trách nhiệm thiếu/chồng chéo, cohesion, granularity và phối hợp. Mỗi dependency giữ bên cần dùng/bên cung cấp, capability, thao tác/workflow, requirement nguồn, lý do, nhãn suy luận và phần chưa rõ. Cùng dùng dữ liệu hoặc đứng cạnh nhau trong workflow không tự chứng minh dependency. Đi qua tình huống nghiệp vụ và lưu findings; interfaces ở mức logic, chưa chốt protocol/công nghệ.
6. **Analyze Architecture Characteristics.** Đánh giá các thuộc tính chất lượng như scalability, reliability, availability, performance, security và modifiability trên phương án components cụ thể. Ghi nguồn, mục tiêu/điều kiện/phạm vi/ưu tiên đã biết; dùng tình huống phân tích ranh giới, trách nhiệm và dependencies; cân nhắc giữ/tách/gộp/chuyển trách nhiệm cùng lợi ích, chi phí và đánh đổi giữa thuộc tính. Ghi giả định, rủi ro và nghĩa vụ kiểm chứng. Thiếu mục tiêu cần quyết định thì về bước 1; đề xuất sửa thì bước 7 áp dụng. Không tự đặt SLA/workload/ưu tiên, đồng nhất constraint với characteristic, hoặc chứng nhận đạt thuộc tính bằng điểm LLM hay hình vẽ.
7. **Restructure Components khi cần.** LLM đề xuất; code áp dụng thay đổi theo phiên bản, giữ lý do/nguồn/phạm vi. Cập nhật mapping bước 4 và các tham chiếu, căn cứ dependencies, tình huống, hồ sơ characteristics bị ảnh hưởng; quay lại bước 5–6. Sau bước 6, nếu chưa phát hiện vấn đề cần sửa thì chuyển bước 8. Khi hết giới hạn hoặc không tiến triển, giữ issues và trạng thái cần review.
8. **Kiểm tra model và sinh diagram bằng code.** Giữ năm công việc trong một bước: **8.1** validate model/refs/mapping/records/version; **8.2** chọn view có phạm vi rõ, giữ liên kết ID gốc; **8.3** converter cố định JSON/model → PlantUML theo loại/hướng/nhãn, alias/escape và thứ tự ổn định; **8.4** render SVG local, đối chiếu phần tử/quan hệ với view và kiểm khả năng đọc; **8.5** đóng gói cùng model revision để review. Phân biệt dependency với provided/required interface. Không tự thêm node/interface/công nghệ để render. Lỗi dữ liệu trả bước tạo, lỗi nghĩa về phân tích, lỗi converter/render/layout sửa tại bước 8; không sửa nghĩa chỉ để có hình. MODELSWARD 2026 là căn cứ cho nguyên lý model có cấu trúc → code converter → renderer trên class diagram; component mapping, view, fidelity, provenance/review là phần DACN bổ sung. Giữ citation trong tài liệu nghiên cứu.
9. **Người dùng review và xác nhận đúng phiên bản.** Trình bày requirement nguồn, actors, components/trách nhiệm, interfaces/tương tác, căn cứ, suy luận và câu hỏi mở. Feedback cấu trúc quay về bước 7 rồi 5–6; làm rõ/đổi requirements quay về bước 1. Nếu đổi nghĩa, cập nhật revision và phân tích lại phần liên quan. Xác nhận gắn đúng phiên bản requirements và model; chấp nhận có điều kiện phải giữ điều kiện và phạm vi được chấp nhận.

### Quy tắc xuyên suốt và bàn giao S02

- Bước 1 nhận câu hỏi nghiệp vụ/mục tiêu chất lượng từ bước 2–6. Nếu thông tin đã có nhưng LLM bỏ sót thì đọc nguồn và sửa phân tích; không hỏi lại người dùng. Bất định về lựa chọn thiết kế giữ trong phân tích/review.
- Khi câu trả lời đổi nghĩa requirements, tạo revision qua S01; không sửa snapshot. Xét phần ảnh hưởng trực tiếp và gián tiếp bằng refs cùng hỗ trợ phân tích ngữ nghĩa; phân tích lại từ phần sớm nhất bị ảnh hưởng. Giữ phần độc lập với bằng chứng phù hợp revision mới. Kết quả theo snapshot cũ không tự ghép vào model mới.
- Chờ trả lời theo phạm vi, tiếp tục phần độc lập; hết thời gian/ngân sách không phải xác nhận. Khi ghép lại vẫn validate toàn model và không bàn giao phần còn cần đánh giá lại như đã được chấp nhận.
- Code kiểm tra cấu trúc/tham chiếu/nguồn/phiên bản sau mỗi lượt LLM. LLM hỗ trợ phân tích ý nghĩa; người dùng xác nhận nghiệp vụ. Nguồn hợp lệ, mapping hợp lệ và render thành công chưa chứng minh thiết kế đúng.
- Không tự gán công nghệ, cardinality, quyền hoặc workload chưa xác định; không biến suy luận thành requirement đã xác nhận.
- Vòng sửa có giới hạn lượt/ngân sách theo cấu hình. Khi chạm giới hạn hoặc không tiến triển, giữ `unresolved issues` và trạng thái cần review; không tự đánh dấu hoàn tất. Giá trị giới hạn cụ thể còn cần review.
- Chưa tích hợp truy xuất KB vào S02; không dùng KB đoán nghiệp vụ riêng. Truy xuất kiến trúc thuộc S04 theo tài liệu.
- Few-shot là thử nghiệm phụ; solver tối ưu, Lean, tìm kiếm nhiều thế hệ và nhiều agents tranh luận không thuộc phạm vi implementation chính S02 theo nguồn 18/10.
- Gói S02 gồm: snapshot nguồn; actors/actions/workflows; thao tác–dữ liệu–quy tắc; components/trách nhiệm/interfaces/dependencies và căn cứ; mapping requirement/criterion; hồ sơ tình huống và architectural characteristics; issues/làm rõ; view, PUML/SVG, validation và cấu hình sinh; review và lịch sử thay đổi. Model, diagram và review gắn đúng phiên bản. Nội dung đã chốt không đồng nghĩa schema JSON chi tiết đã chốt.
- Chỉ chuyển gói sang S03 khi model hợp lệ về cấu trúc, mapping và phần chưa thể hiện đã được báo, người dùng đã review đúng phiên bản. Nếu chấp nhận có điều kiện, chỉ tiếp tục phạm vi không bị chặn và giữ điều kiện. S02 chưa chốt architectural style, deployment topology hoặc architecture quantum; điều kiện bàn giao không tự mở rộng phạm vi implementation sang S03.

## Kiểm thử và đánh giá

- **S01:** đánh giá validation trường/kiểu/ràng buộc, bảo toàn nội dung và unknown values, ID, metadata và revision; bao gồm input không hợp lệ, trường lạ và input cũ thiếu `schema_version` theo contract áp dụng.
- **S02:** đánh giá actors/actions/workflows, thao tác–dữ liệu, đầy đủ trách nhiệm/criteria, căn cứ phân chia/dependency, tình huống, ảnh hưởng architectural characteristics và đánh đổi, suy luận thiếu nguồn, câu hỏi mở và fidelity diagram. Kiểm tra phản hồi sửa, phạm vi ảnh hưởng/tái sử dụng, giới hạn vòng lặp và sự nhất quán phiên bản/xác nhận.
- Không đánh giá components chỉ bằng khớp tên hoặc số lượng với một mẫu duy nhất. Ví dụ phòng khám không quy định một cách chia component bắt buộc.
- Đánh giá giá trị nâng cấp bằng đối chiếu baseline giản lược, chỉ thêm thao tác–dữ liệu, chỉ thêm kiểm tra dependency/tình huống và kết hợp cả hai; giữ cùng requirements, model LLM và ngân sách. Số case, prompt/config cho các nhánh và phương pháp chấm cần review trước chạy; không dùng nhánh nghiên cứu giản lược thay flow production đã chốt.
- Tách kiểm thử code khỏi đánh giá ngữ nghĩa đầu ra LLM; báo riêng phương pháp, kết quả và giới hạn. Mock thành công không phải bằng chứng LLM/renderer thực đã chạy.
- Ghi phiên bản đặc tả, phiên bản code, dữ liệu đánh giá và cách chia dữ liệu; model, prompt, cấu hình khi áp dụng. Lưu bằng chứng kết quả và lỗi đủ để đối chiếu/tái lập, phân biệt kết quả đo với kỳ vọng.
- Không dùng dữ liệu đánh giá cuối để điều chỉnh prompt rồi báo kết quả như đánh giá độc lập. Nếu đã dùng để tinh chỉnh, phải công khai và không tiếp tục coi tập đó là tập đánh giá độc lập.
- Không tự chốt ngưỡng đạt, model hoặc kết luận chất lượng khi chưa có căn cứ. Đề xuất rubric/phương pháp và đưa ra review trước khi dùng để kết luận.
- Chưa dùng benchmark kiến trúc Stage 2 thay đánh giá S01–S02. Ưu tiên metrics là input; contract cấu hình benchmark số học chưa chốt. Điều kiện R3 “50 người dùng trong 30 phút” không chứng minh tải đỉnh production, và phân tích S02 không chứng minh đã đạt p95.

## Bàn giao mỗi đợt implementation để audit

Mỗi đợt phải ghi rõ:

- Phạm vi đã làm, contract và phiên bản áp dụng; trạng thái thực thi/mock/kế hoạch/kết quả đo.
- Thay đổi cùng lý do và các file/artifacts liên quan.
- Kiểm thử đã chạy, cách chạy, kết quả và đường dẫn bằng chứng; nêu rõ phần chưa chạy.
- Hạn chế, giả định, vấn đề chưa giải quyết và phạm vi ảnh hưởng.
- Nội dung cần agent audit hoặc người dùng quyết định; không tự gắn trạng thái đã audit/đã xác nhận.

## Điểm cần làm rõ/review trước phần implementation liên quan

Các mục dưới đây **chưa chốt**, không phải yêu cầu mới đã được xác nhận:

- Baseline [contract S02](docs/S02_OUTPUT_CONTRACT_PROPOSAL.md) `s02/0.1.0-draft.3` và [kế hoạch](docs/S02_IMPLEMENTATION_PLAN_PROPOSAL.md) `s02-plan/0.1.0-draft.3` đã được [audit thiết kế ngày 19/10/2026](/Users/macbookpro/.codex/.chatgpt-projects/g-p-68c38c8799f48191a101e19a975ca4f9/outputs/audits/s02-proposal-draft3-2026-10-19/AUDIT_REPORT.md). F01–F05 đóng ở mức đặc tả, không phải nghiệm thu code hoặc nghiệp vụ.
- Đợt 1 chỉ gồm package/môi trường riêng, schemas/typed refs, checked intake S01, kho S02, revisions, staging/events, nền tảng Answer/application, closure thuần và CLI init/intake/lookup/receipt. Không tự đổi semantics draft.3. S01 a6 và dataset/nguồn giữ nguyên.
- AnalysisSet bất biến có head riêng; công bố kiểm CAS cặp model/AnalysisSet. Đổi set làm gói/review cũ stale; log không làm stale. Staging T0–T2 không trỏ Artifact tới final Run chưa tồn tại; promotion và Run cùng T3.
- Answer và application events bất biến, claim theo Answer và unique applied; recovery giữ identity. Đợt 1 chỉ làm invariants/persistence, chưa điều phối đầy đủ consent/S01 update.
- Lượt hiện tại phản hồi [audit proposal Đợt 2 draft.1](/Users/macbookpro/.codex/.chatgpt-projects/g-p-68c38c8799f48191a101e19a975ca4f9/outputs/audits/s02-phase2-proposal-draft1-2026-10-21/AUDIT_REPORT.md): S02-P2-01 và S02-P2-02 mức P1 còn chờ audit lại. a3 chưa hỗ trợ application cùng snapshot và carry Issue resolved bằng Answer qua Model như proposal cũ. [Addendum A1/A2](docs/S02_PHASE2_CONTRACT_AMENDMENT_PROPOSAL.md) và proposal draft.2 chỉ là đề xuất; chưa sửa contract/code/tests hoặc cấp quyền implementation. Nghiệm thu Đợt 1 giữ phạm vi lịch sử; G2/G3/G4 và các batch phụ thuộc vẫn cần review.
- Closure phải mở rộng **mọi Part được phát hiện tới toàn bộ action_ids**, tiếp tục workflow/Support/mappings đến fixed point và kiểm lại hợp cuối. Không kéo tất cả actions vì chung component/interface/responsibility; không cắt action để né blocker.
- Bằng chứng tests thật, package installed ngoài source, concurrency/fault/recovery và hashes Đợt 1 ở `reports/s02-phase1/`; nghiệm thu giới hạn theo biên bản a3 ngày 21/10. [Đề xuất Đợt 2](docs/S02_PHASE2_IMPLEMENTATION_PLAN_PROPOSAL.md) phải được audit và người dùng giao implementation trước khi viết code. Không suy tests pass hoặc nghiệm thu Đợt 1 thành nghiệm thu các bước phân tích hay quyền chạy live pilot.
- Live LLM/model/API/quyền gửi dữ liệu/ngân sách, prompts, renderer/toolchain và rubric/heldout thuộc các đợt sau trước khi sử dụng; chưa được thực thi hoặc duyệt chi phí trong Đợt 1.
- Đường dẫn/phiên bản dataset bên ngoài, dữ liệu được dùng làm fixtures và cách tách đầu ra; chưa giả định dataset có sẵn.
- Kế hoạch đánh giá S01–S02: tập phát triển/tập đánh giá cuối, rubric ngữ nghĩa, người review, bằng chứng và căn cứ cho ngưỡng đạt nếu cần.
- Nghiệp vụ phòng khám: ai được đặt/hủy lịch, phạm vi phòng khám của nhân viên, priority R1–R4 và các điều kiện vận hành còn thiếu. Giữ unknowns/câu hỏi mở; chỉ chặn phần phụ thuộc, không tự điền để hoàn thiện model.
