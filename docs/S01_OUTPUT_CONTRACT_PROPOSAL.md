# Đề xuất contract đầu ra S01

**Trạng thái: proposed — bản sửa chưa audit/chưa được duyệt.** Tác giả đề xuất: Astra. Ngày tạo: 12/10/2026. Cập nhật: 13/10/2026. Phiên bản đề xuất: `0.1.0-draft.2`.

Bản draft.2 tiếp nhận phản hồi về cập nhật đồng thời và whitespace: cho phép nhiều lần unchanged khi base còn hiện hành; cố định tập ký tự dùng cho nonblank và khoảng trắng quanh ID, bổ sung U+001C–U+001F. Các tình huống mới là minh họa/kỳ vọng, chưa chạy implementation hoặc tests. Sáu envelope giữ nguyên dữ liệu và kết quả giả định, chỉ cập nhật output contract version.

Đề xuất giữ nguyên ba danh sách FR/NFR/constraints, lưu snapshot bất biến và trả envelope riêng cho từng lần chạy S01. Chỉ đầu ra vượt qua toàn bộ kiểm tra và lưu thành công mới được chuyển sang S02. Đây là tài liệu thiết kế cùng ví dụ biên soạn; chưa có implementation hay kết quả thực thi S01. Bảng kiểm thử là kế hoạch, chưa viết hoặc chạy tests.

## 1 Căn cứ và quyết định đã chốt

Các tài liệu nguồn được đọc tại chỗ, không sửa:

- [AGENTS.md](../AGENTS.md).
- [Báo cáo LaTeX](/Users/macbookpro/.codex/.chatgpt-projects/g-p-68c38c8799f48191a101e19a975ca4f9/output/pdf/DACN_Schema_Input_v1_Phong_Kham.tex), các mục “Cấu trúc yêu cầu và quy tắc dữ liệu”, “Phân định với phần xử lý của hệ thống” và “S02”. Schema input chốt ngày 11/10/2026; flow S02 chốt ngày 12/10/2026.
- [Schema input tham chiếu](/Users/macbookpro/.codex/.chatgpt-projects/g-p-68c38c8799f48191a101e19a975ca4f9/outputs/system-input-v1/system-input.schema.json), phiên bản input `1.0.0`.
- [Ví dụ phòng khám](/Users/macbookpro/.codex/.chatgpt-projects/g-p-68c38c8799f48191a101e19a975ca4f9/outputs/system-input-v1/clinic-input.example.json).
- [Validator tham chiếu](/Users/macbookpro/.codex/.chatgpt-projects/g-p-68c38c8799f48191a101e19a975ca4f9/outputs/system-input-v1/input_contract.py): đọc mã `Text` và `SystemInput.check_identifiers` để đối chiếu whitespace; không chạy hoặc sửa validator.

Các quyết định đã chốt là: bảo toàn nội dung/ID/priority/acceptance criteria và thứ tự tiêu chí/unknowns/nguồn; metadata nội bộ không do người dùng điền trong input; input thiếu `schema_version` được hiểu là `1.0.0`; ID duy nhất trên cả ba danh sách và không có khoảng trắng đầu/cuối; không tự bổ sung nghiệp vụ. S01 kiểm tra cấu trúc, S02 phân tích ý nghĩa và làm rõ. S01 không dùng LLM để phân loại lại requirements, diễn giải nghiệp vụ hay sinh components/architectural drivers.

JSON Schema đã biểu diễn số lượng, kiểu, enum, `uniqueItems` cho actors/metrics và `additionalProperties: false` ở các object được khai báo. Schema chưa biểu diễn đầy đủ tính duy nhất toàn cục của ID và khoảng trắng bao quanh ID; chính `$comment` của schema cũng nêu giới hạn này. Không coi việc chỉ chạy JSON Schema là đủ.

Schema tham chiếu cho phép `project_details`, `details`, `constraint` là `null`; các trường mô tả tùy chọn nếu có giá trị chuỗi vẫn phải có ký tự không phải khoảng trắng. `constraint.value` cho phép giá trị JSON tùy ý, kể cả object có key riêng. Các annotation `default` không phải chỉ thị tự điền tất cả trường thiếu.

**Từ mục 2 trở đi là đề xuất của Astra**, cần agent audit review trước khi dùng làm căn cứ implementation. Không thay đổi schema input đã chốt.

## 2 Lựa chọn chính của Astra

| Vấn đề | Phương án khuyến nghị và lý do | Trade-off hoặc phương án khác |
| --- | --- | --- |
| Dữ liệu chuẩn hóa | Giữ riêng FR/NFR/constraints trong `snapshot.input`, sát nguồn và không cần thêm trường phân loại | Danh sách chung thuận tiện duyệt; có thể tạo view trong bộ nhớ sau này, không là contract lưu trữ thứ hai |
| Chuẩn hóa | Chỉ thêm `schema_version` khi thiếu; giữ nguyên mọi dữ liệu khác | Consumer phải xử lý trường tùy chọn vắng mặt; đổi lại không đánh đồng vắng mặt với `null` |
| Truy nguồn | Tham chiếu snapshot bất biến và JSON Pointer; giữ nguồn thô theo `source_id` | Không cần ID riêng cho tiêu chí; không tự nối danh tính tiêu chí qua revision |
| Revision | So sánh cây JSON sau chuẩn hóa; mọi thay đổi dữ liệu, kể cả thứ tự mảng, tạo revision mới | Có revision chỉ do trình bày; S01 không phải đoán thay đổi có đổi nghĩa hay không |
| Lần gửi không đổi | Tạo run mới, dùng lại snapshot hiện hành | Lưu thêm run/source record nhưng không làm tăng revision giả |
| Cập nhật đồng thời | Quyết định kết quả trên base hiện hành tại thời điểm commit; unchanged không tăng revision nên nhiều lần có thể cùng thành công | Cần đồng bộ bước quyết định/commit; payload bằng hiện hành không được bỏ qua base đã lỗi thời |
| Whitespace | Dùng tập W 29 code point cố định ở mục 7.2 cho cả nonblank và biên ID, không trim input | Bổ sung bốn ký tự so với draft.1; adapter validation phải bảo đảm quy tắc này thay vì phụ thuộc regex/strip mặc định |
| Lỗi | Có trạng thái phân biệt, danh sách lỗi có vị trí; `snapshot: null` khi thất bại | Không cung cấp partial payload cho S02; editor lấy dữ liệu lỗi từ nguồn riêng |
| Hash nội dung | Chưa dùng hash để quyết định revision; so sánh giá trị JSON chính xác | Tránh thêm canonicalization vào contract đầu tiên; có thể tối ưu sau khi review |

## 3 Envelope và các kiểu dữ liệu

Contract output đề xuất là `0.1.0-draft.2`; đây không phải bản output đã được duyệt. Ba loại phiên bản có ý nghĩa khác nhau:

- `output_contract_version`: định dạng và quy tắc của envelope S01.
- `snapshot.input.schema_version`: định dạng input, hiện chỉ `1.0.0`.
- `snapshot.revision`: số nguyên tăng theo thay đổi dữ liệu của một `spec_id`, bắt đầu từ 1.

Tất cả trường trong bảng sau là **bắt buộc**, kể cả trường nullable. Không phát sinh key ngoài contract; các object `input` và `error.details` tuân theo quy tắc riêng. Chuỗi định danh hệ thống là chuỗi opaque không rỗng, duy nhất trong kho tương ứng, không suy ra từ title/đường dẫn/requirement ID. Các nhãn `*-demo-*` trong ví dụ là định danh giả lập, không quy định thuật toán tạo ID.

