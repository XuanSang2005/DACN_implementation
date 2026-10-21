# S01 local — hướng dẫn bản 0.1.0a6

Bản CLI đã implement và kiểm thử, **chờ audit toàn bộ S01**. Validation thành công
chỉ xác nhận cấu trúc theo output contract `0.1.0-draft.2`, không xác nhận nghiệp vụ
hoặc chuyển sang thực thi S02. Input schema `1.0.0`; DB structure `1`.

## 1. Môi trường

Đã kiểm chứng trên macOS arm64, CPython **3.13.16** có GIL, SQLite **3.53.1**.
Dùng kho trên filesystem local có hard link, directory descriptor và fsync.
Không đặt DB đang ghi trên network drive hoặc thư mục đồng bộ đám mây; chưa kiểm
chứng Windows, filesystem khác hoặc mất điện/phần cứng hỏng.

Workspace bàn giao đã có `.venv` cài wheel **non-editable**. Để dùng ngay, đặt
`S01_ROOT` là thư mục implementation và `S01_PY="$S01_ROOT/.venv/bin/python"`.
Không đặt PYTHONPATH trỏ vào `src`; CLI đọc schema từ package đã cài.

Ví dụ chuẩn bị **môi trường mới** từ runtime/wheelhouse đã pin trong workspace
(hướng dẫn tái lập; không tạo lại venv trong lượt Đợt 4):

```sh
S01_ROOT=/path/to/DACN_implementation  # placeholder, thay bằng workspace thực
S01_ENV=/path/to/new-venv            # placeholder, nằm ngoài dataset
"$S01_ROOT/.runtime/python/bin/python3.13" -m venv --without-pip "$S01_ENV"
"$S01_ROOT/.tools/uv" pip install --python "$S01_ENV/bin/python" \
  --no-index --find-links "$S01_ROOT/.tools/wheelhouse" --require-hashes \
  -r "$S01_ROOT/requirements-tools.lock" -r "$S01_ROOT/requirements-dev.lock"
"$S01_ENV/bin/python" -m pip install --no-index --no-deps \
  "$S01_ROOT/dist/dacn_s01-0.1.0a6-py3-none-any.whl"
"$S01_ENV/bin/python" -m pip check
```

`requirements-dev.lock` đã gồm runtime dependencies. Nếu chỉ sử dụng CLI, thay nó
bằng `requirements.lock`; không tự nâng dependency. Runtime artifact và phiên bản
tool nằm trong báo cáo Đợt 1; hash wheel/runtime bản bàn giao nằm trong
[manifest Đợt 4](../reports/s01-phase4/environment-manifest.json).

## 2. Config và đường dẫn

TOML nhận đúng ba key ở root:

```toml
state_dir = "state"
busy_timeout_ms = 5000
dataset_roots = ["input", "/path/to/external/dataset"] # phần tử thứ hai là placeholder
```

| Giá trị | Quy tắc |
| --- | --- |
| `state_dir` | Chọn rõ kho; `--state-dir` ưu tiên hơn config. Thiếu cả hai thì lỗi, trừ `show-run --receipt` lấy kho từ receipt |
| `busy_timeout_ms` | Integer 0…2147483647, mặc định 5000; bool/float bị từ chối |
| `dataset_roots` | Mảng thư mục đã tồn tại, mặc định `[]`; cần khai báo mọi vùng nguồn muốn bảo vệ |

Đường dẫn trong TOML tính từ thư mục chứa config **đã resolve**; flag tính từ cwd.
CLI không expand `~` bên trong TOML và không đọc config tự động từ home. Key lạ,
TOML sai hoặc kiểu sai là lỗi cấu hình. Các global flags `--config`, `--state-dir`
đặt **trước** tên lệnh.

`init` tạo riêng thư mục state cuối cùng nếu chưa có; thư mục cha phải tồn tại.
Kho dùng `state_dir/s01.sqlite3`. Các lệnh khác không khởi tạo/reset kho. DB đã có
phải đúng structure/application ID và DDL; không có migration tự động.

Dataset roots phải tồn tại để kiểm được identity trên filesystem; lỗi gõ nhầm
root không bị bỏ qua. Guard còn so identity của các thư mục tổ tiên để nhận ra
alias hoa/thường hoặc Unicode trên filesystem, không chỉ so prefix của chuỗi path.
Receipt/export có thư mục cha đã tồn tại và phải nằm ngoài state directory lẫn
dataset roots. CLI xét đường dẫn resolve, symlink và file identity; không ghi đè
input/config hoặc file đã có, kể cả dangling symlink. DB/sidecars có symlink hoặc
hard link bị từ chối để tránh SQLite sửa một nguồn qua alias. Temp publish nằm
trong cùng thư mục output đã kiểm tra, không dùng temp directory hệ thống.

**Giới hạn bảo vệ:** không thể bảo vệ dataset root chưa khai báo. Thư mục local
phải do người dùng kiểm soát; guard không phải sandbox chống tiến trình khác cố
ý đổi tên/mount thư mục hoặc sửa file giữa các bước kiểm tra. Shell redirection
như `> input.json` có thể truncate file trước khi CLI chạy; dùng `--output` để
được bảo vệ tạo mới, không redirect stdout vào dữ liệu nguồn.

