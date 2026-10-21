# S01 Đợt 3 — sửa P3-F1 sau audit

**Đã implement và kiểm thử bản sửa; chờ agent audit review lại, chưa nghiệm thu.**
Ngày bàn giao: 17/10/2026. Package `dacn-s01 0.1.0a5`; baseline `0.1.0a4`.
Output contract giữ nguyên `0.1.0-draft.2`, input schema `1.0.0`, cấu trúc DB `1`.

Đây là phụ lục cho [báo cáo Đợt 3](../IMPLEMENTATION_REPORT.md). Phạm vi chỉ sửa
**P3-F1** theo [audit 0.1.0a4](/Users/macbookpro/.codex/.chatgpt-projects/g-p-68c38c8799f48191a101e19a975ca4f9/outputs/audits/s01-phase3-0.1.0a4/audit-evidence.json).
Không triển khai Đợt 4, CLI, receipt, API hoặc S02. Báo cáo, suite audit và wheel cũ
được giữ nguyên. Kết quả dưới đây là thực chạy trên dữ liệu **synthetic** và SQLite
tạm riêng; không phải xác nhận nghiệp vụ hoặc kết luận audit chấp nhận bản sửa.

## 1. Baseline và nguyên nhân

[baseline-verification.json](baseline-verification.json) ghi nhận lúc bắt đầu:
package `0.1.0a4`; 13 file package khớp source–installed–wheel với audit;
các file trong manifest Đợt 3 cũ, runtime và dependencies đều khớp. Không phát hiện
thay đổi chưa hiểu. [protected-files-before.json](protected-files-before.json)
chụp hash 113 file trước khi sửa, gồm source, tests/tools cũ, tài liệu, schema,
ví dụ, báo cáo, wheel và các căn cứ/audit bên ngoài được tham chiếu.

Parser hiện tại đọc được hai code point surrogate liền nhau từ các byte UTF-8
`ED A0 80 ED B0 80`. Codec từ Đợt 1 cố ý từ chối serialize biểu diễn này, vì JSON
escape `\ud800\udc00` sẽ được parse thành **một** scalar U+10000, làm đổi nội dung.
Khi chuỗi nằm trong `priority`, `schema_version` hoặc key ngoài schema, validation
đưa nó vào `details` hoặc JSON Pointer của error. `check_envelope` từ chối candidate,
transaction rollback; nhưng `failure()` cũ giữ error đó và lại gọi `check_envelope`.
Exception thứ hai thoát ra trước transaction lưu failed run.

Đã tái hiện trên package `0.1.0a4` cài non-editable, ngoài thư mục source:
suite audit mới **6 failed, 6 passed**; regression chính thức mới **14 failed,
15 passed trên mỗi backend**. Stack trace trong [log trước sửa](before-test-results.txt)
xác nhận lỗi thoát tại `failure() → check_envelope` như audit mô tả.

## 2. Sửa đổi và giới hạn của đường lỗi

[service.py](../../../src/dacn_s01/service.py:97) kiểm tra khả năng serialize
**từng diagnostic** trong nhánh `failure()` bằng chính codec hiện hành:

- Diagnostic biểu diễn chính xác được giữ nguyên, kể cả các lỗi schema thông thường
  xuất hiện cùng lỗi Unicode.
- Diagnostic không thể biểu diễn không được chèn lại vào envelope. Một error
  `PROCESSING_FAILED`, `stage=system`, `target=system`, `pointer=null` và reason
  cố định báo rõ có diagnostic không thể biểu diễn chính xác. Không đưa chuỗi lỗi,
  exception text hoặc stack trace vào reason thay thế.
- Vẫn thêm lỗi hệ thống của thao tác đang thất bại và dùng quy tắc sort/deduplicate
  hiện có. Nếu đồng thời có lỗi persistence, giữ `PERSISTENCE_FAILED` cùng
  `PROCESSING_FAILED`; không đổi lỗi lưu trữ thành `REVISION_CONFLICT`.
- Vẫn chạy `check_envelope` trước khi lưu/trả. Chỉ bắt `CodecError` tại phép kiểm
  tra diagnostic; không bỏ qua kiểm tra invariants hoặc biến mọi exception thành
  thành công.

Đây là fallback cho **chẩn đoán không thể xuất ra**, không phải chuẩn hóa input.
Không sửa chuỗi Unicode, không bỏ trường input, không đổi codec/parser/validator,
không thay contract/schema. Raw source vẫn là BLOB nguyên byte, kể cả byte gây lỗi.
Request gốc vẫn được lưu riêng khi `run.request=null`.