### 3.1 Envelope

| Trường | Kiểu | Ý nghĩa và ví dụ |
| --- | --- | --- |
| `output_contract_version` | string cố định | `"0.1.0-draft.2"` |
| `status` | enum | `validated`, `rejected`, `failed` |
| `result_kind` | enum hoặc null | `new_spec`, `new_revision`, `unchanged`; null nếu không validated |
| `run` | Run | Lần tiếp nhận, nguồn hiện tại và kết quả kiểm tra |
| `snapshot` | Snapshot hoặc null | Chỉ có khi validated; không có bản nháp nửa hợp lệ |
| `handoff` | object | Hai trường bắt buộc `eligible_for_s02: boolean`, `snapshot_id: string hoặc null` |

`validated` nghĩa là vượt kiểm tra theo contract và đã lưu thành công, không có nghĩa đúng nghiệp vụ. `rejected` là input hoặc yêu cầu cập nhật không hợp lệ. `failed` là lỗi xử lý/lưu trữ của hệ thống, không kết luận input sai. Với hai trạng thái sau: `result_kind = null`, `snapshot = null`, `handoff = {"eligible_for_s02": false, "snapshot_id": null}` và có ít nhất một error. Với validated: không có error, mọi check đều `passed`, handoff trỏ đúng snapshot trả về.

### 3.2 Run và nguồn của lần chạy

| Trường trong `run` | Kiểu | Ý nghĩa |
| --- | --- | --- |
| `run_id` | string | Định danh mới cho mỗi lần xử lý, ví dụ `run-demo-001` |
| `received_at`, `completed_at` | string | Thời gian hệ thống nhận và hoàn tất; dạng UTC `YYYY-MM-DDTHH:mm:ss.sssZ` |
| `validator_version` | string | Phiên bản/build bất biến của code validation để tái lập; ví dụ chỉ dùng `illustration-only`, không phải validator đã chạy |
| `input_schema_sha256` | string hoặc null | 64 ký tự hex thường của SHA-256 trên byte file schema thực dùng; null nếu chưa chọn/đọc được schema |
| `request` | object hoặc null | Object có đủ `mode: create hoặc update`, `spec_id: string hoặc null`, `base_revision: integer >= 1 hoặc null`; null khi request đầu vào không biểu diễn được bằng các kiểu này |
| `source` | object | `source_id: string`, `kind: json_file hoặc api hoặc form`, `label: string hoặc null` |
| `input_version` | object | `origin: explicit hoặc legacy_default hoặc unresolved`, `resolved: "1.0.0" hoặc null` |
| `normalizations` | array | Các phép biến đổi thực hiện trong lần này; `[]` nếu không có |
| `validation` | object | `checks` và `errors` theo mục 7 |

`request` là ngữ cảnh thao tác do ứng dụng truyền riêng, **không thêm vào input schema**. `create` yêu cầu `spec_id = base_revision = null`. `update` yêu cầu cả hai có giá trị, đặc tả tồn tại và `base_revision` đúng revision hiện hành. Không suy đoán cập nhật dựa trên title hoặc nội dung giống nhau. Request sai được báo lỗi, không rơi về create.

Nếu request sai kiểu/thiếu key/ngoài cấu trúc trên, `run.request = null`, báo `INVALID_REQUEST` tại vị trí trong request gốc; giữ giá trị sai trong `details.actual` khi key có tồn tại. Không ép kiểu hay tự điền request để tạo object hợp lệ. Lưu ngữ cảnh request gốc trong bản ghi lần tiếp nhận phục vụ audit. Pointer `target=request` luôn tính trên ngữ cảnh gốc, kể cả khi `run.request` là null. Trường hợp request biểu diễn được nhưng không hợp lệ theo mode vẫn trả object đó cùng lỗi, ví dụ update có base_revision null. Validated bắt buộc có request khác null và hợp lệ.

`source_id` định danh một lần chụp nguồn bất biến, không phải đường dẫn tới file ngoài có thể thay đổi. `label` chỉ để hiển thị, ví dụ `clinic-input.example.json`; không là khóa truy vết. Kho nguồn lưu byte JSON gốc trước chuẩn hóa, gắn source record với run. Với form/API truyền object, chụp payload JSON tại biên tiếp nhận, trước adapter có thể tự điền mặc định; nguồn được cam kết bảo toàn là payload đó, không phải trạng thái UI trước khi gửi. Không ép số qua kiểu số gây mất chính xác khi chụp.

Nguồn JSON parse lỗi vẫn được lưu dưới source record phục vụ sửa lỗi. Dữ liệu nguồn chưa hợp lệ không được đưa vào snapshot đặc tả. Vị trí lưu và retention sẽ được quyết định khi thiết kế persistence; không phụ thuộc đường dẫn máy cá nhân. Chỉ chụp payload được gửi, không sao chép dataset. Nếu lỗi xảy ra trước khi lưu nguồn/run, status là failed và ID được cấp chỉ là correlation ID, không cam kết tra cứu được; không được phát handoff.

Timestamp do hệ thống tạo, không nhận từ input; `completed_at >= received_at`. Dùng để audit thời điểm xử lý, không dùng làm ID hoặc quyết định thứ tự revision. Thứ tự revision do commit kiểm soát. SHA-256 ở đây chỉ nhận diện artifact schema để phân biệt các file cùng tên/version; không hash input, không chứng minh validation đã chạy hay nghiệp vụ đúng. Ví dụ dùng digest thực của schema tham chiếu để chỉ rõ căn cứ, nhưng run/timestamp vẫn là giả lập.

### 3.3 Snapshot

| Trường | Kiểu | Ý nghĩa |
| --- | --- | --- |
| `spec_id` | string | Định danh đặc tả do hệ thống cấp, ví dụ `spec-demo-clinic` |
| `revision` | integer >= 1 | Revision của dữ liệu |
| `snapshot_id` | string | Định danh bất biến, duy nhất cho cặp spec/revision |
| `parent_snapshot_id` | string hoặc null | Snapshot liền trước trong cùng spec; null chỉ ở revision 1 |
| `created_by_run_id` | string | Run đầu tiên đã tạo snapshot; không thay khi dùng lại |
| `origin_source_id` | string | Nguồn đã tạo snapshot; không thay bằng nguồn của lần gửi lại |
| `input` | object | Input đã kiểm tra và chuẩn hóa, đúng schema `1.0.0` |

Metadata hệ thống nằm ngoài `input`. ID requirement là ID người dùng đã cung cấp, không đổi thành `spec_id`, không gắn prefix và không đánh số lại. Snapshot không chứa cờ nghiệp vụ đã xác nhận, components, actors suy luận, câu hỏi nghiệp vụ tự sinh hoặc đánh giá độ đầy đủ.

### 3.4 Dữ liệu bên trong snapshot

| Trường input | Bắt buộc | Kiểu và quy tắc |
| --- | --- | --- |
| `schema_version` | Có ở output | Chuỗi `1.0.0`; có thể được thêm từ quy tắc legacy |
| `title`, `context` | Có | Chuỗi có ký tự không phải khoảng trắng |
| `actors` | Có | Mảng ít nhất một chuỗi không trắng, không trùng theo quy tắc mục 7 |
| `functional_requirements` | Có | Mảng ít nhất một Requirement |
| `non_functional_requirements` | Có | Mảng Requirement; cho phép `[]` |
| `constraints` | Có | Mảng Constraint; cho phép `[]` |
| `design_preferences` | Có | Object có `metric_priorities`, hoán vị đúng bốn metric đã chốt |
| `operating_conditions` | Có | Đủ sáu trường đã chốt, mỗi trường là chuỗi không trắng hoặc null |
| `project_details` | Không | Object hoặc null; object chỉ có các key tùy chọn `scope_exclusions`, `external_systems`, `data_context`, chuỗi không trắng hoặc null |