## 3. Luồng chạy local

[Fixture synthetic](examples/s01-local/synthetic-clinic.input.json) được viết riêng
cho minh họa CLI, không sao chép dataset phòng khám hoặc sáu envelope tài liệu.
Các lệnh CLI dưới đây đã được chạy từ package cài ngoài source trong
[walkthrough log](../reports/s01-phase4/local-walkthrough.json); biến đường dẫn và
ID trong hướng dẫn là placeholder cho lần chạy mới của bạn. Lệnh chuẩn bị shell
là cách tạo vùng thử tương đương, không phải log nguyên văn lượt đo.

```sh
S01_ROOT=/path/to/DACN_implementation # placeholder
S01_PY="$S01_ROOT/.venv/bin/python"
S01_WORK=$(mktemp -d -t dacn-s01-local)
mkdir "$S01_WORK/input" "$S01_WORK/output"
cp "$S01_ROOT/docs/examples/s01-local/synthetic-clinic.input.json" "$S01_WORK/input/clinic.json"
chmod 400 "$S01_WORK/input/clinic.json"
```

Tạo `"$S01_WORK/s01.toml"` với nội dung sau; chỉ bảo vệ vùng synthetic này trong
ví dụ, hãy bổ sung dataset root thực của bạn khi dùng dữ liệu thật:

```toml
state_dir = "state"
busy_timeout_ms = 5000
dataset_roots = ["input"]
```

```sh
"$S01_PY" -m dacn_s01 --config "$S01_WORK/s01.toml" init
"$S01_PY" -m dacn_s01 --config "$S01_WORK/s01.toml" submit --mode create \
  --input "$S01_WORK/input/clinic.json" --receipt "$S01_WORK/output/create.receipt.json" \
  --output "$S01_WORK/output/create.envelope.json"
"$S01_PY" -m dacn_s01 show-run --receipt "$S01_WORK/output/create.receipt.json"
```

Create trả `snapshot.spec_id`, `snapshot.snapshot_id`, `snapshot.revision=1`.
`priority:null` và điều kiện chưa biết giữ nguyên. Lấy `SPEC_ID` từ output vừa nhận;
`RUN_ID`, `SNAPSHOT_ID`, `SOURCE_ID` bên dưới cũng là placeholder từ envelope thực.

```sh
"$S01_PY" -m dacn_s01 --config "$S01_WORK/s01.toml" submit --mode update \
  --spec-id SPEC_ID --base-revision 1 --input "$S01_WORK/input/clinic.json" \
  --receipt "$S01_WORK/output/unchanged.receipt.json"
"$S01_PY" -m dacn_s01 --config "$S01_WORK/s01.toml" show-run --run-id RUN_ID
"$S01_PY" -m dacn_s01 --config "$S01_WORK/s01.toml" show-snapshot --snapshot-id SNAPSHOT_ID
"$S01_PY" -m dacn_s01 --config "$S01_WORK/s01.toml" show-snapshot --spec-id SPEC_ID --revision 1
"$S01_PY" -m dacn_s01 --config "$S01_WORK/s01.toml" list-runs --spec-id SPEC_ID
"$S01_PY" -m dacn_s01 --config "$S01_WORK/s01.toml" show-source --source-id SOURCE_ID \
  --output "$S01_WORK/output/original-source.bin"
```

Để tạo revision mới, chuẩn bị file input mới ở đường dẫn khác, chỉ sửa nội dung
đã được quyết định; gửi update với base hiện hành và **receipt mới**. Không sửa
file nguồn cũ. Walkthrough đã thử thay priority của R1 thành `should` như một
thay đổi **synthetic**, tạo r2; tra `--revision 1` sau đó vẫn trả snapshot r1.
Gửi lại input cũ với base lỗi thời bị conflict dù payload bằng head hiện tại.

## 4. Command/output contract

| Lệnh | Stdout khi thành công |
| --- | --- |
| `init` | JSON `{state_dir, database}` đã resolve, không phải envelope S01 |
| `submit` | Đúng một envelope S01, kèm newline; có thể thêm `--output` để export cùng bytes |
| `show-run --run-id …` hoặc `--receipt …` | Envelope đã lưu, kể cả rejected/failed; `--output` tùy chọn |
| `show-snapshot --snapshot-id …` hoặc `--spec-id … --revision …` | Snapshot bất biến được yêu cầu; `--output` tùy chọn |
| `show-source --source-id … --output …` | Không ghi stdout; export **nguyên bytes**, kể cả input parse lỗi/UTF-16 |
| `list-runs --spec-id …` | Mảng envelope đã kiểm liên kết; `--output` tùy chọn; `[]` nếu không có liên quan |

List gồm run có snapshot thuộc spec hoặc `run.request.spec_id` khớp, kể cả
unchanged/rejected/failed có request biểu diễn được. Có thể list các rejection cho
spec chưa tồn tại. Request sai cấu trúc có projection null phải tra bằng run ID/
receipt. Sắp theo `(received_at, run_id)` để ổn định, **không phải thứ tự commit**.
Chưa có phân trang; list kiểm các run trong một read transaction, phù hợp kho local
nhỏ. Giá trị/timestamp/validator version/provenance đã lưu không bị cập nhật.

