# Phản hồi S02-2A-P3-01 — dacn-s02 0.4.0a2

**Đã sửa, chờ audit lại.** Chỉ sửa finding High về normal init nhận nhầm migration partial thành fresh active. Không tự đóng finding hoặc nghiệm thu P3. Quyền thực hiện theo yêu cầu riêng và NEXT_PROMPT của audit a1 ngày 23/10/2026. Căn cứ storage draft.2 §6.2: partial/version0 không được runtime initialize/reset. Contract/profile/rules IDs, schemas/registry/manifest và DDL giữ nguyên. Namespace filesystem mới là cơ chế thực thi reservation; không thêm migration manifest fields, DB tables, claims, activation tự động hoặc thiết kế nghiệp vụ.

## Nguyên nhân và thay đổi

Ở a1, durable receipt có trước mkdir đích nhưng directory/DB rỗng không có dấu nhận diện migration sống sót độc lập với SQLite transaction. Rollback hoặc SIGKILL sau reserve có thể để lại directory không DB hoặc DB version0. `Repository.initialize` nhận trạng thái đó là fresh, cấp store/activation IDs mới, làm normal writes được phép dù migration chưa complete/activate.

- [reservation.py](/Users/macbookpro/Documents/DACN_implementation/packages/s02/src/dacn_s02/reservation.py:17): marker ở `<destination.parent>/.dacn-s02-migration-reservations/<destination.name>`, dùng chính tên leaf để giữ filesystem equivalence của hoa/thường và Unicode. Namespace nội bộ không được dùng làm destination; namespace không phải directory thực bị từ chối. Không tạo/xóa lock file: `flock` exclusive trên inode parent hiện có, acquisition có timeout.
- [migration.py](/Users/macbookpro/Documents/DACN_implementation/packages/s02/src/dacn_s02/migration.py:249): sau source eligibility + durable receipt, lấy guard và kiểm lại destination/marker. Marker create-only O_EXCL/O_NOFOLLOW, chứa canonical receipt; fsync file, namespace directory, parent directory, readback rồi mới mkdir đích/DB. Guard giữ qua copy commit và checked reopen. Marker không bị unlink/reset. Trước marker chưa có reservation; marker đã tạo nhưng rỗng/torn cũng không bao giờ được hiểu là fresh.
- [migration.py:reconcile](/Users/macbookpro/Documents/DACN_implementation/packages/s02/src/dacn_s02/migration.py:228): đối chiếu giá trị JSON của marker với receipt (không coi thứ tự members/whitespace là identity); marker hợp lệ nhưng chưa có directory là partial. Marker sai/torn giữ lỗi, không tự ghi lại. Resume chỉ dùng cùng receipt; không cấp lại IDs, reset hoặc implicit copy đích partial.
- [repository.py](/Users/macbookpro/Documents/DACN_implementation/packages/s02/src/dacn_s02/repository.py:73): initialize lấy cùng guard trước kiểm/DB effects. Missing/version0 có marker bị từ chối trước create/write. Kho nonempty phải qua writable + full checker; nếu có marker thì origin phải migration và binding khớp manifest. Kho committed-inactive vẫn báo ACTIVATION_REQUIRED; active hợp lệ chỉ checked read, giữ bytes/IDs/operator/timestamp. DB1 vẫn bị từ chối từ inspection mode=ro.
- [cli.py](/Users/macbookpro/Documents/DACN_implementation/packages/s02/src/dacn_s02/cli.py:42): gọi `initialize(create_parent=True)`; leaf mkdir nằm trong guard thay vì CLI tạo ngoài lock. API cũ mặc định không tạo parent. Chỉ CLI/explicit caller mới dùng tùy chọn tạo parent này.
- [tests](/Users/macbookpro/Documents/DACN_implementation/packages/s02/tests/test_migration_reservation.py:1), [spawn worker](/Users/macbookpro/Documents/DACN_implementation/packages/s02/tests/reservation_worker.py:1): 34 cases mới/backend; gồm 12 SIGKILL cases (6 checkpoint × API/CLI), 8 migration-first API/CLI races, fresh-first race, ACK loss/restart, malformed markers, valid fresh rollback retry, active binding refusal, 4 case/Unicode alias controls và kill lúc vừa tạo namespace; thêm control receipt cùng identity nhưng đảo thứ tự members/whitespace vẫn được copy-resume/reconcile/activate nhận, giữ nguyên cả hai receipt và marker bytes.

## Thứ tự durability và concurrency

1. Đọc nguồn mode=ro, kiểm eligibility/full legacy/DB2 projection. Giữ source read transaction. Durable receipt đã có đủ identity trước destination effects.
2. Lấy flock parent. Fresh init cũng lấy cùng inode lock, kể cả qua tên alias; không có cửa sổ check-then-write không khóa giữa hai entry points.
3. Tạo namespace nếu cần. Crash tại đây chưa có marker/target: reconcile missing; resume cùng receipt được phép.
4. Tạo marker O_EXCL. Từ lúc entry xuất hiện, init fail-closed, kể cả marker rỗng. Nếu process chết trước durability, chưa tạo target; nếu marker còn thì giữ hold, không tự repair.
5. Fsync marker + namespace + parent trước tạo target. Sau barrier này, target có thể vắng, partial, rollback/version0 hoặc hot journal nhưng reservation đã bền vững và init không thể phân loại nó fresh.
6. Copy transaction/commit/reopen dưới guard. Process death thả flock; marker tồn tại độc lập. Activation vẫn là explicit transaction riêng, không thay đổi logic.

