# Phản hồi audit storage 2A — draft.2

Ngày 22/10/2026. Proposal: `s02-2a-storage-plan/0.1.0-draft.2`.

**proposed — đã phản hồi S02-2A-01/02, chờ audit lại; chưa được duyệt implementation.**

Chỉ sửa hai finding của [audit draft.1](/Users/macbookpro/.codex/.chatgpt-projects/g-p-68c38c8799f48191a101e19a975ca4f9/outputs/audits/s02-phase2-2a-storage-draft1-2026-10-21/AUDIT_REPORT.md). Đây là phản hồi của implementation agent ở mức tài liệu; không tự đóng finding hoặc ghi nhận auditor đã chấp thuận draft.2. A1/A2/G2 và lựa chọn owner profiles L1/E1 giữ nguyên. S01 a6 và nghiệm thu S02 a3 Đợt 1 không đổi.

## 1. Đối chiếu từng finding

| Finding | Vị trí sửa | Phản hồi và ca kiểm dự kiến |
| --- | --- | --- |
| **S02-2A-01 (P1)** | [Proposal §6.2](S02_PHASE2_2A_SCHEMA_MIGRATION_PROPOSAL.md:155), bảng recovery §6.4, [cases RO01–RO03](S02_PHASE2_2A_SCHEMA_MIGRATION_PROPOSAL.md:244) | Tất cả source connections mở mode=ro từ đầu, gồm preflight/copy verification/resume/reconcile/helpers. Cấm public a3.verify, rw fallback, immutable=1 và tự recovery. Reuse logic L1 trên connection chỉ đọc vẫn kiểm đầy đủ identity/version/DDL/hash/graph. Nguồn cần recovery ⇒ dừng trước tạo/ghi đích, giữ DB/journal; recovery riêng rồi inspect lại. RO01 nguồn sạch và negative full-validation; RO02 hot journal tại preflight; RO03 hot journal khi resume với đích vắng hoặc đã commit |
| **S02-2A-02 (P2)** | [Receipt §5.1](S02_PHASE2_2A_SCHEMA_MIGRATION_PROPOSAL.md:125), [identity sau copy/activation §6.3](S02_PHASE2_2A_SCHEMA_MIGRATION_PROPOSAL.md:177), [cases ID01–ID08](S02_PHASE2_2A_SCHEMA_MIGRATION_PROPOSAL.md:247) | Receipt s02-migration/1 bắt buộc migration_id/target_store_id/activation_id; create-only + fsync trước destination. Resume chỉ dùng IDs trong receipt đã kiểm. Manifest cùng ba IDs; activation so migration_id qua singleton metadata và so ID/store/profile/basis với receipt/manifest. Thiếu/sai receipt từ chối, không bù ID từ đích. Cùng identity đã commit trả row cũ; khác identity conflict. Bổ sung crash trước copy, sau copy, sau activation mất ACK và hai lịch cạnh tranh cùng/khác identity |

Thay câu cho phép public a3 verify bằng quy tắc cấm rõ ràng. Không đổi public API hoặc code a3. Thay quy tắc cạnh tranh cũ “một thắng, một conflict” bằng phân nhánh cùng identity trả kết quả cũ / khác identity conflict; identity đúng đã được manifest pin nên không dùng “đến trước thắng” cho yêu cầu sai.

Receipt pin thêm **source_inventory_sha256 đã biết ở preflight** để resume sau crash trước copy vẫn phát hiện được nguồn đổi. Trường này có mục đích so nguồn; không phải hash manifest tương lai. Receipt không có manifest hash, copy counts hoặc activation timestamp. Cả ba UUID, paths, version và root nguồn bất biến sau khi ghi receipt; không append metadata sau copy. Quy tắc này cần auditor review cùng S02-2A-02.

## 2. Ví dụ và checkpoints

[JSON 01](examples/s02-phase2-2a/01-profile-and-migration.json) nâng proposal_version, dùng ba UUID giả định cố định khớp JSON 02 và cập nhật kỳ vọng recovery/race; catalog L1/E1, binding rules và semantics đã audit không đổi.

[JSON 02](examples/s02-phase2-2a/02-readonly-preflight-and-activation-recovery.json) có receipt đủ fields §5.1, manifest/metadata projection chứa identity, activation row, UTF-8 payload/hash minh họa và negative receipts. Mọi scenario đều `executed: false`, `runtime_ready: false`, `production_importable: false`. Paths/IDs/operator/time đều synthetic, không được tạo trong filesystem. Manifest projection **không phải full runtime manifest**: chưa có table inventory đầy đủ, tool/resource hashes E1 hoặc DDL2. SHA trong ví dụ chỉ hash bytes của payload minh họa, không chứng minh DB đã copy/verify; khi implement phải hash toàn manifest thực. Root nguồn trong ví dụ là hash một chuỗi synthetic được công bố, không phải measurement DB.

| Checkpoint trong JSON 02 | Evidence được giả định đã bền vững | Kỳ vọng khi implementation được giao |
| --- | --- | --- |
| C1: crash sau receipt, trước copy | Receipt; chưa manifest/activation | Inspect nguồn ro, root khớp; đọc lại đúng ba IDs; copy vào đích cũ đã chọn, không UUID mới |
| C2: copy commit, trước activation | Receipt + metadata/manifest; chưa activation | Đối soát IDs/bytes/root; không recopy; giữ đích inactive cho tới quyết định operator, dùng activation_id từ receipt |
| C3: activation commit, ACK mất | Ba loại evidence, activation row bất biến | Checked lookup/identity match trả đúng row cũ, không đổi operator/time hoặc ghi activation thứ hai |
| C4: receipt sai / hai activation cạnh tranh | Negative receipts và đích đã pin identity | Receipt thiếu/sai ⇒ từ chối; khác identity ⇒ conflict; cùng identity/basis ⇒ một insert, cả hai nhận row cũ sau re-check; busy là lỗi persistence riêng |

