# S01 Đợt 4 — CLI và bàn giao local

**Đã implement và kiểm thử; đề nghị audit toàn bộ S01. Chưa nghiệm thu S01.**
Ngày bàn giao: **18/10/2026**. Package **`0.1.0a6`**. Baseline **`0.1.0a5`** đã
đạt audit trong phạm vi Đợt 3, P3-F1 đóng theo kết quả người dùng cung cấp và
[audit a5](/Users/macbookpro/.codex/.chatgpt-projects/g-p-68c38c8799f48191a101e19a975ca4f9/outputs/audits/s01-phase3-0.1.0a5/audit-evidence.json).
Kết luận đó không được mở rộng thành chấp nhận Đợt 4 hoặc toàn bộ S01.

Output contract giữ nguyên **`0.1.0-draft.2`**, input schema **`1.0.0`**, DB
structure **`1`**. Không triển khai S02, LLM, KB, renderer, API, web UI, prune hay
backup. Tất cả tests/walkthrough dưới đây dùng **synthetic input** và kho tạm riêng;
CLI, SQLite, filesystem, subprocess, lock và kill là **thực chạy**.

## 1. Căn cứ và baseline

Đã đọc AGENTS, contract, kế hoạch (đặc biệt 5.4, 6–10), báo cáo Đợt 3/a5,
code/tests/API hiện có và audit mới nhất trước khi sửa. Đã trình bày command,
config, receipt, output/error contract trước implementation.

[baseline-verification.json](baseline-verification.json) xác nhận lúc bắt đầu:
13 file package a5 khớp source–installed–wheel, các file trong manifest a5 khớp,
Python/SQLite/dependencies không drift; không có thay đổi chưa hiểu.
[protected-files-before.json](protected-files-before.json) chụp **133 file** trước
thay đổi. AGENTS, nguồn LaTeX, contract/plan, schema, clinic example, sáu JSON minh
họa, tests/tools/báo cáo/wheel/audit cũ được giữ nguyên.

AGENTS vẫn tham chiếu flow S02 cũ. Việc đồng bộ với nguồn hiện hành là đầu việc
**trước S02**, không chỉnh AGENTS trong lượt này. Quyết định triển khai Đợt 4 của
người dùng là căn cứ cho CLI; không sửa nhãn proposed trong tài liệu contract/plan.

## 2. Phạm vi và file thay đổi

| File/artifact | Trách nhiệm và lý do |
| --- | --- |
| [__main__.py](../../src/dacn_s01/__main__.py) | Entry point `python -m dacn_s01` của package cài |
| [cli.py](../../src/dacn_s01/cli.py) | Parse flags, gọi service/repository, stdout/stderr/exit codes, receipt trước submit và lỗi giao nhận |
| [local_io.py](../../src/dacn_s01/local_io.py) | TOML, kiểm operational metadata/path identity, dataset guards, receipt và publish file không ghi đè |
| [repository.py](../../src/dacn_s01/repository.py) | Thêm `verify`, `get_snapshot_revision`, `list_runs`; tái dùng checked lookup trong một read transaction |
| [pyproject.toml](../../pyproject.toml) | Chỉ tăng version a5 → a6; không đổi dependencies/build backend |
| [tests/phase4](../../tests/phase4) | 93 E2E/integration cases, harness subprocess/IPC, oracle literal/SQL/bytes riêng |
| [run_phase4_checks.py](../../tools/run_phase4_checks.py), [collect_phase4_evidence.py](../../tools/collect_phase4_evidence.py) | Build/install/test logs, instrumentation, identity/protected hashes và kiểm bằng chứng |
| [Hướng dẫn local](../../docs/S01_LOCAL_GUIDE.md), [fixture synthetic](../../docs/examples/s01-local/synthetic-clinic.input.json) | Cách setup theo lock, config, chạy và recovery; fixture mới, không thuộc dataset bên ngoài |
| Thư mục báo cáo này, wheel a6 | Artifacts bàn giao và lịch sử kiểm thử của đợt |

[production-changes.patch](production-changes.patch) là diff so với wheel a5.
Trong các module đã có, **chỉ repository thêm lookup**; service, comparator,
validation/envelope/codec/schema/DDL giữ nguyên byte. Không tạo implementation
validation/revision thứ hai trong CLI. Không sửa hoặc nới kỳ vọng tests Đợt 1–3.

## 3. Command/config/output contract thực tế

