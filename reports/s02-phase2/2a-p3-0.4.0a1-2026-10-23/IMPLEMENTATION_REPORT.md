# Bàn giao 2A-P3 migration local — dacn-s02 0.4.0a1

**P3 đã triển khai, chờ audit độc lập.** Quyền triển khai do yêu cầu riêng của người dùng và NEXT_PROMPT audit P2 a2. P2 a2 đã nghiệm thu kỹ thuật local, findings 01/02 đã được auditor đóng; không suy thành nghiệm thu P3. Tất cả stores trong lượt này là synthetic/test. Không thực thi migration operational, không sửa dataset, gọi LLM/live hoặc triển khai 2B/2C.

## Phạm vi và thay đổi

Trước lượt này, P2 chỉ đọc manifest đã chốt, có fresh DB2 activation; chưa có migration protocol. Bản mới thêm inspect/copy DB1→DB2/receipt/reconcile/explicit activation/lookup-migrated; giữ nguyên DDL2, schemas L1/E1/manifest, registry, contract/profile/rules IDs và dependencies. API `reviews=` nhận binding ngoài DB từ caller tin cậy như quyết định của người dùng; thiếu/sai binding tiếp tục từ chối graph. Không có persistence/authentication review mới.

| Điều kiện | Thực thi / vị trí | Bằng chứng |
| --- | --- | --- |
| Nguồn chỉ đọc từ đầu, cả resume/reconcile | migration.py `_source`: URI mode=ro, BEGIN + SELECT; legacy verifier + exact DDL + FK/integrity; giữ transaction qua copy/reopen/activation | `migration_golden`, `migration_hot_journal`, forensic archives |
| Eligibility đầy đủ | Mọi operation finalized; LLM dispatch có response; không unknown_outcome; S01 observation đúng dispatch command/event qua lineage, outcome known | negative prepared/interrupted/finalized unknown/unobserved, positive stale/failed captures và successor observation; unknown observation không release |
| DB1 read compatibility rộng hơn migration | Exact-DDL DB2 projection trong memory và cùng `_check_db2`; không tạo receipt/đích trước khi đủ invariants | missing selection/claim DB1 vẫn đọc được nhưng migration từ chối |
| Durable identity trước effects | `_read_receipt`, `_durable`, `_identity`: schema đóng s02-migration/1, UUIDv4 ba IDs, paths/root/plan; temp fsync + no-overwrite publication + directory fsync + readback | missing/invalid/lost-ACK receipt; resume không gọi UUID factory |
| Copy nguyên bytes | `_seed`: parameter binding toàn 17 bảng/cột cũ; thêm L1 profile; không serialize lại JSON/BLOB; operations chèn parent trước child vì FK immediate | rich DB1 được tạo bằng wheel a3, raw equality, stale claim giữ nguyên; control child ID `0` đứng trước UUID parent |
| Copy commit inactive | `_seed` kiểm graph/profiles/manifest/FK/integrity; copy BEGIN IMMEDIATE không activation; mở lại existing-only | lỗi trước/sau từng bảng, trước/sau commit; normal writer bị chặn khi inactive |
| Reconcile và activation | `_target_checked`, `_reconcile`, `activate`: ba IDs/root/basis/profile; CAS absent→một row; retry giữ operator/timestamp | process thật kill, cùng identity cạnh tranh, wrong identity trước/sau, busy tách identity conflict |
| Lookup và rollback information | `lookup_migrated` yêu cầu hai receipts + active target + command thuộc baseline L1; `rollback_eligible` so tất cả legacy columns hiện hành | lookup exact old command; E1 writes làm rollback_eligible=false; không đổi config/downgrade |

Code: [migration.py](../../../packages/s02/src/dacn_s02/migration.py), [CLI](../../../packages/s02/src/dacn_s02/cli.py), [Repository](../../../packages/s02/src/dacn_s02/repository.py). Dòng/symbol chính xác ở [code-locations.json](code-locations.json). `_check_legacy` giữ nguyên source; phần DB2 của `_check` chỉ được tách sang `_check_db2` để dùng chung cho projection, được đối chiếu AST. Không sửa helper dùng nghĩa L1, registry hoặc schema để vượt gate.

## Kết quả thực thi mới trên wheel audit

| Lượt thực thi mới | C | Python |
| --- | --- | --- |
| final-full-s02 | 589/589 pass | 589/589 pass |
| final-s01-regression | 986/986 pass | 986/986 pass |
| final-audit-p1 | 27/27 pass | 27/27 pass |
| final-audit-p2-original | 16/17 pass, 1 lỗi setup đã biết | 16/17 pass, 1 lỗi setup đã biết |
| final-audit-p2-v2 | 17/17 pass | 17/17 pass |
| p1-regression | 383/383 pass | 383/383 pass |
| legacy-regression | 217/217 pass | 217/217 pass |

Không skip/xfail. Original P2 `test_writer_refuses_review_fork_after_selection_loss` vẫn lỗi setup tại checked `heads()` sau khi xóa selection; đây là phản chứng harness đã được auditor P2 a2 xác nhận, không phải finding implementation mới. Chạy bản gốc nguyên byte và ghi exit 1 riêng; v2 do auditor cung cấp và tám boundary cases pass. Sáu file P1 giữ nguyên assertions/bytes. Hash audit inputs và helpers được kiểm trong [oracle-preservation.json](oracle-preservation.json), [test-input-preservation.json](test-input-preservation.json).

