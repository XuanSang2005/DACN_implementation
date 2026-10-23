# Bàn giao S02 2A-P2 — dacn-s02 0.3.0a1

**P2 đã triển khai, chờ audit độc lập.** Hoàn tất ngày 23/10/2026; thư mục mang ngày bắt đầu 22/10. P1 `0.2.0a3` đã nghiệm thu kỹ thuật cấp thấp/local, findings 01–04 đã đóng theo audit P1. Bàn giao này không tự nghiệm thu P2 hoặc cấp quyền P3/live.

## Wheel S02 duy nhất để audit

**[audit-wheel/dacn_s02-0.3.0a1-py3-none-any.whl](audit-wheel/dacn_s02-0.3.0a1-py3-none-any.whl)**

SHA-256: `4417dfa99f54558aded5cf3073a89bb4d2d282ab456af58bddb97e27da444487`.

DB structure **2**. L1 `s02-profile/legacy-a3`, E1 `s02-profile/a1a2-v1`; contract/rules IDs và schema/registry L1/E1 giữ nguyên. S01 a6 wheel đi kèm là bản sao nguyên ZIP lịch sử. Các wheels dưới `build-*`, `release`, `manifest-build` là thử nghiệm phát triển, **không phải đối tượng audit**; `audit-rebuild` chỉ phục vụ chứng minh rebuild payload tương đương.

## Phạm vi đã thực thi

DDL2, registry/metadata/fresh activation, repository chỉ ghi E1, owner-profile dispatch, whole-graph checks trước commit và khi đọc, claims/uniqueness/CAS toàn kho; DB1 checked read-only ngay từ connection đầu. API lookup giữ raw bytes và trả profile có thẩm quyền; receipt mới ghim store identity. Không tự nâng cấp DB1, bổ sung fields vào payload thiếu hoặc tạo human review.

Theo quyết định người dùng ngày 23/10, đã triển khai reader `origin=migration` với **schema manifest đóng, framing và mutable_baseline**, kiểm đủ 17 bảng/columns/PK/count/hashes, identity/version/profile/DDL và lineage sau E1 writes. Đây là reader trên fixtures synthetic, không phải công cụ migration hoặc bằng chứng đã copy nguồn thực.

- [Báo cáo triển khai và transaction boundaries](IMPLEMENTATION_REPORT.md), [hướng dẫn API/giới hạn](../../../docs/S02_2A_P2_IMPLEMENTATION.md).
- [Schema/framing/mutable_baseline đã chốt](../../../docs/S02_2A_P2_MIGRATION_MANIFEST_PROPOSAL.md), [JSON Schema](../../../docs/examples/s02-phase2-p2/migration-manifest.schema.proposed.json).
- [Exact DDL](exact-ddl.sql), [DDL hashes](exact-ddl.json), [vị trí code](code-locations.json), [hashes runtime thực](rules-bundle.json).

## Kết quả đo mới trên wheel audit

Cài non-editable trong venv mới ngoài source, chạy từ cwd ngoài checkout; CPython 3.13.16 có GIL, SQLite 3.53.1, macOS arm64. Mỗi backend và S01/S02 là process riêng. Không skip/xfail.

| Lane | C | Python | Evidence |
| --- | ---: | ---: | --- |
| P2 corpus cuối | 454 đạt | 454 đạt | 383 ca ngoài DB2 từ [full batch](audit-p2-regression/checks/commands.json) + toàn bộ 71 ca DB2 cuối từ [final DB2 batch](audit-db2-final-02/checks/commands.json) |
| S01 a6 trong môi trường audit | 986 đạt | 986 đạt | [audit-s01](audit-s01/commands.json) |
| Sáu files audit P1 nguyên byte | 27 đạt | 27 đạt | [audit-oracles](audit-oracles/checks/commands.json), [hashes gốc](oracle-preservation.json) |
| Baseline Đợt 1 S02 a3 | 217 đạt | 217 đạt | [legacy-regression](legacy-regression/commands.json) |
| Baseline P1 S02 a3 | 383 đạt | 383 đạt | [p1-regression](p1-regression/commands.json); S01 986/backend cũng đạt trong lane này |
| Baseline sáu files audit P1 | 27 đạt | 27 đạt | [p1-oracles](p1-oracles/commands.json) |
| Differential L1 với Đợt 1 a3 | 413 trùng | 413 trùng | [so toàn outcomes](differential-summary.json): 67 accepted, 346 rejected |
| Hai graph phản ví dụ P1-04 | Đều từ chối | Đều từ chối | [replay-summary](replay-summary.json); exit 1 là rejection mong đợi |