Global flags `--config`, `--state-dir` đứng trước tên lệnh; không chọn kho từ home
hoặc config tự phát hiện. Lỗi quá sớm chưa có đủ ngữ cảnh chỉ trả stderr/exit,
không dựng envelope/record giả.

| Lệnh | Input bổ sung | Output |
| --- | --- | --- |
| `init` | Kho chọn rõ | JSON `{state_dir, database}`; khởi tạo hoặc xác minh DB |
| `submit` | `--input`, `--mode`, **`--receipt` bắt buộc**; `--spec-id`, `--base-revision`, `--output` tùy chọn | Một envelope JSON stdout; export nếu yêu cầu |
| `show-run` | `--run-id` hoặc `--receipt`, không cả hai | Envelope đã lưu; export tùy chọn |
| `show-snapshot` | `--snapshot-id` hoặc cặp `--spec-id --revision` | Đúng snapshot lịch sử; không retarget sang head; export tùy chọn |
| `show-source` | `--source-id --output` | File nguyên byte; stdout trống |
| `list-runs` | `--spec-id`, export tùy chọn | Mảng checked envelopes; `[]` nếu không có liên quan |

`list_runs` đọc các run trong một transaction và kiểm liên kết hiện có, chọn run
có snapshot thuộc spec hoặc `run.request.spec_id` khớp. Bao gồm unchanged và
rejected/failed có request biểu diễn được; có thể tra rejection cho spec chưa tồn
tại. Request null cần run ID/receipt; request gốc vẫn tra được qua API `get_request`.
Sắp `(received_at, run_id)` là thứ tự hiển thị ổn định, không tuyên bố commit order.
Bản local chưa phân trang/index metadata mới; chi phí đọc tất cả run là trade-off
để không thêm DDL/JSON extraction và giữ invariants đã có.

TOML nhận đúng `state_dir`, `busy_timeout_ms` (integer 0…2147483647, mặc định 5000),
`dataset_roots` (mảng thư mục **đã tồn tại**, mặc định `[]`). `--state-dir` ưu tiên
config. Relative paths trong config tính từ parent config đã resolve, flags tính
từ cwd; không expand `~` trong TOML. Key/kiểu sai là lỗi cấu hình. Yêu cầu dataset
roots đã tồn tại giúp phát hiện typo và kiểm identity filesystem, không bỏ qua
một vùng nguồn tưởng đã được bảo vệ. Đây là lựa chọn operational, không thay input
schema hoặc nghĩa của requirements.

Kho là `state_dir/s01.sqlite3`. Init chỉ tạo thư mục state cuối cùng, parent phải
có sẵn; submit/lookup không initialize/reset. DB foreign/khác version/thiếu trigger
bị từ chối. `verify()` vẫn dùng connection/read transaction của repository; lookup
có thể kích hoạt recovery SQLite nên path guard áp dụng cả cho lookup.

Flags là adapter syntax: token số hợp lệ được parse bằng Decimal, không float.
`--base-revision oops` trả usage 64; `1.5`/`0`, mode/routing sai hoặc update thiếu
spec/base đi vào service để báo `INVALID_REQUEST`, với stage phụ thuộc input như
baseline. CLI không tự biến update lỗi thành create hoặc bỏ field routing sai.

| Exit | Hành vi |
| --- | --- |
| 0 | Init, submit validated, lookup/export thành công |
| 2 | Submit rejected |
| 3 | Failed hoặc lỗi filesystem/config/receipt/persistence/giao nhận |
| 64 | Cú pháp dùng CLI sai trước tiếp nhận |
| 4 | Lookup không tìm thấy record; không chứng minh submission trước thất bại |

JSON được serialize hoàn chỉnh bằng codec trước khi xuất; không log/banner/
traceback vào stdout. Stderr dùng thông báo có kiểm soát, không dump payload hoặc
exception chứa payload. Export publish trước stdout; export lỗi có thể không có
stdout. Stdout pipe bị đóng được xử lý exit 3, không để shutdown flush đổi thành
exit 120. Output bị cắt không phải envelope hợp lệ. Lookup exit 0 chỉ là đọc thành
công, kể cả khi envelope đã lưu có status rejected/failed.

## 4. Receipt, atomic publication và recovery

Receipt operational có đúng ba trường, không nằm trong envelope:

```json
{"receipt_version":"1","run_id":"ILLUSTRATION_ONLY","state_dir":"/resolved/local/state"}
```

