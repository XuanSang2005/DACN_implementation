# P2 — phản hồi phạm vi triển khai

Package `dacn-s02 0.3.0a1`, DB2. Căn cứ: storage draft.2 §2–5/§7, amendments A1/A2 đã chốt, nghiệm thu P1 a3 và yêu cầu P2 riêng của người dùng. Ngày 23/10/2026 người dùng chốt thêm schema manifest đầy đủ, framing và mutable_baseline. Không thay semantics/profile/rules IDs của L1/E1.

| Phần | Thay đổi và hành vi |
| --- | --- |
| DDL2 | `storage_schema.py` thêm profile NOT NULL/FK không default, registry/metadata/activation STRICT và immutable triggers. Giữ các tables/indexes/constraints lịch sử. `storage_schema_l1.py` nguyên byte module trước sửa |
| Registry/identity | `store_profiles.py` so exact packaged bytes/descriptors/hashes; UUID/store/profile/activation/basis checks. Fresh init nguyên tử, inactive không auto-activate |
| Repository | Cột owner cấp E1 cho writes; event/stage theo command. DB2 checked read gọi P1 whole graph với authoritative maps; SQL materialized links được so theo owner schema. Không sửa records để vượt shape |
| Transaction | Preflight RO; BEGIN IMMEDIATE rồi kiểm registry/activation/full graph lại; apply; verify trước COMMIT. Unique/claim/CAS toàn kho; stale và lost-ACK behavior giữ protocol; command L1 không append/finalize |
| DB1 compatibility | Mở mode=ro ngay từ đầu; exact DDL1 + verifier cũ AST bằng nhau. Init/write MIGRATION_REQUIRED. Không recovery nguồn tự động, không nâng cấp tại chỗ |
| Manifest reader | Schema/framing được chốt riêng; 17 tables, raw JSON/BLOB/links L1, source root và baseline sessions/claims/reviews. So metadata/activation/path/profile/version và lineage sau E1 successors. Không copy/activate/migration receipt |
| API/CLI | Lookup wrappers + raw bytes; receipt mới s02/2 có store_id; receipt s02/1 chỉ DB1/path cũ. Config artifacts mới ghim E1/contract/rules. Không export v2 hoặc import CLI |
| Review evidence | Explicit trusted caller bindings theo P1, snapshot khi mở Repository, recheck digest khi write/read. Không tạo approval từ metadata, không thêm bảng human review |

Code và evidence cụ thể: `implementation.diff`, `exact-ddl.sql/json`, `code-locations.json`, `audit-package-evidence/manifest.json`, `audit-rebuild-comparison.json`. Diff đối chiếu actual state trước sửa, không phải chỉ Git HEAD đang có công việc P1 chưa commit.

Schema L1/E1/registry và P1 logic A1/A2/task scope/target footprint/operation identity/Part–mapping association giữ nguyên bytes. `legacy-preservation.json`, `protected-inventory.json` và tests mới là căn cứ; không suy chúng thành equivalence mọi đầu vào hoặc nghiệm thu nghiệp vụ.

Bản trước manifest và các wheel build discovery giữ như evidence phát triển, không phải wheel audit. Các dữ liệu test/review/operator/LLM-response strings là synthetic; không chạy LLM, renderer, dataset, operational store hay migration.
