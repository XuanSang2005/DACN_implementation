# S01 Đợt 3 — Persistence và revision

**Đợt 3 đã implement và kiểm thử, chờ audit; chưa nghiệm thu toàn bộ S01.**
Ngày bàn giao: 17/10/2026. Package `dacn-s01 0.1.0a4`.
Contract `0.1.0-draft.2`, input schema `1.0.0`, cấu trúc DB `1`.
Đây là ba phiên bản khác nhau; revision đặc tả vẫn bắt đầu từ 1 theo từng spec.

## 1. Baseline và phạm vi

Đã đọc AGENTS, contract, kế hoạch (đặc biệt mục 4–5, 8–10), báo cáo sửa F1/F2,
code/tests hiện tại và audit độc lập ngày 17/10. Người dùng giao thực hiện Đợt 3;
kết luận đóng F1/F2 chỉ áp dụng Đợt 1–2 trên `0.1.0a3`.

[baseline-verification.json](baseline-verification.json) ghi xác minh đầu lượt:
code/package/wheel `0.1.0a3`, runtime và dependencies khớp baseline. Nguồn LaTeX
khác digest ngày 13/10, phù hợp việc tài liệu nguồn được cập nhật sau đó mà audit
17/10 đã ghi nhận; không phải thay đổi do implementation. Bản nguồn thực đọc lúc
làm việc ghi flow S02 chốt ngày **17/10/2026** (observation cũ trong audit còn nói
bản 15/10). Phần S01 vẫn giữ schema 1.0.0. Đã lấy digest hiện tại làm mốc bảo vệ
lượt này, không khôi phục hoặc ghi đè tài liệu nguồn.

**Giữ nguyên AGENTS.md. Cần đồng bộ flow S02 trong AGENTS với nguồn LaTeX mới
trước khi triển khai S02.** Không sửa contract, schema, dataset, sáu JSON minh họa,
dependency locks, báo cáo hoặc artifact audit cũ. Wheel `0.1.0a3` được giữ lại.

Đã implement repository SQLite, comparator/request/revision, service, checked
lookup và kiểm thử thật trên DB tạm. Chưa có CLI/API, receipt filesystem, S02,
LLM, KB hoặc renderer. Các payload kiểm thử là **synthetic**, nhưng transaction,
commit, lookup và các process trong integration tests là **thực chạy**.

## 2. Thiết kế DB thực tế

DDL đầy đủ được xuất nguyên từ code tại [database-schema.sql](database-schema.sql).
Nguồn thực thi là [storage_schema.py](../../src/dacn_s01/storage_schema.py).
Các bảng dùng `STRICT`; dữ liệu JSON không đi qua SQLite JSON extraction hoặc REAL.

| Bảng | Dữ liệu và ràng buộc |
| --- | --- |
| `schema_artifacts` | `digest` PK, `raw_schema` BLOB; kiểm SHA-256 khi archive/lookup |
| `sources` | `source_id` PK, `raw_input` BLOB nguyên byte, kind, label được encode bằng codec trong `label_json` TEXT |
| `runs` | `run_id` PK; source FK và UNIQUE; request gốc/envelope là JSON TEXT; FK tới schema và snapshot nullable |
| `snapshots` | Snapshot JSON TEXT, metadata phục vụ lookup/FK; PK snapshot ID; UNIQUE(spec, revision); creator run UNIQUE; source/run/spec/parent FK |
| `specs` | Spec PK, head bắt buộc; FK ghép `(head_snapshot_id, spec_id)` bảo đảm cùng spec |

`application_id = 0x4441434E` và `user_version = 1` nhận diện kho. Khởi tạo chỉ
nhận DB trống, chưa có application/version/object. Kho đã có phải đúng version và
DDL catalog hiện tại; version không hỗ trợ, DB khác hoặc thiếu trigger bị từ chối.
Không tự reset, xóa dữ liệu hoặc chạy migration suy đoán. Mọi thay đổi DDL tương
lai cần version/migration được review riêng.

