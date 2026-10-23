# S02 2A-P2 — DB2 và owner-profile persistence

P1 `0.2.0a3` đã được nghiệm thu kỹ thuật cấp thấp/local; findings 01–04 đã đóng theo biên bản 22/10/2026. Người dùng giao riêng P2 trong lượt này. Bản sửa `dacn-s02 0.3.0a2`, DB structure 2. **Đã nghiệm thu kỹ thuật local** theo [audit P2 a2](/Users/macbookpro/.codex/.chatgpt-projects/g-p-68c38c8799f48191a101e19a975ca4f9/outputs/audits/s02-2a-p2-0.3.0a2-2026-10-23-015238/AUDIT_REPORT.md). Quyền P3 local được người dùng giao riêng sau audit; xem [hướng dẫn P3](S02_2A_P3_IMPLEMENTATION.md). Không mở 2B/2C, live LLM, renderer hoặc S03.

## Ranh giới và API

`Repository.initialize(operator=...)` chỉ tạo mới/DB rỗng hợp lệ: exact DDL2, hai registry rows, metadata UUID và fresh activation trong một transaction. DB2 đã tồn tại được kiểm toàn kho; inactive không được auto-activate. DB1 trả `MIGRATION_REQUIRED`, không ALTER, backfill hay mở rw.

`prepare`, `append_event`, `finalize` chỉ tạo E1 do repository cấp. Không nhận profile từ caller và không đổi payload thiếu fields thành E1. Events/stages lấy profile operation; command L1 chỉ đọc, kể cả append log và finalize retry. Config artifacts mới có profile/contract/rules pins; reused config L1 giữ nguyên bytes. Whole-graph checker P1 được gọi với maps từ cột storage đã kiểm, không default L1 trong DB2.

Lookup mới: `lookup_record(id, raw=False)` trả `{profile_id, record}`; `raw=True` trả đúng ASCII bytes đang lưu. `lookup_command` có profile cùng operation/events/stages/run; `lookup_event(..., raw=True)` trả raw payload bytes; `lookup_stage` có inherited profile và bytes; `raw_operation` trả profile + request_json bytes. `store_info` trả identity/activation; DB1 không có UUID giả. Các `get_*` bare payload giữ phục vụ code nội bộ sau full-store checks, không được suy profile từ payload để dispatch.

CLI hiện có chỉ init/checked intake/lookups. `show-record` trả wrapper mới, `show-command` có authoritative profile. Command mới dùng receipt `s02/2` ghim command_id/state_dir/store_id theo storage proposal §5. Receipt `s02/1` chỉ dùng DB1 đúng state_dir; không route sang DB2. Receipt file cũ không bị sửa. Path guards checkout/dataset/S01/symlink/hardlink vẫn giữ. Không public arbitrary import hoặc export v2; E1 Export vẫn bị profile từ chối.

## Review evidence

`Repository(path, reviews={issue_id: HumanReviewEvidence(...)})` nhận bindings tin cậy ngoài payload theo API P1. Mapping được snapshot khi mở repository; records/graph digest vẫn được kiểm ở mỗi write/read, gồm lịch sử human_review. Caller phải cung cấp lại khi reopen. Thiếu/sai binding từ chối toàn graph cần review; CLI không tự tạo binding hoặc nhận metadata LLM làm quyền xác nhận. Điều này chưa phải persistence/authentication người review; các ca tests ghi rõ synthetic reviewer. Không có bảng/record approval mới hoặc tự sinh human review.

## Transaction và compatibility

Mọi checked read dùng URI `mode=ro` từ connection đầu, bắt đầu read transaction trước kiểm cấu trúc. Không `immutable=1`, fallback rw, repair hoặc source recovery. DB1 dùng exact DDL1 và verifier L1 giữ hành vi cũ; `storage_schema_l1.py` giữ nguyên bytes DDL module trước P2. Hot journal cần recovery mà SQLite không đọc được thì từ chối, không tự sửa nguồn.

Writer preflight chỉ đọc để từ chối DB1/inactive. Connection ghi existing-only bắt đầu `BEGIN IMMEDIATE`, kiểm lại exact DDL/registry/metadata/activation và toàn store; áp mutation, kiểm full graph/materialized links/claims/heads/promotions lần nữa trước COMMIT. FK deferred giữ cyclic T3. Không `INSERT OR REPLACE`. Paired CAS giữ Model + AnalysisSet; conflict sinh stale outcome đúng command/Run cũ, không rebase. Unique application/Run và active claims không phân vùng theo profile. Lost ACK reconcile qua connection mới, không submit lại.

