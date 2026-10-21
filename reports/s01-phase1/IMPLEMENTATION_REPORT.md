# S01 — Đợt 1: môi trường và codec

**Đã implement và chạy kiểm thử; bàn giao chờ agent audit. Chưa được nghiệm thu.**
Ngày bàn giao: 13/10/2026. Package: `dacn-s01 0.1.0a1`.
Baseline giữ nguyên: output contract `0.1.0-draft.2`, input schema `1.0.0`.

## 1. Kết quả và phạm vi thực tế

Đã tạo package cài bằng wheel, môi trường CPython 3.13.16 có GIL, dependency locks,
schema resource nguyên byte, codec JSON chính xác và kiểm thử liên quan.
Kết quả cuối: **110 passed trên C extension + 110 passed trên fallback Python**;
mỗi lượt exit 0, không failed/skipped. Đây là cùng 110 ca chạy trên hai backend,
không phải 220 yêu cầu độc lập. `pip check` đạt.

Chưa triển khai validation requirements, adapter W, cross-field, normalization
schema_version, envelope, comparator/revision, database/persistence, receipt,
CLI nghiệp vụ hoặc S02/LLM/KB/renderer. Không có source records/snapshots nghiệp vụ.
Metaschema check trong đợt này chỉ kiểm tra **artifact schema**.

Không sửa AGENTS.md, contract, implementation plan, sáu JSON minh họa, schema nguồn,
ví dụ phòng khám hoặc LaTeX. Digest trước/sau nằm trong
[protected-files-verification.json](protected-files-verification.json).
Không khởi tạo Git. Chỉ sao chép riêng schema được cho phép.

## 2. Môi trường thực chạy và lựa chọn build

| Thành phần | Phiên bản/kết quả đo |
| --- | --- |
| Python mặc định trên máy, chỉ dùng bootstrap | CPython 3.14.6; không dùng chạy package/tests S01 |
| Runtime project | CPython **3.13.16**, Clang 22.1.3, `Py_GIL_DISABLED=0`, GIL enabled |
| Nguồn runtime | Astral python-build-standalone, release **20261009**, macOS aarch64, regular build |
| Platform đo | macOS 26.5.1, arm64 |
| SQLite được link | **3.53.1**; chỉ đọc version, không tạo DB |
| Runtime dependencies trực tiếp | jsonschema **4.26.0**, simplejson **4.2.0** |
| Test | pytest **9.1.1** |
| Backend build | `setuptools.build_meta`, setuptools **80.9.0**, wheel **0.45.1** |
| Installer / resolver | pip **25.2** trong venv; uv **0.13.0** chỉ bootstrap/resolution |