Nếu init giữ lock trước, copy chờ rồi đối soát thấy fresh store và từ chối, không đổi identity hoặc tạo marker. Nếu copy giữ lock trước, init chờ rồi từ chối inactive/partial; active migration mới có đường idempotent. Guard serialize cả sibling stores dùng chung parent; timeout là lỗi có thể retry cùng operation, không auto repair. Source lock không thay writer fencing sau khi protocol release; operator vẫn phải dừng writer cũ.

## Kết quả thực chạy mới

Mỗi số là **một backend**, không cộng C/Python, không coi overlap giữa suites là coverage độc nhất. Wheel cài non-editable, cwd ngoài source, CPython 3.13.16 GIL/SQLite 3.53.1/macOS arm64; instrumentation gọi encoder thực, Python fallback có 0 C encoder calls.

| Bộ kiểm | C | Python | Evidence |
| --- | --- | --- | --- |
| a1 oracle partial-init, trước sửa | 3 pass + 7 fail | 3 pass + 7 fail | baseline-p3-oracles/checks/audit-1-* |
| a1 oracle preservation, trước sửa | 4 pass | 4 pass | baseline-p3-oracles/checks/audit-2-* |
| a2 oracle partial-init nguyên bản | 10 pass | 10 pass | handoff-focused/checks/audit-1-* |
| a2 oracle preservation nguyên bản | 4 pass | 4 pass | handoff-focused/checks/audit-2-* |
| Regression mới riêng finding | 34 pass | 34 pass | handoff-focused/checks/audit-3-* |
| Full S02, gồm các ca mới | 623 pass | 623 pass | handoff-full/checks |
| Full S01 a6 | 986 pass | 986 pass | handoff-s01 |
| Sáu oracle P1 nguyên bản | 27 pass | 27 pass | handoff-p1-oracles/checks |
| Ba oracle P2 nguyên bản | 16 pass + 1 known setup fail | 16 pass + 1 known setup fail | handoff-p2-original/checks |
| P2 v2 + boundaries | 17 pass | 17 pass | handoff-p2-v2/checks |

Không skip/xfail hoặc sửa assertions/oracle. Ca P2 `test_writer_refuses_review_fork_after_selection_loss` vẫn gọi checked heads ngoài pytest.raises sau corruption: lỗi setup đã được auditor xác nhận ở P2 a2 và P3 a1, giữ nguyên và báo riêng. Không dùng harness persistence P2 cũ sai API. `helper-preservation.json` đối chiếu toàn input/helper/adaptor cũ với lượt baseline mới; assertions/helpers lịch sử không đổi. Adapter P2 chỉ là lane đã chốt, production được import từ installed wheel.

Full S02 chạy lại cả eligibility/source RO/hot journal, lost ACK, raw17-table preservation, activation identity/races và P1/P2 regressions; không dùng số lịch sử thay kết quả. L1 differential chạy mới phase1 a3, P1 a3 và candidate trên hai backends: 413/413 outcomes khớp, 67 accepted; xem [differential-summary](differential-summary.json). Không chạy lại full baseline suites 383/217; baseline wheels chỉ dùng fixture generation/differential trong lượt này.

Chi tiết JUnit, tên failures, logs, counts tại [test-results](test-results.json), [instrumentation](instrumentation.json), mỗi `*.command.json` chứa argv/cwd/environment/exit code. Các process checkpoints ghi PID, monotonic time và backend counts trong logs/observations; SIGKILL là kill process thật, khác với exception hooks.

## Package và bảo toàn

Wheel duy nhất chọn audit: [dacn_s02-0.4.0a2-py3-none-any.whl](handoff-wheel/dacn_s02-0.4.0a2-py3-none-any.whl). SHA-256 `7fbd0fb483989f7e57f53ee2b4545aa72b2efec07e36c9436401af55cd5d97ab`. `handoff-build` và `handoff-rebuild` dùng hai copy sạch; so **30 ZIP entries**, gồm payload, METADATA/WHEEL/top_level/RECORD, bằng nhau. Không ép ZIP SHA trùng artifact lịch sử. Collector kiểm 26 payload S02 + 16 S01, direct URL non-editable, metadata và source–wheel–installed; pip check đạt. [Package evidence](handoff-package-evidence/), [rebuild](rebuild-comparison-handoff.json), [a1→a2 wheel diff](wheel-a1-a2-diff-handoff.json).

Inventory trước sửa có 8.793 file (loại trừ .git, runtime/tools/venv caches, __pycache__, .pytest_cache, build/egg-info và chính output mới; không giả định Git HEAD đại diện dirty workspace): 8.783 giữ hash; 10 file đổi trong allowlist (5 production/version, 5 hướng dẫn hiện hành), thêm 3 file (reservation/helper/tests). [Inventory gốc](input-inventory.json), [bảo toàn](preservation-handoff.json), [diff đúng dirty-state](changes-handoff.patch), [Git trước](git-before.txt)/[sau](git-handoff.txt). Không reset/index/commit hoặc dọn artifacts.