DB2 không bị biến thành store writable chỉ vì user_version=2. Unknown DDL/version/profile/rules/capabilities/hashes làm cả checked read/write bị từ chối. Baseline DB1 readers vẫn từ chối DB2, cả khi hạ riêng user_version.

## Manifest origin=migration — chỉ reader

Người dùng đã [chốt schema, framing và mutable_baseline](S02_2A_P2_MIGRATION_MANIFEST_PROPOSAL.md) ngày 23/10/2026. Resource riêng `schemas/storage/migration-manifest.json` được pin SHA-256; schema L1/E1 và registry giữ nguyên byte. Reader kiểm đầy đủ schema đóng, versions/paths/IDs/profiles/DDL, manifest BLOB hash, 17 table inventories và source root bằng framing N/I/T/B đã chốt.

Projection immutable L1 được hash trực tiếp từ raw SQL columns/JSON/BLOB/typed links; không serialize lại record lịch sử. Baseline ba bảng mutable nằm trong manifest, có PK/count/hash, session/head/claim/review lineage checks để E1 successors không làm lịch sử giả thành current. Metadata/activation phải khớp manifest và store identity. Destination string phải đúng thư mục DB; không mở source hoặc giả xác nhận alias/offline.

Trong bản P2 không có API copy/migrate/activate/reconcile/receipt migration. Fixtures SQL seeded ở tests là synthetic; không phải migration production. Reader chỉ chứng minh nhất quán nội bộ manifest/DB, không xác thực producer hoặc chứng minh source thật được copy. P3 vẫn phải đối soát source read-only, eligibility, receipts, copy bytes, cutover và activation riêng.

## Kiểm thử hiện hành

Không chạy mặc định suite legacy-write bằng wheel P2 rồi gọi đó là regression nguyên bản. Hai lanes:

- Baseline dùng wheels S01 a6, S02 Đợt 1 `0.1.0a3`, P1 `0.2.0a3`, tests/helpers/oracles frozen.
- P2 dùng `packages/s02/tools/run_p2_checks.py --report-dir <mới> --baseline-python <venv-P1/bin/python> --baseline-helpers <frozen-tests> --legacy-python <venv-phase1-a3/bin/python>`. Tool tạo test workspace riêng, ghi toàn input hashes và adapter diff, rồi chạy từng backend/process bằng runner chung. Không thêm production source vào sys.path. Dùng `--audit-file`/`--audit-only` cho nguyên files oracle; helpers P2 khác setup được công bố tường minh.

Adapter chỉ khai báo E1 fields, config pins, profile/receipt/wrapper API, vị trí fault injection và location docs. Pure P1 fixtures có in-memory L1 projection để giữ assertions legacy root; không ghi projection vào DB2. Oracle cũ “DB1 không ghi E1” vẫn chạy baseline; oracle tương ứng P2 kiểm DB2 không ghi payload L1, giữ rollback/head/record-absence assertions. Tests mới `test_db2.py` dùng `p2_helpers.py`; no skips/xfail.

Bàn giao tại [START_HERE](../reports/s02-phase2/2a-p2-fixes-0.3.0a2-2026-10-23/START_HERE.md), chỉ rõ wheel audit duy nhất và kết quả cuối trên hai backends. Các wheel thử nghiệm khác chỉ là development evidence.

## Sửa review integrity trong 0.3.0a2

S02-2A-P2-01/02 đã được auditor đóng trong audit P2 a2. DB2 đối soát tất cả Review L1+E1 theo bundle: đúng một root, không fork/cycle/disconnected history; active selection có đủ inventory và trỏ tip duy nhất, kể cả revoked. Không tự repair hoặc xếp theo timestamp. Checked read và cả hai lần kiểm trong write transaction dùng cùng gate; CAS khi ghi successor giữ nguyên. Mutable baseline chỉ là căn cứ lịch sử.

Owner E1 yêu cầu revoked có predecessor hợp lệ, khác chính nó và cùng bundle. L1 schema/resources và hành vi validate_record theo owner L1 giữ nguyên, gồm khoảng trống root revoked đã tái hiện trên P1 a3. DB1 vẫn chỉ đọc theo verifier legacy; DB2 mixed áp thêm consistency check selection trên toàn lịch sử, không sửa JSON L1. Đây là sửa thực thi contract §9, không đổi profile/rules IDs hoặc schema.

Một ca audit a1 gọi checked heads sau khi cố ý xóa selection nhưng trước pytest.raises; bản sửa từ chối ngay ở heads. Bàn giao ghi nguyên kết quả 8/9 review-selection và phản chứng cụ thể; không nới checked read hoặc sửa oracle để gọi là 9/9. Các regression mới kiểm riêng write/rollback bằng request pins lấy trước lúc làm hỏng fixture.