Requirement có bốn trường bắt buộc: `id` (chuỗi không trắng, không có khoảng trắng đầu/cuối), `text` (chuỗi không trắng), `priority` (`must/should/could/null`), `acceptance_criteria` (mảng chuỗi không trắng, có thể rỗng). Trường tùy chọn: `title`, `group` (chuỗi không trắng hoặc null), `details` (object hoặc null). `details` có các key tùy chọn `trigger`, `data`, `business_rules`, `exceptions`, mỗi giá trị là chuỗi không trắng hoặc null.

Constraint giữ cấu trúc trên nhưng `priority` chỉ được `must`; có thể thêm `constraint` là null hoặc object với **cả hai** key bắt buộc `kind` (chuỗi không trắng), `value` (giá trị JSON bất kỳ, kể cả null). Object tự do nằm bên trong `value` không bị coi là trường lạ của schema.

`operating_conditions` gồm `critical_scenarios`, `expected_load`, `peak_load`, `data_volume`, `growth`, `resource_budget`. Bốn metric là `response_time_p95`, `sustainable_throughput`, `cpu_utilisation`, `scaling_gain`. Thứ tự metric thuộc dữ liệu người dùng, không tự sắp lại.

## 4 Chuẩn hóa được phép

Chỉ có **một phép thay đổi dữ liệu**: nếu root input là object và **không có key** `schema_version`, thêm key đó với giá trị `1.0.0` vào bản làm việc. Ghi đúng một phần tử trong `run.normalizations`:

```json
{"operation":"add","input_pointer":"/schema_version","value":"1.0.0","reason":"LEGACY_SCHEMA_VERSION"}
```

Đó là cấu trúc đầy đủ của Normalization; cả bốn trường bắt buộc và các giá trị trên cố định ở phiên bản đề xuất này. Chỉ ghi nếu phép thêm thực sự đã thực hiện; nguồn thô không đổi. Phép thêm vẫn được ghi nếu sau đó phát hiện input không hợp lệ, nhưng không trả bản chuẩn hóa lỗi thành snapshot.

Parse/serialize có thể đổi thụt dòng, escape tương đương và thứ tự key của object; nguồn thô giữ biểu diễn gốc. Không đổi giá trị JSON. Không trim/collapse khoảng trắng, đổi hoa thường, Unicode-normalize, dịch/viết lại text, parse số/đơn vị từ mô tả, đổi kiểu, sort/deduplicate mảng, bổ sung priority/tiêu chí, bỏ key lạ hoặc thêm mặc định tùy chọn. Vắng mặt và null vẫn khác nhau. ID có khoảng trắng bao quanh bị từ chối thay vì âm thầm sửa.

`schema_version: null`, `""`, `" 1.0.0 "`, số `1`, hoặc `"2.0.0"` không được hưởng mặc định legacy. Thiếu `acceptance_criteria` là lỗi required; chỉ mảng `[]` được gửi rõ ràng mới biểu thị chưa cung cấp tiêu chí. Không chuyển chuỗi rỗng/số 0 thành null. Giá trị 0 hợp lệ trong vùng JSON tự do vẫn giữ nguyên, không suy đoán đó là unknown.

## 5 Truy vết requirement và acceptance criterion

Source record và snapshot đều bất biến. Reference lưu trong artifacts downstream có đúng hai trường bắt buộc: `snapshot_id: string`, `input_pointer: string`. Pointer tính **từ root của `snapshot.input`**, không từ root envelope. Quy ước: root là chuỗi rỗng; mỗi đoạn bắt đầu `/`; index mảng tính từ 0; key chứa `~` encode thành `~0`, key chứa `/` encode thành `~1`.

Ví dụ tham chiếu đầy đủ, là minh họa chưa chạy:

```json
{
  "requirement_ref": {
    "snapshot_id": "snap-demo-clinic-r1",
    "input_pointer": "/functional_requirements/0"
  },
  "criterion_ref": {
    "snapshot_id": "snap-demo-clinic-r1",
    "input_pointer": "/functional_requirements/0/acceptance_criteria/1"
  }
}
```

Object bọc `requirement_ref`/`criterion_ref` ở ví dụ chỉ minh họa cách dùng Reference, không thêm field này vào envelope. Reference thứ nhất trỏ R1; reference thứ hai trỏ “Phản hồi xung đột chỉ rõ slot.”. Muốn truy nguồn: resolve snapshot, lấy `origin_source_id`, đọc nguồn gốc tại **cùng pointer**. Ngoại lệ duy nhất là `/schema_version` được thêm khi nguồn legacy thiếu key; run tạo snapshot ghi nguồn của giá trị này là quy tắc `LEGACY_SCHEMA_VERSION`, không giả là người dùng đã nhập.

Không cần bảng source map lặp lại toàn bộ payload vì không thay đổi vị trí của dữ liệu nguồn. Các trường khác cũng truy vết theo cùng quy tắc. Có thể tra requirement qua `(spec_id, revision, requirement_id)` rồi tìm đúng một phần tử trong ba danh sách; không dùng riêng ID làm reference xuyên spec. Criterion chưa có ID do người dùng cấp; identity an toàn trong bản này là `(snapshot_id, input_pointer)`.

| Thao tác ở revision mới | Cách xử lý tham chiếu |
| --- | --- |
| Sửa text/priority/tiêu chí dưới ID cũ | ID giữ nguyên như input; reference cũ vẫn trỏ nội dung cũ. Tạo reference gắn snapshot mới; không suy ra người dùng đã duyệt nội dung mới |
| Thêm requirement/criterion | Dùng ID requirement được gửi và vị trí mới; không tự sinh ID thay người dùng |
| Xóa requirement/criterion | Không xóa nguồn/snapshot cũ; không retarget reference cũ sang phần tử kế tiếp |
| Đổi thứ tự requirements/criteria | Tạo revision mới và pointer mới; reference cũ vẫn đúng trong snapshot cũ |
| Đổi ID requirement | Biểu diễn là bỏ ID cũ, thêm ID mới; không tự suy đoán rename dựa trên text giống nhau |
| Cùng ID chuyển FR sang NFR/constraint | Giữ đúng loại người dùng gửi, validation theo nhóm mới; ghi nhận thay đổi qua snapshots, không tự phân loại |
| ID đã xóa xuất hiện lại | Ghi nhận tái xuất hiện ở revision mới; không tự nối lại mapping hoặc xác nhận cũ |
| Hai criterion có nội dung giống nhau | Cho phép vì schema không cấm; phân biệt theo index trong snapshot, không gộp hoặc ghép lịch sử bằng text |

Không tự nối identity criterion qua các revision bằng index hoặc nội dung. Downstream phải đối chiếu lại mapping khi snapshot thay đổi; có thể đề xuất cơ chế liên kết tường minh riêng sau này. S01 không biết việc tái sử dụng ID có đúng ý nghĩa hay không; người sửa có trách nhiệm giữ ID cho cùng requirement và dùng ID mới cho requirement khác. Việc kiểm tra ngữ nghĩa thuộc S02/audit.

## 6 Revision và lịch sử

Trình tự đề xuất: chụp nguồn → parse và nhận diện version → chuẩn hóa được phép → schema checks → cross-field checks → kiểm tra request/base revision → so sánh snapshot hiện hành → commit nguyên tử → trả kết quả. Chỉ chạy bước phụ thuộc khi dữ liệu tiền đề đủ hợp lệ; không sinh lỗi giả do bước trước chưa qua.

