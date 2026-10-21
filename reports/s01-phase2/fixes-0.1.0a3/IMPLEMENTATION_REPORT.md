# S01 Đợt 2 — sửa F1/F2 sau audit

**Đã implement và kiểm thử; chờ agent audit review lại, chưa nghiệm thu.**
Ngày bàn giao: 13/10/2026. Bản sửa: `dacn-s01 0.1.0a3`; baseline: `0.1.0a2`.
Contract giữ nguyên `0.1.0-draft.2`, input schema `1.0.0`.

Đây là phụ lục cho [báo cáo 0.1.0a2](../IMPLEMENTATION_REPORT.md). Báo cáo, logs,
manifest và wheel cũ được giữ nguyên làm lịch sử; các khẳng định trong báo cáo cũ
phải đọc trong phạm vi suite/bản build lúc đó. Hai lỗi audit cho thấy 724 tests
pass của baseline chưa bao phủ đủ lỗi kiểu lồng trong `anyOf` và pointer lỗi parse.

## 1. Nguyên nhân và thay đổi

### F1: giữ lỗi bên trong nhánh anyOf phù hợp

Code cũ bỏ mọi child error có `validator == "type"`. Vì vậy lỗi kiểu tại
`constraint.kind` bị bỏ cùng lỗi chọn nhánh `null`: trường hợp chỉ sai `kind`
bị báo sai ở object cha; trường hợp đồng thời thiếu `value` hoặc thừa `extra`
bị mất lỗi `kind`.

[validation.py](../../../src/dacn_s01/validation.py) nay xác định nhánh sai kiểu
bằng cả ba dấu hiệu có cấu trúc của `ValidationError`: keyword `type`,
`absolute_path` trùng node `anyOf`, và `schema_path` tương đối có dạng
`[branch_index, "type"]`. Với schema đóng gói hiện tại, cấu trúc này cũng áp dụng
cho nhánh đi qua `$ref` local. Chỉ loại lỗi thuộc nhánh sai kiểu đó; giữ các lỗi
ở bên trong nhánh phù hợp và ánh xạ đệ quy như trước. Khi tất cả nhánh đều sai
kiểu tại node, trả một `TYPE_MISMATCH` tại node với hợp các kiểu cho phép.

Không hardcode `constraint.kind`, vị trí nhánh object, hoặc parse message thư viện.
Các pointer/details, sort/deduplicate vẫn đi qua bộ ánh xạ và `ordered_errors`
hiện có; không thay dữ liệu, schema hoặc W. Kiểm thử thêm schema synthetic có
hai lớp nullable và đảo thứ tự nhánh nhằm kiểm tra trực tiếp tính cấu trúc của sửa đổi.
Đây là test riêng cho adapter, không mở rộng input schema.

### F2: pointer lỗi parse bắt buộc null

Code cũ chỉ kiểm tra cú pháp pointer và miễn yêu cầu non-null cho stage parse,
nên vẫn cho qua `""` hoặc `"/invented/path"`.

[envelope.py](../../../src/dacn_s01/envelope.py) nay bắt buộc `pointer is None`
khi stage đã được xác minh là `parse`, bao phủ `INVALID_JSON` và
`DUPLICATE_JSON_KEY`. Các stage khác giữ quy tắc hiện có. `byte_offset` vẫn tùy
chọn; tests dùng cả details không có offset và offset synthetic hợp lệ.

## 2. File thay đổi và phạm vi

| File | Thay đổi |
| --- | --- |
| `src/dacn_s01/validation.py` | Một hunk sửa cách chọn lỗi nhánh `anyOf` |
| `src/dacn_s01/envelope.py` | Một hunk thêm invariant pointer parse |
| `pyproject.toml` | Chỉ tăng package version `0.1.0a2` → `0.1.0a3` |
| [test_audit_regressions.py](../../../tests/phase2/test_audit_regressions.py) | 41 ca synthetic, kỳ vọng literal độc lập từ contract |
| [run_phase2_fix_checks.py](../../../tools/run_phase2_fix_checks.py) | Ghi lệnh/cwd/môi trường/kết quả trước và sau sửa; đường dẫn suite audit nhận qua argument |
| [collect_phase2_fix_evidence.py](../../../tools/collect_phase2_fix_evidence.py) | Đối chiếu package/wheel/source, runtime/dependencies và protected hashes; ghi riêng phụ lục này |
| Thư mục báo cáo này và wheel `0.1.0a3` | Bằng chứng trước/sau, manifest và artifact bàn giao |

[production-changes.patch](production-changes.patch) là diff byte-source với
wheel `0.1.0a2` được giữ lại. Các file cũ trong manifest chỉ thay đổi đúng hai
module và version trong pyproject; tests/tools cũ giữ nguyên. Không xóa, skip hoặc
nới kỳ vọng test cũ để đạt kết quả. Không cài mới/nâng dependency.