Trigger cấm UPDATE/DELETE schema/source/run/snapshot; cấm xóa spec hoặc đổi spec ID.
Snapshot revision mới phải có parent là head hiện hành, cùng spec và revision trước.
Head chỉ tiến đúng một revision. Khởi tạo spec yêu cầu head r1 có parent null.
FK run→snapshot và snapshot→spec được deferred để ghi các record liên kết trong
cùng transaction. Không dùng `INSERT OR REPLACE`.

Metadata cột và JSON được tạo cùng lần trong service. Repository kiểm lại chúng,
request gốc so với `run.request`, source/kind/label/schema, creator/origin/parent,
snapshot trong envelope và record snapshot. Với kết quả validated còn xác minh
raw source chuẩn hóa ra đúng snapshot, kể cả run unchanged dùng nguồn mới. Trước
commit, snapshot kết quả phải đúng head trong transaction. Khi lookup run cũ,
không yêu cầu snapshot cũ phải còn là head mới nhất.

## 3. Transaction, lỗi và recovery

Mỗi operation dùng connection riêng rồi đóng. Cấu hình thực đã kiểm thử:
`autocommit=True`, `foreign_keys=ON`, `synchronous=FULL`, rollback journal `DELETE`.
Điều khiển bằng SQL `BEGIN IMMEDIATE`, `COMMIT`, `ROLLBACK`; không gọi
`Connection.commit()` để nhầm nó có hiệu lực trong chế độ autocommit này.
Xem [Python sqlite3 transaction control](https://docs.python.org/3.13/library/sqlite3.html#transaction-control).

Trình tự service:

1. Nhận immutable raw bytes và request riêng; chụp request qua codec, không ép float.
   Cấp run ID/thời điểm nhận trước transaction. Kiểm tra biểu diễn request chỉ
   phục vụ projection; chỉ công bố lỗi request sau khi input checks đạt.
2. Chạy parse → version/normalization → schema → cross-field ngoài write transaction.
3. `BEGIN IMMEDIATE`; kiểm run ID chưa dùng, cấp source ID chưa có trong kho.
   Nếu input hợp lệ, kiểm request rồi đọc head **trong transaction này**.
4. Kiểm base trước equality; quyết định new_spec/unchanged/new_revision. Không đọc
   head trước transaction để dùng lại, không tự rebase hoặc submit lại.
5. Tạo/check envelope; ghi schema artifact khi cần → source → run/request/envelope →
   snapshot mới nếu có → spec/head. Unchanged chỉ thêm source/run, giữ nguyên snapshot.
   Rejected cũng lưu source/run, không snapshot/head mới.
6. Kiểm liên kết/candidate và `foreign_key_check` trong transaction; SQL COMMIT.
   Sau commit đọc lại bằng connection mới và kiểm liên kết trước trả validated.

Tất cả dữ liệu trên cùng SQLite transaction, không chia nguồn ra file riêng rồi
coi là atomic. Các FK deferred được kiểm tại commit; SQLite điều phối writer.
Xem [SQLite transactions](https://sqlite.org/lang_transaction.html) và
[foreign keys](https://sqlite.org/foreignkeys.html).

| Điểm lỗi | Hành vi thực tế |
| --- | --- |
| Input/request sai | rejected; giữ bytes/request gốc khi kho ghi được; lỗi trước revision thì revision not_run |
| Không serialize context chính xác được | failed/PROCESSING_FAILED; không bịa request thay thế hoặc hứa đã lưu record |
| Lỗi trước commit, rollback được xác nhận | Rollback toàn candidate, thử **một lần** ghi failed audit record cùng run/source; không thử lại nghiệp vụ |
| BEGIN lock timeout | failed/PERSISTENCE_FAILED; revision chưa kiểm tra, không REVISION_CONFLICT |
| COMMIT BUSY, transaction còn mở | SQL ROLLBACK; có thể thử lưu failed audit record riêng. Với khóa còn giữ, record lỗi cũng có thể không lưu được |
| Mất xác nhận sau COMMIT | Đóng connection cũ; lookup run ID bằng connection mới. Trả run đã commit nếu record nhất quán và đúng source của lần này |
| Commit chưa rõ, lookup không xác minh được | failed/no handoff, reason yêu cầu đối soát; không khẳng định rollback hoặc overwrite record đã commit |
| Commit acknowledged nhưng lookup không xác minh được | failed/no handoff, giữ DB đã commit nguyên trạng, tra cứu lại theo run ID |
| Process chết trước/sau commit | Không có response. Test parent dùng run ID biết trước để mở DB mới, kiểm recovery; không tự submit lại |

Lock timeout mặc định 5 giây, truyền qua constructor repository; test lock dùng 0
để xác định lỗi tức thời. Đây là cấu hình vận hành, không ràng buộc nghiệp vụ.
Nếu không lưu được failed run, correlation ID trong response không cam kết lookup
được. Một response failed do chưa xác minh được commit có thể có run validated
trong DB; chỉ checked lookup sau đối soát quyết định kết quả đã lưu.

## 4. Comparator, ID, nguồn và API thư viện

`json_equal` preflight bằng codec hiện có rồi so cây có kiểu: object bỏ qua thứ
tự key, array giữ thứ tự, bool tách number, missing khác null, string exact không
trim/Unicode-normalize. Decimal/int hữu hạn so trực tiếp theo giá trị, không làm
tròn theo precision context; 1=1.0, 0=-0. Không dùng hash/serialized bytes quyết
định revision. Quay về nội dung cũ vẫn tạo revision kế tiếp từ head hiện hành.

Raw input là BLOB kể cả parse lỗi, UTF-16/BOM hoặc byte không decode được.
Request/snapshot/envelope đi qua cùng codec đã audit và lưu TEXT ASCII JSON; số
payload/error.details không qua cột số SQLite. Revision hệ thống dùng INTEGER
SQLite; vượt giới hạn lưu trữ sẽ failed, không cắt/truncate hoặc đổi contract.
JSON gốc của request được giữ ngay cả khi projection `run.request=null`.

UUIDv4 mặc định cho run/source/spec/snapshot. Source/spec/snapshot va chạm thì
cấp lại trước công bố, tối đa 8 lần để dừng generator lỗi. Run ID đã được cấp/nhận
phải giữ để đối soát; nếu trùng record có sẵn, response failed và không overwrite,
không coi đó là retry idempotent. ID và clock có test seam nội bộ.
Clock UTC millisecond lùi thì completed_at được chặn dưới bằng received_at;
revision ordering vẫn theo transaction. Build validator có digest code/profile,
version dependencies/runtime; manifest riêng ghi hashes artifact cụ thể.

API thư viện đã có:

| API | Ý nghĩa |
| --- | --- |
| `Repository(path, timeout=5.0).initialize()` | Khởi tạo rõ ràng hoặc xác minh cấu trúc kho; không tự chọn state directory |
| `Service(repository).allocate_run_id()` | Cấp ID trước commit, không ghi DB/reserve ID/receipt |
| `Service.submit(raw, request, run_id=..., source_kind=..., source_label=...)` | Chạy pipeline; request nằm ngoài input schema; mặc định cấp run ID nếu caller chưa truyền |
| `get_run(run_id)` | Checked envelope đã lưu, giữ timestamp/build và nội dung; không tạo run |
| `get_request(run_id)` | Request audit gốc; dùng get_run để phân biệt run thiếu với request gốc null |
| `get_snapshot(snapshot_id)`, `get_head(spec_id)` | Snapshot đã kiểm quan hệ; đọc snapshot cũ không retarget theo head |
| `get_source(source_id)` | Raw bytes đã lưu, không đọc lại file dataset |

Lookup không tìm thấy trả None; kho sai cấu trúc hoặc record bất nhất raise lỗi,
không trả validated. Public lookup dùng connection mode=rw để hỗ trợ recovery
SQLite; không tạo DB bị thiếu. Kết quả lookup là cây mới, không mutable DB record.
Reference requirement/criterion resolve bằng snapshot ID + JSON Pointer trên input;
origin source của snapshot giữ nguyên qua unchanged. Không nối identity criterion
qua revision. Không thêm source map trùng dữ liệu hoặc cờ xác nhận nghiệp vụ.

Điểm cấp/nhận run ID cho phép Đợt 4 ghi receipt trước gọi submit; **chưa có receipt
filesystem, transport recovery hoặc API idempotency**. Test worker là harness trong
tests, không phải CLI sản phẩm. Không có retention/prune/xóa nghiệp vụ tự động.

## 5. Kiểm thử và bằng chứng thực chạy

**864 passed trên mỗi backend C/Python**, không failed/skipped trong suite bàn giao.
Đó là 765 ca Đợt 1–2 giữ nguyên + 99 ca mới, không phải 1.728 yêu cầu độc lập.
Instrumentation process pytest đo **5.169 C / 0 Python** và **0 C / 5.169 Python**.
Worker process có instrumentation riêng, ghi factory calls và backend trong event
result; không nhập các số đó vào số calls của process pytest.

Suite audit F1/F2 chạy lại **12 passed**; suite audit mở rộng 17/10 **36 passed**;
`pip check` exit 0. Đây là kiểm tra hồi quy của các suite Đợt 1–2 do agent audit
cung cấp, không phải kết luận audit độc lập cho implementation Đợt 3 mới này.

| Nhóm mới | Oracle/kiểm tra chính |
| --- | --- |
| Comparator/request thuần | Literal expectations, large Decimal/5001-digit integer/precision=2; bool-number, missing-null, key/array/string; errors/pointers/details, kể cả key request rỗng và escaped pointer |
| Service/contract | Create mới dù nội dung giống; legacy unchanged; edit/reorder/return-old; stale base trước equality; request shape/routing/spec không có; rejected/failed/no handoff |
| Storage/provenance | Đóng/mở connection mỗi thao tác; raw bytes, UTF-16, parse lỗi, số chính xác, unknowns; source mỗi run, provenance snapshot bất biến; clock lùi/ID collision/lookup thiếu |
| DB guards | STRICT/config/version/DDL; immutable UPDATE/DELETE, FK, unique(spec,revision), parent/head cùng spec; candidate sai và corruption có chủ đích bị checked lookup chặn |
| Atomicity/failure | Inject ở before_insert, after_source_insert, after_snapshot_insert, before_commit; thêm after_records trên update để kiểm rollback cả head đã cập nhật |
| Concurrency/recovery | Năm lịch với process thật, BEGIN/COMMIT lock thật, mất ack giả lập, kill thật trước/sau commit |

**Năm lịch cạnh tranh, đều chạy trên hai backend:** mỗi ca seed r1 rồi hai process
A/B có connection riêng, cùng DB file. A dừng qua IPC sau BEGIN IMMEDIATE. B dùng
chính connection của nó thử BEGIN với busy_timeout=0 và nhận SQLITE_BUSY thực,
ghi event; sau đó đi vào BEGIN của service với timeout 5 giây. Parent chỉ giải
phóng A sau bằng chứng B đã cạnh tranh. Probe là SQL kiểm thử trong hook, không
phải retry submit nghiệp vụ. Không dùng sleep; pipe/select và deadline kiểm deadlock.

| Lịch (A quyết định trước) | A | B | Head / snapshot count cuối |
| --- | --- | --- | --- |
| Hai payload bằng r1 | unchanged | unchanged | r1 / 1 |
| Hai payload cùng thay đổi P | new_revision | REVISION_CONFLICT | r2 / 2 |
| Hai thay đổi P/Q | new_revision | REVISION_CONFLICT | r2 / 2 |
| A unchanged, B thay đổi | unchanged | new_revision | r2 / 2 |
| A thay đổi, B gửi r1 | new_revision | REVISION_CONFLICT | r2 / 2 |

Mỗi ca cuối có 3 run và 3 source gồm seed, 1 spec. Unchanged trả snapshot r1
nguyên trạng; conflict không trả snapshot. Events ghi monotonic time và các điểm
begin/decision/insert/commit/result; thời điểm hook sau COMMIT có thể được scheduler
ghi muộn hơn lúc B lấy khóa, nên không nhầm thứ tự log hook với thứ tự commit SQL.

Phân biệt loại bằng chứng:

- **Fault injection:** sqlite exception trước/sau insert, sau update head, trước
  commit; serializer fault; mất ack sau commit; lookup tạm không hoạt động sau commit.
  Rollback được kiểm bằng connection mới. Các ca lỗi update giữ nguyên r1/head.
- **Khóa thật:** writer chặn BEGIN và reader SHARED chặn COMMIT. Cả hai là
  PERSISTENCE_FAILED; không conflict giả hoặc trạng thái snapshot/head dở dang.
- **Kill process thật:** SIGKILL tại hook trước commit: 0 run/source/snapshot/head.
  SIGKILL sau commit trước trả kết quả: 1 run/source/snapshot/head, checked lookup
  trả validated và nguồn đúng. Cả hai process exit -9, thực hiện ở mỗi backend.
- **Corruption test:** chỉ trong DB tạm, cố ý bỏ/khôi phục trigger để thay record;
  đo guard nội dung độc lập với guard DDL. Không coi test này là chống tampering
  của người có quyền quản trị file DB.

Log phát triển được giữ: lượt đầu có 2 collection errors vì dùng tên parameter
`request` dành riêng của pytest; đã đổi tên parameter, không đổi oracle. Sau đó
57 ca nền passed, rồi 92 ca/backend passed; suite cuối có thêm kiểm rollback head,
pointer key rỗng, UTF-16/error number và cấp run ID. Không che các lượt trước.

## 6. Tái lập và artifacts

Giữ runtime **CPython 3.13.16 regular GIL**, SQLite liên kết **3.53.1**, macOS arm64;
jsonschema 4.26.0, simplejson 4.2.0, pytest 9.1.1 và build backend đã pin.
Build/install chỉ package DACN bằng `--no-index --no-deps --no-build-isolation`;
không thay runtime/dependency locks. Không khởi tạo Git.

Từ project root, với venv/locks hiện có:

```sh
.venv/bin/python -B tools/run_phase3_checks.py --build \
  --audit-test /path/to/s01-phase2-0.1.0a2/test_phase2_audit.py \
  --audit-test /path/to/s01-progress-2026-10-17/test_extended_audit.py
.venv/bin/python -B tools/collect_phase3_evidence.py
```

Các audit paths trên là placeholder; argv và cwd thực nằm trong log. Runner chạy
tests từ thư mục tạm **ngoài source/project**, code import từ wheel cài non-editable,
bỏ PYTHONPATH/PYTEST_ADDOPTS/PYTEST_PLUGINS, tắt plugin autoload và pytest cache,
dùng -B/PYTHONDONTWRITEBYTECODE. Collector bàn giao cũng chạy từ cwd tạm; lệnh
trong evidence-verification ghi đúng executable/script path. DB tests nằm trong
pytest tmp_path riêng; không DB làm việc hoặc bản sao dataset trong repo.

- [final-results.txt](final-results.txt), [final-commands.json](final-commands.json): lệnh, cwd, môi trường, kết quả/exit code của build/install, hai full suites, pip check, hai suites audit; tất cả exit 0.
- [final-concurrency-fault-evidence.json](final-concurrency-fault-evidence.json): **36 records** phân theo backend, gồm event timelines, final state, fault/recovery và kill evidence.
- [development-results.txt](development-results.txt): giữ lịch sử development, gồm failures và các lượt pass trước suite cuối.
- [environment-manifest.json](environment-manifest.json): runtime/SQLite/distributions/config, validator build ID, code/test/tool hashes, installed direct_url và source–installed–wheel identity.
- [evidence-verification.txt](evidence-verification.txt): collector exit 0, 13 package files khớp byte, xác minh đủ năm lịch và hai kill boundary trên mỗi backend.
- [protected-files-before.json](protected-files-before.json), [protected-files-verification.json](protected-files-verification.json): mốc đầu lượt và đối chiếu cuối. Inventory có 66 file, **65 giữ nguyên**; ngoại lệ có chủ đích duy nhất là một dòng mô tả package trong `__init__.py`. Mọi tài liệu/dataset/locks/evidence cũ và module Đợt 1–2 thực thi giữ nguyên.

Wheel cuối: `dist/dacn_s01-0.1.0a4-py3-none-any.whl`, SHA-256:
`c20caa13ca9fa66253ebad5d21be7cdef1eab28b2faab498975e1f1566f3bfb1`.
Wheel `0.1.0a3` vẫn có SHA-256
`859f96c8def6cd3be7544c652e648ed36f4884dd307fffc6bbe090716937e830`.
Hash từng module/package entry có trong manifest, không chỉ kiểm tên version.

## 7. File thay đổi và điểm cần audit

| File/nhóm | Lý do |
| --- | --- |
| [revision.py](../../src/dacn_s01/revision.py) | Equality có kiểu, request errors/projection, quyết định revision thuần |
| [storage_schema.py](../../src/dacn_s01/storage_schema.py) | DDL/version/constraints/triggers |
| [repository.py](../../src/dacn_s01/repository.py) | Initialize, transaction, records, checked lookup và đối chiếu liên kết |
| [service.py](../../src/dacn_s01/service.py) | Điều phối pipeline, run ID/clock/build, commit/reconciliation và failure archive |
| `pyproject.toml`, `src/dacn_s01/__init__.py` | Tăng version và cập nhật mô tả phạm vi package |
| [tests/phase3](../../tests/phase3) | 99 ca mới, synthetic fixtures và worker IPC riêng |
| [run_phase3_checks.py](../../tools/run_phase3_checks.py), [collect_phase3_evidence.py](../../tools/collect_phase3_evidence.py) | Chạy package/thu bằng chứng, không là CLI nghiệp vụ |
| Thư mục report này, wheel 0.1.0a4 | Artifact bàn giao mới; không sửa bằng chứng cũ |

Audit cần xem transaction boundary/DDL/deferred FK; ordering stale-base-before-
equality và reuse provenance; failed-record attempt so với retry nghiệp vụ;
reconciliation không overwrite khi mất ack; guard trước commit và lookup; evidence
hai process và mức bảo đảm thực của fault tests. Phiên bản DB và chính sách từ chối
DDL drift cũng cần được review trước tạo kho sử dụng lâu dài.

Giới hạn còn lại:

1. Chỉ kiểm CPython/macOS/SQLite đã pin trên filesystem local. Chưa kiểm mất điện,
   disk-full thực, hỏng phần cứng hoặc network/cloud-synced filesystem. Fault
   injection và SIGKILL không chứng minh các tình huống đó.
2. Raw source được chụp trước parse trong bộ nhớ, durable cùng final transaction;
   crash trước commit có thể không có record. Không có intake journal/pending state.
3. Chưa CLI/receipt/transport recovery/API idempotency; không tuyên bố exactly-once.
   Run ID đã tồn tại phải lookup, không submit lại; failed correlation có thể chưa lưu.
4. Guard phụ thuộc schema/profile được hỗ trợ trong build hiện tại. Chưa có cơ chế
   chạy nhiều phiên bản schema/DB hoặc migration; unsupported version bị từ chối.
5. Giữ giới hạn codec/resource Đợt 1–2; chưa kiểm mọi kích thước input. Bản local
   giữ toàn bộ history, chưa có quota/backup/prune feature; người có quyền sửa DB
   và vô hiệu trigger nằm ngoài bảo đảm chống can thiệp.
6. Không chạy persistence trên dataset phòng khám trong đợt này; nguồn chỉ đọc và
   checksum được bảo vệ. Dữ liệu test không xác nhận nghiệp vụ hoặc độ đầy đủ.
7. `validate_input()` độc lập vẫn dừng revision not_run; chỉ service qua commit và
   checked lookup mới trả validated. Handoff contract được tạo cho kết quả test
   đã lưu thật; không có S02 consumer hoặc bước phân tích nghiệp vụ được gọi.

**Đợt 3 đã implement và kiểm thử, chờ audit; chưa nghiệm thu toàn bộ S01.**
Dừng trước Đợt 4 và S02; không suy kết quả test thành nghiệm thu của agent audit.