RO01–RO03 và ID01–ID08 là **11 ca dự kiến mới**, gồm variants; không phải 11 tests pass. Hai lịch ID06–07 cần hai process/hai connections/IPC/deadline khi có implementation. Hash checks hiện tại chỉ đối chiếu các object JSON/chuỗi minh họa và files, không mô phỏng SQLite concurrency hoặc recovery.

## 3. Bằng chứng audit được dẫn lại đúng phạm vi

[preflight-probe.json](/Users/macbookpro/.codex/.chatgpt-projects/g-p-68c38c8799f48191a101e19a975ca4f9/outputs/audits/s02-phase2-2a-storage-draft1-2026-10-21/preflight-probe.json) là kết quả **auditor đã chạy** trên kho tạm từ wheel a3/CPython 3.13.16/SQLite 3.53.1. Child exit 73 để lại hot journal: mode=ro trả SQLITE_READONLY_ROLLBACK, hai file giữ nguyên; a3.verify phục hồi DB về trạng thái cũ đúng logic a3 nhưng đổi bytes DB và xóa journal. Không dùng operational store, không phải kiểm mất điện hoặc migration mới. Lượt này chỉ đọc và hash lại evidence, không chạy probe hoặc application tests.

## 4. Files thay đổi và kiểm tra tĩnh

| File | Loại / lý do |
| --- | --- |
| [AGENTS.md](../AGENTS.md:120) | Sửa một bullet trạng thái: phản hồi hai finding, chờ audit lại; không sửa flow S02 |
| [Proposal 2A](S02_PHASE2_2A_SCHEMA_MIGRATION_PROPOSAL.md) | Nâng draft.2; sửa source open policy, durable identity, recovery và cases |
| [JSON 01](examples/s02-phase2-2a/01-profile-and-migration.json) | Sửa version/UUID minh họa và kỳ vọng M02/M07 |
| [JSON 02](examples/s02-phase2-2a/02-readonly-preflight-and-activation-recovery.json) | File mới: receipt/manifest/activation projections và bốn checkpoints |
| [Báo cáo này](S02_PHASE2_2A_DRAFT2_AUDIT_RESPONSE.md) | File mới: đối chiếu finding, giới hạn và bàn giao |
| [STATIC_CHECKS_DRAFT2.json](examples/s02-phase2-2a/STATIC_CHECKS_DRAFT2.json) | Manifest mới, create-only; không ghi đè STATIC_CHECKS.json hoặc manifest lịch sử |

Baseline trước sửa gồm 4.637 files: inventory workspace trong phạm vi ghi ở manifest, tập file bên ngoài được bảo vệ từ bàn giao trước, và toàn thư mục audit storage draft.1. Trước sửa, **4.623 file bảo vệ cũ** và **6 hashes artifacts audit draft.1** đều khớp. Sau sửa, **4.634/4.634 file ngoài ba file cho phép sửa** giữ nguyên bytes/hash; có đúng ba file mới trong bảng trên. Production source/tests/schemas/locks, package version, artifacts và bằng chứng lịch sử không đổi. Plan Đợt 2, addendum, contract, bảy ví dụ A1/A2/G2 và manifest draft.1 được kiểm nguyên file, không chỉ chọn sections.

Kiểm tĩnh: **2 JSON hiện hành + 7 JSON cũ đọc được; 8 bindings, 98 liên kết local, 2 payload UTF-8/hash/độ dài và 4 nhóm checkpoint đạt đối chiếu**. Ba negative receipts được nhận diện đúng trong artifact minh họa; không phải kết quả validator ứng dụng. 23 ca dự kiến (12 cũ + 11 mới) đều ghi chưa thực thi; 4 manifest tĩnh lịch sử nguyên byte. Lệnh `python3 /tmp/s02-2a-draft2-static.py`, exit code 0; chi tiết tại manifest mới. Phép kiểm dùng strict JSON (duplicate keys/nonfinite bị từ chối, Decimal), JSON Pointers và identity receipt–manifest–metadata–activation. Manifest chứa before/after hashes + diffs của ba file sửa, inventory files bảo vệ, phạm vi loại trừ và mã kiểm tĩnh để auditor tái lập phép đối chiếu; không tự nhúng hash manifest vào chính nó.

Không mở SQLite, không tạo DB/receipt/snapshot thực, không import production modules, chạy migration/application tests, cài package/build, gọi LLM hoặc renderer. Không kiểm runtime behavior, actual durability/fsync, hot-journal rejection của tool mới, concurrency, disk-full hoặc mất điện. E1/DB2/migration mới chưa tồn tại; kiểm tĩnh không thay audit implementation. Các thư mục runtime/venv/cache bị loại trừ được liệt kê trong manifest; đây không phải hash toàn máy hoặc toàn dataset.

## 5. Nội dung cần auditor xem lại

- Tính bao phủ của source mode=ro từ lần mở đầu, không có đường public a3.verify/rw/immutable hoặc recovery ngầm.
- Nguồn authoritative của cả ba IDs và source root trong receipt, thời điểm fields xuất hiện, chuỗi equality/hash tới activation, refusal khi identity sai hoặc receipt mất.
- Cùng identity/basis trả row đã commit; khác identity không thắng CAS dù tới trước. Thiếu/sai identity không làm phát sinh ID thay thế.
- Các ca RO01–RO03/ID01–ID08 đã đủ làm oracle cho implementation sau này chưa; bindings/hash minh họa không phải bằng chứng ứng dụng.

**proposed — đã phản hồi S02-2A-01/02, chờ audit lại; chưa được duyệt implementation.** Dừng tại tài liệu để auditor review.
