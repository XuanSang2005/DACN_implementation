# S01 — Đợt 2: validation và envelope invariants

**Đã implement và kiểm thử; Đợt 2 đang chờ audit/nghiệm thu.**
Ngày bàn giao: 13/10/2026. Package: `dacn-s01 0.1.0a2`.
Người dùng đã duyệt Đợt 1 và giao bắt đầu Đợt 2 trong hội thoại.
Không suy việc duyệt Đợt 1 thành kết luận audit cho code mới.

Baseline không đổi: [contract 0.1.0-draft.2](../../docs/S01_OUTPUT_CONTRACT_PROPOSAL.md),
[kế hoạch, dòng Đợt 2 ở mục 9](../../docs/S01_IMPLEMENTATION_PLAN_PROPOSAL.md),
input schema 1.0.0 và AGENTS.md. Đã đọc lại phần requirements trong nguồn LaTeX.

## 1. Kết quả thực chạy

**724 passed trên C extension + 724 passed trên fallback Python**, mỗi lượt exit 0,
không failed/skipped. Đây là cùng một suite chạy hai backend, không phải 1.448
yêu cầu độc lập. `pip check` exit 0. Package được build/cài non-editable; suite cuối
chạy từ cwd tạm ngoài project, không PYTHONPATH và không tự nạp pytest plugins.

| Nhóm | Số ca pytest mỗi backend |
| --- | ---: |
| Codec Đợt 1 | 102 |
| Schema resource/package Đợt 1 | 8 |
| Validation Đợt 2 | 558 |
| Envelope invariants Đợt 2 | 56 |
| Tổng | 724 |

Đã đọc trực tiếp ví dụ phòng khám ở chế độ chỉ đọc: parse/schema/cross_field passed,
revision not_run; không có error hoặc normalization; bảo toàn decoded values.
Chỉ lưu kết quả kiểm tra và digest trong [clinic-input-check.json](clinic-input-check.json),
không sao chép dataset hay tạo snapshot/envelope nghiệp vụ.

## 2. Phạm vi và ranh giới thực thi

Đã implement profile W, version gate, normalization duy nhất, schema checks,
cross-field ID, ánh xạ lỗi và kiểm tra cấu trúc/invariants của envelope.

**Chưa implement** request/base validation trong pipeline, comparator/revision,
persistence, source/run/snapshot records, commit, lookup, receipt, CLI nghiệp vụ
hoặc S02. Không LLM, KB hoặc renderer. Không triển khai Đợt 3.

`validate_input()` trả **kết quả nội bộ**, không phải envelope S01. Khi ba lớp input
passed, `outcome="passed"` và `checks.revision="not_run"`; không trả status
`validated`, result_kind, snapshot hoặc handoff. Chỉ validation cấu trúc, không
xác nhận nghiệp vụ hoặc độ đầy đủ.

`check_envelope()` kiểm tra một candidate được cung cấp, đọc schema resource local
khi kiểm tra snapshot.input, không truy cập repository/network. Hàm không tạo hay
phát envelope thành công. Việc kiểm tra không chứng minh candidate đã commit,
nguồn đáng tin hoặc snapshot/source có thể resolve. Đợt 3 phải thực hiện những
kiểm tra đó trước phát handoff. Các candidate thành công trong tests là **synthetic**,
có IDs và validator_version ghi rõ giả lập, không đại diện run đã lưu.

## 3. Code và lựa chọn thực tế

| File | Trách nhiệm |
| --- | --- |
| [validation.py](../../src/dacn_s01/validation.py) | API `validate_input(raw: bytes) -> InputValidation`; W/type checker/schema adapter, version/normalization, error mapping, cross-field |
| [errors.py](../../src/dacn_s01/errors.py) | Error đủ bảy trường contract, JSON Pointer escaping, sort/deduplicate xác định |
| [envelope.py](../../src/dacn_s01/envelope.py) | `check_envelope(value) -> None`, raise EnvelopeInvariantError khi sai cấu trúc/invariants; không có repository hoặc success builder |
| [tests/phase2](../../tests/phase2) | Fixture synthetic riêng, kiểm thử validation và envelope |
| [pyproject.toml](../../pyproject.toml), `src/dacn_s01/__init__.py` | Version package tăng 0.1.0a2 và mô tả đúng phạm vi hiện tại |
| `tools/run_phase2_checks.py` | Chạy đầy đủ Đợt 1 + 2 trên hai backend, append câu lệnh/output/exit code |
| `tools/collect_phase2_evidence.py` | Đo môi trường, đối chiếu wheel/source/resource, protected hashes và ví dụ phòng khám chỉ đọc |