Differential L1: 413 outcomes (67 accepted) bằng nhau giữa a3, P1 a3 và candidate, cả C/Python; instrumentation thực tế ở [differential-summary.json](differential-summary.json). S01/regression baseline được chạy lại riêng, không dùng số lịch sử. Full S02 cuối dùng adapter P2 đã audit, không sửa tests cũ. [run_full_parallel.py](run_full_parallel.py) chỉ đổi lịch chạy hai backend thành hai process song song, cùng pytest arguments/conftest, cwd/env/artifacts riêng; không đổi assertion hoặc instrumentation. Các oracle dùng runner hiện hành nguyên byte.

Process proof: mỗi backend có 5 kill boundaries (receipt durable, copy trước/sau commit, activation trước/sau commit), 3 hot-journal phases, 3 activation identity/order cases, source reader chặn commit writer và busy deadline. Lost ACK còn được inject qua hooks; không đồng nhất hook exception với kill. [migration-observations.json](migration-observations.json) chứa IPC PID/checkpoint/in-transaction/encoder calls. Hot journal được tạo bằng writer process thật có cache spill, kiểm magic header rồi SIGKILL; cả DB/journal giữ size/hash, đích không đổi. [final-hot-journal-c](final-hot-journal-c/RESULT.json) và [final-hot-journal-python](final-hot-journal-python/RESULT.json) giữ forensic copies, không phải stores để mở rw.

## Packaging và bảo toàn

Wheel audit duy nhất: `audit-wheel/dacn_s02-0.4.0a1-py3-none-any.whl`.
SHA-256: `6c9caa88803d75079bd1eef3852161b355a03023170e138f0dac545935c5ae56`.

Build từ copy sạch; non-editable trong `final3-venv`, cwd ngoài source; runtime CPython 3.13.16 GIL / SQLite 3.53.1 / macOS arm64. [package manifest](package-audit-evidence/manifest.json) kiểm source=wheel=installed, S01 cùng baseline a6, METADATA/WHEEL, direct_url và dependency versions. [Rebuild comparison](rebuild-comparison.json) đối chiếu payload/METADATA/WHEEL/RECORD; không yêu cầu ZIP timestamps/hash phải bằng. `pip check` exit 0.

Inventory trước sửa gồm 4847 files; 4838 giữ nguyên, 9 files hiện hành đổi và 6 files mới ngoài thư mục bàn giao. Không xóa file đầu vào. [Input inventory](input-inventory.json), [protected inventory](protected-inventory.json), [diff đúng pre-edit dirty state](implementation.diff), `before-git-status.txt`, `before-git-diff.txt`, `before-git-head.txt` và `before/` giữ đủ căn cứ. Excludes: .git/.runtime/.tools/.venv, build, egg-info, __pycache__/.pytest_cache và symlinks; không tuyên bố kiểm hash byte toàn venv/cache. Schema/DDL/manifest/registry/S01/locks và artifacts/evidence lịch sử nằm trong inventory bảo vệ. [Kiểm seal audit P2 a2](historical-audit-seal-check.json) đối chiếu thêm 861 artifacts ngoài checkout: không mismatch.

## Hồ sơ phát triển và giới hạn

Các `dev-check-*`, `full-s02`, `verified-full-s02`, `release/`, `release-final/` là evidence phát triển, không phải candidate audit. Chúng được giữ nguyên. Dev-check-02 có lỗi lifetime semaphore trong fixture multiprocessing (đã giữ reference gate và chạy lại); dev-check-04/05 có lỗi fixture observation enum/redispatch và phát hiện thứ tự immediate FK. Không dùng failed development runs làm kết quả release. Lệnh hot-journal-c đầu tiên lỗi đường dẫn script/cwd, được ghi riêng; final-hot-journal-* mới là bằng chứng cuối. Guard create-only còn chặn một lần dùng lại label differential cũ; đã chạy differential cuối bằng label diff-final3 mới, giữ log cũ. Không thay oracle để sửa các lỗi này.

Chưa chứng minh power-loss/hardware durability, disk-full thực, filesystem network/online migration, performance/large-store memory bounds, authentication của operator/review, hoặc fencing writer cũ sau khi thả read lock. Read lock chỉ chặn commit trong thời gian giữ lock; operator phải giữ writers stopped. Partial/version0/unknown target không được reset tự động; forensic copies không được mở rw. `rollback_eligible` là kiểm dữ liệu tại thời điểm đọc, không tự cho phép cutover/rollback và không khóa writer vĩnh viễn. Không có migration ngược hoặc merge E1 vào DB1. Rich fixture kiểm đủ 17 bảng; `record_stage_links` có inventory rỗng hợp lệ, không tuyên bố đã kiểm một record StageRef không tồn tại trong fixture. Sources và review/operator content đều synthetic; validation không xác nhận nghiệp vụ hoặc human consent thật.

Reproduce: [REPRODUCE.md](REPRODUCE.md), tạo output/work mới. Commands/cwd/env/exit codes ở `*.command.json` và `*/checks/commands.json`; logs/JUnit đi kèm. Tất cả kết luận acceptance P3 dành cho auditor độc lập.

**P3 đã triển khai, chờ audit độc lập.**
