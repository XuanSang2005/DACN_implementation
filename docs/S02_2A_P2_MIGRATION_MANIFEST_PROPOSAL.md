# P2 — schema manifest đầy đủ để review

Trạng thái: **đã được người dùng chốt ngày 23/10/2026 trong lượt P2**: “Chốt schema + framing + mutable_baseline như tài liệu; triển khai checks và tests trong P2.” Chốt thiết kế không phải nghiệm thu implementation. Người dùng yêu cầu chốt schema đầy đủ trước khi reader hỗ trợ `origin=migration`. Tài liệu này cụ thể hóa §6.3 của storage draft.2; không triển khai copy, receipt migration, activation/cutover hoặc mở nguồn operational.

Schema đóng để review: [migration-manifest.schema.proposed.json](examples/s02-phase2-p2/migration-manifest.schema.proposed.json). Layout của đúng 17 bảng DB1: [legacy-table-layouts.json](examples/s02-phase2-p2/legacy-table-layouts.json). Không đổi schema L1/E1 hoặc registry đã nghiệm thu.

## Nội dung đề xuất

Tất cả trường đều bắt buộc, object đóng và không có fallback. Giữ tên/ý nghĩa đã có trong identity projection draft.2: format/plan version, ba UUIDv4, source/destination state_dir, source inventory root, application ID, DB versions và write profile. Bổ sung đầy đủ DDL hashes, hai profile resource/rules/contract hashes, tool/package/Python/SQLite/rules-bundle versions, inventory algorithm, inventory từng bảng, exclusions và `mutable_baseline`.

- `format=s02-migration-manifest/1`, plan version đúng draft.2, source DB1/target DB2, application ID `44414332`, write profile E1.
- Paths là absolute canonical POSIX strings, khác nhau, không `.`/`..`/trailing slash (ngoại trừ root); không truy cập source để canonicalize. Destination phải bằng thư mục chứa DB đang mở. Alias/symlink/hardlink và source offline do P3 kiểm khi copy/activate, không suy từ chuỗi trong manifest.
- DDL hash: SHA-256 của JSON ASCII compact, keys sorted, mapping tên→exact SQL; không hash thứ tự `sqlite_master`. Hash DB1 là `ee348ac9d29992545b2654ce2ad1d4f0a203f98434de3abc4de84d9e8e1ed4d3`, DB2 hiện tại là `9d0625fa92dd5f9068260014af3032cc1460cddd491ab258c8a8ff5eec256d58`.
- Profile entries là đúng hai entries packaged, gồm schema/descriptor hashes và contract/rules IDs. Tool version ghi producer của manifest, không bắt bằng version reader về sau; rules bundle là SHA-256 thực, không coi nhãn version là hash code.
- Mỗi bảng ghi đúng thứ tự columns và PK theo DDL1, row_count, source_sha256 và copied_legacy_sha256. Hai hash phải bằng nhau. Inventory không chứa cột profile mới hoặc ba bảng DB2 mới.
- `mutable_baseline` là phần cần chốt bổ sung: bản sao **chỉ ba bảng mutable** `sessions`, `application_heads`, `active_reviews` tại copy. Mọi row dùng fields/kiểu đúng cột DB1. Nhờ đó reader sau E1 writes vẫn kiểm được root inventory lịch sử mà không yêu cầu head/claim hiện tại quay về lúc migrate. Không chép toàn bộ source DB vào manifest.

## Framing inventory `s02-db1-inventory/1`

Đây là cụ thể hóa mới của framing N/I/T/B đã nêu ở §6.3; chưa có manifest production mang thuật toán này.

1. `cell(tag,payload) = tag ASCII một byte || length uint64 big-endian || payload`. N có payload rỗng; I là integer ASCII canonical (không bool/float); T là UTF-8 nguyên giá trị SQL TEXT; B là bytes nguyên gốc. JSON TEXT columns vẫn bắt ASCII. Không decode→encode JSON lịch sử để hash.
2. Row digest là SHA-256 của nối các cells theo column order DDL1. Rows sort theo declared PK, SQLite BINARY ordering; tất cả PK DB1 là TEXT, không dùng thứ tự chèn.
3. Table digest là SHA-256 của nối `T(table_name), I(column_count), T(column_name)..., I(pk_count), T(pk_name)..., I(row_count), B(row_digest)...`. Digest B là 32 raw bytes, không 64 ký tự hex.
4. Source root là SHA-256 của nối `T("s02-db1-inventory/1"), I(table_count), [T(table_name), B(table_digest)]...` theo table_name ASCII tăng dần.
5. Mutable-baseline rows phải duy nhất theo PK; tính table digest của chúng và so với inventory. Không cho phép thiếu bảng/rỗng giả khi row_count khác 0.

## Checked read DB2 dự kiến

Sau exact DDL/registry nhưng trước graph, decode manifest bằng codec exact; kiểm schema đóng và framing/version trên. Kiểm metadata.migration_id/store_id/write_profile_id, activation_id và basis SHA-256 của **manifest BLOB nguyên bytes**. Không tự bổ sung fields hoặc lấy ID thiếu từ activation.

Kiểm projection bất biến L1 trực tiếp từ DB đang mở:

| Bảng | Row thuộc lịch sử L1 |
| --- | --- |
| records | owner profile L1 |
| operations | owner profile L1 |
| models, analysis_sets, artifacts | record_id thuộc records L1 |
| staged_blobs, operation_events, promotions | command_id thuộc operations L1 |
| record_links, record_event_links, record_stage_links | owner_id thuộc records L1 |
| event_record_links, event_event_links, event_stage_links | owner event thuộc operation L1 |

Hash/count projection phải đúng inventory; không bỏ cột raw JSON/BLOB hoặc materialized links. Không rebuild links để sửa drift. Các bảng mutable dùng `mutable_baseline` để khôi phục root lịch sử; đồng thời kiểm identities còn tồn tại, session spec giữ nguyên, sequence không giảm, old heads là ancestors hợp lệ của current pair, claim/review hiện tại nối lineage tương ứng. Full graph/head/claim checker tiếp tục kiểm trạng thái hiện tại, không coi baseline là current head.

Các checks này chứng minh nhất quán nội bộ của manifest và kho đích, **không chứng minh source đã thực sự được copy, operator đã giữ source offline hay người thật đã activate**. P3 phải independently checked-read source `mode=ro`, đối chiếu copy byte-for-byte, receipt/path/IDs và source root trước activation. Không có public migration/import/activation API trong P2.

## Kiểm thử sau khi chốt

Positive fixtures gồm manifest đầy đủ cho synthetic mixed store và trạng thái sau E1 successor/claim/review; legacy bytes giữ nguyên. Negative fixtures kiểm từng identity/version/path/profile/hash, thiếu/lạ fields, missing table/column/PK, count/root sai, bool thay integer, drift raw JSON/BLOB/links L1, duplicate mutable PK và mutable baseline sai lineage. Mọi từ chối phải giữ DB bytes. DDL/profile resources vẫn ghim và kiểm hai backends.

Quyết định nêu ở đầu tài liệu cho phép triển khai reader checks và tests trên schema/framing/mutable_baseline này. Không cấp quyền P3 hoặc xác thực migration production. Wheel thử nghiệm trước quyết định không phải wheel bàn giao cuối.