JSON trên là **minh họa**, không phải receipt đã chạy. Format có version riêng để
không nhầm với schema input/output hoặc revision. CLI tạo UUID bằng điểm cấp ID
của service trước khi submit, path kho đã resolve. Không thêm timestamp hay trạng
thái thành công vào receipt vì chúng không chứng minh commit.

Trình tự thực:

1. Parse flags/config, kiểm metadata biểu diễn được và path protections; kiểm kho
   đã tồn tại/hợp cấu trúc, đọc input bytes một lần. Chưa có submit S01.
2. Cấp run ID; tạo temp 0600 bằng `O_CREAT|O_EXCL|O_NOFOLLOW` trong chính parent
   directory output đã kiểm. Giữ directory descriptor, không dùng global temp dir.
3. Ghi toàn bộ receipt, flush buffer, `fsync(file)`; dùng `os.link` với directory
   descriptors để tạo tên đích mới. Tên đã có không bị thay; không dùng rename
   overwrite hoặc `os.replace`.
4. Xóa temp của chính lần này, `fsync(directory)`. Chỉ khi toàn bộ bước hoàn tất
   mới gọi service với run ID đã ghi. Hai process tranh receipt có tối đa một bên
   qua publication để submit.
5. Service thực hiện transaction Đợt 3 nguyên trạng. CLI serialize/export/stdout
   kết quả trả về; lỗi giao nhận không gọi lại submit hoặc sửa record đã commit.

