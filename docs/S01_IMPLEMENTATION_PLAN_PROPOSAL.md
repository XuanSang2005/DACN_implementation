# Đề xuất kế hoạch implementation S01

**Trạng thái: proposed — chưa audit/chưa được duyệt.** Tác giả đề xuất: Astra. Ngày: 13/10/2026.

Khuyến nghị bản đầu là **CLI local trên CPython 3.13, dùng SQLite cho nguồn, run và snapshot; validation bằng jsonschema với profile W của contract; parse số bằng Decimal và serialize bằng simplejson**. Kế hoạch triển khai theo từng đợt có kiểm thử độc lập và bằng chứng để audit. Tất cả cấu trúc code, lệnh và tests dưới đây là dự kiến, chưa được tạo hoặc chạy.

## 1 Baseline và phạm vi

- Đã đọc [AGENTS.md](../AGENTS.md) và [contract S01 0.1.0-draft.2](S01_OUTPUT_CONTRACT_PROPOSAL.md). Theo thông tin người dùng cung cấp trong lượt này, agent audit đã rà soát draft.2 và không còn phát hiện chặn trong phạm vi thiết kế. Dùng đúng bản đó làm baseline; không sửa trạng thái hay nội dung file contract trong nhiệm vụ này.
- SHA-256 của file contract được đọc: `39027bfdeeed0c880ccda35cd307eaf4d9729031bf0f80bfe8b8758b03eeb926`. Digest nhận diện bản tài liệu, không phải hash dữ liệu dùng để tính revision.
- S01 tiếp nhận JSON có cấu trúc, bảo toàn nguồn, chỉ thêm schema_version khi thiếu, kiểm tra, quản lý revision và xuất envelope. Thành công chỉ xác nhận cấu trúc theo contract.
- Ngoài phạm vi bản đầu: API/HTTP, form/UI, S02, LLM, KB, diagram, đánh giá ngữ nghĩa hoặc benchmark kiến trúc. Các giá trị source.kind khác json_file vẫn thuộc contract nhưng chưa có adapter tương ứng trong bản CLI.
- Dataset bên ngoài chỉ đọc. Chỉ chụp payload thực sự được gửi vào kho S01; không sao chép dataset. Các đoạn lệnh trong tài liệu không phải chỉ thị đã thực thi.

Các quy tắc contract là căn cứ đã có. Stack, tổ chức code, schema lưu trữ, CLI, receipt và kế hoạch kiểm thử bên dưới là **lựa chọn kỹ thuật đề xuất**, cần review trước implementation. Chưa phát hiện thêm mâu thuẫn chặn thiết kế trong quá trình lập kế hoạch; các giới hạn triển khai cần quyết định được liệt kê ở mục 11.

## 2 Stack khuyến nghị và căn cứ

### 2.1 Thành phần cần dùng

| Thành phần | Khuyến nghị | Mục đích và trạng thái xác minh |
| --- | --- | --- |
| Runtime | CPython **3.13.x**, bản có GIL thông thường | Chọn một minor version cho bản đầu; chốt patch cụ thể và nguồn phân phối ở đợt 1 trước chạy code. Chưa kiểm tra runtime trên máy dự án; không giả định python3 hiện có đúng phiên bản |
| Parse | json trong standard library, với object_pairs_hook, parse_int, parse_float, parse_constant | Có điểm can thiệp trước khi mất duplicate keys và trước chuyển số sang float; chi tiết mục 3 |
| Số | decimal.Decimal trong standard library | Cả token số nguyên lẫn thập phân của input đi thẳng từ chuỗi token sang Decimal |
| Schema validation | **jsonschema 4.26.0**, Draft202012Validator mở rộng có giới hạn | Bám schema nguồn; thay đúng phép nonblank theo W và cấu hình type checker; không dựng lại toàn schema bằng model khác |
| Serialization | **simplejson 4.2.0** | Xuất Decimal thành JSON number chính xác, không thành string hoặc float |
| Persistence | SQLite qua sqlite3 của CPython | Một database local, transaction tường minh; không thêm ORM hoặc database server |
| CLI/config/ID | argparse, pathlib, tomllib, uuid, datetime, hashlib trong standard library | CLI, đọc config, UUIDv4, thời gian UTC và nhận diện schema/build |
| Kiểm thử | **pytest 9.1.1**, standard library subprocess/multiprocessing | Unit, contract, integration, CLI và hai process cạnh tranh trên cùng DB tạm |
| Môi trường và đóng gói | venv, pip; một build backend khi đóng gói ở đợt 1 | Chỉ là công cụ phát triển/đóng gói, không đưa framework web vào runtime |

Hai dependency runtime trực tiếp là jsonschema và simplejson; pytest là dependency kiểm thử trực tiếp. Các dependency bắc cầu cần được resolver ghi đầy đủ khi khóa môi trường ở đợt 1, không tuyên bố tổng môi trường chỉ có ba package. Chưa tạo dependency file, lockfile, virtualenv hoặc cài package.