Routing sai nhưng biểu diễn được, ví dụ `--mode create --spec-id x`, được service
báo `INVALID_REQUEST`. `--base-revision` dùng cú pháp JSON number chính xác: `1.5`,
`0` đọc được rồi bị service từ chối; `oops` là lỗi cú pháp CLI. Thiếu spec/base của
update được service xử lý; không tự chuyển sang create. `--revision` của lookup
phải là số nguyên dương và không tự hiểu là head.

| Exit | Ý nghĩa |
| --- | --- |
| 0 | Init, submit validated hoặc lookup/export thành công |
| 2 | Submit rejected theo contract |
| 3 | Failed hoặc lỗi cấu hình, filesystem, persistence, receipt hay giao nhận |
| 64 | Lỗi cú pháp flag trước tiếp nhận |
| 4 | Lookup không tìm thấy record |

Lookup exit 0 không tạo run mới và không biến failed thành validated. Dùng status
và handoff trong envelope cùng checked record; không lấy exit code thay invariant.
Thông báo vận hành ở stderr. Lỗi quá sớm chưa có envelope chỉ báo stderr/exit;
không dựng checks/snapshot giả. JSON luôn đi qua codec chính xác, số không qua float.
Export JSON được publish trước khi viết stdout; export thất bại có thể không có
stdout. Pipe/stdout lỗi có thể để lại output bị cắt, không coi đó là envelope đủ.

## 5. Receipt và mất phản hồi

Receipt là metadata vận hành ngoài envelope:

```json
{"receipt_version":"1","run_id":"PLACEHOLDER_RUN_ID","state_dir":"/resolved/path/to/state"}
```

Nội dung trên là **minh họa**, không dùng để lookup. Receipt thực được cấp run ID
trước submit; chỉ gọi service sau khi publish và flush receipt hoàn tất. Receipt
không là bằng chứng thành công, không phải idempotency key hoặc exactly-once.

| Tình huống | Cách xử lý |
| --- | --- |
| Receipt đã có | Submit bị từ chối. Tra `show-run --receipt PATH`; không ghi đè/xóa receipt rồi tự submit lại |
| Mất stdout hoặc lỗi export sau commit | Tra bằng receipt để lấy kết quả đã lưu. Xuất sang **đường dẫn mới**. DB vẫn giữ kết quả; CLI không tạo thêm run/revision |
| `show-run --receipt` trả 4 | Chưa thấy record không chứng minh lần trước thất bại: process có thể đang chạy/commit cần đối soát. Xác định process gốc đã dừng và mở lại kho để đối soát trước khi quyết định gửi một lần mới với receipt mới |
| Flag/config chỉ kho khác receipt | Lỗi mâu thuẫn; kiểm đường dẫn kho gốc, không tự chọn một bên |
| Publish/flush receipt lỗi | Không bắt đầu submit S01. Có thể đã để lại receipt hoàn chỉnh nhưng chưa xác nhận flush; giữ artifact và đối soát, không coi tồn tại file là thành công |
| Process chết giữa publish | Có thể còn `.dacn-*.tmp`, hoặc receipt đã publish và temp cùng trỏ một inode. Không có tự động prune; giữ để đối soát, không sửa artifact đang được process khác dùng |

Đường ghi tạo temp 0600 cùng thư mục, ghi/flush/fsync file, link tạo mới tên đích,
xóa temp riêng, fsync directory. Không unlink tên đích khi gặp lỗi. Exception thông
thường cố dọn temp riêng; kill/hỏng cleanup có thể để lại temp. Export dùng cùng
quy tắc và cũng có thể đã có file hoàn chỉnh dù trả exit 3 do flush lỗi.

Nếu cần xem request gốc khi `run.request=null`, auditor có API đọc đã kiểm liên kết
`Repository(state_dir / "s01.sqlite3").get_request(run_id)`. Không chỉnh DB trực tiếp
để sửa run/snapshot; thay đổi requirements bằng update từ input mới.

Để truy vết tiêu chí, lấy đúng snapshot ID hoặc spec/revision, rồi đọc nguồn bằng
`snapshot.origin_source_id`. Ví dụ tiêu chí đầu của FR đầu có JSON Pointer
`/functional_requirements/0/acceptance_criteria/0` trong nguồn đã parse. Với run
unchanged, nguồn tạo snapshot này có thể khác `run.source.source_id` của lần gửi
mới. Pointer/index chỉ có nghĩa trong snapshot/nguồn cụ thể; không dùng index hay
text để nối tiêu chí giữa các revision khác nhau.

Giữ toàn bộ source/run/snapshot/schema/receipt; không có retention/prune tự động.
Export source/envelope không phải bản backup toàn DB. Chưa triển khai API, S02,
LLM, KB hoặc renderer. Chi tiết bằng chứng và giới hạn trong
[báo cáo bàn giao](../reports/s01-phase4/IMPLEMENTATION_REPORT.md).