Codec Đợt 1, schema/provenance đóng gói, dependency locks, báo cáo Đợt 1 và các căn
cứ được bảo vệ giữ nguyên. Source package wheel cuối khớp byte với code trên đĩa
và package đã cài, kiểm chứng bởi script evidence.

### W và JSON types

W là frozenset của **29 code point liệt kê tường minh**, không lấy từ strip,
isspace hay regex Unicode runtime. Handler `pattern` thay hoàn toàn handler mặc
định, chỉ nhận pattern nonblank `\S` đã có trong artifact. Kiểm tra profile trước
iter_errors; pattern ngoài profile hoặc reference không local là PROCESSING_FAILED.
Schema nguồn không sửa. Các keyword khác giữ validator gốc.

Type checker chỉ nhận các kiểu JSON concrete; number là finite Decimal/int,
boolean tách riêng. Integer của Decimal xét tuple digits/exponent, không phép
toán làm tròn và không phụ thuộc context precision. Không coercion, không tự điền
schema annotation defaults. String trong constraint.value không chịu nonblank.

Cách thay handler/type checker dựa trên API chính thức
[jsonschema extend](https://python-jsonschema.readthedocs.io/en/stable/creating/)
và [TypeChecker](https://python-jsonschema.readthedocs.io/en/stable/validate/);
khả năng thực tế của version đã pin được kiểm tra trong suite.

### Thứ tự và bảo toàn dữ liệu

1. Parse qua codec đã duyệt: duplicate/syntax là rejected; giới hạn công cụ là failed.
2. Root object/version gate. Version sai dừng schema ngay; không tự gán 1.0.0.
3. Chỉ khi key version thiếu: tạo root làm việc và thêm schema_version 1.0.0,
   ghi đúng một normalization. Raw bytes không sửa.
4. Đọc/xác minh schema resource và profile; thu các lỗi schema độc lập.
5. Chỉ khi schema passed mới kiểm tra ID theo FR → NFR → constraints, index tăng.
6. Dừng ở input checks; revision luôn not_run.

InputValidation chứa checks/errors, input_version, normalizations, schema digest
và normalized_input. Dữ liệu chuẩn hóa chỉ được trả khi cả ba input checks đạt.
Khi lỗi, normalized_input=None; vẫn giữ version/normalization đã thực sự xác định
để lớp sau ghi run record. Các object của kết quả thuộc riêng lần gọi; raw bytes
và object của test/caller đã serialize không bị biến đổi. Caller chịu trách nhiệm
giữ raw source; module này không tự lưu nguồn.

### Error adapter và envelope

Error adapter dùng validator keyword, instance/schema/path/context có cấu trúc,
không phân tích message thư viện. `anyOf` gom lỗi nhánh phù hợp; nullable sai kiểu
trả một TYPE_MISMATCH với các kiểu cho phép. minLength/pattern của chuỗi rỗng gom
thành một EMPTY_OR_WHITESPACE. Priority/metric/version dùng mã chuyên biệt.
Required báo key thiếu và không chế `actual:null`; additionalProperties báo từng
key lạ. Pointer escape `~` và `/`; generic schema_pointer được lấy từ vị trí node
thực trong artifact, kể cả node qua `$ref`. Cơ sở API:
[jsonschema ValidationError](https://python-jsonschema.readthedocs.io/en/stable/errors/).

Mỗi lần trùng sau lần đầu có pointer riêng và related_pointer đến lần đầu;
không deduplicate data. Sort lỗi theo stage, pointer (null trước), code; target là
tie-breaker để ổn định khi cần. Cùng stage/target/pointer/code chỉ giữ một error.
Lỗi công cụ/configuration đi vào system/PROCESSING_FAILED, không thành rejection
nghiệp vụ; không lộ traceback/message thư viện có thể chứa toàn payload.

Envelope checker kiểm tra tập trường/kiểu, timestamp, version/digest, request có
thể biểu diễn, normalization, thứ tự checks/errors, taxonomy/details và sự nhất
quán status/result/snapshot/handoff. Với candidate validated còn kiểm tra snapshot
input, request/result/revision, parent và origin run/source. Đây chỉ là quan hệ
trong candidate, **không phải** so sánh head, kiểm tra base ở commit, chứng minh
parent tồn tại hoặc chứng minh nguồn unchanged được lưu. Những việc đó thuộc Đợt 3.

## 4. Ma trận kiểm thử và bằng chứng

| Quy tắc | Dữ liệu/oracle và kiểm tra |
| --- | --- |
| W đầy đủ | 29 ký tự, mỗi ký tự tại title/actor/ID/criterion nonblank; cả hai biên ID; giữa ID; version trắng/biên trái/phải. Oracle literal độc lập với W của code |
| Phạm vi nonblank | Mọi vị trí Text ở root, FR/NFR/constraint, details, conditions, project_details, constraint.kind; rỗng/hỗn hợp W; gom anyOf/minLength/pattern |
| Ngoài W/không regex veto | U+200B/U+FEFF ở tất cả vị trí Text; ID biên; thay handler gốc bằng hàm luôn fail vẫn chạy profile đúng; NFC/NFD/case/spacing không gộp |
| Bảo toàn | Text/ID/priority/null/criteria/thứ tự và tiêu chí lặp; optional absent khác null; only-default-when-missing; normalizations giữ khi schema sau đó fail |
| Version/root/parse | Thiếu/explicit/null/số/bool/object/array/rỗng/biên/version khác; root không object là schema error; syntax/duplicate là parse error; giới hạn Decimal là processing failure |
| Cross-field | Duplicate cùng nhóm/cross-group và biên W đồng thời; first occurrence cố định dù đảo thứ tự keys; schema failed thì cross_field not_run |
| Actors/metrics | Actor exact duplicates; metric count, duplicate và invalid độc lập; null/wrong type; đủ 24 hoán vị hợp lệ được giữ thứ tự |
| Required/unknown/types | Thiếu field không actual giả; unknown ở các object khai báo, pointer `~`/`/`; nullable/type/anyOf; FR/actors minItems; NFR/constraints/criteria rỗng được giữ |
| Free JSON/số | constraint.value chứa key tùy ý, chuỗi trắng, bool/null; số 5001 chữ số, 1e400, fraction dài với context prec=2; kiểu và Decimal tuple giữ nguyên |
| System failures | Test doubles cho resource lỗi, pattern bất ngờ, engine exception; failed, không normalized_input/handoff, không chạy lớp phụ thuộc |
| Envelope invariants | Candidate new_spec/new_revision/unchanged synthetic; failure từ errors thực; mutation status/handoff/checks/keys/types/timestamp/hash/normalization/errors/routing/provenance bị chặn |
| Hồi quy Đợt 1 | Chạy lại nguyên codec/schema/package suite trên cả hai backend từ môi trường đã cài |
| Clinic chỉ đọc | Chạy validator thật trên file nguồn, ghi digest/checks và preservation; không coi còn null/câu hỏi nghiệp vụ là lỗi cấu trúc |

Oracle là literal/kỳ vọng độc lập từ contract và fixtures nhỏ tự viết. Không dùng
comparator S01 (chưa tồn tại), output minh họa hoặc chính hàm validation làm oracle
duy nhất. Tests envelope có dùng validator thật để kiểm tra integration nhưng đồng
thời có các mutation/kỳ vọng cụ thể độc lập.

Backend instrumentation gọi encoder thật: lượt C ghi **696 C / 0 Python**, lượt
fallback ghi **0 C / 696 Python**. Cả hai chạy đầy đủ suite; không tuyên bố mọi input
có thể có đều tương đương chỉ từ các mẫu đã đo.

Lượt phát triển ban đầu: 527 validation passed và 56 envelope passed. Sau khi bổ
sung null/absence, ID exact và các metric boundaries, suite cuối 724 passed/backend.
Không có ca thất bại trong các lượt Đợt 2 đã chạy; lịch sử lệnh phát triển vẫn được giữ.

## 5. Môi trường và tái lập

Giữ CPython **3.13.16 regular GIL**, jsonschema **4.26.0**, simplejson **4.2.0**,
pytest **9.1.1**, setuptools **80.9.0** và wheel **0.45.1** của Đợt 1.
Không thêm/nâng dependency; pip chỉ cài lại package DACN 0.1.0a2 sau build.
Manifest ghi toàn bộ distributions/build/platform/SQLite và file hashes thực đo.
Wheel cuối: `dist/dacn_s01-0.1.0a2-py3-none-any.whl`, SHA-256
`97a87a12a02c6e412d6159447b289bf36abf8083ab829506b6dd2ef3e3101a9f`.

Các lệnh đã chạy, từ project root:

```sh
.venv/bin/python -m pip wheel --no-deps --no-build-isolation --wheel-dir dist .
.venv/bin/python -m pip install --no-deps --force-reinstall dist/dacn_s01-0.1.0a2-py3-none-any.whl
.venv/bin/python tools/run_phase2_checks.py
```

Thu evidence bằng lệnh sau; thay hai placeholder bằng đường dẫn nguồn chỉ đọc
(đường dẫn thực đã dùng được lưu trong các JSON report, không hardcode vào logic):

```sh
.venv/bin/python tools/collect_phase2_evidence.py --schema-source /path/to/system-input.schema.json --clinic-source /path/to/clinic-input.example.json
```

Từ môi trường sạch, tạo venv bằng runtime 3.13.16 đúng artifact đã ghi ở Đợt 1,
cài `requirements-dev.lock` bằng `pip install --require-hashes -r requirements-dev.lock`
rồi chạy các lệnh trên. Không cần resolve lại dependencies. Không chạy tool evidence
của Đợt 1 trên package 0.1.0a2; report/wheel Đợt 1 là lịch sử riêng và được giữ nguyên.

Gói bằng chứng:

- [test-results.txt](test-results.txt): lệnh/cwd/output/exit code của suite cuối và evidence check.
- [development-results.txt](development-results.txt), [build-install.txt](build-install.txt): các lượt phát triển và build/install.
- [environment-manifest.json](environment-manifest.json): môi trường, cấu hình W và hashes code/tests/locks/wheel.
- [schema-resource-verification.json](schema-resource-verification.json): nguồn/resource/wheel khớp byte và metaschema.
- [clinic-input-check.json](clinic-input-check.json): lần kiểm tra clinic thật, không snapshot/handoff.
- [protected-files-verification.json](protected-files-verification.json): căn cứ/dataset/codec/locks/report Đợt 1 không thay đổi.

## 6. Giới hạn và bàn giao audit

1. Agent audit cần xem W/profile không regex veto, kiểu số/bool, anyOf mapping,
   pointer/schema_pointer, sort/deduplicate và phân loại rejected/failed.
2. Review ranh giới API: InputValidation passed không là validated S01; checker
   envelope không chứng nhận commit hoặc provenance. Không dùng checker đơn độc
   để nhận dữ liệu vào S02. Không có cơ chế handoff thật trong đợt này.
3. Lỗi resource/engine trong suite được fault-inject rõ ràng; candidate snapshots,
   request/revision/provenance là giả lập. Chưa kiểm thử persistence hay race condition,
   chưa có bằng chứng durability, recovery, source resolution hoặc base-at-commit.
4. Giữ các giới hạn codec đã báo ở Đợt 1: số vượt khả năng Decimal, int nội bộ quá dài,
   độ sâu quá lớn và literal adjacent surrogate pair. Validation có thể đạt cấu trúc
   nhưng serialization sau đó vẫn phải báo PROCESSING_FAILED nếu không bảo toàn được.
   Không thêm rejection nghiệp vụ để né giới hạn công cụ.
5. Ma trận được chạy trên macOS arm64/CPython 3.13.16. Chưa chứng nhận nền tảng khác,
   OOM/OS kill hoặc mọi input kích thước bất kỳ. Exception boundary không phải quota.

Không phát hiện mâu thuẫn baseline cần sửa trong đợt này. Không sửa contract để vừa
implementation. **Bàn giao Đợt 2 để review; dừng trước Đợt 3.**