| Tình huống | Kết quả |
| --- | --- |
| `create` hợp lệ | Spec ID và snapshot ID mới, revision 1, parent null; `new_spec` |
| `update` hợp lệ, base hiện hành, dữ liệu bằng hiện hành | `unchanged`; trả nguyên snapshot cũ, thêm run/source record |
| `update` hợp lệ, base hiện hành, dữ liệu khác | `new_revision`; revision hiện hành + 1, snapshot ID mới, parent trỏ hiện hành |
| Nội dung giống spec khác nhưng gửi `create` | Vẫn tạo spec mới; không gộp theo nội dung |
| Input lỗi, request lỗi hoặc base lỗi thời | `rejected`; không tăng revision hoặc thay snapshot hiện hành |
| Lỗi hệ thống/lưu trữ | `failed`; không handoff; không được công bố snapshot chưa commit |

So sánh cây JSON có kiểu: key object không có thứ tự; array có thứ tự; string so chính xác theo chuỗi Unicode, không normalize; boolean phân biệt số; null phân biệt key vắng mặt. Số JSON được so theo giá trị toán học chính xác, không qua float làm mất chữ số; `1` và `1.0`, `0` và `-0` bằng nhau. Biểu diễn lexical gốc luôn nằm ở source record. Parser cần giữ số chính xác, hoặc báo không thể xử lý bằng lỗi hệ thống; không truncate hoặc âm thầm đổi số. Không nhận NaN/Infinity vì không phải JSON.

Mọi khác biệt giá trị sau chuẩn hóa đều tăng revision: text, khoảng trắng bên trong chuỗi, priority, null thành giá trị, thêm/xóa trường tùy chọn, đổi thứ tự actor/requirement/criterion/metric. Chỉ đổi thụt dòng, thứ tự key hoặc escape JSON tương đương thì không tăng. Input legacy thiếu version và input có `"schema_version":"1.0.0"` có thể cho cùng snapshot sau chuẩn hóa; mỗi run giữ provenance riêng.

So với **revision hiện hành**, không so với mọi lịch sử để tái sử dụng revision cũ. Nếu r3 trở lại nội dung r1, r3 vẫn là revision mới có parent r2. Không mang xác nhận S02 của r1 sang r3. Mọi revision mới yêu cầu downstream review sự thay đổi; S01 không tự xác định phần nào đổi nghĩa. Cách phân tích lại phần bị ảnh hưởng là công việc S02.

Snapshot, nguồn tạo snapshot và run tạo snapshot được giữ bất biến. Run gửi lại lưu `run.source` mới nhưng snapshot vẫn giữ `origin_source_id` và `created_by_run_id` cũ; nhờ đó biết cả nguồn khai sinh lẫn lần gửi hiện tại. Artifact output/version validator/timestamps/normalization/errors của một run không thuộc dữ liệu revision. Đổi validator hoặc revalidate dưới output contract khác không tự tạo revision nếu dữ liệu không đổi; vẫn cần run mới, và không tự coi validation cũ là kết quả của validator mới.

### 6.1 Cập nhật đồng thời

Kiểm tra ban đầu không thay kiểm tra cuối. Tại thời điểm quyết định và commit kết quả, đối chiếu lại `base_revision` với revision hiện hành; bước đối chiếu, so sánh dữ liệu và ghi kết quả phải nhất quán với nhau, không cho một update khác xen giữa làm kết luận dựa trên base cũ. Chưa chọn cơ chế khóa/giao dịch cụ thể.

- **Base còn hiện hành, input bằng hiện hành:** commit run/source record với `unchanged`, dùng lại snapshot. Không tăng revision hoặc đánh dấu base đã bị “tiêu thụ”; nhiều lần unchanged có thể cùng thành công nếu không có revision mới xen vào trước quyết định của chúng.
- **Base còn hiện hành, input khác hiện hành:** kiểm tra lại base gắn nguyên tử với commit revision mới. Chỉ một update tạo được revision kế tiếp từ base đó; update khác còn gửi base cũ nhận `REVISION_CONFLICT`.
- **Base đã lỗi thời:** trả conflict trước khi xét khả năng unchanged, kể cả payload gửi đến bằng nội dung revision mới. Không tự rebase hoặc đổi request sang base mới.

Một kết quả unchanged đã commit hợp lệ ở r1 vẫn đúng theo thời điểm đó nếu sau đó update khác tạo r2. Nó tiếp tục trỏ snapshot r1, không được trình bày là snapshot mới nhất vô thời hạn. Thứ tự ở đây là thứ tự quyết định/commit, không suy từ timestamp nhận request hay thứ tự response tới client.

Các tình huống sau là **minh họa chưa chạy**, độc lập với chuỗi sáu ví dụ ở mục 9. Mỗi tình huống bắt đầu từ r1; cả A và B gửi `base_revision = 1`. Payload r1 là clinic input; payload P là r1 chỉ đổi priority R1 thành `should` như ví dụ 06.

| Tình huống | Thứ tự quyết định/commit | Kết quả A và B | Revision cuối |
| --- | --- | --- | --- |
| A và B đều gửi r1 | A rồi B, không có update khác | Cả hai validated/unchanged; run/source riêng, cùng snapshot r1 | 1 |
| A và B đều gửi P, khác r1 | A tạo r2 trước khi B quyết định | A validated/new_revision; B rejected/REVISION_CONFLICT dù P bằng r2 | 2 |
| A gửi P, B gửi một thay đổi khác r1 | A tạo r2 trước | A validated/new_revision; B rejected/REVISION_CONFLICT, không ghi đè A | 2 |
| A gửi r1, B gửi P | A commit unchanged trước, B tạo r2 sau | A validated/unchanged r1; B validated/new_revision r2 | 2 |
| A gửi r1, B gửi P | B tạo r2 trước khi A quyết định | B validated/new_revision; A rejected/REVISION_CONFLICT | 2 |

Trong các trường hợp conflict trên, `checks.revision = failed`, `result_kind = null`, `snapshot = null`, handoff false/null; Error có `stage = revision`, `target = request`, `pointer = /base_revision`, `related_pointers = []`, `details = {"expected_revision": 2, "provided_revision": 1}`. Các check input trước đó passed theo giả định payload hợp lệ. Lần unchanged thành công không làm check revision của lần unchanged sau bị failed chỉ vì có run trước đã commit.

### 6.2 Retry khi mất phản hồi

Nếu trạng thái commit không rõ, phải đối soát, không khẳng định rollback. `run_id` do server cấp chỉ giúp khi client đã biết nó; nếu response đầu tiên mất hoàn toàn, client có thể chưa có run ID để tra cứu. **Trước khi triển khai API phải chốt cơ chế đối soát bằng định danh client biết trước hoặc idempotency key**, gồm phạm vi duy nhất, thời hạn lưu và cách xử lý cùng key nhưng payload khác. Bản đề xuất này chưa thêm trường hoặc tự chọn cơ chế đó.

Chưa có cơ chế này thì retry được coi là run mới: retry create có thể tạo spec khác nếu lần trước đã commit; retry update đã tạo revision có thể gặp base cũ và conflict. Điều đó không chứng minh lần trước thất bại. Không dùng nội dung giống nhau hoặc hành vi unchanged thay bảo đảm idempotency.

## 7 Validation và cấu trúc lỗi

### 7.1 Các lớp kiểm tra

`run.validation` có hai trường bắt buộc:

- `checks`: object có đúng `parse`, `schema`, `cross_field`, `revision`; mỗi giá trị là `passed`, `failed`, hoặc `not_run`.
- `errors`: mảng Error; `[]` chỉ khi không có lỗi. Không dùng mảng này chứa câu hỏi nghiệp vụ hoặc unknown hợp lệ.

`parse` kiểm tra JSON và duplicate object keys trước khi parser ghi đè mất dữ liệu. `schema` gồm gate schema version và schema input tham chiếu với phép kiểm tra nonblank tường minh ở mục 7.2. `cross_field` kiểm tra ID toàn cục và khoảng trắng quanh ID theo cùng tập W. `revision` kiểm tra request, spec tồn tại và base revision (bao gồm kiểm tra cuối cho cả unchanged và new_revision ở mục 6.1). Với create, revision check xác nhận mode và trường routing hợp lệ, chưa có revision mới cho đến commit. Nếu một lớp failed thì lớp sau để not_run; trong lớp đã chạy, thu thập các lỗi độc lập xác định được. Lỗi hệ thống có thể xảy ra dù các check dữ liệu đều passed.

### 7.2 Quy tắc cụ thể

| Kiểm tra | Quy tắc và phân loại |
| --- | --- |
| JSON lỗi/duplicate key | Chặn ở parse. Duplicate key không được chọn giá trị đầu/cuối và bỏ giá trị còn lại |
| Thiếu version | Root object thiếu key: resolved `1.0.0`, origin `legacy_default`, thêm normalization rồi validation đầy đủ |
| Version đúng | Chuỗi đúng `1.0.0`: origin `explicit`, resolved `1.0.0` |
| Version sai kiểu/null/rỗng/trắng/bao quanh bằng whitespace | `INVALID_SCHEMA_VERSION`, origin `unresolved`, resolved null; không sửa giá trị |
| Chuỗi version khác không trắng và không có whitespace bao quanh | `UNSUPPORTED_SCHEMA_VERSION`, origin `unresolved`, resolved null; không giả định tương thích |
| Root không phải object/parse lỗi | Origin unresolved, resolved null; không áp dụng default. Root sai kiểu là lỗi schema; parse lỗi thì schema not_run |
| ID trùng trong hoặc giữa FR/NFR/constraints | `DUPLICATE_REQUIREMENT_ID`; đối chiếu exact string toàn cục, phân biệt hoa thường; báo vị trí xuất hiện sau và vị trí trước |
| ID có whitespace ở đầu/cuối | `ID_SURROUNDING_WHITESPACE`; không trim. Whitespace nằm giữa ID được giữ nếu schema cho phép |
| ID/text/actor/criterion/chuỗi mô tả rỗng hoặc chỉ whitespace | Lỗi schema `EMPTY_OR_WHITESPACE`; không thay null; không đặt ràng buộc nonblank cho string tự do trong `constraint.value` |
| Actor trùng | Exact string như `uniqueItems` của schema: `DUPLICATE_ACTOR`; không tự gộp tên theo hoa thường/trim/Unicode-normalization |
| Actor gần giống do viết hoa/khoảng trắng/Unicode | Giữ nguyên nếu schema hợp lệ; chưa khẳng định là hai vai trò khác nghĩa. Đưa lựa chọn so trùng mạnh hơn ra audit, không âm thầm bổ sung rule |
| Metric thiếu/trùng/lạ | Schema kiểm tra đúng 4 phần tử, enum và unique; lỗi tương ứng `METRIC_COUNT`, `DUPLICATE_METRIC`, `INVALID_METRIC`. Không sort hoặc deduplicate |
| Priority sai enum/constraint không must | `INVALID_PRIORITY`; null hợp lệ cho FR/NFR, không hợp lệ cho constraint |
| Trường lạ | `UNKNOWN_FIELD` ở mọi object có `additionalProperties: false`; chặn và giữ nguyên nguồn, không strip. Không áp rule này bên trong `constraint.value` tự do |
| Thiếu trường bắt buộc | `MISSING_FIELD`; `schema_version` là ngoại lệ duy nhất được default. Báo pointer tới key thiếu |
| Null/[] hợp lệ | Không là lỗi; giữ dữ liệu cho S02 làm rõ. Không kết luận “đủ thông tin” vì errors rỗng |

**Quy tắc cụ thể của draft.2:** tập W gồm đúng 29 code point: **U+0009–U+000D, U+001C–U+001F, U+0020, U+0085, U+00A0, U+1680, U+2000–U+200A, U+2028–U+2029, U+202F, U+205F, U+3000**. Không tự mở rộng W theo phiên bản Unicode hay runtime. Quy tắc này cố định trong bản đề xuất, chưa có nghĩa toàn contract đã được duyệt.

1. **Nonblank:** sau kiểm tra kiểu string, phải có ít nhất một code point không thuộc W. Chuỗi rỗng hoặc mọi code point đều thuộc W nhận `EMPTY_OR_WHITESPACE` tại stage schema. Áp dụng cho đúng các vị trí Text có ràng buộc nonblank trong schema, bao gồm ID, text, title/context, actors, criteria, mô tả tùy chọn khi là string và constraint.kind; không áp vào string tự do trong constraint.value, không đổi chính sách nullable.
2. **Biên ID:** sau khi ID đã qua nonblank, code point đầu và cuối đều không thuộc W. Nếu vi phạm, nhận `ID_SURROUNDING_WHITESPACE` tại stage cross_field. Không trim để sửa, không cấm W ở giữa ID bằng quy tắc này. ID chỉ chứa W dừng tại schema, không sinh thêm lỗi biên.
3. **Version gate:** dùng chính W khi phân biệt chuỗi rỗng/toàn whitespace/có whitespace ở biên; các trường hợp đó là `INVALID_SCHEMA_VERSION`. Enum/version matching vẫn chính xác, không trim.

**Khác biệt với bản cũ và tham chiếu:** draft.1 bỏ sót U+001C–U+001F; draft.2 đưa cả bốn vào W, nên ID như `"\u001cR1"` bị từ chối, phù hợp hành vi ID được phản hồi từ validator tham chiếu. Mã tham chiếu kiểm tra biên bằng Python `str.strip()` và khai báo nonblank bằng `pattern=r"\S"` của Pydantic; mã đó chưa tự liệt kê tập code point cố định cho cả hai phép kiểm tra. Vì vậy không tuyên bố mọi hành vi nonblank của mọi engine đang trùng nhau, và không coi việc chỉ dùng lại pattern đó là đủ tương thích.

Đối với engine coi U+001C–U+001F là non-whitespace, chuỗi chỉ gồm các ký tự này có thể qua `\S`; draft.2 chủ ý từ chối. U+200B và U+FEFF **không thuộc W**: nếu không vi phạm quy tắc khác, chúng đủ làm chuỗi nonblank và không bị quy tắc biên ID từ chối. Đây là giới hạn cụ thể, không phải xác nhận chuỗi đó dễ đọc hoặc hợp nghĩa. Không thêm lệnh cấm ký tự vô hình khác trong bản này.

**Yêu cầu đối với implementation sau review:** phép nonblank và biên ID phải đánh giá trực tiếp theo W hoặc một biểu thức tương đương liệt kê chính xác các khoảng mã; không dùng `\s`, `\S`, `strip()`, `trim()` hay `isspace()` mặc định làm nguồn quyết định cuối. Adapter schema phải áp dụng ngữ nghĩa nonblank tường minh này cho các vị trí tương ứng với pattern `\S` trong schema tham chiếu; các keyword khác vẫn được giữ. Không kết hợp thêm một regex engine có tập whitespace khác như điều kiện veto độc lập, vì có thể chặn giá trị contract cho phép. Schema nguồn trên đĩa không sửa; validation record và output contract version chỉ rõ profile này. Nếu công cụ chưa thể áp dụng profile đúng, đó là lỗi cấu hình/xử lý (`failed`), không báo input hợp lệ bị rejected theo một engine tùy ý.