Chọn patch 3.13.16 vì có bản regular arm64 cụ thể trong catalog phân phối đã kiểm tra,
đúng minor được giao; không dùng Python 3.14.6 của máy. Runtime nằm trong `.runtime/`,
venv trong `.venv/`, bootstrap/wheels trong `.tools/`; không cài dependency toàn cục.
uv cung cấp catalog của [python-build-standalone](https://docs.astral.sh/uv/guides/install-python/),
không phải binary macOS do python.org phát hành. URL mirror `releases.astral.sh`
trả HTTP 403 ở lần tải đầu; đã tải **cùng version/release/architecture** từ GitHub
chính thức của Astral, không thay runtime. Digest archive đo được:
`11785155d0f70e634178219c20925d8f20be00a3da4684fc4f5019dd15602ef7`.
Đây là digest đo từ artifact tải qua HTTPS; chưa xác minh chữ ký phát hành độc lập.

Setuptools phù hợp package thuần Python với resource tĩnh, không cần plugin build.
Pin 80.9.0 là lựa chọn build cụ thể đã cài/build thử, không tuyên bố là bản mới nhất.
Build thực dùng `--no-build-isolation --no-deps` sau khi cài đầy đủ lock để tránh
một resolver build khác tự chọn version. Cấu hình theo
[setuptools pyproject](https://setuptools.pypa.io/en/latest/userguide/pyproject_config.html);
tài liệu online mang version mới hơn, bằng chứng cho 80.9.0 là build/install thực.

`requirements.lock` khóa runtime và dependency bắc cầu. `requirements-dev.lock`
khóa toàn bộ runtime + pytest + build/installer cùng dependency bắc cầu, tất cả có
version và SHA-256. `requirements-tools.lock` khóa wheel uv bootstrap cho macOS arm64.
Đã cài với `--require-hashes`, và tải wheelhouse riêng với cùng lock/hash.
Manifest ghi cả danh sách distributions thực cài, `Requires-Dist`, artifact wheels
được chọn, checksum runtime/C extension/code/tests/locks và cấu hình encoder trích
trực tiếp từ mã đã cài. Lock này chứng nhận môi trường macOS arm64/CPython 3.13.16;
chưa chứng nhận các OS/architecture khác.

## 3. API và hành vi codec

API nội bộ ở [codec.py](../../src/dacn_s01/codec.py):

- `parse_json(raw: bytes) -> JSONValue`: nhận mọi root JSON, số nguyên/thập phân đều
  thành Decimal trực tiếp từ token; trả bool/null đúng loại. Không thêm default,
  trim, normalize Unicode, kiểm tra root requirements hoặc áp W.
- `serialize_json(value: JSONValue) -> bytes`: chỉ nhận kiểu concrete NoneType,
  bool, str, int, finite Decimal, list, dict với keys concrete str; không nhận
  subclass, float, tuple, custom object, cyclic tree. Shared child không phải cycle.
  Output là ASCII JSON bytes (cũng là UTF-8 hợp lệ); trả toàn bộ hoặc raise, không
  stream partial result. Caller không được sửa tree đồng thời trong khi serialize.
- Lỗi có `code`, `reason`; `DuplicateKeyError` thêm decoded `key`.
  `INVALID_JSON` cho syntax/encoding hoặc NaN/Infinity;
  `DUPLICATE_JSON_KEY` cho key đã decode trùng trong cùng object;
  `PROCESSING_FAILED` cho giới hạn biểu diễn/tài nguyên hoặc giá trị nội bộ không hỗ trợ.
  Chưa dựng Error/envelope S01; lớp sau phải ánh xạ stage/target/status theo context.

`object_pairs_hook` kiểm tra hết danh sách cặp trước khi tạo dict. Áp dụng cả nested,
arrays và constraint.value. Không có parse mặc định làm mất duplicate trước hook.
Không chế JSON Pointer hoặc byte offset từ character position của parser.
Raw bytes không bị sửa, nhưng codec **không lưu nguồn**; phần intake tương lai phải
giữ bytes gốc. Lexical số, escape, BOM và indentation không được tái tạo bởi serializer.

Các tùy chọn serializer tường minh gồm `use_decimal=True`, `allow_nan=False`,
`ignore_nan=False`, `bigint_as_string=False`, `int_as_string_bitcount=None`,
`skipkeys=False`, `ensure_ascii=True`, `check_circular=True`, `sort_keys=False`;
tắt tuple/namedtuple/iterable/for_json adapters, `default=None`, compact separators.
Không dùng float trung gian hay `default=str`. Numeric token được kiểm tra bằng
regex JSON và parser độc lập trong tests, không chỉ roundtrip qua codec.

Khả năng hooks/bytes encoding dựa trên [CPython json](https://docs.python.org/3.13/library/json.html),
Decimal trực tiếp từ chuỗi dựa trên [Decimal](https://docs.python.org/3.13/library/decimal.html),
serialization options đối chiếu [simplejson tag 4.2.0](https://raw.githubusercontent.com/simplejson/simplejson/v4.2.0/simplejson/__init__.py).
Các khẳng định thực nghiệm dưới đây dựa trên tests đã chạy, không suy từ tài liệu.

### Encoding và Unicode đã kiểm tra

Giữ cơ chế bytes detection của CPython: UTF-8, UTF-16 LE/BE và UTF-32 LE/BE,
mỗi loại có/không BOM (10 ca). BOM đầu được parser nhận diện; BOM giữa JSON không
được tự xóa. Invalid byte sequence không giải mã được trả INVALID_JSON.
U+FEFF trong string, U+200B, U+001C được giữ; không có nonblank/biên ID ở đợt này.
Chuỗi NFC/NFD, dấu cách, thứ tự keys/arrays, duplicate criteria đều giữ decoded value.

CPython còn nhận lone surrogates qua JSON escape và UTF-8 surrogatepass. Codec giữ
hành vi đó, không tự thêm rejection khi parse. Lone surrogate và ký tự astral chuẩn
được roundtrip bằng ASCII escapes. Có một giới hạn serializer cần audit, mục 7.

## 4. Schema resource

[schema_resource.py](../../src/dacn_s01/schema_resource.py) đọc qua importlib.resources,
xác minh digest cố định rồi parse schema với duplicate-key hook và `parse_int=int`
để minItems/minLength là int khi chạy `Draft202012Validator.check_schema`.
Lỗi artifact là SchemaResourceError/PROCESSING_FAILED, không phải lỗi requirements.
Mỗi lần load trả tree mới; caller sửa tree không sửa resource.

Nguồn, resource đã cài và resource trong wheel đều có digest
`0a7cda79ac2d949579c0a2279df3d60c18b8f0cd6335e28fac6d51d46248613d`.
Mọi `$ref` trong artifact này là local fragment. Không export Pydantic hay tải schema
qua mạng; test chặn socket trong khi đọc/check artifact vẫn đạt.
[PROVENANCE.md](../../src/dacn_s01/schemas/input/1.0.0/PROVENANCE.md)
ghi nguồn và profile bổ sung draft.2; **chưa thực thi profile**.

## 5. Kiểm thử thực chạy và bằng chứng

[test-results.txt](test-results.txt) giữ câu lệnh, cwd, stdout/stderr và exit code
của từng lượt, kể cả thất bại. Suite cuối chạy từ thư mục tạm ngoài project, tắt
autoload plugins và bỏ PYTHONPATH; tests import package từ wheel cài non-editable.
Subprocess `python -I` với cwd tạm kiểm tra import/resource riêng thêm một lần.

| Nhóm | Oracle/phương pháp và kết quả cuối |
| --- | --- |
| Duplicate keys | Raw byte fixtures ở root/nested/array/constraint.value; escape tương đương, emoji literal/escape, slash; đúng lỗi trước overwrite; keys riêng object vẫn giữ |
| Syntax/root | Invalid syntax, raw control, NaN/±Infinity bị từ chối; null/array/object/string/bool/number đều parse được |
| Số chính xác | 9007199254740993, 5001 chữ số, fraction >28 chữ số, 1e400, exponent âm, -0/-0.000; expected Decimal từ source + tuple digits/sign/exponent, regex numeric token và simplejson decoder độc lập; context prec=2, Emax=9 vẫn giữ chính xác |
| Kiểu và nội dung | Bool giữ bool, number giữ number; null/missing, text/ID/priority/criteria, thứ tự, Unicode và keys; input bytes/tree không bị sửa |
| Internal types/errors | Float, nonfinite Decimal, subclass, tuple/namedtuple, bytes, arbitrary object, bad keys, cycles bị chặn; không dùng fallback hoặc thay bằng null/string |
| Runtime limits thực | Exponent vượt libmpdec, nesting 10000, int nội bộ 5001 chữ số: PROCESSING_FAILED; không tuyên bố serialize thành công |
| Schema/package | Digest, duplicate artifact keys, metaschema/int keywords, resource mất/thay đổi, cài wheel và đổi cwd; tất cả đạt |
| Backend | Hai process pytest riêng; C được gọi 25 lần và Python 0 trong lượt C; Python 25, C 0 trong lượt fallback; assert backend thực được gọi |
| Unicode regression | Literal adjacent surrogate pair ở value/key: phát hiện nguy cơ collapse, trả PROCESSING_FAILED, giữ dữ liệu gốc |

Expected là synthetic fixtures nhỏ trong tests, không ghi vào dataset và không lấy
sáu envelope minh họa làm output implementation. Decimal source/tuple và parser
independent là oracle số; không dùng float hoặc comparator S01.

Test doubles chỉ gồm: thay resource bytes để đi qua nhánh duplicate/metaschema sau
digest gate, thay vị trí resource để tạo lỗi missing/digest, và chặn socket. Wrapper
đếm encoder factory **gọi encoder thật**, không thay kết quả serialization. Toggle
backend dùng API nội bộ của simplejson đã pin; cần xem lại nếu nâng version.

Lịch sử: lượt đầu 108 passed/backend. Probe thêm phát hiện adjacent surrogate có thể
đổi hai code point thành một. Hai regression tests chạy trước sửa **failed thực**,
exit 1; sau sửa preflight và rebuild/reinstall, suite cuối 110 passed/backend.
Log thất bại được giữ. Không đổi expected của số chính xác để làm tests passed.
Tests giới hạn số xác nhận lỗi có phân loại; không phải bằng chứng hỗ trợ số vượt giới hạn.

## 6. File bàn giao và cách tái lập

| File/thư mục | Mục đích |
| --- | --- |
| `src/dacn_s01/` | `__init__.py`, codec, schema_resource, py.typed, schema/provenance; không có module nghiệp vụ tương lai |
| `tests/test_codec.py`, `tests/test_schema_resource.py`, `tests/conftest.py` | Synthetic unit/resource/package tests và chọn/đo backend |
| `pyproject.toml`, `.python-version`, `.gitignore` | Package/backend/runtime pin, pytest configuration; .gitignore không khởi tạo Git |
| `requirements.in`, `requirements-dev.in`, ba `requirements*.lock` | Inputs resolver và locks đã pin/hash đầy đủ |
| `tools/run_phase1_checks.py` | Chạy suite từ cwd tạm, append log kể cả lỗi |
| `tools/collect_phase1_evidence.py` | Đo manifest, xác minh source/resource/wheel và protected files; đường dẫn nguồn truyền bằng argument |
| `dist/dacn_s01-0.1.0a1-py3-none-any.whl` | Wheel cuối thực đã cài/test, digest trong manifest |
| `.runtime/`, `.venv/`, `.tools/` | Artifacts môi trường local; không phải source records S01 |
| Báo cáo ở thư mục này | Implementation report, manifest, test log, schema verification, protected hashes, bootstrap/distribution metadata, dependency/build logs |

Các lệnh dưới chạy từ root project. Đây là cách tái lập trên runtime đã tải; các
lệnh tương ứng đã chạy với `.venv` hiện có (log build/install riêng). Với bản sao
project sạch, tạo `.runtime` từ đúng archive/URL/SHA-256 trong
[python-distribution.json](python-distribution.json), giữ regular arm64 build.
Không dùng `python3` mặc định để thay runtime. Không cần uv để cài từ lock đã có.

```sh
.runtime/python/bin/python3.13 -m venv .venv
.venv/bin/python -m pip install --require-hashes -r requirements-dev.lock
.venv/bin/python -m pip wheel --no-deps --no-build-isolation --wheel-dir dist .
.venv/bin/python -m pip install --no-deps --force-reinstall dist/dacn_s01-0.1.0a1-py3-none-any.whl
.venv/bin/python tools/run_phase1_checks.py
.venv/bin/python tools/collect_phase1_evidence.py --schema-source /path/to/read-only/system-input.schema.json
```

Có thể cài dependency offline bằng cách thêm `--no-index --find-links .tools/wheelhouse`
vào lệnh pip install lock; wheelhouse thực đã tải và hashes được ghi trong manifest.
Không chạy resolver để tái lập; chỉ dùng resolver khi chủ động thay locks và review.
Lệnh compile đã dùng nằm trong header từng lock; uv bootstrap wheel/hash trong
[bootstrap-uv.json](bootstrap-uv.json). Venv tạo ban đầu kèm pip 26.2.1 của distribution,
sau đó pip được đưa về 25.2 đúng lock; không cập nhật package ngoài lock.

Wheel rebuild có thể khác SHA-256 vì metadata timestamp ZIP; nhận diện build đã
audit bằng wheel digest **và** source/lock hashes trong manifest, không giả định
hai lần build là byte-reproducible. Script evidence kiểm tra mọi file package nguồn
khớp byte với wheel và package đã cài. `.venv`/runtime không phải artifact portable;
package wheel không hardcode đường dẫn cá nhân.

## 7. Giới hạn và nội dung agent audit cần xem

1. **Giới hạn biểu diễn số/tài nguyên:** payload integer 5001 chữ số đã roundtrip
   chính xác qua Decimal. Số có exponent cực lớn vượt khả năng libmpdec báo
   PROCESSING_FAILED cả khi Decimal trap bật/tắt. Python int do caller nội bộ tự
   tạo với >4300 chữ số hiện không serialize được vì int-to-string limit; báo lỗi,
   không đổi sang string/null. Không vô hiệu hóa limit hệ thống. Nesting 10000 chạm
   recursion limit cũng báo PROCESSING_FAILED. Chưa mô phỏng OOM/OS kill hay chứng
   minh mọi kích thước input xử lý được; chưa đặt resource quota vận hành.
2. **Issue Unicode cần review:** UTF-8 surrogatepass có thể tạo Python string chứa
   hai literal code point high/low surrogate liền nhau. `ensure_ascii=True` sẽ ghép
   chúng khi decode lại; preflight chặn serialize với PROCESSING_FAILED ở cả key và
   value. Parse vẫn nhận nguyên dữ liệu, không biến thành INVALID_JSON. Đây là giới
   hạn của cách xuất đã chọn, không quy tắc nghiệp vụ mới. Lone surrogate và emoji
   chuẩn đã được kiểm tra thành công. Nếu muốn hỗ trợ thêm trường hợp literal pair,
   cần review chiến lược encoding; chưa sửa contract để cấm input đó.
3. Review tính đầy đủ của preflight, mapping lỗi cho Đợt 2 và việc giữ raw bytes
   ngoài codec. Codec không hứa source location khi hook không cung cấp.
4. Review provenance, artifact digest, backend pin, runtime phân phối bởi Astral và
   phạm vi lock macOS arm64. Chưa có build/test trên Linux/Windows hoặc free-threaded.
5. Review oracle và hai backend thực; không suy từ tests codec rằng W, schema
   validation requirements, revision/concurrency, persistence hay handoff đã đúng.

Không có blocker chưa sửa trong các ca chức năng bắt buộc của Đợt 1 đã kiểm thử.
Các giới hạn ở trên vẫn tồn tại và cần audit; không ghi nhận implementation đã qua
audit hay requirements đã được người dùng xác nhận. **Dừng tại Đợt 1.**