Phiên bản package trên là **ứng viên được đề xuất**, đã đối chiếu trang phát hành chính thức: [jsonschema](https://pypi.org/project/jsonschema/), [simplejson](https://pypi.org/project/simplejson/), [pytest](https://pypi.org/project/pytest/). Khả năng cài và phối hợp trên macOS/runtime mục tiêu chưa được chạy xác minh. Chốt exact patch Python, bản SQLite được link và hashes của dependencies trong manifest trước implementation; không để môi trường tự nâng version khi tái lập.

### 2.2 So sánh các phương án đáng cân nhắc

| Phương án khác | Trade-off so với khuyến nghị |
| --- | --- |
| Pydantic làm đầu vào chính | Thuận tiện cho typed models, nhưng cần quản lý thêm defaults/coercion/serialization và một bản model có thể lệch schema. Validator tham chiếu dùng Pydantic là nguồn đối chiếu, không bắt buộc implementation phải dùng lại toàn bộ cơ chế đó |
| Chỉ standard library, tự viết validator và encoder | Ít dependency hơn nhưng tăng code phải audit, đặc biệt JSON Schema và xuất Decimal. Chọn hai thư viện nhỏ để giảm phần tự triển khai này |
| PostgreSQL | Hợp lý khi cần nhiều writer hoặc dịch vụ dùng chung; bản local hiện chưa cần vận hành server và migrations phức tạp hơn |
| Nhiều file JSON độc lập | Dễ nhìn nhưng phải tự giải quyết khóa, cập nhật head và recovery nhiều file. SQLite gom các bản ghi liên quan vào cùng transaction; file export chỉ là bản xuất |
| API ngay từ đầu | Thêm tầng vận chuyển, lỗi mất response và idempotency. Bản này chỉ đề xuất CLI; nếu mở API phải có thiết kế adapter riêng đáp ứng mục 6.2 của contract trước implementation, không coi CLI receipt là lời giải idempotency HTTP |

## 3 Chứng minh khả năng đáp ứng contract ở mức thiết kế

Đây là lập luận thiết kế dựa trên API được công bố; bằng chứng thực nghiệm sẽ nằm ở các đợt implementation. Không dùng ví dụ tài liệu làm bằng chứng tests passed.

### 3.1 Duplicate keys và parse

Đọc file input đúng một lần dưới dạng bytes, giữ bản đó làm nguồn. json cung cấp object_pairs_hook nhận danh sách cặp key/value trước khi tạo dict; parse_int và parse_float nhận chuỗi token số; parse_constant có thể từ chối NaN/Infinity. Các mặc định không được dùng nguyên trạng. [Python json](https://docs.python.org/3.13/library/json.html).

Thiết kế callback duyệt từng danh sách cặp, phát hiện key đã xuất hiện rồi mới tạo dict khi không trùng. Callback áp dụng cho mọi object, kể cả object trong array và constraint.value. Key đã giải mã được so exact, nên key viết bằng escape tương đương vẫn bị nhận diện trùng. Duplicate ở hai object khác nhau không phải lỗi. Không có bước tạo dict mặc định trước callback hoặc parse lại bằng parser khác rồi mất duplicate.

Nếu phát hiện duplicate, dừng parse với DUPLICATE_JSON_KEY; pointer null được contract cho phép vì hook không cung cấp vị trí nguồn đầy đủ. details.reason nêu key trùng bằng biểu diễn an toàn. Không tự chế byte_offset từ index ký tự; chỉ thêm offset khi có ánh xạ byte chắc chắn. Lỗi cú pháp là INVALID_JSON; lớp phụ thuộc not_run. Nguồn thô lỗi vẫn được lưu nếu persistence hoạt động.

### 3.2 Số chính xác trong toàn bộ vòng đời

Đề xuất cả parse_int và parse_float dùng Decimal từ **chuỗi token**, không đi qua int/float trung gian. Như vậy còn tránh phụ thuộc giới hạn chuyển chuỗi số nguyên sang int của parser mặc định. Metadata do hệ thống tạo, như revision, vẫn dùng integer; không biến số trong input thành kiểu string để tránh mất chính xác.

Decimal tạo từ chuỗi giữ số chữ số đầu vào; context precision tác động khi tính toán, không cắt số ngay khi xây giá trị. Vì vậy S01 không áp unary plus, normalize, quantize hoặc phép toán làm tròn lên payload. [Python decimal](https://docs.python.org/3.13/library/decimal.html).

Khi ghi snapshot/envelope, simplejson với use_decimal=true xuất Decimal thành JSON number. Chọn tường minh allow_nan=false, ignore_nan=false, bigint_as_string=false, int_as_string_bitcount=null và skipkeys=false; không có fallback default=str. Trước serialize, kiểm tra cây chỉ chứa các kiểu JSON được cho phép, số phải hữu hạn và không có float do code vô tình đưa vào. Phần hỗ trợ Decimal đã được đối chiếu cả [tài liệu simplejson](https://simplejson.readthedocs.io/en/latest/) và [mã nguồn tag 4.2.0](https://raw.githubusercontent.com/simplejson/simplejson/v4.2.0/simplejson/__init__.py). Trang tài liệu hiện mang nhãn 3.19.1, nên không dựa riêng nhãn latest để khẳng định tương thích version mới.

Lưu nguồn gốc bằng BLOB; lưu JSON chuẩn hóa/envelope bằng TEXT đã serialize chính xác. Không đưa constraint.value qua cột REAL/NUMERIC, SQLite JSON extraction hoặc ORM tự đổi kiểu. Đọc lại TEXT bằng cùng parser chính xác. Dữ liệu số đi theo chuỗi: token nguồn → Decimal → JSON number dạng text → Decimal, không có float ở giữa. Nguồn BLOB giữ cả biểu diễn lexical như 1.00 hoặc 1e0.

So revision bằng bộ so sánh cây có phân loại kiểu: boolean riêng; nhóm số finite Decimal/int so giá trị chính xác; string exact; array theo vị trí; object theo tập key và giá trị. Không dùng trực tiếp phép bằng dict/list của Python làm toàn bộ chuẩn so sánh, vì boolean có thể bị đồng nhất với 0/1. 1 và 1.0 bằng nhau, -0 và 0 bằng nhau; true khác 1; key thiếu khác key có null. Không dùng hash hoặc JSON string đã serialize để quyết định revision.

Giới hạn của Decimal, parser, bộ nhớ hoặc SQLite vẫn có thể bị chạm với input cực lớn. Khi không thể giữ chính xác một JSON number hợp lệ, trả failed/PROCESSING_FAILED hoặc PERSISTENCE_FAILED theo nơi lỗi; không cắt chữ số, biến thành null hay kết luận INVALID_JSON chỉ vì công cụ thiếu khả năng. NaN/Infinity là cú pháp số không hợp lệ và phải bị rejected. Ngưỡng tài nguyên cụ thể là cấu hình vận hành cần review, không âm thầm thêm constraint nghiệp vụ.

### 3.3 Không biến đổi dữ liệu và áp dụng W

jsonschema không tự điền default trong instance theo cách dùng thông thường. Kế hoạch không cài extension điền default. Chỉ module normalization tạo bản sao root và thêm schema_version khi key vắng mặt; không sửa tree nguồn hay tự thêm trường tùy chọn. [jsonschema FAQ](https://python-jsonschema.readthedocs.io/en/stable/faq/).

Draft202012Validator sẽ được mở rộng bằng API validators.extend, thay handler pattern cho đúng pattern nonblank của schema baseline. Cơ chế này thay handler cũ hoàn toàn, nên có thể tránh chạy thêm regex mặc định như một điều kiện veto. TypeChecker có thể cấu hình riêng cho Decimal và boolean. Đây là khả năng thư viện đã xác minh ở tài liệu, chưa phải adapter đã được kiểm thử. [Mở rộng validator](https://python-jsonschema.readthedocs.io/en/stable/creating/), [Type checking](https://python-jsonschema.readthedocs.io/en/stable/validate/).

Quy tắc adapter dự kiến:

- Tập W lấy đúng 29 code point của draft.2: U+0009–U+000D, U+001C–U+001F, U+0020, U+0085, U+00A0, U+1680, U+2000–U+200A, U+2028–U+2029, U+202F, U+205F, U+3000.
- Handler pattern nonblank: nếu instance là string, có ít nhất một code point ngoài W mới đạt. Không gọi lại handler regex mặc định cho pattern này; không quét mọi string trong cây, vì constraint.value là vùng JSON tự do.
- Cross-field: ID đã qua schema mới xét code point đầu/cuối thuộc W, uniqueness toàn cục theo thứ tự FR → NFR → constraints. Version gate dùng cùng W. Không trim, case-fold hoặc Unicode-normalize.
- Giữ nguyên các keyword khác của schema; các lỗi minLength/pattern cùng nguyên nhân được gom theo taxonomy baseline. Nếu schema package xuất hiện pattern ngoài profile dự kiến, báo lỗi cấu hình để review, không âm thầm bỏ qua hoặc chọn engine khác.
- Type checker cho number chỉ nhận finite Decimal/int và loại boolean; integer dựa giá trị nguyên chính xác, không ép chuỗi thành số. Input schema hiện không ràng buộc numeric domain trong constraint.value, nhưng bộ so sánh vẫn cần phân biệt kiểu ở đó.
- Không tái tạo object bằng constructor có default. Không lọc key lạ trước validation. Missing/null, giá trị chuỗi gốc và thứ tự array được giữ xuyên suốt.

U+200B/U+FEFF trong string được xử lý như ký tự ngoài W theo baseline. Adapter không thêm điều kiện dễ đọc hoặc cấm ký tự vô hình; khi encoding output có khó khăn, escape JSON tương đương được phép, không thay nội dung. Đề xuất output ensure_ascii=true để giữ cả các trường hợp escape đặc biệt qua kênh UTF-8; đây chỉ là biểu diễn JSON, không đổi text sau decode.

## 4 Các phần xử lý và ranh giới

| Bước | Trách nhiệm | Input và output nội bộ cần thiết |
| --- | --- | --- |
| Tiếp nhận/chụp nguồn | CLI đọc bytes một lần, tạo ngữ cảnh request riêng, cấp run/source ID và thời điểm nhận | Bytes gốc, source.kind/label, request gốc; chưa có snapshot |
| Parse | Duplicate keys, cú pháp, số chính xác; không xử lý nghiệp vụ | Cây JSON hoặc lỗi parse, nguồn gốc vẫn giữ |
| Nhận diện version | Root/type/version gate theo contract | input_version; không default cho null/sai version |
| Chuẩn hóa | Chỉ thêm version khi thiếu trên bản làm việc | Cây chuẩn hóa và danh sách normalizations |
| Schema checks | Schema đóng gói cộng profile W; tổng hợp lỗi độc lập trong lớp | checks.schema và errors có pointer đúng |
| Cross-field checks | ID toàn cục, biên ID; không suy luận tên actor/nghiệp vụ | checks.cross_field và errors |
| Request/base revision | Kiểm tra mode/spec/base; persistence cung cấp head trong transaction cuối | Request hợp lệ, current snapshot hoặc lỗi revision |
| So sánh hiện hành | Hàm thuần quyết định unchanged/new_revision từ hai cây đã parse chính xác | Quyết định không chứa thao tác SQL hoặc xuất CLI |
| Commit | Repository phối hợp một transaction, cấp snapshot/spec ID khi cần, kiểm tra invariants cuối | Envelope đã lưu cùng nguồn, snapshot và head nhất quán |
| Output | CLI chỉ xuất envelope đã hoàn tất, tách log; đọc lại được theo run ID | JSON stdout hoặc export; exit code theo mục 7 |

Parse/schema/cross-field/revision giữ nguyên thứ tự baseline. Lớp failed làm lớp phụ thuộc not_run. Lỗi input/request là rejected; lỗi cấu hình/tool/persistence là failed. Nếu lỗi trước khi dựng đủ dữ liệu cho phần nào, không đánh dấu phần đó passed. Không dùng snapshot cũ làm fallback trong envelope thất bại.

Module validation trả kết quả và lỗi có cấu trúc; không đọc CLI flags, ghi DB, sinh ID hay gọi đồng hồ. Module revision chứa phép so sánh và quyết định thuần; không tự đọc head bên ngoài transaction. Service điều phối trình tự, metadata và envelope. Repository nhận quyết định trong transaction và chịu trách nhiệm commit. CLI chuyển lỗi vận chuyển/cấu hình lệnh sang thông báo phù hợp, không lặp lại logic validation.

Error adapter dựa vào validator, path, schema_path và context có cấu trúc; không parse message thư viện để suy ra mã lỗi. Với required/additionalProperties, đối chiếu key thực tế và schema để lấy đúng pointer; lỗi trùng metric/actor cần xác định vị trí trước/sau theo contract. Gộp anyOf rồi sort/deduplicate bằng quy tắc baseline, không phụ thuộc thứ tự thư viện trả lỗi. [jsonschema ValidationError](https://python-jsonschema.readthedocs.io/en/stable/errors/).

### 4.1 Cây thư mục dự kiến

Chỉ là sơ đồ trong tài liệu; các file dưới đây chưa được tạo:

```text
docs/
  S01_OUTPUT_CONTRACT_PROPOSAL.md
  S01_IMPLEMENTATION_PLAN_PROPOSAL.md
  examples/s01/
src/dacn_s01/
  __init__.py
  __main__.py
  cli.py
  codec.py
  validation.py
  revision.py
  service.py
  repository.py
  schemas/input/1.0.0/system-input.schema.json
  schemas/input/1.0.0/PROVENANCE.md
tests/
  unit/
  contract/
  integration/
  e2e/
  fixtures/s01/
pyproject.toml
requirements.lock
requirements-dev.lock
```

Không cần plugin system, generic event bus, ORM hoặc interface cho nhiều database ở bản đầu. Ranh giới giữa service và repository có thể là các hàm nhỏ có kiểu dữ liệu rõ ràng; chỉ thêm abstraction nếu giúp kiểm thử transaction/failure mà không che giấu đường đi dữ liệu.

### 4.2 Đóng gói schema

Ở đợt implementation được giao sau này, đưa **bản sao nguyên byte của riêng artifact schema đã chốt** vào package resource version 1.0.0; ghi nguồn, ngày, SHA-256 và các quy tắc bổ sung thuộc output contract trong PROVENANCE.md. Không export lại schema từ model Pydantic để tránh drift. Lượt hiện tại chưa sao chép schema hoặc dataset.

Runtime đọc resource bằng đường dẫn package, không dùng đường dẫn máy cá nhân. Hash trên byte schema thực dùng đi vào run.input_schema_sha256; archive artifact theo hash trong kho local để sau này vẫn đối chiếu được nếu package đổi. Chỉ resolve các tham chiếu nội bộ của schema này, không tự tải schema qua mạng. Kiểm tra hash, metaschema và profile khi khởi động; schema hỏng/khác baseline là lỗi cấu hình, không là lỗi requirements.

Tách việc đọc **schema artifact tin cậy** khỏi parser payload: các hằng số nguyên nhỏ trong schema như minItems/minLength được đọc thành int để kiểm tra metaschema, không buộc validator thư viện nhận schema có các keyword đó ở dạng Decimal. Payload người dùng, snapshot.input và giá trị lỗi vẫn qua codec số chính xác; đây không phải phép đổi kiểu dữ liệu requirements. Artifact schema vẫn kiểm tra duplicate keys, digest và cấu trúc trước khi dùng.

validator_version nhận diện immutable build gồm code adapter, dependency lock và profile W; manifest riêng ghi exact Python/SQLite/dependency versions, artifact hashes và cấu hình chạy. Không thêm trường manifest vào envelope hay tăng revision khi chỉ đổi build. Chưa có Git vẫn có thể nhận diện build bằng digest gói nguồn/manifest; không khởi tạo Git trong lượt này.

## 5 Thiết kế lưu trữ local

### 5.1 Vị trí và dữ liệu

Kho được chọn bằng --state-dir hoặc cấu hình người dùng. Giá trị đề xuất khi cấu hình lần đầu là thư mục state local riêng, ví dụ ~/.local/share/dacn/s01; không hardcode đường dẫn người dùng trong logic. CLI phải hiển thị/ghi trong receipt đường dẫn DB đã resolve để audit không đọc nhầm kho. Các exports/evidence do người dùng chọn riêng; không ghi vào docs/examples hoặc dataset.

| Nhóm bảng dự kiến | Nội dung có thẩm quyền | Ràng buộc chính |
| --- | --- | --- |
| schema_artifacts | Digest và bytes schema thực dùng | Digest duy nhất; append-only |
| sources | source_id, raw_input BLOB, kind, label | PK source_id; bất biến sau commit; nguồn lỗi cũng giữ nguyên bytes |
| runs | run_id, source_id, request gốc dạng JSON chính xác, envelope đầy đủ đã serialize, schema digest | PK run_id; source/schema FK khi có; run cuối cùng bất biến |
| snapshots | snapshot_id, spec_id, revision, parent ID, origin_source_id, created_by_run_id, snapshot JSON chính xác | PK snapshot_id; unique(spec_id, revision); FK source/run/parent |
| specs | spec_id và head_snapshot_id hiện hành | PK spec_id; head trỏ snapshot cùng spec; đây là phần được cập nhật khi có revision mới |

Đây là mô hình logic, chưa phải DDL đã chốt. Các cột index/FK lặp lại metadata JSON nhằm enforce quan hệ và tra cứu; service phải tạo từ cùng dữ liệu, không cho hai bản metadata được sửa độc lập. Lưu cả envelope của run có thể lặp nội dung snapshot khi unchanged; chấp nhận chi phí cho bản nhỏ để tái xuất đúng kết quả cũ. Khi cần tối ưu sau này phải giữ nguyên contract và bằng chứng truy vết.

UUIDv4 từ hệ thống dùng cho spec/run/source/snapshot; không lấy từ requirement ID hoặc title. PK/unique mới là ràng buộc cuối cùng; nếu va chạm phát hiện trước khi công bố ID thì cấp lại, còn vi phạm nhất quán khác phải failed chứ không ghi đè. Revision bắt đầu 1, tăng đúng một trong transaction; không dựa vào thời gian hay UUID để sắp revision. received_at/completed_at theo UTC millisecond và phải thỏa completed_at >= received_at; thay đổi đồng hồ hệ thống cần được kiểm thử, không dùng timestamp làm khóa cạnh tranh.

Request gốc là context mode/spec_id/base_revision nhận từ adapter trước revision validation, tách khỏi input. Các flag CLI có cú pháp chuyển thành request có kiểu rõ ràng; parse số của flag không phải ép kiểu dữ liệu requirements. Request không biểu diễn được giữ ở cột audit gốc, còn run.request theo quy tắc nullable của contract. Nguồn input không đọc lại từ file khi resolve: tra sources bằng source_id; resolve snapshot bằng snapshot_id hoặc spec_id/revision rồi dùng origin_source_id và pointer. Run gửi lại luôn có source_id mới nhưng snapshot reused giữ provenance cũ.

### 5.2 Transaction và đồng thời

Đề xuất một DB trên filesystem local, rollback journal DELETE, synchronous=FULL, foreign_keys=ON ở mỗi connection; không đặt DB đang ghi trên network drive hoặc thư mục đồng bộ đám mây. Foreign keys cần bật tường minh, và có thể dùng deferred FK cho liên kết run/snapshot tạo trong cùng commit. [SQLite foreign keys](https://sqlite.org/foreignkeys.html), [PRAGMA](https://sqlite.org/pragma.html).

Service parse/validate input ngoài write transaction để giảm thời gian giữ khóa. Sau đó repository dùng **BEGIN IMMEDIATE**, đọc head mới nhất, kiểm tra base, so dữ liệu và ghi. SQLite chỉ có một write transaction tại một thời điểm; BEGIN IMMEDIATE có thể báo SQLITE_BUSY nếu writer khác đang hoạt động. [SQLite transactions](https://sqlite.org/lang_transaction.html).

Đề xuất điều khiển transaction tường minh trong sqlite3: autocommit=true để không có BEGIN ngầm, dùng các câu lệnh SQL BEGIN IMMEDIATE/COMMIT/ROLLBACK cho đơn vị công việc. Không nhầm Connection.commit() trong chế độ này là thao tác commit SQL; tài liệu ghi nó không có hiệu lực. Chính sách này cần integration test với runtime đã khóa. [Python sqlite3 transaction control](https://docs.python.org/3.13/library/sqlite3.html#transaction-control).

**Phạm vi commit nguyên tử:** source bytes + request/run/envelope + schema artifact cần archive + snapshot mới nếu có + cập nhật head. Tất cả nằm trong một SQLite transaction, không chia raw source sang file rồi giả định hai nơi cùng atomic. Envelope candidate được serialize và kiểm tra invariants trước commit; chỉ xuất validated sau khi COMMIT thành công. Với rejected vẫn commit source/run lỗi, không snapshot/head mới.

Không có source/run cuối cùng đã commit trước parse ở phương án này: “chụp nguồn” trước chuẩn hóa nghĩa là giữ bytes bất biến trong lần xử lý; độ bền đạt ở transaction cuối. Crash trước commit có thể không lưu nguồn/run, đúng giới hạn đã nêu trong contract. Nếu cần tiếp nhận bền vững ngay trước parse, đó là yêu cầu bổ sung cho intake journal/pending state, cần review riêng chứ không tự thêm vào envelope.

Nguồn, snapshot, run và schema artifact cấm UPDATE/DELETE qua ứng dụng; đề xuất thêm trigger chống sửa/xóa trên các bảng bất biến. Chỉ specs.head thay đổi theo transaction hợp lệ. FK/unique/trigger bảo vệ một phần; service vẫn kiểm tra parent cùng spec, revision liền trước, snapshot/envelope khớp nhau. Không INSERT OR REPLACE để lách tính bất biến. Người có quyền sửa DB trực tiếp vẫn ngoài bảo đảm chống can thiệp của bản local.

| Hai process gửi từ base 1 | Lập luận dưới write transaction | Kết quả mong đợi |
| --- | --- | --- |
| Cả hai bằng r1 | A commit run unchanged, head vẫn r1; B lấy khóa rồi đọc lại r1 | Cả hai unchanged, hai run/source, một snapshot r1 |
| Cả hai gửi P khác r1 | A tạo r2; B chỉ đọc head sau khi được phép ghi | B conflict dù P bằng r2; chỉ một revision mới |
| Hai thay đổi khác nhau | Tương tự, không dùng head đọc trước khi lấy khóa | Một new_revision, một conflict |
| Unchanged commit trước thay đổi | A không cập nhật head; B vẫn có base hợp lệ | A unchanged r1, B new_revision r2 |
| Thay đổi commit trước unchanged | B tạo r2 trước khi A quyết định cuối | A conflict, không trả unchanged dựa trên r1 cũ |

Lock timeout không phải REVISION_CONFLICT: nếu chưa đọc/kiểm tra được head thì là lỗi persistence. Đề xuất chờ khóa tối đa 5 giây, cấu hình được; khi hết thời gian không tự submit lại như run mới. Với SQLITE_BUSY tại COMMIT cần quản lý transaction còn mở: thử lại commit trong ngân sách hoặc rollback/đối soát; không mở thêm transaction lồng tùy ý. Số 5 giây là thông số vận hành đề xuất, không là ngưỡng chất lượng hay thay đổi contract.

### 5.3 Lỗi và recovery

| Điểm lỗi | Hành vi và bằng chứng cần giữ |
| --- | --- |
| Không đọc đủ input/schema hoặc serialize không chính xác được | failed, không handoff; giữ nguồn/run lỗi nếu có đủ dữ liệu và kho ghi được; không giả source đã lưu |
| Input/request không hợp lệ | rejected; source/run ghi trong transaction, snapshot null, head không đổi |
| Lỗi trong transaction trước commit được xác nhận | Rollback toàn bộ candidate; thử ghi một run failed cùng nguồn trong transaction riêng khi kho còn hoạt động; không để snapshot/head dở dang |
| Không biết COMMIT đã thành công chưa | Tra run_id bằng connection mới sau recovery. Nếu có envelope đã commit nhất quán, trả/retrieve bản đó; không ghi đè run thành failed. Nếu chưa xác định được, chỉ báo failed vận hành/no handoff và hướng dẫn đối soát; không khẳng định rollback |
| Commit thành công nhưng stdout/export lỗi | Kết quả trong DB vẫn có thẩm quyền. Không đổi validated thành rejected hoặc tạo revision mới; tra lại run để xuất lại. CLI báo lỗi giao nhận qua stderr/exit code riêng |
| Tiến trình chết trước commit | Có thể không có run/source; DB recovery không để head trỏ snapshot chưa commit. Receipt không là bằng chứng thành công |
| Tiến trình chết sau commit trước output | DB chứa toàn bộ kết quả; đọc theo run_id, không submit lại để lấy output |

Atomicity được dựa vào transaction/journal của SQLite, không vào việc “ghi file xong”. Bảo đảm vẫn phụ thuộc filesystem/OS thực hiện khóa và flush đúng; test kill process không chứng minh chịu được mọi dạng mất điện hoặc hỏng phần cứng. [SQLite atomic commit](https://sqlite.org/atomiccommit.html).

### 5.4 Receipt local và retention

Đề xuất CLI submit yêu cầu đường dẫn --receipt do người dùng biết trước, nằm ở vùng output riêng. Trước bất kỳ commit S01 nào, adapter cấp run_id và ghi receipt tối thiểu gồm run ID và đường dẫn kho đã resolve bằng thao tác tạo mới, không ghi đè, publish nguyên tử và flush phù hợp filesystem local. Nếu bước này không hoàn tất thì không bắt đầu commit S01. Receipt là metadata vận hành ngoài envelope, không là source/snapshot hay cờ thành công.

Khi mất output, người dùng đọc receipt rồi chạy show-run. Không có record chưa chứng minh thất bại nếu process gốc còn sống hoặc trạng thái DB chưa rõ; cần kết thúc/đối soát process và recovery trước khi tạo lần gửi mới. Receipt đã tồn tại không được dùng để tự chạy lại submit; CLI từ chối overwrite và hướng dẫn tra kết quả. Đây là cơ chế tra cứu của CLI local, **không phải exactly-once hoặc idempotency API**. Cách publish/flush receipt và recovery phải được audit/test; chưa tạo receipt thật trong lượt này.

Bản đầu giữ toàn bộ raw source, run, snapshots, schema artifacts và receipts; không có tự động prune hoặc lệnh xóa nghiệp vụ. Test dùng DB/receipts tạm, được xóa theo vòng đời test. DB thử nghiệm và DB làm việc không dùng chung. Backup/export vào đường dẫn riêng; sao lưu DB đang mở phải dùng phương pháp SQLite hỗ trợ, không chỉ copy tùy ý file đang ghi. Dung lượng tăng theo số lần gửi là trade-off cần theo dõi, không tự sửa retention khi triển khai.

## 6 Cấu hình và cách chạy dự kiến

CLI tên module dự kiến dacn_s01; chỉ các lệnh dưới đây, chưa tạo API. Config TOML chọn qua --config có state_dir, busy_timeout_ms và dataset_roots để bảo vệ vùng nguồn; thứ tự ưu tiên --state-dir trên config, còn thiếu thì yêu cầu khởi tạo cấu hình rõ ràng. Schema/profile không cho override tùy ý bằng path trong bản đầu. State/receipt/export phải nằm ngoài dataset; adapter kiểm tra đường dẫn resolve không trùng input và không nằm trong dataset root đã cấu hình bảo vệ, kể cả qua symlink. Không thể chứng minh dataset được bảo vệ nếu người dùng chưa khai báo đúng root; ghi giới hạn này trong hướng dẫn chạy.

| Lệnh dự kiến | Chức năng |
| --- | --- |
| init | Tạo kho local và kiểm tra cấu hình; không tiếp nhận requirements |
| submit --mode create | Đọc --input; request ngoài input có mode=create, spec_id/base_revision null |
| submit --mode update --spec-id --base-revision | Giữ nguyên input schema; truyền riêng ngữ cảnh cập nhật |
| show-run --run-id hoặc --receipt | Đọc envelope đã commit, không chạy validation lại và không tạo run mới |
| show-snapshot --snapshot-id hoặc --spec-id/--revision | Đọc snapshot bất biến; không mặc định đánh đồng với head |
| show-source --source-id --output | Xuất nguyên byte nguồn; không parse/chuẩn hóa rồi ghi lại |
| list-runs --spec-id | Tra run liên quan gồm unchanged/rejected khi request biểu diễn được; run sai request vẫn tra được bằng run_id/receipt |

Ví dụ sau **chưa tồn tại/chưa chạy**; các đường dẫn là placeholder do người chạy chọn, không hardcode vào logic:

```text
python -m dacn_s01 --state-dir /path/to/local-state init
python -m dacn_s01 --state-dir /path/to/local-state submit --mode create --input /path/to/read-only-input.json --receipt /path/to/outputs/attempt-01.receipt.json
python -m dacn_s01 --state-dir /path/to/local-state submit --mode update --spec-id SPEC_ID --base-revision 1 --input /path/to/edited-input.json --receipt /path/to/outputs/attempt-02.receipt.json
python -m dacn_s01 --state-dir /path/to/local-state show-run --receipt /path/to/outputs/attempt-02.receipt.json
python -m dacn_s01 --state-dir /path/to/local-state show-snapshot --spec-id SPEC_ID --revision 1
```

Lần đầu cần môi trường đã khóa; các lệnh cài đặt cụ thể sẽ thuộc đợt setup sau khi kế hoạch được giao triển khai. Không đưa ví dụ này vào shell script thực thi trong lượt hiện tại.

## 7 Output và mã thoát

- Submit trả đúng một envelope JSON trên stdout khi có thể hoàn tất xuất, kể cả rejected/failed; không chèn banner/progress/traceback vào JSON. stderr dành cho log vận hành, run ID và thông báo lỗi giao nhận, không dump toàn payload.
- Đề xuất exit code: 0 cho validated; 2 cho rejected; 3 cho failed hoặc lỗi xuất kết quả; 64 cho lỗi cú pháp CLI trước khi có S01 request; 4 cho lookup không tìm thấy record. Handoff chỉ dựa envelope và record tin cậy, không dựa riêng exit 0.
- Các lookup thành công trả record được yêu cầu và exit 0, không có nghĩa chúng tạo ra một S01 validated mới. Lỗi giao nhận sau commit trả exit 3 và stderr nêu cách show-run bằng receipt; output bị cắt không được coi là envelope hợp lệ.
- Semantic request errors đi qua lớp revision theo contract. Lỗi cú pháp flag trước tiếp nhận, ví dụ không đọc được dạng số của --base-revision, là usage error của adapter; không chế tạo schema error trong requirements.
- Không tự retry submit. Kết quả đã lưu đọc lại bằng show-run, không cập nhật timestamps/validator_version hay provenance cũ. Export chỉ là bản sao đọc được của record đã commit; hỏng export không làm đổi DB.

## 8 Kế hoạch kiểm thử

**Chưa viết hoặc chạy tests.** Sử dụng dữ liệu nhỏ, DB và receipts trong thư mục tạm riêng. Không ghi vào dataset, schema nguồn hay sáu JSON minh họa. Những ví dụ đó làm tài liệu đối chiếu; test input/expected của implementation phải được tạo có provenance, không coi output minh họa đã là kết quả chạy thật.

pytest cung cấp parametrization và tmp_path cho các ca độc lập; đề xuất dùng chúng cho ma trận contract và kho tạm. Điều này xác nhận công cụ có khả năng cần thiết, không chứng minh test của DACN đã hoạt động. [pytest parametrization](https://docs.pytest.org/en/stable/how-to/parametrize.html), [pytest tmp_path](https://docs.pytest.org/en/stable/how-to/tmp_path.html).

### 8.1 Unit tests

| Dữ liệu/tình huống | Cách kiểm tra | Kết quả mong đợi |
| --- | --- | --- |
| Duplicate ở root/nested/constraint.value; key escape tương đương; key giống ở hai object khác nhau | Gọi codec với raw bytes có key lặp, không xây dict trước test | Lặp cùng object bị DUPLICATE_JSON_KEY trước mất dữ liệu; hai object riêng được giữ |
| NaN/Infinity, cú pháp sai, root sai kiểu | Đối chiếu stage và trạng thái phụ thuộc | Invalid JSON dừng parse; root JSON hợp lệ sai kiểu dừng schema |
| 9007199254740993, số nguyên >4300 chữ số, thập phân >28 chữ số, 1e400, số mũ âm và -0 | Kiểm tra giá trị chính xác và loại nội bộ; serialize/parse lại, không float làm oracle | Không mất chữ số/đổi number thành string; giới hạn tài nguyên phải failed rõ, không kết luận đạt nếu chưa xử lý được ca chuẩn |
| true với 1; false với 0; 1 với 1.0; -0 với 0; missing với null | Expected được viết độc lập theo contract, không gọi chính comparator làm oracle | Boolean khác number; hai cặp số bằng nhau; missing khác null |
| Đổi thứ tự object key/array, sửa text/priority/criteria, đổi null/vắng mặt | Đối chiếu comparator và quyết định thuần | Key order không tăng revision; thay đổi array/value/missing tăng |
| Thiếu schema_version; null/số/rỗng/bao quanh W/version khác | Kiểm tra normalization log và input_version | Chỉ thiếu key được thêm; nguồn không đổi; sai version không được default |
| Toàn bộ 29 phần tử W tại nonblank và cả hai biên ID; W ở giữa ID | Parametrize từng code point, chuỗi hỗn hợp W và chuỗi rỗng | Đúng stage/code theo baseline; không trim và không sinh lỗi cross-field sau schema failed |
| U+200B/U+FEFF ngoài W, text có W hai bên và nội dung giữa | Kiểm tra adapter thay pattern, không regex veto thứ hai | Giá trị contract cho phép được giữ đúng, không normalize |
| FR/NFR/constraint: ID trùng, actor trùng, metrics sai, priority sai, fields lạ/thiếu | Ma trận mục 10 contract, đối chiếu error.code/pointer/details | Mã chuyên biệt, vị trí chính xác; trường lạ không bị bỏ; constraint.value tự do không bị cấm nhầm |
| Text/ID/priority/criteria/thứ tự/unknowns và optional missing | So cây nguồn/normalized với expected literal độc lập | Không có thay đổi ngoài thêm version khi thiếu; không default optional |
| Lỗi anyOf/required/additionalProperties, nhiều lỗi độc lập | Expected error list cố định, không so text của thư viện | Sort/dedup đúng baseline; missing không bị báo actual:null |

Các giá trị số lớn đặt trong constraint.value để thực sự được schema cho phép. Cần kiểm thử số ngay cả khi nằm trong details.actual của envelope rejected: đường ghi lỗi cũng không được làm mất số.

### 8.2 Contract tests

| Dữ liệu/tình huống | Cách kiểm tra | Kết quả mong đợi |
| --- | --- | --- |
| Sáu kịch bản clinic theo tài liệu | Chạy service với clock/ID kiểm soát được, đối chiếu shape, fields bắt buộc và các giá trị nghiệp vụ | new_spec, legacy unchanged, duplicate ID, duplicate metric, unchanged và new_revision đúng baseline |
| validated/rejected/failed ở mỗi lớp | Kiểm tra matrix status/result_kind/checks/errors/snapshot/handoff | validated phải đồng nhất; thất bại không có snapshot/handoff, không fallback bản cũ |
| Snapshot reused so với snapshot mới | Kiểm tra tuple spec/revision/parent/creator/origin | Reuse giữ metadata gốc; revision mới liên kết đúng và không kế thừa xác nhận nghiệp vụ |
| Envelope cố ý sai handoff ID, thiếu check passed hoặc snapshot không tồn tại | Kiểm tra guard tại boundary xuất/tra record, không gọi S02 | Không xuất envelope thành công sai invariants; không cần implement S02 consumer |
| Clock lùi, ID va chạm giả lập, version serializer/schema khác | Inject clock/ID có kiểm soát, kiểm tra lỗi/invariants | Timestamp hợp contract; không overwrite; không đổi revision chỉ vì build metadata |

Có thể viết một schema envelope phục vụ tests sau này, nhưng đó là cách mã hóa baseline cần review, không tự thêm trường hoặc nghĩa mới. Không lấy snapshot testing toàn file với timestamps ngẫu nhiên làm kiểm tra duy nhất.

### 8.3 Integration tests

| Dữ liệu/tình huống | Cách kiểm tra | Kết quả mong đợi |
| --- | --- | --- |
| DB tạm, create → unchanged → edit → reorder → trở lại nội dung cũ | Đóng/mở connection giữa các thao tác; truy vấn số record và parent/head | Reuse đúng, revision tuyến tính, nguồn mỗi run riêng; quay lại nội dung cũ vẫn tạo revision mới |
| Raw bytes có indentation/escape/số lớn và input parse lỗi | Resolve source và so bytes; resolve snapshot qua pointer | Nguồn byte-for-byte, số/value không đổi sau restart; nguồn lỗi không thành snapshot |
| Update/delete trực tiếp record bất biến, parent/source FK sai, duplicate spec/revision | Thực hiện thao tác ở DB tạm để thử constraint/trigger | DB chặn; không ghi đè lịch sử hoặc tạo tham chiếu treo |
| Năm lịch cạnh tranh trong mục 6.1 contract | Hai process và hai SQLite connection độc lập trên cùng DB file; đồng bộ có chủ đích | Kết quả và head như bảng mục 5.2; không chỉ kiểm tra tuần tự |
| Lock timeout, lỗi insert, lỗi commit, lỗi serialize | Inject failure tại ranh giới cụ thể; mở connection mới kiểm tra sau lỗi | Không partial snapshot/head; failed không handoff; không gọi busy là revision conflict |
| Kill process trước/sau commit, trước stdout | Parent điều phối child qua IPC và kiểm tra recovery bằng run ID/receipt | Trước commit không có final state dở; sau commit có thể đọc đúng envelope dù chưa nhận response |

**Cách tạo race thực:** parent khởi động hai process cùng nối một file SQLite tạm, không dùng hai :memory: DB. Dùng barrier/event/pipe ở trước BEGIN và sau khi writer A lấy khóa; cho B thực sự thử giao dịch khi A chưa commit, rồi giải phóng A. Đổi thứ tự cho hai ca mixed unchanged/new_revision. Các điểm đồng bộ là hook nội bộ cho test, không thành flag production. Không dùng sleep làm bằng chứng thứ tự; đặt deadline để phát hiện deadlock. Lưu lịch sự kiện lock/decision/commit/result của mỗi process và trạng thái DB cuối. Fake repository chỉ dùng unit test, không đủ chứng minh race được xử lý.

**Mô phỏng persistence failure:** unit/integration dùng repository fault injection trước insert, sau insert snapshot trước cập nhật head, trước COMMIT và lỗi xác nhận sau COMMIT. Thêm thử nghiệm với DB read-only/lock thực và child process bị terminate tại điểm đã đồng bộ. Fake I/O error không thay bằng chứng rollback thực; kill process không thay thử nghiệm mất điện. Disk-full có thể cần môi trường chuyên biệt; nếu chưa chạy được phải ghi rõ khoảng trống, không báo đã chứng minh toàn bộ durability.

### 8.4 End-to-end tests

| Dữ liệu/tình huống | Cách kiểm tra | Kết quả mong đợi |
| --- | --- | --- |
| Chạy module CLI bằng subprocess trên các payload hợp lệ/lỗi | Thu riêng stdout, stderr và return code; đọc JSON bằng codec chính xác trong harness | Một envelope đúng hoặc lỗi usage đã quy định; log không lẫn stdout |
| State dir/config khác nhau, input chỉ đọc và output riêng | Quan sát các file được tạo và digest input trước/sau | DB/receipt chỉ ở vùng tạm được chọn; input/dataset không đổi |
| create/update flags, base sai, spec không tồn tại | Kiểm tra request nằm ngoài snapshot.input | Đúng routing và lỗi revision; không thêm metadata vào user input |
| Receipt trùng, output pipe đóng sau commit, show-run/show-source/show-snapshot | Chạy lại lookup, không submit lại | Receipt không overwrite; kết quả đã commit truy hồi được; source xuất nguyên byte |
| Cài package vào môi trường thử, đổi working directory | Gọi CLI không có đường dẫn schema máy cá nhân | Schema resource vẫn resolve, digest đúng; không tải KB/schema qua mạng |

## 9 Các đợt implementation dự kiến

Mỗi đợt chỉ bắt đầu khi được giao triển khai; tiêu chí dưới đây là điều kiện nghiệm thu kỹ thuật đề xuất, chưa phải kết quả đo hay kết luận đã đạt.

| Đợt | Phạm vi và dependencies | Deliverables dự kiến | Điều kiện hoàn thành và bằng chứng | Agent audit cần xem |
| --- | --- | --- | --- | --- |
| 1 Môi trường và codec | Review kế hoạch; runtime/dependency candidates | Package skeleton tối thiểu, lock/manifest, schema resource nguyên byte, codec và tests số/duplicate | Cài tái lập được trên runtime đã pin; chứng minh duplicate và vòng đời Decimal; report versions/hashes và test output | Dependency API thực so với tài liệu; number loss, default/coercion, schema drift |
| 2 Validation và envelope | Đợt 1 | W adapter, normalization, cross-field, error mapping, envelope invariants; unit/contract tests | Ma trận validation baseline và preservation có bằng chứng; không có field mới hoặc ngữ nghĩa mới | W đủ 29, không regex veto; lỗi/pointer/order; phân loại rejected/failed |
| 3 Persistence và revision | Đợt 2, mô hình DB được review | DB initialization/migration nhỏ, repository, service revision, lookup; integration tests | Atomic source/run/snapshot/head, reuse/parent/provenance đúng; năm lịch process thực và fault tests có log | Transaction boundary, constraint/immutability, race, recovery và giới hạn chưa chứng minh |
| 4 CLI và bàn giao local | Đợt 3, receipt/exit policy được review | CLI/config hướng dẫn, receipts, E2E và gói bằng chứng | Chạy từ package, input read-only, JSON sạch, output recovery; báo cáo đầy đủ S01 | CLI không lặp logic nghiệp vụ, request ngoài input, crash/receipt và không mở scope S02 |

Mỗi đợt bàn giao phạm vi/contract version, thay đổi và lý do, cách tái lập, tests thực sự đã chạy, artifacts/logs, hạn chế và quyết định cần audit. Manifest kết quả ghi exact build/runtime/dependencies/schema/config cùng dữ liệu fixtures; không thêm metadata ngoài contract vào envelope. Nếu test fail do contract thiếu hoặc mâu thuẫn, ghi issue và đề xuất riêng; không sửa baseline cho vừa code.

## 10 Tiêu chí hoàn thành S01

S01 chỉ được đề xuất nghiệm thu khi thực thi đủ pipeline và CLI đã chọn, bảo toàn nguồn/dữ liệu, quản lý snapshot/revision và concurrency đúng draft.2; có bằng chứng kiểm thử của cả bốn nhóm, đặc biệt số chính xác, W, năm lịch cạnh tranh và các điểm lỗi persistence đã cam kết. Toàn bộ sai lệch hoặc trường hợp chưa kiểm chứng phải hiện trong báo cáo; không lấy số lượng tests hoặc coverage phần trăm làm thay thế cho invariant còn sai.

Người review phải có thể lấy run ID, xem request/nguồn/envelope, resolve snapshot/criterion và tái chạy bằng môi trường được ghi nhận. Các đường lỗi phải chặn handoff như contract. Audit implementation là đợt review riêng, không suy từ việc contract đã qua audit thiết kế. Hoàn thành S01 không tự mở rộng sang S02 hoặc khẳng định requirements đúng nghiệp vụ.

## 11 Quyết định cần audit và phần chưa xác minh

1. Chọn CPython 3.13.x cùng các version package ứng viên; chốt patch Python, bản SQLite link, build backend và dependency lock đầy đủ ở đợt 1. Chưa kiểm tra cài đặt/wheel/khả năng phối hợp trên máy hiện tại.
2. Chấp nhận codec hai thư viện: standard-library parse với Decimal cho mọi token số, simplejson serialize; cần chứng minh cả C extension và cấu hình được chọn không đổi giá trị. Tài liệu/nguồn mã xác nhận khả năng API, chưa thay tests thực nghiệm.
3. Review handler pattern W thay thế và type checker/error adapter. Không đổi W hoặc thêm cấm U+200B/U+FEFF. Đây là triển khai profile baseline, không tái thương lượng contract.
4. Chấp nhận SQLite một file, BEGIN IMMEDIATE, raw BLOB/JSON TEXT, tính bất biến, thời điểm lưu nguồn cùng final commit và retention không tự prune. Nếu cần nguồn durable trước parse phải yêu cầu thiết kế intake riêng.
5. Chấp nhận CLI-only, receipt bắt buộc, lookup/exit codes và ranh giới lỗi giao nhận sau commit. Cơ chế publish receipt local cần kiểm thử filesystem; không dùng nó để tuyên bố API đã giải quyết idempotency.
6. Chốt giới hạn tài nguyên vận hành và lock timeout cùng cách báo failed khi không thể xử lý chính xác; không tự thêm schema rejection cho dữ liệu JSON hợp lệ. Encoding/BOM và các trường hợp Unicode bất thường cần đối chiếu parser ở đợt 1; nếu phải thu hẹp miền input thì báo review, không tự đổi contract.
7. Review độ phủ thử nghiệm fault: phân biệt lỗi giả lập, khóa/I/O thật, kill process và mất điện/disk-full chưa kiểm chứng. Không báo durability mạnh hơn bằng chứng thực có.

Trong lượt này chỉ tạo tài liệu kế hoạch. Không tạo code, tests, config, dependency files, database, source records hoặc snapshots; không chạy tests, cài dependencies, khởi tạo Git hoặc sửa AGENTS.md/contract/dataset. Tất cả URL trong tài liệu là nguồn chính thức đã tham khảo ngày 13/10/2026; các thiết kế giao dịch, module và kiểm thử là suy luận/đề xuất của Astra dựa trên khả năng đó.