Schema gate không xử lý tiếp phiên bản không hỗ trợ. Với schema lỗi không tính thêm lỗi toàn cục từ dữ liệu sai kiểu. Metrics thiếu lẫn trùng có thể báo cả hai lỗi schema độc lập; không cần tạo lỗi xuyên trường giả. Khi cùng một nguyên nhân có nhiều nhánh `anyOf` báo lỗi, chuẩn hóa thành một Error hữu ích tại vị trí tương ứng, không trả nguyên traceback validator.

### 7.3 Error

| Trường | Kiểu | Ý nghĩa |
| --- | --- | --- |
| `code` | string | Mã ổn định, máy xử lý theo mã thay vì message |
| `stage` | enum | `parse`, `schema`, `cross_field`, `revision`, `system` |
| `target` | enum | `input`, `request`, `system` |
| `pointer` | string hoặc null | Pointer trong target; null nếu không xác định được vị trí cấu trúc |
| `related_pointers` | array of string | Các vị trí cùng target liên quan, ví dụ ID xuất hiện trước |
| `message` | string | Mô tả rõ lỗi; có thể bản địa hóa |
| `details` | object | Giá trị thực nhận, ràng buộc mong đợi hoặc thông tin xung đột cần sửa; `{}` nếu không cần |

Tất cả bảy trường bắt buộc. Mọi Error đều chặn handoff, không cần thêm boolean `blocking` dễ mâu thuẫn. `target=input` luôn chỉ nguồn của **run hiện tại** qua `run.source.source_id`; không chỉ nguồn tạo snapshot cũ. Pointer tới key thiếu không resolve được là chủ ý. Lỗi parse dùng pointer null và offset byte từ 0 nếu xác định được. Error không chứa stack trace hay toàn payload không cần thiết. Thứ tự errors xác định theo stage ở trên, pointer theo thứ tự chuỗi (null trước), rồi code; `related_pointers` xếp theo thứ tự chuỗi, loại trùng.

Quy ước `details` cho các nhóm mã; không gán `actual: null` cho key vắng mặt:

| Mã | Các trường details cần có |
| --- | --- |
| `INVALID_JSON`, `DUPLICATE_JSON_KEY` | `reason: string`; thêm `byte_offset: integer >= 0` nếu xác định được |
| `MISSING_FIELD` | `field: string` |
| `TYPE_MISMATCH` | `expected_types: string[]`, `actual_type: string` |
| `EMPTY_OR_WHITESPACE`, `ID_SURROUNDING_WHITESPACE` | `actual: string` |
| `INVALID_SCHEMA_VERSION`, `UNSUPPORTED_SCHEMA_VERSION` | `actual: JSON`, `supported: ["1.0.0"]` |
| `DUPLICATE_REQUIREMENT_ID` | `requirement_id: string` |
| `DUPLICATE_ACTOR`, `DUPLICATE_METRIC` | `value: string` |
| `METRIC_COUNT` | `expected: 4`, `actual: integer >= 0` |
| `INVALID_METRIC` | `actual: JSON`, `allowed: string[]` đủ bốn metrics |
| `INVALID_PRIORITY` | `actual: JSON`, `allowed: JSON[]` theo FR/NFR hoặc constraint |
| `UNKNOWN_FIELD` | `field: string` |
| `SCHEMA_VIOLATION` | `keyword: string`, `schema_pointer: string` cho rule chưa có mã chuyên biệt, ví dụ minItems của actors/FR |
| `INVALID_REQUEST` | `field: string`, `reason: string`; thêm `actual: JSON` khi trường sai có tồn tại, không thêm khi thiếu |
| `SPEC_NOT_FOUND` | `spec_id: string` |
| `REVISION_CONFLICT` | `expected_revision: integer`, `provided_revision: integer` |
| `PROCESSING_FAILED`, `PERSISTENCE_FAILED` | `reason: string` mô tả có kiểm soát, không nội dung stack trace |

Ưu tiên mã chuyên biệt hơn TYPE_MISMATCH/SCHEMA_VIOLATION cho version, priority và phần tử metric; cùng stage/target/pointer/code chỉ có một error. Mỗi lần trùng ID/actor/metric sau lần đầu tạo một error, `related_pointers` chứa vị trí lần đầu. Không tự sửa payload dựa trên `details`.

Để xác định “lần đầu” của ID, duyệt theo thứ tự cố định `functional_requirements` → `non_functional_requirements` → `constraints`, trong mỗi danh sách theo index tăng dần; không phụ thuộc thứ tự key của object. Actor/metric duyệt theo index mảng. Nếu request bị lỗi nhưng lớp input trước đó đã failed, revision check vẫn not_run; không tuyên bố request đã được kiểm tra chỉ vì đã ghi lại ngữ cảnh.

### 7.4 Đầu ra thất bại

Không trả `snapshot.input` một phần, không đưa snapshot hợp lệ của revision trước vào envelope bị từ chối để làm fallback. Nếu cần hiển thị revision trước, ứng dụng đọc riêng từ lịch sử. Request update có thể trỏ spec cũ nhưng không làm thay đổi tính invalid của lần gửi hiện tại.

Chỉ phát handoff sau khi commit snapshot/run/source cần thiết thành công. Nếu không thể ghi run thất bại vào kho, response vẫn báo failed nếu tiến trình còn trả được; không tuyên bố đã lưu audit record. Crash không có response cần tầng ứng dụng đối soát, không được diễn giải là validated.

## 8 Ranh giới chuyển sang S02

Consumer chỉ nhận khi output contract được hỗ trợ, `status = validated`, `errors = []`, cả bốn checks passed, snapshot khác null và có thể tra cứu, `handoff.eligible_for_s02 = true`, handoff ID khớp snapshot. Consumer kiểm tra nguồn tin cậy và tính nhất quán envelope, không chỉ tin một boolean do caller tự tạo. Các ví dụ ở đây không phải artifact chạy thật để nạp S02.

`null` đúng chỗ, NFR/constraints rỗng hoặc acceptance criteria rỗng không tự chặn S02. S02 cần dữ liệu đó để phát hiện thiếu sót, làm rõ nghiệp vụ, actors/actions/workflows và xây model. S01 không tự sinh câu hỏi “ai được hủy lịch” từ R2, không kết luận R3 đủ cấu hình benchmark và không tự gán quyền.

Validation thành công chỉ xác nhận cấu trúc theo contract và quy tắc xác định; không xác nhận requirements đúng nghiệp vụ, đủ thông tin, được người dùng duyệt hoặc sẵn sàng benchmark. Run record không là review record S02. Snapshot mới không kế thừa xác nhận phiên bản cũ.

## 9 Ví dụ JSON minh họa chưa chạy

Các file trong [docs/examples/s01](examples/s01/) là tài liệu minh họa đầy đủ envelope, biên soạn theo đề xuất; không phải fixtures đã được test, không phải output của code S01 và chưa được audit. Run IDs, source IDs, snapshot IDs và timestamps là giả lập. `validator_version = illustration-only` áp dụng riêng minh họa. Source ID trong ví dụ chỉ liên hệ tới các payload mô tả dưới đây, không đại diện kho nguồn đã triển khai.

