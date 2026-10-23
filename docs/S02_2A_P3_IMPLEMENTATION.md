# S02 2A-P3 — migration local

`dacn-s02 0.4.0a3`: **Đã nghiệm thu kỹ thuật P3 local/synthetic** theo [audit a3](acceptance/P3_AUDIT_REPORT.md) và [biên bản](acceptance/S02_2A_P3_ACCEPTANCE.json). P3-01/02 đã đóng; P1/P2 giữ nghiệm thu trước. Chỉ thực thi trên kho synthetic/test. Giữ storage plan draft.2, manifest schema/framing/mutable_baseline đã chốt, L1/E1 profiles/rules và schemas nguyên byte.

Audit a1 phát hiện S02-2A-P3-01: init coi đích partial là fresh. a2 thêm reservation filesystem và khóa chung init/copy; a3 guard cả namespace/marker tự sinh bằng policy `writable`, loại source/aliases/links trước effects của copy mới và resume. Auditor a3 đã đóng cả hai findings và kiểm hồi quy fix 01. Bàn giao a1 giữ nguyên [trạng thái lịch sử](../reports/s02-phase2/2a-p3-0.4.0a1-2026-10-23/START_HERE.md).

API `dacn_s02.migration.Migration(settings, source_state_dir)` nhận `Settings` có `state` là đích mới, protected/dataset/S01 roots và timeout như CLI cũ. Source, target, receipt phải ngoài protected roots/checkout, paths không alias; receipt ngoài hai stores, parent có sẵn. Không tự tạo parent tree hoặc reset đích tồn tại. API có `reviews=` để caller tin cậy cấp review bindings khi đối soát đích đã có E1 human_review; thiếu/sai binding bị từ chối, CLI không đọc review evidence từ JSON. Không lưu/xác thực review trong migration metadata. API `inspect`, `copy`, `reconcile`, `activate`, `lookup_migrated` đều yêu cầu `offline=True`: operator đã dừng toàn bộ writer cũ và giữ dừng đến khi chuyển cấu hình thủ công. Đây không phải fencing tự động.

CLI vẫn dùng `dacn-s02 --config <config.toml>`; `state_dir` trong config chỉ đích synthetic/test, `--source-state-dir` chỉ nguồn DB1. Các subcommands:

- `migration-inspect --source-state-dir <source> --offline-confirmed`
- `migration-copy --source-state-dir <source> --offline-confirmed --migration-receipt <receipt mới>`
- `migration-copy ... --migration-receipt <receipt cũ> --resume`: cùng identity, không reset partial.
- `migration-reconcile ... --migration-receipt <receipt cũ>`
- `migration-activate ... --migration-receipt <receipt cũ> --confirm-activation --operator <người quyết định>`
- `lookup-migrated ... --migration-receipt <receipt migration> --receipt <s02/1 receipt cũ>`

Dấu `...` giữ `--source-state-dir` và `--offline-confirmed`; không là câu lệnh sao chép trực tiếp. Không chạy những lệnh này trên operational store trong phạm vi được giao.

Nguồn mở URI mode=ro từ connection đầu, BEGIN + SELECT giữ read snapshot qua kiểm/copy/reopen/activation. Full legacy verification và integrity check, mọi operation finalized, không dispatch chưa có kết quả hoặc unknown_outcome. S01 observation phải chỉ đúng dispatch command/event trong lineage đã kiểm; observation ở successor được tính nếu outcome đã biết, `lookup_status=unknown` không release gate. Sau đó tạo projection DB2 **trong memory**, dùng exact DDL2/registry, L1 owner và cùng `_check_db2` như repository: read compatibility DB1 rộng hơn eligibility. Chỉ khi tất cả hợp lệ mới tạo durable receipt s02-migration/1 với ba UUIDv4. Receipt create-only, fsync file + parent, readback trước reserve target. Resume không cấp lại identity.