3.938 artifacts handoff a1 và 814 artifacts audit a1 giữ nguyên hashes/seals; [historical-seals](historical-seals-handoff.json). Schemas L1/E1/registry/manifest, DDL1/DDL2, S01 a6, locks/dependencies và validators không đổi. So AST riêng `_check_legacy`, `_check_db2`, read/write gate, `_source`, `_seed`, target checker, activation, manifest và receipt durability đều nguyên: [invariant bodies](invariant-body-preservation-handoff.json). IDs contract/profile/rules giữ nguyên; actual code bundle hash thay theo code thật và được manifest generator tính lại khi copy. Hash mới `b7f0d428d989222533c5be03bfe8240bcdb84ec585edc00b42f51116791e4f57`, độc lập tính lại từ wheel bằng installed rules_hash; [đối chiếu IDs/hashes](rules-hash-comparison.json).

## Attempts và giới hạn

Lượt collector `preservation-handoff` đã kiểm inventory/AST/seals/rebuild nhưng dừng do script thay nhầm path baseline a1 thành handoff-wheel. `finish-handoff-evidence` chỉ tiếp tục phần còn lại với path audit-wheel a1 đúng, kiểm lại hashes hiện hành; giữ log lỗi đầu. Lượt reproduce-handoff-focused bị dừng vì metadata handoff.json chưa được tạo do lỗi collector trên; retry vào output mới với label v2. Đây là lỗi orchestration evidence của implementation agent, không đổi production, oracle hoặc kho lịch sử.

Giữ mọi attempt/log: `dev` là build đầu; `dev2-focused` chạy hai oracle pass nhưng test mới đụng hai conftest nên setup fail. `dev2-retry-focused` lộ lỗi helper mới dùng disk() cho directory chưa tồn tại (12 fail/backend); đã thêm snapshot phân biệt absent/empty trong **test mới**, không sửa helpers/oracles cũ. `dev2-retry2-focused` đạt 23 case/backend. Các `final-*` (full 617 tests/backend, 5 failures diagnostic) là candidate trung gian trước khi tự rà soát phát hiện hash tên marker không giữ filesystem case equivalence. Sau đổi sang namespace + leaf thật, candidate `release-*` qua oracle/controls nhưng full regression vẫn phát hiện 5 failures/backend do trả mã lỗi mới MIGRATION_IDENTITY_MISMATCH thay vì MIGRATION_IDENTITY_CONFLICT đã chốt. Đã sửa đúng mã lỗi production, giữ assertions; build `audit-*` và chạy lại campaign. Rà soát compatibility sau đó bổ sung control receipt cùng identity nhưng khác thứ tự JSON/whitespace; đổi đối soát marker sang giá trị JSON, không sửa receipt. Build `handoff-*` từ copy sạch/venv mới và chạy lại toàn bộ kiểm chứng. Không dùng wheel/kết quả `dev*`, `final*`, `release-*`, `audit-*` hoặc `handoff-rebuilt-wheel` thay wheel audit chỉ định.

- Bảo vệ cooperating a2 init/copy trên filesystem local đã pin. Không chống SQL thô, executable a1, xóa/đổi namespace, đổi parent inode, hoặc di chuyển stores ngoài protocol. Không tuyên bố advisory lock là security boundary với writer không hợp tác.
- **Partial do a1 tạo trước đây không có marker và không có metadata không thể phân biệt bằng bytes với fresh directory/DB rỗng. Giữ quarantine/evidence, không chạy init trên chúng.** Không tự scan/discover receipts, retro-fit marker, repair hay dọn các partial lịch sử. Các kho a1 committed/active vẫn phải qua checked metadata như trước.
- SIGKILL/checkpoints và fsync ordering không phải mô phỏng hardware power loss, disk-full thật, network filesystem hoặc mọi scheduling. Case/Unicode alias tests khẳng định filesystem premise của baseline macOS; không dùng skip để che môi trường không tương thích.
- Không migration operational, dataset mutation, LLM/live, tự cutover/config, 2B/2C, authentication persistence hoặc performance certification. Human review inputs vẫn do caller tin cậy cấp bên ngoài DB; không tự tạo human approval.
- Reproduction wrapper đã chạy `--help` và `--focused-only` end-to-end trên đúng wheel bàn giao trong 4 venv mới: baseline 7 fail/7 pass và candidate 48 pass mỗi backend; [logs/JUnit/hash copies](reproduction-focused-evidence/summary.json). Chưa chạy wrapper full end-to-end thêm lần nữa; các thành phần đầy đủ đã thực chạy trong campaign. Hướng dẫn tại [REPRODUCE](REPRODUCE.md).

Auditor cần kiểm lại wheel/hash chỉ định, thứ tự durability, race/kill/name-alias controls và giới hạn trên. **Đã sửa, chờ audit lại.**