| File | Input và ngữ cảnh giả định | Kết quả minh họa |
| --- | --- | --- |
| [01 valid clinic](examples/s01/01-valid-clinic.output.json) | Payload chính xác từ clinic-input.example.json; mode create | Spec mới revision 1, R1–R4 priority null; unknowns nguyên trạng |
| [02 missing schema version](examples/s01/02-missing-schema-version.output.json) | Cùng payload, bỏ đúng key schema_version; update spec trên, base 1 | Thêm version vào bản chuẩn hóa; unchanged, snapshot r1 giữ nguồn từ run 001 |
| [03 invalid duplicate ID](examples/s01/03-invalid-duplicate-id.output.json) | Từ clinic input, đổi /non_functional_requirements/0/id từ R3 thành R1; update base 1 | Schema passed, cross_field failed; không snapshot/handoff |
| [04 invalid duplicate metric](examples/s01/04-invalid-duplicate-metric.output.json) | Từ clinic input, đổi metric index 3 thành response_time_p95; update base 1 | Schema failed vì trùng, thiếu scaling_gain là hệ quả; không chạy cross_field/revision |
| [05 unchanged resubmission](examples/s01/05-unchanged-resubmission.output.json) | Gửi lại nguyên clinic input; update base 1 | Run/source mới; snapshot r1, origin_source và created_by_run giữ nguyên |
| [06 next revision](examples/s01/06-next-revision.output.json) | Từ clinic input, chỉ đổi /functional_requirements/0/priority từ null thành should; update base 1 | Revision 2, parent r1; không tự coi thay đổi đã được nghiệp vụ xác nhận |

Các source record giả định tương ứng lần lượt là `src-demo-001` đến `src-demo-006`; run tương ứng `run-demo-001` đến `run-demo-006`. Bản 03/04 bị từ chối nên không đổi current revision; bản 02/05 unchanged; bản 06 mới tăng lên 2. Thay đổi priority ở bản 06 **chỉ là thao tác giả định do người dùng gửi**, không sửa ví dụ nguồn và không chốt priority R1 cho dự án.

Ở bản 01, dữ liệu đúng cấu trúc vẫn chưa trả lời quyền đặt/hủy lịch, phạm vi phòng khám của nhân viên và tải vận hành. Đây là các điểm đã nêu trong báo cáo để S02 làm rõ, không phải phát hiện do S01/LLM đã chạy. Bản 02 minh họa rõ source của lần gửi lại khác source đã tạo snapshot; kiểm toán legacy normalization phải xem run 002, không sửa provenance r1.

## 10 Bảng tình huống kiểm thử dự kiến

**Chỉ là kế hoạch để audit; chưa viết hoặc chạy tests.** Input nền là clinic input trừ khi ghi khác. “Giữ revision” giả định đã có r1; lỗi ở create không tạo spec/snapshot.

| Input hoặc tình huống | Kết quả mong đợi | Quy tắc được kiểm tra |
| --- | --- | --- |
| Clinic input nguyên bản, create | validated, new_spec r1; giữ mọi null và R1–R5 | Schema hợp lệ không đồng nghĩa đủ nghiệp vụ |
| Bỏ schema_version, update base 1 | validated unchanged; đúng một normalization | Chỉ default khi thiếu key |
| Version null, số, rỗng, bao quanh whitespace | rejected INVALID_SCHEMA_VERSION | Không sửa giá trị sai thành mặc định |
| Version 2.0.0 | rejected UNSUPPORTED_SCHEMA_VERSION | Không áp schema 1 cho version chưa hỗ trợ |
| JSON cú pháp sai, NaN, Infinity | rejected INVALID_JSON; snapshot null | Parse trước validation, không handoff |
| JSON có hai key text trong một requirement | rejected DUPLICATE_JSON_KEY | Không làm mất dữ liệu bằng overwrite |
| Root là array/null | rejected TYPE_MISMATCH, không legacy default | Root phải là object |
| ID trùng cùng nhóm và giữa hai nhóm | rejected DUPLICATE_REQUIREMENT_ID với hai vị trí | Unique toàn cục, không chỉ uniqueItems |
| ID " R1", "R1 ", NBSP bao quanh | rejected ID_SURROUNDING_WHITESPACE ở cross_field | Không trim ID; dùng W cố định |
| Với từng code point w trong 29 phần tử W: ID w + "R1" hoặc "R1" + w | Schema nonblank passed; cross_field rejected ID_SURROUNDING_WHITESPACE | Bao phủ đầy đủ W ở cả hai biên, không phụ thuộc strip mặc định |
| ID `"\u001cR1"`, `"R1\u001f"` | rejected ID_SURROUNDING_WHITESPACE | Sửa sai khác ID của draft.1 với tham chiếu |
| Với từng w trong W: text/actor/criterion/ID chỉ chứa w; chuỗi hỗn hợp toàn W; chuỗi rỗng | rejected EMPTY_OR_WHITESPACE ở schema; cross_field not_run | Nonblank theo W, kể cả U+001C–U+001F; không sinh hai lớp lỗi cho ID trắng |
| ID `"R\u001c1"` | Giữ nếu không vi phạm rule khác; khác R1 nên có thể tạo revision mới | W bên trong ID không bị rule biên cấm |
| Text `"\u001cNội dung\u001f"` | Giữ nguyên nếu các trường khác hợp lệ | Nội dung nonblank không bị trim hoặc áp rule biên ID |
| Text chỉ chứa U+200B hoặc U+FEFF; ID có chúng ở đầu/cuối | Qua nonblank và rule biên W nếu không vi phạm rule khác | Hai code point này nằm ngoài W, không cho regex runtime tự veto |
| JSON string `"\\u001c"` giải mã thành sáu ký tự literal, so với JSON string `"\u001c"` | Literal là nonblank; chuỗi thứ hai giải mã thành một code point thuộc W và bị chặn nếu đứng một mình | Kiểm tra code point sau parse, không so cách viết JSON |
| Version `"\u001c1.0.0"` hoặc chỉ U+001F | rejected INVALID_SCHEMA_VERSION, không default/trim | Gate version dùng cùng W |
| Engine áp sai nonblank, ví dụ tự cho U+001C là nonblank hoặc chặn U+FEFF ngoài W | Không được kết luận theo engine; implementation phải áp profile, nếu chưa hỗ trợ thì failed PROCESSING_FAILED | Contract quyết định kết quả; khác biệt adapter là lỗi hệ thống |
| ID "R 1" hoặc R1/r1 khác nhau | Giữ nếu hợp lệ và không trùng exact | Không thêm prefix, cấm whitespace nội bộ hoặc case-fold ngoài đặc tả |
| Text có khoảng trắng bao quanh nhưng không trắng hoàn toàn | Giữ nguyên chuỗi; update khác text cũ thì revision mới | Không trim nội dung |
| Text/criterion/actor chỉ whitespace | rejected EMPTY_OR_WHITESPACE | Nội dung bắt buộc không trắng |
| Actors trùng exact | rejected DUPLICATE_ACTOR | Schema uniqueItems |
| Actors chỉ khác hoa thường/khoảng trắng | Giữ theo đề xuất exact; chưa kết luận khác vai trò | Chính sách so trùng còn cần audit |
| FR rỗng; NFR/constraints rỗng | FR rỗng bị chặn; NFR/constraints rỗng riêng lẻ được giữ | Phân biệt minItems và unknown hợp lệ |
| Criterion [] so với bỏ key acceptance_criteria | [] hợp lệ, thiếu key bị MISSING_FIELD | Không tự điền required |
| Hai criterion giống nhau | Giữ cả hai, hai pointer khác nhau | Không deduplicate tiêu chí |
| Thiếu/trùng/metric lạ hoặc 5 metrics | rejected với mã count/duplicate/invalid phù hợp | Đủ đúng 4 metrics, mỗi metric một lần |
| Constraint priority null/should | rejected INVALID_PRIORITY | Constraint bắt buộc must |
| Key lạ ở root, requirement hoặc details | rejected UNKNOWN_FIELD tại key tương ứng | Không strip field lạ |
| Object có key tùy ý trong constraint.value | Giữ nếu JSON hợp lệ | Không áp additionalProperties sai phạm vi |
| project_details/details/constraint là null hoặc vắng mặt | Giữ nguyên mỗi biểu diễn theo schema | Không điền các default annotation |
| Thiếu operating_conditions.expected_load | rejected MISSING_FIELD dù null là giá trị hợp lệ | Required khác nullable |
| priority null/conditions null | validated, không sinh lỗi nghiệp vụ | Unknown hợp lệ chuyển S02 |
| Submit lại nguyên bản, update base hiện hành | Run/source mới, unchanged, không đổi snapshot origin | Phân biệt lần chạy với revision |
| Chỉ đổi thứ tự key/thụt dòng/escape tương đương | unchanged; nguồn thô của run khác | So sánh giá trị JSON |
| Số rất lớn trong constraint.value, hoặc 1 so với 1.0 | Giữ giá trị chính xác; 1 và 1.0 không tạo revision | Không mất chính xác số; nguồn vẫn giữ lexical |
| Đổi priority, text hoặc null thành giá trị | Revision +1, parent đúng; snapshot cũ bất biến | Mọi thay đổi dữ liệu đều versioned |
| Thêm/xóa/reorder requirements hoặc criteria | Revision +1, pointer cũ vẫn đọc snapshot cũ | Không retarget index xuyên revision |
| Đảo metric hoặc actor | Revision +1 | Mảng có thứ tự |
| Thêm trường tùy chọn với null thay vì vắng mặt | Revision +1 | Missing khác null |
| Đổi ID, chuyển nhóm, tái xuất hiện ID | Giữ payload hợp lệ; revision mới, không tự nối mapping cũ | Không suy luận rename/identity ngữ nghĩa |
| r3 có nội dung giống r1 sau r2 | Tạo r3 parent r2; không quay về r1 | Lịch sử tuyến tính, không tái dùng revision cũ |
| Cùng input nhưng mode create mới | Spec khác revision 1 | Không gộp đặc tả theo nội dung |
| Update không có spec/base, spec lạ | rejected INVALID_REQUEST/SPEC_NOT_FOUND | Ngữ cảnh cập nhật tách khỏi input |
| Base cũ, kể cả payload bằng revision hiện hành | rejected REVISION_CONFLICT; không tự đổi thành unchanged | Kiểm tra base trước so sánh nội dung |
| Hai update cùng base 1, cả hai bằng r1, không có revision mới xen vào | Cả hai validated/unchanged; hai run/source riêng, cùng snapshot r1; current vẫn 1 | Unchanged không tiêu thụ base |
| Hai update cùng base 1, cùng payload P khác r1 | Một new_revision r2; lần quyết định sau rejected REVISION_CONFLICT dù payload bằng r2 | Chỉ một revision mới từ một base; kiểm tra lại nguyên tử tại commit |
| Hai update cùng base 1, hai thay đổi khác nhau | Một new_revision r2; bên thua conflict, không ghi đè | Không last-write-wins |
| Unchanged commit trước update tạo revision mới | Cả hai thành công; unchanged trỏ r1, update trỏ r2 | Run commit không thay đổi head không gây conflict giả |
| Update tạo r2 trước quyết định cuối của request so với r1 | Request base 1 bị conflict dù trước đó đã so sánh là không đổi | Kiểm tra cuối áp dụng cho cả unchanged; không dùng kết quả đọc cũ |
| Response mất trước khi client biết run_id do server cấp | Chưa có bảo đảm retry an toàn; phải chốt client-known ID/idempotency trước API | Run ID chỉ có ở response không đủ để đối soát mất toàn bộ response |
| Lỗi lưu sau các check passed | failed, snapshot null, handoff false; đối soát nếu commit chưa rõ | Không phát dữ liệu chưa commit |
| Envelope lỗi hoặc handoff ID không khớp snapshot | Consumer từ chối | S02 không chỉ tin boolean |
| Validator đổi nhưng dữ liệu không đổi | Run khác, revision giữ nguyên sau validation thành công | Phiên bản code khác revision dữ liệu |