Cách dùng `dir_fd`, hard link và flush/fsync dựa trên API standard library đã
đối chiếu [Python os.link](https://docs.python.org/3.13/library/os.html#os.link),
[os.fsync](https://docs.python.org/3.13/library/os.html#os.fsync); TOML dùng
[tomllib](https://docs.python.org/3.13/library/tomllib.html). Hành vi filesystem local
được kiểm bằng hai process/IPC và lỗi I/O trong suite, không chỉ suy từ “ghi file
xong”. Không có fallback sang cơ chế overwrite khi OS không hỗ trợ thao tác.

| Điểm lỗi | Artifact/trạng thái và cách xử lý |
| --- | --- |
| Trước link, gồm file fsync lỗi | Không bắt đầu S01 submit; temp riêng được cố dọn. Crash/cleanup lỗi có thể để lại temp |
| Sau link, trước hoặc tại directory fsync | Có thể có receipt hoàn chỉnh nhưng durability chưa được xác nhận; không bắt đầu S01 submit, không xóa tên đích |
| Receipt đã có | Từ chối submit; hướng dẫn `show-run --receipt`, không tái dùng run ID để submit |
| Kill sau receipt, trước commit | Receipt còn; lookup có thể trả 4. Chưa thấy run không kết luận submission trước chắc chắn thất bại |
| Kill sau commit, chưa stdout | Receipt tra lại đầy đủ envelope/source/snapshot đã lưu |
| Export/stdout lỗi sau commit | Exit 3/stderr hướng dẫn receipt/run ID; giữ DB nguyên, không tạo thêm run/revision |
| Explicit kho khác receipt | Báo mâu thuẫn. Symlink/alias filesystem tới cùng kho được coi là cùng location |

Xuất file cũng dùng cùng publisher, không overwrite. Export fsync lỗi có thể để
lại file hoàn chỉnh; người dùng tra DB và xuất sang tên mới. Không tuyên bố receipt
là commit proof, idempotency key, hoặc exactly-once. Chỉ đối soát run ID/checked
record khi mất phản hồi. Không tự retry submit; retention giữ toàn bộ lịch sử và
artifacts, không có prune.

## 5. Bảo vệ đường dẫn và metadata

Mọi đường ghi state/DB/sidecar/receipt/export/temp đều qua guard. Dataset roots,
state và input/config/receipt đọc được resolve; guard so cả path lẫn file identity.
Containment còn kiểm identity các ancestor để nhận alias hoa/thường hoặc Unicode
trên filesystem macOS không phân biệt các cách viết. Không normalize text/ID của
requirements để đạt kiểm tra đường dẫn.

Receipt/export phải ngoài state lẫn dataset, và parent đã tồn tại. Từ chối file
đích đã có, kể cả symlink dangling. DB/`-journal`/`-wal`/`-shm` phải là regular files
không symlink/hard-link alias (`st_nlink==1`); tránh SQLite sửa một nguồn không biết
qua hard link. Paths đọc được bảo vệ bằng samefile, không chỉ so tên.

Metadata do adapter tạo có chuỗi UTF-8 biểu diễn được, không NUL; request dùng codec
trước receipt. Giá trị requirements trong raw input không bị kiểm/sửa theo policy
metadata: các ca Unicode P3-F1 vẫn vào service, trả failed/PROCESSING_FAILED và
giữ raw BLOB. Unicode path bình thường được hỗ trợ; argv/path có surrogateescape
không thể biểu diễn an toàn bị lỗi vận hành trước receipt, không thay ký tự.

Guard là bảo vệ dữ liệu local đã khai báo, không phải sandbox chống user/process
khác cố ý đổi directory/mount/symlink giữa các bước. Không bảo vệ root chưa khai
báo, không can thiệp shell redirect đã truncate file trước khi CLI chạy. Dùng
`--output` thay redirect vào file nguồn. Thư mục state/output phải do người dùng
kiểm soát và không bị retarget đồng thời. Các giới hạn này có trong hướng dẫn local.

## 6. Kiểm thử thực chạy và bằng chứng

Các lượt cuối chạy **package a6 cài non-editable ngoài source**, môi trường bỏ
PYTHONPATH/PYTEST_ADDOPTS/PYTEST_PLUGINS, tắt autoload plugin và bytecode/cache vào
vùng nguồn/audit. E2E worker dùng `runpy.run_module('dacn_s01', run_name='__main__')`
trong subprocess để instrument backend và gắn IPC/fault hook; vẫn đi qua entry
point, argparse và CLI thật. Hook không có flag/config/env sản phẩm.

Đã chạy thêm `python -m dacn_s01` nguyên dạng trong E2E smoke và walkthrough 11 lệnh
ngoài source. Walkthrough gồm mọi command, create/unchanged/r2/stale, lookup r1 sau
r2 và export raw; input/config hashes trước/sau bằng nhau. Kho và ID trong log là
kết quả synthetic thực chạy, đã bị dọn cùng thư mục tạm, không phải dữ liệu nghiệp vụ.

| Lượt cuối / artifact | Kết quả | Exit |
| --- | --- | ---: |
| Development suite Đợt 4, C/Python sau path review | 93 passed/backend | 0 |
| Toàn bộ Đợt 1–4, C | **986 passed** | 0 |
| Toàn bộ Đợt 1–4, Python | **986 passed** | 0 |
| Suite audit P3-F1 do người dùng cung cấp | 12 passed, cả hai backend | 0 |
| Suite audit F1/F2 cũ | 12 passed, cả hai backend | 0 |
| Suite extended audit cũ | 36 passed, cả hai backend | 0 |
| Probe cross-field trong audit a5, chạy lại nguyên đoạn Python đã đọc | 4 passed, hai version origin × hai backend | 0 |
| Build/install wheel local; pip check | Thành công; No broken requirements found | 0 |
| Walkthrough real module CLI | 11 lệnh đúng output/exit mong đợi; stale cố ý exit 2 | 0/2 đúng ca |

986 = 893 tests Đợt 1–3/a5 giữ nguyên + 93 tests mới. Không failed/skipped trong
các lượt cuối. Không cộng các backend thành số yêu cầu độc lập và không coi suite
audit đã được đọc/chạy lại là audit mù chấp nhận a6.

Instrumentation đo factory thật trên lượt cuối:

| Nơi đo | Backend C: C/Python calls | Backend Python: C/Python calls |
| --- | --- | --- |
| Process pytest chính | 6597 / 0 | 0 / 6597 |
| 203 subprocess CLI hoàn tất có instrumentation/backend | 1610 / 0 | 0 / 1610 |

Không gộp vào số subprocess instrumented các child bị SIGKILL trước khi flush
telemetry, literal `python -m` smoke/walkthrough hoặc suite audit chọn backend
bằng fixture riêng. Kill events vẫn có PID/điểm IPC và DB state riêng.

### Ma trận bất biến được kiểm

| Nhóm | Oracle và bằng chứng thực |
| --- | --- |
| Lifecycle/routing | Literal status/result/checks/code/pointer/details; SQL số run/source/snapshot/spec; create→unchanged→edit→stale, không fallback hoặc retarget r1 |
| Lookup | Run/snapshot byte-values/metadata giữ nguyên; list gồm create/unchanged/update/conflict; spec thiếu có thể list rejection; read không tạo run; corruption data khi khôi phục DDL đúng vẫn bị guard từ chối |
| Nguồn và số | Read-only input, raw UTF-16/BOM/parse lỗi, 5001 chữ số, fraction >28 chữ số, signed zero kiểm Decimal tuple; export byte equality; legacy chỉ thêm version |
| Unicode/unknowns | Ba vị trí P3-F1 qua CLI; cross-field + lỗi an toàn, legacy/explicit; raw source/normalization giữ; null và criteria/order không thay; metadata không biểu diễn được bị chặn trước receipt |
| Config/kho | Relative paths, override, unknown/type/range/missing root; missing DB không init; foreign/version/DDL sai không reset; `busy_timeout_ms=0` khi khóa writer thật |
| Path guards | Spaces/Unicode, symlink parent/file, dangling links, same path/hard link input/config, DB/sidecars hard link, export trong state; ba điểm state/receipt/export thử alias hoa/thường thật trên filesystem hiện tại |
| Receipt race | Hai process, hai IPC socket, cùng dừng trước link; parent quan sát cả hai ready rồi giải phóng. Exit [0,3], đúng một run/source/snapshot/spec, receipt chỉ run thắng, không overwrite |
| Receipt lỗi | Inject lỗi tại `os.fsync` file/directory và `os.link`: zero run; directory-fsync lỗi để lại receipt hoàn chỉnh; EACCES receipt directory thật cũng zero run |
| Delivery lỗi | Pipe stdout đóng thật, file export bị process khác tạo sau commit, directory mất quyền ghi thật: exit 3, receipt lookup validated, vẫn một run/r1; inject export fsync file/directory cũng giữ committed record |
| Kill/recovery | SIGKILL thật tại receipt_ready, before_commit, after_commit qua IPC/deadline; receipt đã có; hai ca đầu zero records, ca sau đủ records và show-run trả validated |
| Regression nền | Toàn bộ W/regex/non-coercion/number/error/provenance của Đợt 1–3 chạy lại; năm lịch update cạnh tranh, real BEGIN/COMMIT lock và các điểm fault/kill cũ vẫn đạt |

Không dùng sleep hay chạy tuần tự làm bằng chứng tranh receipt/kill. Fault injection
được ghi riêng với actual I/O/locks và SIGKILL. [final-evidence.json](final-evidence.json)
chứa 36 records concurrency/fault Đợt 3, 28 records E2E/path/receipt Đợt 4 và 186
records tổng hợp instrumentation theo test (250 tổng). Những ca assertion khác
nằm trong code và verbose log, không được quảng cáo là record event riêng.

### Lịch sử phát triển được giữ lại

Lượt đầu Đợt 4 có 79 passed/backend; sau thêm ca có full suite 979 passed/backend.
Hai ca metadata bổ sung ban đầu gây **1 failed, 980 passed/backend** vì fixture cố
tạo filename byte `FF` bị filesystem macOS từ chối trước khi CLI chạy. Sửa fixture
để gửi argv không biểu diễn được trực tiếp, kiểm CLI từ chối trước mở file/receipt;
không skip, không sửa kỳ vọng core. Targeted rerun 2 passed/backend (38 deselected
do `-k`), full sau đó 981 passed/backend.

Rà soát tiếp phát hiện containment theo string chưa bao phủ alias hoa/thường của
thư mục trên filesystem hiện tại; đã bổ sung ancestor identity và yêu cầu dataset
root tồn tại, thêm năm ca, rebuild a6 trước lượt cuối 986/backend. Đây là phát hiện
và sửa trong development, chưa phải kết luận audit độc lập. Các build a6 trung
gian chỉ phục vụ đợt này; wheel bàn giao được xác định bằng hash mục 8. Baseline a5
không bị ghi đè.

Logs append giữ cả các lượt trên. `final-commands.json`/`final-evidence.json` trỏ
lượt cuối; các mốc trước sửa fixture và trước path review có bản JSON riêng để đối
chiếu. Collector từng dừng khi lượt metadata còn failed; chỉ chạy thành công và
ghi manifest bàn giao sau khi toàn bộ lượt cuối đạt.

## 7. Tái lập và chỉ mục bằng chứng

[Hướng dẫn local](../../docs/S01_LOCAL_GUIDE.md) có setup theo lock, config, tất cả
commands, source/criterion provenance, receipt tồn tại/chưa có run và lỗi giao
nhận. Fresh venv setup là hướng dẫn tái lập, không tự ghi đã tạo lại venv ở đợt này.
Không nâng runtime/dependencies vì baseline đủ dùng.

Chạy trực tiếp suite từ ngoài source, không ghi đè evidence bàn giao:

```sh
S01_ROOT=/path/to/DACN_implementation # placeholder
S01_PY="$S01_ROOT/.venv/bin/python"
S01_CHECK=$(mktemp -d -t dacn-s01-audit)
cd "$S01_CHECK"
unset PYTHONPATH PYTEST_ADDOPTS PYTEST_PLUGINS
export PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHONDONTWRITEBYTECODE=1
"$S01_PY" -B -m pytest -c "$S01_ROOT/pyproject.toml" -s -v --tb=short -p no:cacheprovider "$S01_ROOT/tests" --encoder-backend=c
"$S01_PY" -B -m pytest -c "$S01_ROOT/pyproject.toml" -s -v --tb=short -p no:cacheprovider "$S01_ROOT/tests" --encoder-backend=python
"$S01_PY" -B -m pip check
```

Suite audit lấy đường dẫn trong command records, chạy `--noconftest` không thêm
`--encoder-backend`; fixture audit tự chạy cả hai. Đoạn probe a5 nguyên bản được
lưu trong log, dùng Python stdin ở cwd tạm. Không có dependency vào đường dẫn máy
cá nhân trong code sản phẩm.

| Bằng chứng | Nội dung |
| --- | --- |
| [development-results.txt](development-results.txt), [development-commands.json](development-commands.json), [development-evidence.json](development-evidence.json) | Build/install non-editable, suite riêng Đợt 4 và các lượt development |
| [final-results.txt](final-results.txt), [final-commands.json](final-commands.json), [final-evidence.json](final-evidence.json) | Full suites, audit suites, exit codes, process events, trạng thái DB, instrumentation |
| [pre-metadata-fixture-correction-commands.json](pre-metadata-fixture-correction-commands.json), [pre-metadata-fixture-correction-evidence.json](pre-metadata-fixture-correction-evidence.json) | Mốc có lỗi fixture, đối chiếu log append |
| [metadata-fixture-correction-checks.json](metadata-fixture-correction-checks.json) | Targeted rerun fixture đã sửa, stdout/stderr/exit |
| [before-path-identity-review-commands.json](before-path-identity-review-commands.json), [before-path-identity-review-evidence.json](before-path-identity-review-evidence.json) | Mốc 981/backend trước sửa guard ancestor identity |
| [prior-audit-probes.txt](prior-audit-probes.txt), [prior-audit-probes-command.json](prior-audit-probes-command.json) | Bốn probe a5 chạy lại; source hash và exit code |
| [local-walkthrough.json](local-walkthrough.json) | 11 lệnh `python -m` thực; outputs, checks và hashes input/config |
| [environment-manifest.json](environment-manifest.json), [evidence-verification.txt](evidence-verification.txt) | Runtime/deps/package identity và collector đã chạy |
| [protected-files-verification.json](protected-files-verification.json) | Hash đầu/cuối, hai thay đổi chủ ý, không ngoại lệ khác |
| [artifact-sha256.json](artifact-sha256.json) | Index artifact bàn giao, không tự hash chính index |

## 8. Manifest và bảo vệ artifacts

- CPython **3.13.16**, GIL bật, SQLite **3.53.1**, macOS arm64. Dependencies runtime
  `jsonschema 4.26.0`, `simplejson 4.2.0`; pytest `9.1.1`. Runtime/C extension và toàn
  bộ distributions ngoài version package giữ nguyên baseline.
- **16/16 file package** khớp source–installed–wheel. METADATA/WHEEL, non-editable
  direct_url và wheel archive hash khớp. Manifest còn hash 54 project files.
- **131/133 file inventory đầu lượt giữ nguyên**; hai thay đổi chủ ý là repository
  thêm lookup và pyproject tăng version. Các file mới được liệt kê riêng trong
  manifest/report, không được tính nhầm thành baseline được bảo vệ.
- Baseline wheel a5 giữ nguyên SHA-256
  `5b3dbc9feac551a727896555f60282c5170d93b7a042cb79ffec01b68493da82`.
- Wheel bàn giao: [dacn_s01-0.1.0a6-py3-none-any.whl](../../dist/dacn_s01-0.1.0a6-py3-none-any.whl),
  SHA-256 **`e4ebbe7988d7cb5255d93845c94ba41aeb043900c762ca7636d4f7c093bff20b`**.
- Validator build:
  `dacn-s01/0.1.0a6+sha256:38b3ce1cf52578ea7f9d999009847bd4d68ddafaea18c0e687e9f3aff112c635`.

Không sửa schema/dataset/sáu JSON minh họa hoặc audit cũ, không sao chép toàn bộ
dataset, không khởi tạo Git. New synthetic demo ở thư mục riêng, có nguồn và nhãn
rõ. Schema package giữ nguyên digest đã audit.

## 9. Đối chiếu tiêu chí hoàn thành S01 — mục 10 kế hoạch

“Đạt” dưới đây là theo bằng chứng kỹ thuật đã thực thi trong phạm vi test, chưa
thay kết luận agent audit hoặc nghiệm thu của người dùng.

| Tiêu chí | Trạng thái | Bằng chứng/giới hạn |
| --- | --- | --- |
| Pipeline và CLI local đã chọn | Đạt | 11 lệnh walkthrough, 93 E2E/integration cases; cùng service đã audit |
| Bảo toàn nguồn/nội dung/ID/priority/criteria/unknowns | Đạt | Raw BLOB/export byte equality; readonly input/config hashes; snapshot comparisons; codec và preservation suites cũ |
| Số chính xác, W 29, no coercion/regex veto | Đạt | Unit/contract suites Đợt 1–2 giữ nguyên; full 986/backend; CLI Decimal/legacy/P3-F1 kiểm thực |
| Snapshot/revision/provenance/history | Đạt | Lifecycle/reuse/parent/base conflict, get_snapshot_revision không retarget, checked lookups/corruption tests |
| Năm lịch update cạnh tranh và atomic persistence | Đạt | 36 process/fault records Đợt 3 chạy lại, IPC/BUSY/DB state; receipt race bổ sung |
| Error paths chặn handoff và recovery | Đạt | Failed/rejected matrices, receipt trước submit, actual pipe/permission/kill và injected fsync/commit faults; không tự retry |
| Auditor tra request/source/envelope/snapshot/criterion | Đạt | CLI lookup và API get_request khi projection null; hướng dẫn origin_source_id + JSON Pointer theo snapshot |
| Tái lập đúng môi trường, hashes, logs và giới hạn công khai | Đạt | Locks giữ nguyên; manifest identity; commands/logs; hướng dẫn; setup mới chưa tạo lại ở đợt này |
| Chứng minh mất điện/disk-full/phần cứng hoặc mọi filesystem | Chưa kiểm chứng | Không suy từ SIGKILL, fault injection hoặc fsync acknowledgement |
| Audit implementation toàn bộ S01 và nghiệm thu | Chưa đạt | Đề nghị review chính bản a6/wheel hash này; chờ quyết định người dùng |

## 10. Hạn chế và yêu cầu audit

Đề nghị audit command/config semantics, chốt receipt/atomic publish, bảo vệ
ancestor identity và linked sidecars, recovery sau giao nhận/kill, historical
lookup/list-runs, và bằng chứng full S01 gắn đúng artifact a6.

Môi trường kiểm chứng là filesystem local macOS hiện tại, user thường (các test
permission cần quyền này). Không kiểm chứng Windows, network/cloud FS, mount
retarget hay concurrent hostile directory mutation. Không cam kết bảo vệ root
chưa khai báo hoặc shell redirection. Receipt chỉ giữ path kho; người dùng phải
giữ đúng kho và artifacts, không xem receipt như chữ ký xác thực kho đã bị thay.

Không thử mất điện, disk-full, hỏng phần cứng; không khẳng định fsync là chứng
nhận bền vững trước mọi sự cố. SIGKILL có đồng bộ và I/O thật được tách rõ với
fault injection. Chưa có resource quotas, pagination/prune/backup; large inputs
vẫn chịu giới hạn runtime/SQLite đã ghi ở baseline.

Không chạy đánh giá ngữ nghĩa nghiệp vụ, chưa triển khai S02 hoặc API idempotency.
Giữ việc đồng bộ AGENTS trước S02. Không tự ghi nhận bản này đã audit/được duyệt;
dừng sau bàn giao.

**Đợt 4 đã implement và kiểm thử; đề nghị audit toàn bộ S01. Chưa nghiệm thu S01 và chưa triển khai S02.**