Ranh giới transaction không đổi: candidate không biểu diễn được bị rollback;
service tạo failed envelope an toàn và thử lưu source + request/run + schema
artifact cần thiết trong transaction riêng như baseline. Không tạo snapshot, không
đổi head, không handoff. Nếu commit của transaction lưu lỗi mất xác nhận, lookup
bằng run ID trên connection mới vẫn đối soát bản đã commit. Nếu kho không hoạt
động, trả failed khi còn có thể trả, không khẳng định đã lưu audit record.

## 3. File thay đổi

| File/artifact | Thay đổi và mục đích |
| --- | --- |
| [service.py](../../../src/dacn_s01/service.py:97) | Một hunk làm diagnostic trong đường lỗi có thể serialize an toàn |
| [pyproject.toml](../../../pyproject.toml:7) | Chỉ tăng package `0.1.0a4` → `0.1.0a5` |
| [test_failure_diagnostics.py](../../../tests/phase3/test_failure_diagnostics.py) | 29 regression/đối chứng synthetic, không phụ thuộc suite audit bên ngoài |
| [run_phase3_fix_checks.py](../../../tools/run_phase3_fix_checks.py) | Ghi lệnh/cwd/môi trường/exit code/log trước–sau; chạy package đã cài ngoài source |
| [collect_phase3_fix_evidence.py](../../../tools/collect_phase3_fix_evidence.py) | Đối chiếu artifact, runtime/dependencies, file được bảo vệ và lịch process |
| Thư mục phụ lục này; wheel `0.1.0a5` | Bằng chứng và artifact bàn giao mới |

[production-changes.patch](production-changes.patch) đối chiếu code với wheel a4
và kiểm tra pyproject chỉ đổi version. 12/13 file package còn lại giữ nguyên byte,
bao gồm repository/revision/DDL, codec, validator và envelope checker. Không sửa,
xóa, skip hoặc nới kỳ vọng tests cũ. Không nâng/cài thêm dependencies, không đổi
runtime hay khởi tạo Git.

## 4. Kết quả thực chạy

| Build / lượt | Backend | Kết quả | Exit code |
| --- | --- | --- | ---: |
| a4, regression mới trước sửa | C | 14 failed, 15 passed | 1 |
| a4, regression mới trước sửa | Python | 14 failed, 15 passed | 1 |
| a4, suite audit P3-F1 | C + Python, fixture audit | 6 failed, 6 passed | 1 |
| a5, regression mới | C | 29 passed | 0 |
| a5, regression mới | Python | 29 passed | 0 |
| a5, toàn bộ Đợt 1–3 | C | 893 passed | 0 |
| a5, toàn bộ Đợt 1–3 | Python | 893 passed | 0 |
| a5, suite audit P3-F1 chạy lại | C + Python, fixture audit | 12 passed | 0 |
| a5, suite audit F1/F2 cũ | C + Python, fixture audit | 12 passed | 0 |
| a5, suite extended audit ngày 17/10 | C + Python, fixture audit | 36 passed | 0 |
| a5, `pip check` | — | No broken requirements found | 0 |
| a5, build và install wheel local | — | Cả hai thành công, `--no-index --no-deps` | 0 |

893 = 864 tests hiện có + 29 regression mới. Không failed/skipped trong các lượt
sau sửa. Cùng tình huống chạy hai backend không phải hai yêu cầu độc lập. Không
chạy lại full suite a4 trong lượt này: số 864/backend của a4 là kết quả audit đã
cung cấp; các lượt **trước sửa thực chạy lần này** chỉ là ba dòng đầu bảng.

Instrumentation quan sát encoder factory thật:

| Lượt | C calls | Python calls |
| --- | ---: | ---: |
| Regression trước sửa, C | 839 | 0 |
| Regression trước sửa, Python | 0 | 839 |
| Regression sau sửa, C | 1221 | 0 |
| Regression sau sửa, Python | 0 | 1221 |
| Full suite sau sửa, C | 6390 | 0 |
| Full suite sau sửa, Python | 0 | 6390 |

Suite audit bên ngoài tự chọn backend và chạy `--noconftest`; không gán số
instrumentation project cho suite audit. Các suite đã được đọc và dùng để sửa lỗi,
nên đây là kiểm tra hồi quy theo audit, không phải một cuộc audit mù mới.

Logs/lệnh thực: [before-test-results.txt](before-test-results.txt),
[before-commands.json](before-commands.json), [after-test-results.txt](after-test-results.txt),
[after-commands.json](after-commands.json), [build-results.txt](build-results.txt),
[build-commands.json](build-commands.json).

### Oracle của regression mới