## 11 Điểm còn cần quyết định và bàn giao audit

Agent audit cần đối chiếu các lựa chọn sau với căn cứ đã chốt; chưa có quyết định nào trong danh sách này được ghi là đã chấp nhận:

1. Chấp nhận envelope và ba trạng thái; snapshot inline cùng nguồn thô lưu riêng; nội dung/kiểu trường có đủ mà không thừa metadata không.
2. Chấp nhận chỉ thêm version khi thiếu, giữ khác biệt missing/null và không trim dữ liệu. Review profile W 29 code point ở draft.2, gồm U+001C–U+001F và phép nonblank tường minh thay ngữ nghĩa regex mặc định; xác nhận giới hạn U+200B/U+FEFF ngoài W. So trùng actor vẫn exact; nếu muốn mạnh hơn phải chốt rule riêng, không sửa schema nguồn trong đợt này.
3. Chấp nhận revision theo mọi thay đổi giá trị/mảng và so số chính xác; chấp nhận không tăng revision vì thứ tự key/serialization hoặc explicit so với legacy schema version.
4. Chấp nhận reference criterion theo snapshot/index, không có identity bền qua revision. Nếu cần identity bền, thiết kế edit mapping tường minh trước khi implement, không ghép bằng LLM/text.
5. Review các lịch cập nhật ở mục 6.1: nhiều unchanged được cùng thành công khi base còn hiện hành; chỉ một revision mới được tạo từ một base; request base cũ luôn conflict. Trước triển khai API phải chốt đối soát bằng định danh client biết trước hoặc idempotency key theo mục 6.2, không dựa riêng vào run_id có trong response có thể bị mất.
6. Chấp nhận taxonomy lỗi, nguyên tắc không trả partial snapshot và điều kiện handoff. Review hành vi persistence failure/commit chưa rõ để không tuyên bố lịch sử đã lưu khi chưa có bằng chứng.
7. Chốt vị trí và retention nguồn/snapshot/run, phương thức nhận form/API bảo toàn dữ liệu, cùng chiến lược ID và phiên bản validator khi chọn cách triển khai. Đây là quyết định kỹ thuật còn mở, không chọn stack trong tài liệu này.

Người dùng vẫn quyết định nghiệp vụ và phạm vi. Các câu hỏi phòng khám được giữ cho S02, không phải điều kiện để tự điền requirements ở S01. Audit contract không đồng nghĩa người dùng đã xác nhận nội dung của bất kỳ snapshot minh họa nào.

Phạm vi bàn giao: một đề xuất contract và sáu envelope JSON minh họa; không implementation, prompts, executable tests hoặc dependencies. Các tình huống ở mục 10 là kỳ vọng cần review, không phải bằng chứng tests passed hay chất lượng hệ thống. Hạn chế chủ yếu: criterion chưa nối identity xuyên revision, persistence/API chưa thiết kế chi tiết, chính sách whitespace/actor cần review. Không sửa AGENTS.md, schema input hoặc dataset, không khởi tạo Git.