Sau durable receipt, copy lấy `flock` exclusive trên inode thư mục cha hiện có của destination. Marker tại `<parent>/.dacn-s02-migration-reservations/<tên leaf>` được tạo O_EXCL/O_NOFOLLOW, chứa nguyên canonical receipt; fsync file, thư mục reservation và parent, rồi readback **trước** mkdir destination. Tên leaf được giữ nguyên để case/Unicode aliases dùng cùng entry theo filesystem; tên namespace nội bộ bị cấm làm destination. Namespace tạo trước marker chưa reserve đích; crash ở đó không có target effects. Marker rỗng/torn vẫn chặn fresh init; lỗi/kill trước publication không có effects ở đích. Marker không bị xóa sau commit/activation. Reconcile đối chiếu marker với đúng receipt; marker hợp lệ nhưng chưa có directory là partial, không tự retry copy/reset. Không đổi schema receipt/manifest/DDL hoặc IDs.

`Repository.initialize` lấy cùng lock trước mọi DB effects. Missing/version0 có marker bị từ chối; kho nonempty phải qua writable/full checks và, nếu có marker, phải là migration với binding khớp. CLI gọi `initialize(create_parent=True)` để tạo leaf bên trong lock; không mkdir leaf trước lock. Các API callers cũ giữ mặc định không tạo parent. Lock giữ qua commit/reopen; process death tự thả lock, marker vẫn còn. Khóa dùng chung parent nên có thể serialize init/copy các sibling stores; timeout giữ lỗi, không tự recovery.

Cơ chế này áp dụng cho các tiến trình a3 cùng tuân thủ protocol (giữ bảo vệ reservation của a2). Không chống writer a1/SQL thô hoặc người dùng xóa marker, đổi parent inode/di chuyển directory. Partial a1 trước đây không có marker và không có metadata thì không thể phân biệt bằng bytes với fresh directory/DB rỗng: phải giữ quarantine/evidence, không chạy init và không tự retro-fit/repair. Các kho a1 committed/active vẫn qua checked metadata như trước. Không có quyền migration operational; cleanup docs/tooling/tracking là thay đổi riêng, giữ nguyên payload và evidence.

Copy parameter binding tất cả cột cũ của 17 bảng, JSON TEXT/BLOB không tái serialize; chỉ thêm profile L1. Một BEGIN IMMEDIATE chứa DDL2, registry, metadata/manifest và copy; kiểm raw equality, FK/integrity và toàn graph trước commit. Đích committed nhưng inactive; normal writer bị chặn. Reopen bằng connection existing-only đối soát cả ba IDs/root/profiles/manifest. Không thêm Run/event nghiệp vụ hoặc sửa lịch sử.

Activation là xác nhận riêng; BEGIN IMMEDIATE kiểm lại toàn kho và CAS absent→một row. Retry giữ nguyên operator/timestamp; wrong identity không thể thắng kể cả đến trước. Reconcile không activate. `rollback_eligible` chỉ cho biết rows hiện tại bằng toàn baseline cũ, không thực hiện rollback hoặc chứng minh operator đã đóng băng mọi writer. E1 writes làm mất eligibility. Tool không sửa config, route receipt cũ ngầm, downgrade hoặc xóa stores.

SOURCE_RECOVERY_REQUIRED chỉ dùng khi SQLite báo SQLITE_READONLY_ROLLBACK, có extended code/path/stage. Nguồn DB/journal giữ nguyên. Busy và lỗi khác không được gọi là recovery/identity conflict. Receipt mất ACK dừng trước effects; copy/activation mất ACK phải dùng cùng receipt để reconcile. `missing`, `partial`, `committed_inactive`, `active` phân biệt trạng thái kiểm được. Đích corrupt/hot-journal không đọc được giữ lỗi và evidence, không tự reset. Partial cần operator quyết định cleanup/restart riêng, ngoài tool này.

Giới hạn: local filesystem/runtime đã pin; không online migration, network filesystem, power-loss/hardware assurance, performance certification, chữ ký chống giả mạo, tự source recovery hoặc orchestration. SQLite read lock chặn commit writer trong lúc giữ lock, không cấm writer lấy RESERVED lock và không ngăn writer cũ chạy lại sau khi thả lock. Review/operator strings trong tests đều synthetic.

Bằng chứng mới, wheel audit duy nhất, diff đúng dirty-state trước sửa và cách tái lập: [START_HERE](../reports/s02-phase2/2a-p3-fix02-0.4.0a3-2026-10-23/START_HERE.md).