| Nhóm | Số ca/backend | Kiểm tra độc lập và kết quả mong đợi đã đạt |
| --- | ---: | --- |
| Ba vị trí audit × create/update/request sai cấu trúc | 9 | Literal `failed/PROCESSING_FAILED`, no snapshot/handoff; parse passed, schema failed, hai lớp sau not_run; đọc raw BLOB/request/run đúng sau mở connection mới; update giữ nguyên head/snapshot cũ; SQL kiểm đếm và FK độc lập |
| Error biểu diễn được đi cùng error không biểu diễn được | 2 | Giữ nguyên `MISSING_FIELD /context`, details `{field: context}`; thêm PROCESSING_FAILED, không mất lỗi thường |
| Ba vị trí × chuỗi thường/astral/lone surrogate/surrogates có ký tự ngăn | 12 | Vẫn rejected đúng INVALID_PRIORITY/UNSUPPORTED_SCHEMA_VERSION/UNKNOWN_FIELD; giữ nguyên actual hoặc field/pointer, roundtrip và lookup được |
| Ba cách biểu diễn tại title | 3 | Cặp literal vẫn failed theo giới hạn codec; escape pair và UTF-8 scalar U+10000 vẫn validated, giữ đúng scalar |
| Fault injection trong đường lưu failed run | 3 | Lỗi trước BEGIN: giữ cả lỗi persistence và processing, không record; lỗi sau insert source: rollback toàn bộ; mất xác nhận sau commit: đọc lại đúng failed run đã lưu, không gửi lại |

Expected codes, checks, pointers, metadata và số record được viết trực tiếp trong
tests; kiểm DB dùng SQL riêng, không lấy kết luận từ comparator/decision của
implementation. Tests còn xác nhận codec vẫn từ chối serialize hai surrogate
literal, lookup lặp không đổi timestamp/build, raw input có khoảng trắng đầu/cuối
giữ nguyên, request sai cấu trúc giữ số thập phân chính xác khi `run.request=null`.

### Concurrency và lỗi persistence cũ được chạy lại

[after-concurrency-fault-evidence.json](after-concurrency-fault-evidence.json)
có 36 record thực chạy từ full suite, gồm lịch sự kiện và trạng thái DB cuối:

- Năm lịch hai process/hai connection/cùng DB, trên mỗi backend: hai unchanged
  cùng thành công (head 1); cùng thay đổi và hai thay đổi khác nhau có một revision
  mới/một conflict (head 2); unchanged trước change cùng thành công (head 2);
  change trước unchanged làm lần dùng base cũ conflict (head 2).
- IPC/deadline và quan sát `SQLITE_BUSY` thật chứng minh contention; collector
  kiểm `busy(B) < before_commit(A) < after_begin(B)`. Không thay bằng sleep hoặc
  chạy tuần tự.
- Kill process thật tại điểm trước/sau commit trả `-9`; mở connection mới thấy
  trước commit không record, sau commit có trọn source/run/snapshot/head.
- Fault injection trước/sau insert, trước commit, mất acknowledgement, rollback
  update và commit chưa rõ; khóa BEGIN/COMMIT thật đều được chạy lại.

Ba ca fault injection mới của P3-F1 nằm trong log/test regression; không gộp thành
ca kill process hoặc tuyên bố chúng là lỗi phần cứng thật.

## 5. Artifact, runtime và bảo vệ dữ liệu

[environment-manifest.json](environment-manifest.json) chứa hash source, installed,
wheel và project files; versions/dependencies thực tế; validator build và đường
dẫn import non-editable. [evidence-verification.txt](evidence-verification.txt)
ghi kết quả collector đã chạy thành công.

- CPython **3.13.16**, GIL bật, macOS arm64; SQLite **3.53.1**.
- `jsonschema 4.26.0`, `simplejson 4.2.0`, `pytest 9.1.1`; dependencies và binary
  runtime/C extension không đổi so với baseline.
- **13/13 file package** giống nhau giữa source–installed–wheel; METADATA/WHEEL
  và hash wheel trong `direct_url.json` của bản cài khớp.
- **111/113 file inventory giữ nguyên**. Hai thay đổi chủ ý là `service.py` và
  version trong `pyproject.toml`; không có ngoại lệ khác. Xem
  [protected-files-verification.json](protected-files-verification.json).
- AGENTS, contract, plan, schema nguồn/đóng gói, LaTeX, clinic example, sáu JSON
  minh họa, tests/tools cũ và các báo cáo/audit/wheel cũ trong inventory giữ nguyên.
  Không sao chép hoặc ghi vào dataset.