## 3. Kết quả thực chạy, tách trước và sau sửa

Các kết quả dưới đây là chạy code thật trên package đã cài non-editable. Dữ liệu
test và candidate envelope là **synthetic**, không phải run/snapshot đã commit.

| Build / lượt | Backend | Kết quả | Exit code |
| --- | --- | --- | ---: |
| `0.1.0a2`, regression mới, trước sửa production code | C | 25 failed, 16 passed | 1 |
| `0.1.0a2`, regression mới, trước sửa production code | Python | 25 failed, 16 passed | 1 |
| `0.1.0a2`, suite audit gốc chạy lại trước sửa | C + Python, fixture của audit | 10 failed, 2 passed | 1 |
| `0.1.0a3`, regression mới | C | 41 passed | 0 |
| `0.1.0a3`, regression mới | Python | 41 passed | 0 |
| `0.1.0a3`, toàn bộ Đợt 1 + 2 | C | 765 passed | 0 |
| `0.1.0a3`, toàn bộ Đợt 1 + 2 | Python | 765 passed | 0 |
| `0.1.0a3`, suite audit gốc chạy lại | C + Python, fixture của audit | 12 passed (6/backend) | 0 |
| `0.1.0a3`, pip check | — | No broken requirements found | 0 |

765 = 724 ca hiện có + 41 regression; cùng suite chạy hai backend, không phải
1.530 yêu cầu độc lập. Không failed/skipped trong các lượt sau sửa. Con số 724 pass
trên baseline là bằng chứng lịch sử, không phải lượt full suite mới chạy trước sửa.

Instrumentation hiện có đo lời gọi encoder thật:

| Lượt | C factory calls | Python factory calls |
| --- | ---: | ---: |
| Regression trước sửa, chọn C | 85 | 0 |
| Regression trước sửa, chọn Python | 0 | 85 |
| Regression sau sửa, chọn C | 109 | 0 |
| Regression sau sửa, chọn Python | 0 | 109 |
| Full suite sau sửa, chọn C | 805 | 0 |
| Full suite sau sửa, chọn Python | 0 | 805 |

Suite audit ngoài codebase tự chọn hai backend bằng fixture riêng; chạy với
`--noconftest`, không dùng instrumentation của project. Không gán các số factory
calls ở trên cho suite audit. File audit được đọc để sửa lỗi và chạy lại theo yêu
cầu, nên kết quả 12 pass là kiểm tra hồi quy trên suite do agent audit cung cấp,
không phải đánh giá mù mới hoặc kết luận audit chấp nhận bản sửa.

### Bao phủ regression mới

| Nhóm | Oracle/kết quả kiểm tra |
| --- | --- |
| Ba ca F1 audit | `kind:123` có TYPE tại `/constraints/0/constraint/kind`, expected `string`, actual `number`; thiếu `value` giữ thêm MISSING; thừa `extra` giữ thêm UNKNOWN, đúng thứ tự |
| Kiểu `kind` khác | null/bool/array/object: đúng pointer và actual_type, không báo sai kiểu object cha |
| Đối chứng nullable | `constraint:null` và object hợp lệ passed; số/bool/array/string ở node constraint chỉ có một TYPE, expected `object,null` |
| Nullable khác/lồng nhau | `details` sai `trigger`, `data` và thừa field giữ đủ lỗi; schema synthetic hai lớp nullable, cả hai thứ tự nhánh, giữ TYPE của `box.label` |
| Hai mã parse | Null được nhận; `""` và `/invented/path` bị từ chối; kiểm cả object nội bộ và sau codec roundtrip, có/không có offset |
| Invariants liên quan | Schema/parse rejected đúng checks và lớp phụ thuộc not_run; không normalized input/snapshot/handoff; không đổi rejected thành failed; processing failure vẫn failed; stage schema/system không bị ép pointer null |

Các expected paths/types/codes được viết trực tiếp trong tests; tests chính thức
không import hoặc phụ thuộc đường dẫn tuyệt đối của workspace audit. F1 còn kiểm
bảo toàn input và candidate qua vòng serialize/parse. Full suite giữ kiểm thử sort,
deduplicate, W, version, unknowns, số chính xác, codec và các envelope invariants cũ.

## 4. Môi trường, cách chạy và evidence

Giữ CPython **3.13.16 regular GIL**, macOS arm64; jsonschema **4.26.0**,
simplejson **4.2.0**, pytest **9.1.1**, setuptools **80.9.0**, wheel **0.45.1**.
Manifest so toàn bộ distributions với baseline, trừ version chính package DACN.
Checksum runtime executable và C extension cũng không thay đổi.