454 là **383 + 71**, không phải 452 + 71: full batch ban đầu có 69 ca DB2; toàn nhóm DB2 được chạy lại sau khi bổ sung positive claim/review lineage. Hashes inputs và adapter outputs của 383 ca còn lại không đổi. [Execution summary](execution-summary.json) kiểm và ghi chi tiết phép ghép này. Không tuyên bố legacy-write tests nguyên vẹn chạy trên E1: [TEST_MAPPING](TEST_MAPPING.md) giải thích từng thay đổi setup/API; mỗi lane lưu `ADAPTER.json` và diff. Files/assertions audit độc lập giữ nguyên byte.

[Instrumentation](instrumentation.json) xác nhận backend encoder thực. [Race/fault timelines](race-fault-timelines.json) gồm 5 races và 4 process terminations/backend, SQLite lock, fault injection và lost ACK; có PID, IPC/barrier, thời điểm, encoder counts và trạng thái sau checked reopen. Các DB evidence đều synthetic. Các lượt discovery/harness lỗi được giữ nguyên, không tính là release pass.

## Bảo toàn và tái lập

- [Diff so actual state trước sửa](implementation.diff), [inventory trước](before-inventory.json), [inventory bảo toàn](protected-inventory.json): 2.278 files đã ghi nhận, 2.266 nguyên byte, 12 files hiện hành thay đổi có chủ đích, không mất file; 12 implementation files mới. Giữ cả công việc chưa commit có sẵn. Hai README trước sửa được lấy từ captured Git HEAD rồi kiểm đúng hash inventory, có provenance riêng.
- [DB1 verifier/DDL và resources](legacy-preservation.json): verifier cũ giữ AST, DDL1 module nguyên byte, schemas L1/E1/registry không đổi; S01, locks/dependencies và artifacts lịch sử giữ nguyên.
- [Source–wheel–installed](audit-package-evidence/manifest.json): 24 payload S02, 16 S01, METADATA/WHEEL và non-editable direct URL. [Rebuild từ copy sạch](audit-rebuild-comparison.json) bằng payload/METADATA/WHEEL; [build inputs](audit-build-provenance.json). `pip check` đạt.
- [Commands/cwd/environment/exit codes và cách tái lập](REPRODUCE.md), từng `*.command.json/.log`, JUnit XML và `observations.json` trong lanes. [Release input hashes](release-inputs.json), [toàn bộ artifact hashes](ARTIFACT_HASHES.json).

## Giới hạn cần auditor xem xét

Tests kiểm cấu trúc/persistence trên fixtures synthetic, không xác nhận nghiệp vụ hoặc chất lượng LLM. Review bindings vẫn do caller tin cậy cung cấp lại khi reopen; chưa có protocol lưu/xác thực người review. Manifest reader chứng minh nhất quán nội bộ inventory/IDs/lineage, không chứng minh producer đáng tin hoặc nguồn thực đã được copy. Differential 413 outcomes là corpus hữu hạn, không phải chứng minh equivalence mọi đầu vào.

Chưa triển khai/chạy P3 copy/migrate/receipt/resume/cutover/activation migrated, operational store, dataset, 2B/2C, live LLM, renderer hoặc S03. Chưa kiểm mất điện phần cứng, disk-full thực hoặc hiệu năng ở quy mô lớn. Không tự đóng finding mới hoặc ghi P2 đã nghiệm thu.