Wheel mới: [dacn_s01-0.1.0a5-py3-none-any.whl](../../../dist/dacn_s01-0.1.0a5-py3-none-any.whl).
SHA-256: `5b3dbc9feac551a727896555f60282c5170d93b7a042cb79ffec01b68493da82`.

Wheel a4 giữ nguyên: `c20caa13ca9fa66253ebad5d21be7cdef1eab28b2faab498975e1f1566f3bfb1`.
Validator build a5:
`dacn-s01/0.1.0a5+sha256:0e62d39ed4162c257ed0af4134e4321c1c1f4df44cdcff8771d0777abb43866f`.
[artifact-sha256.json](artifact-sha256.json) là index hash artifacts trong phụ lục,
không tự hash chính nó.

## 6. Tái lập từ package đã cài, ngoài source

Các lệnh dưới đây dùng runtime/dependencies hiện có. Có thể cài lại wheel mới bằng
`pip install --no-index --no-deps --force-reinstall` rồi chạy trong vùng tạm riêng.
Không cần import từ `src` hoặc sửa PYTHONPATH. Logs của lượt bàn giao nằm ở mục 4;
lệnh dưới đây dùng để tái lập, không ghi đè các evidence đó.

```sh
S01_ROOT=/Users/macbookpro/Documents/DACN_implementation
S01_PY="$S01_ROOT/.venv/bin/python"
S01_TMP=$(mktemp -d -t dacn-p3-fix-review)
cd "$S01_TMP"
unset PYTHONPATH PYTEST_ADDOPTS PYTEST_PLUGINS
export PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHONDONTWRITEBYTECODE=1
"$S01_PY" -B -m pytest -c "$S01_ROOT/pyproject.toml" -s -v --tb=short -p no:cacheprovider "$S01_ROOT/tests" --encoder-backend=c
"$S01_PY" -B -m pytest -c "$S01_ROOT/pyproject.toml" -s -v --tb=short -p no:cacheprovider "$S01_ROOT/tests" --encoder-backend=python
"$S01_PY" -B -m pip check
```

Chạy riêng regression bằng cách thay đường dẫn `tests` thành
`tests/phase3/test_failure_diagnostics.py`. Chạy suite audit với đường dẫn tuyệt
đối trong `after-commands.json`, thêm `--noconftest`, bỏ `--encoder-backend`
(fixture audit chọn cả hai). `-B` và tắt cache tránh ghi vào vùng audit chỉ đọc.

Runner mới nhận `--phase before|after` và nhiều `--audit-test`, xác nhận version
đã cài trước khi chạy. Lượt `before` yêu cầu a4, `after` yêu cầu a5; mỗi subprocess
pytest chạy ngoài source với môi trường sạch như trong log. Build không fetch
dependency; đã dùng wheel non-editable của đúng version cho các lượt tương ứng.

## 7. Hạn chế và nội dung cần audit

- Xin agent audit review lại P3-F1 trên đúng **0.1.0a5**: diagnostic không thể
  serialize không tái nhập đường lỗi; error thường vẫn giữ; raw source/request
  được lưu khi kho hoạt động; không snapshot/handoff hoặc thay head ở lần failed.
- Fallback chỉ bảo đảm phần diagnostics trong phạm vi lỗi này. Adapter vẫn cần
  cung cấp request/source metadata/ID biểu diễn được như tiền điều kiện service;
  chưa chứng minh đường trả lỗi cho mọi metadata sai, hook/clock hỏng hoặc cạn
  tài nguyên tiến trình. Không thay codec để chấp nhận cặp surrogate literal.
- Nếu bỏ một diagnostic vì không thể biểu diễn, envelope báo PROCESSING_FAILED;
  chi tiết giá trị/vị trí nguyên gốc phải xem raw source. Không giả vờ đây là một
  schema rejection đầy đủ.
- Đã chạy các ca SQLite/IPC/kill và fault injection mô tả ở trên trên môi trường
  pinned; chưa kiểm chứng mất điện, disk-full hoặc lỗi phần cứng. Không nâng tuyên
  bố durability vượt bằng chứng baseline.
- Chưa chạy CLI/receipt/API recovery/idempotency hoặc S02; không đánh giá ngữ nghĩa
  nghiệp vụ. AGENTS vẫn tham chiếu flow S02 cũ; cần đồng bộ trước khi triển khai S02,
  giữ nguyên file trong đợt sửa này theo chỉ đạo.
- Không tự đóng finding hoặc ghi nhận đã được audit/được duyệt. Dừng trước Đợt 4,
  chờ kết quả audit của người dùng.

**Đợt 3 đã implement và kiểm thử, chờ audit; chưa nghiệm thu toàn bộ S01.**