Runner khởi chạy từng lượt pytest bằng process riêng, cwd là thư mục tạm **ngoài
project**, bỏ `PYTHONPATH`, `PYTEST_ADDOPTS`, `PYTEST_PLUGINS`; đặt
`PYTEST_DISABLE_PLUGIN_AUTOLOAD=1`, dùng `-B` và `-p no:cacheprovider`. Không ghi
bytecode/cache vào thư mục audit chỉ đọc. Cờ `-c` và test path tuyệt đối chỉ trỏ
config/tests; import code từ package đã cài trong site-packages.

Các lệnh chính đã chạy từ project root, theo thứ tự:

```sh
# Đã chạy lúc package/source còn là 0.1.0a2, trước sửa production code.
.venv/bin/python -B tools/run_phase2_fix_checks.py --phase before --audit-test /path/to/test_phase2_audit.py

# Sau khi sửa source/version; chỉ build và cài package DACN, không resolve dependencies.
.venv/bin/python -m pip wheel --no-index --no-deps --no-build-isolation --wheel-dir dist .
.venv/bin/python -m pip install --no-index --no-deps --force-reinstall dist/dacn_s01-0.1.0a3-py3-none-any.whl
.venv/bin/python -B tools/run_phase2_fix_checks.py --phase after --audit-test /path/to/test_phase2_audit.py
```

`/path/to/test_phase2_audit.py` là placeholder để tái lập; đường dẫn thực đầy đủ,
argv, cwd và exit code của từng process được giữ trong các log/JSON bên dưới.
Runner `before` sẽ từ chối môi trường đang cài `0.1.0a3`: tái lập baseline cần
cài wheel `0.1.0a2` trong môi trường riêng, không coi kết quả bản sửa là baseline.
Collector cũng chạy từ cwd tạm ngoài project với executable venv và script path
tuyệt đối; lệnh chính xác trong `evidence-verification.txt`.

- [before-test-results.txt](before-test-results.txt), [before-commands.json](before-commands.json): failures trước sửa, bao gồm suite audit.
- [after-test-results.txt](after-test-results.txt), [after-commands.json](after-commands.json): regression, full suite, instrumentation, pip check và audit sau sửa.
- [baseline-0.1.0a2.json](baseline-0.1.0a2.json): xác minh source/installed/wheel trước sửa.
- [build-install.txt](build-install.txt): build/install bản sửa, cả hai lệnh exit 0.
- [environment-manifest.json](environment-manifest.json): môi trường đo thực tế, hashes từng file source/installed/wheel, tests/tools, direct_url chứng minh cài từ wheel.
- [protected-files-before.json](protected-files-before.json), [protected-files-verification.json](protected-files-verification.json): cả **45 file** giữ nguyên, gồm contract/plan/AGENTS, locks, schema/provenance, codec, dữ liệu/LaTeX nguồn, reports cũ, wheel baseline và ba artifact audit.
- [evidence-verification.txt](evidence-verification.txt): collector exit 0; **9 package files** khớp byte giữa source đang review, package đã cài và wheel; W giữ đủ 29 code point không đổi.

Các checksum SHA-256 chính của bản sửa:

| Artifact | SHA-256 |
| --- | --- |
| `dist/dacn_s01-0.1.0a3-py3-none-any.whl` | `859f96c8def6cd3be7544c652e648ed36f4884dd307fffc6bbe090716937e830` |
| `validation.py` (source = installed = wheel entry) | `565ef5d0e33cb3b8baa344da423edb34401b78379905c3cd7899700b227f61a5` |
| `envelope.py` (source = installed = wheel entry) | `539ae0dbc2c6b7712916d8f3e84e0b87e5deab1a6eacd42767fe5713675b11cc` |

## 5. Giới hạn và nội dung cần audit lại

Agent audit cần review việc phân biệt lỗi kiểu ngay tại nhánh với lỗi con qua
`schema_path`/`absolute_path`, tính đầy đủ của lỗi độc lập và việc F2 chỉ siết
pointer tại stage parse. Bằng chứng áp dụng cho schema đóng gói và phiên bản
jsonschema đã pin; không tuyên bố adapter hỗ trợ mọi schema bên ngoài tùy ý.

Giữ các giới hạn codec/nền tảng đã ghi ở Đợt 1–2. Chưa kiểm thử nền tảng khác hoặc
mọi input kích thước bất kỳ. Không bổ sung persistence, revision service, SQLite,
CLI nghiệp vụ, receipt hoặc S02. Các script trong `tools/` chỉ phục vụ kiểm thử và
thu bằng chứng, không tạo source/run/snapshot nghiệp vụ.

Input hợp lệ vẫn dừng ở **`revision: not_run`**. Checker envelope vẫn chỉ xác minh
candidate; không chứng minh commit/provenance hay phát handoff thực. Không xác nhận
requirements đúng nghiệp vụ hoặc đủ thông tin. **Dừng trước Đợt 3; bàn giao bản
sửa F1/F2 để agent audit review lại.**
