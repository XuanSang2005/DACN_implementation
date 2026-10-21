# Bàn giao Đợt 1 S02 — nền tảng và nối S01

Ngày **19/10/2026**, Asia/Ho_Chi_Minh. Package **dacn-s02 0.1.0a1**. Trạng thái: **đã implement và kiểm thử nền tảng; chờ audit, chưa nghiệm thu**. Không mở Đợt 2.

## Căn cứ và baseline

- [Audit thiết kế draft.3](/Users/macbookpro/.codex/.chatgpt-projects/g-p-68c38c8799f48191a101e19a975ca4f9/outputs/audits/s02-proposal-draft3-2026-10-19/AUDIT_REPORT.md), [bằng chứng audit](/Users/macbookpro/.codex/.chatgpt-projects/g-p-68c38c8799f48191a101e19a975ca4f9/outputs/audits/s02-proposal-draft3-2026-10-19/audit-evidence.json): F01–F05 đóng ở mức đặc tả, cho phép Đợt 1; không phải nghiệm thu code.
- [Contract](../../docs/S02_OUTPUT_CONTRACT_PROPOSAL.md) `s02/0.1.0-draft.3`, [plan](../../docs/S02_IMPLEMENTATION_PLAN_PROPOSAL.md) `s02-plan/0.1.0-draft.3`. Không đổi version hoặc semantics. [So sánh](proposal-rule-comparison.json) xác nhận toàn nội dung từ §1 của cả hai file giữ nguyên; chỉ cập nhật trạng thái đầu tài liệu.
- S01 giữ **0.1.0a6**, input **1.0.0**, output **0.1.0-draft.2**, DB **1**. Runtime quan sát: CPython **3.13.16 GIL**, SQLite **3.53.1**, macOS arm64. Không nâng dependency baseline.
- Trước sửa đã đối chiếu đúng hashes của **13 file** trong audit draft.3 và chụp [baseline mới](baseline.json). Tập bảo vệ lần này gồm **198 file được liệt kê**, không dùng lại số 185 như bằng chứng mới và không tuyên bố kiểm toàn filesystem/dataset. AGENTS và hai phần trạng thái proposal được phép sửa riêng.

## Phạm vi đã làm và tổ chức package

Package, venv, locks, source, tests, tools, wheel đặt trong [s02/](../../s02/). Không ghi đè root pyproject, locks, src/tests/tools S01 hoặc các wheels a1–a6. Dependency S01 cài từ wheel a6; không editable install. Metadata S02 pin S01 a6/jsonschema 4.26.0; lock toàn môi trường gồm simplejson 4.2.0, pytest 9.1.1 và các wheels nền tảng hiện có. Không cài SDK LLM hoặc renderer.

| File/nhóm | Nội dung và lý do |
| --- | --- |
| [AGENTS.md](../../AGENTS.md) | Dẫn audit thiết kế; giới hạn Đợt 1; bắt buộc F01–F05 và bàn giao audit trước Đợt 2 |
| Hai proposal S02 | Chỉ trạng thái đầu file; giữ các điều khoản từ §1 |
| [pyproject.toml](../../s02/pyproject.toml), `.python-version`, hai locks | Namespace `dacn_s02`, môi trường riêng, offline exact wheel hashes cho platform đang kiểm |
| [schemas/contract.json](../../s02/src/dacn_s02/schemas/contract.json), [materialize_schema.py](../../s02/tools/materialize_schema.py) | Draft 2020-12 cho Record/export, toàn các body, refs và payload vận hành. Materialize từ bảng trường contract, không suy schema từ examples |
| [codec_boundary.py](../../s02/src/dacn_s02/codec_boundary.py), [errors.py](../../s02/src/dacn_s02/errors.py) | Public codec S01, số chính xác/duplicate keys/Unicode/missing-null, taxonomy S02 và diagnostics an toàn |
| [validation.py](../../s02/src/dacn_s02/validation.py) | Validator riêng; W29, bool khác number, required/unknown fields, typed refs, snapshot pointers, mapping inventory, model/set/record invariants |
| [s01_adapter.py](../../s02/src/dacn_s02/s01_adapter.py) | Checked lookup đúng run/snapshot, allowlist baseline, archive envelope/schema/run source/origin source; không initialize/submit/get_head |
| [storage_schema.py](../../s02/src/dacn_s02/storage_schema.py), [repository.py](../../s02/src/dacn_s02/repository.py) | SQLite riêng, immutable records/BLOB/links, two-head CAS, checked lookup, staging/promotion, application claim, recovery commit chưa rõ |
| [events.py](../../s02/src/dacn_s02/events.py) | Typed T0–T3 và application events; consent/input/request/event lineage, unique applied; chưa điều phối nghiệp vụ clarification |
| [scope.py](../../s02/src/dacn_s02/scope.py) | Closure và reverse impact thuần; mọi Part mở rộng toàn actions, workflow/Support/cycles/global parts, blockers/reanalysis/review scope và hợp cuối |
| [service.py](../../s02/src/dacn_s02/service.py) | Intake/session tối thiểu; điểm cấp command ID trước receipt; start không tạo model/phân tích |
| [local_io.py](../../s02/src/dacn_s02/local_io.py), [cli.py](../../s02/src/dacn_s02/cli.py), `__main__.py` | TOML, path protection, receipt create-only, init/start/show-command/show-record; stdout JSON và exit codes |
| [tests/](../../s02/tests/), [tools/](../../s02/tools/) | Fixtures synthetic, independent expected sets, real processes/SQLite, CLI, runner ngoài checkout và collector |
| [Wheel](../../s02/dist/dacn_s02-0.1.0a1-py3-none-any.whl), thư mục báo cáo này | Artifact bàn giao và bằng chứng thực chạy; hashes/danh sách đầy đủ trong manifest/inventory |

Không có route import JSON/record tùy ý, LLM gọi tool ghi DB, hoặc CLI để tự khai validation/review/handoff. Repository batch APIs là ranh giới **code nội bộ được tin cậy**. Schema shape không tự cấp quyền sinh record hệ thống cho dữ liệu bên ngoài.

## DDL và transaction thực tế

[DDL.sql](DDL.sql) được xuất từ **package đã cài**. `application_id=0x44414332`, structure version **1**. `initialize` chỉ nhận DB trống chưa được claim hoặc DB S02 đúng cấu trúc; foreign/version/DDL khác bị từ chối, không reset/migrate. Mọi connection đọc lại FK=ON, synchronous=FULL, journal=DELETE và kiểm exact DDL. Các pragmas của DB race/kill được ghi trong manifest.

Tables: `sessions`, `records`, `models`, `analysis_sets`, `artifacts`, `operations`, `operation_events`, `staged_blobs`, `promotions`, `application_heads`, `active_reviews`, cùng sáu bảng typed links record/event → record/event/stage. Record JSON có hash bytes; metadata/index columns và links được đối chiếu lại với JSON. Không SQL REAL hoặc JSON numeric extraction. Schema annotations `x-record` sinh links từ fields đã có schema, không nhận links nhập tay.

- Records, artifacts, models, sets, operations, stages, events, promotions và typed links có trigger cấm update/delete. Không `INSERT OR REPLACE`.
- Model parent cùng session, set parent cùng model dùng composite FK; unique revision theo session/model. Head pair có composite FK cùng model/session; kiểm revision/creator/result/parent và latest head bằng code.
- `reserved_run_id` unique ở operations, **không FK tới Run tương lai**. Artifact.producer FK chỉ deferred trong transaction đã có đủ final records. Unique finalized/command, promotion/stage và applied/Answer được DB hỗ trợ; active application/review dùng CAS.
- IDs UUIDv4, kiểm format và uniqueness. Cấp ID trước receipt thử tối đa 8 lần khi collision; ID đã công bố không tự thay. Timestamps UTC millisecond để audit; completion được clamp nếu clock lùi, không dùng clock chọn winner/revision.

Write boundary dùng explicit `BEGIN IMMEDIATE`. T0 prepare operation/session nếu mới, staged bytes và prepared event nguyên tử. T1 dispatch intent là commit riêng trước external send trong giao thức; Đợt 1 chưa có send. T2 capture bytes và response event cùng commit, chưa tạo Artifact/Attempt/Run. T3 đọc base pair/source, kiểm trước no-op, ghi records/promotions/final Run/typed links/applied event nếu có/finalized event/head trong **một commit**. New Run không được tự nhận một set cũ là kết quả vừa công bố. Source archive chỉ commit cùng SourceContext ở intake.

Writer tự kiểm graph/hashes/FK/metadata trước COMMIT và chỉ trả kết quả sau COMMIT. Khi head đã đổi, finalization giữ Artifact/Run evidence, trả Run stale với MODEL_CONFLICT hoặc ANALYSIS_CONFLICT, không publish candidate/rebase. Log tăng sequence vận hành nhưng không đổi head pair. Review pointer có CAS riêng ở tầng persistence; chưa có workflow review/acceptance hoàn chỉnh.

Checked reads dùng một read transaction nhất quán và kiểm toàn kho nhỏ: cấu trúc, record hashes, artifact/stage hashes, columns, typed refs, source archives, model/set indexes, heads và event chains. Cách này dễ đối chiếu, đổi lại chi phí lookup tăng theo lịch sử; chưa tối ưu cho kho lớn. Kho S01 dùng public checked reads `mode=rw` để hỗ trợ SQLite recovery theo baseline; intake không sửa requirements/history và không thêm bảng S01. Test hash S01 thực hiện lúc DB quiescent.

## Recovery, identity và ranh giới F03

Receipt `s02/1` được publish create-only bằng temp file + fsync + link + fsync directory, biết command ID trước intake/T0. Không có atomic transaction xuyên receipt filesystem và DB. Receipt còn đó sau mất phản hồi giúp lookup; nó không chứng minh command đã commit. Intake thất bại trước T0 không tạo SourceContext tin cậy; receipt có thể lookup không thấy command. `start` với command ID đã có bị từ chối và yêu cầu lookup.

Lỗi trước COMMIT có rollback; lock timeout là PERSISTENCE_FAILED, không conflict revision. Nếu COMMIT đã thử mà kết quả chưa rõ, writer đóng connection cũ và đối soát command/event/final Run qua **connection mới**. Có kết quả đã commit thì trả đúng kết quả đó; không ghi đè thành failed. Nếu chưa xác định được thì giữ lỗi commit outcome unknown, yêu cầu lookup, không tự submit lại.

Lookup command dẫn xuất prepared/dispatch_unknown/captured/finalized/interrupted từ events. Captured phục hồi bằng chính staged bytes; dispatch_unknown không tự biến thành chưa gửi. Recovery intent có command riêng và parent gốc; finalization vẫn CAS command/reserved Run gốc. Chưa có CLI recovery/orchestrator/network; test fixtures chứng minh cơ chế lưu/đọc/finalize, không chứng minh exactly-once provider.

Answer text/initial interpretation bất biến. Interpretation/consent/S01 dispatch/observation/application/recovery là typed events, giữ refs đúng Answer lineage. Claim cạnh tranh một Answer chỉ một winner. `application_applied` cùng Change/model/AnalysisSet/resolved Issue/final Run; applied unique theo Answer. Fixture existing-source apply/retry không tạo Answer thứ hai. Consent hash và exact S01 request được kiểm; không có lời người dùng thật hoặc S01 update thật do S02 thực hiện trong đợt này.

## Scope closure và freshness

Closure dùng work sets theo IDs, không limit độ sâu rồi cho qua. **Part mới phát hiện luôn nạp đủ action_ids**, sau đó tiếp tục workflow từ entry, rules, matching parts, Dependency.Support, prerequisites và global system parts. Cycles hội tụ; Support null/choice unknown hoặc selected action không reachable giữ SCOPE_UNDETERMINED. Không expand mọi action chỉ vì chung responsibility/component/interface. Actor/data refs được kiểm cấu trúc, không tự biến thành các actions bổ sung.

Chỉ sau fixed point mới kiểm accepted scope, current blocking Issues, model states, pending reanalysis và blocking conditions. Hợp cuối được closure/gate lại. `allowed_scope` giữ đầy đủ supporting context cần dùng. `blocked_scope` của hàm thuần biểu diễn các **actions/parts còn bị chặn**, theo ba ví dụ F04 mới trong file08; không lấy phần bù của mọi actor/data/support node làm nghĩa vụ bị chặn. Chi tiết closure và reasons của từng seed được trả nội bộ để giải thích. Code không tự đọc guard/prose để chứng minh độc lập.

AnalysisSet current selection có đúng một record/key; không âm thầm bỏ key; successor trỏ record current; Scenario thay làm Characteristic tham chiếu bản cũ bị từ chối. Affected kiểm hợp scope và reverse closure; unknown thì conservative full scope. Đổi set cùng model làm bundle/validation cũ stale. Historical lookup giữ nguyên record; dùng để handoff phải qua `check_freshness` và các gates đầy đủ ở các đợt sau. Không mang approval qua set/model mới.

## Kiểm thử và bằng chứng thực chạy

[Tổng hợp thực chạy](execution-summary.json), [lệnh S02](s02-commands.json), [lệnh S01 regression](s01-commands.json), [quan sát S02](s02-observations.json), [quan sát S01](s01-observations.json). Các file `.log` giữ stdout/stderr, working directory và exit code; không dùng test count thay cho oracle các bất biến.

| Suite thực chạy | Passed | Failed | Skipped | Exit |
| --- | ---: | ---: | ---: | ---: |
| s01-c | 986 | 0 | 0 | 0 |
| s01-python | 986 | 0 | 0 | 0 |
| s02-c | 141 | 0 | 0 | 0 |
| s02-python | 141 | 0 | 0 | 0 |

Các suite chạy từ installed wheel ngoài checkout, không skipped/xfail. Instrumentation quan sát factory C/Python thực; process workers và CLI harness ghi số đếm riêng. Test CLI thông thường còn chạy entrypoint `python -m dacn_s02` mặc định; probe riêng chứng minh CLI cùng Service chạy được với fallback Python. Không diễn giải biến môi trường đơn thuần thành bằng chứng backend.

Năm lịch cạnh tranh thực dùng **hai spawned processes, hai kết nối riêng, cùng DB file**, barrier và deadlines:

| Lịch | Oracle và kết quả quan sát |
| --- | --- |
| Hai model publications cùng base | Một completed, một stale/MODEL_CONFLICT; một model/set được commit |
| Hai AnalysisSet publications cùng base | Một completed, một stale/ANALYSIS_CONFLICT; head set tăng một lần |
| AnalysisSet publication và log | Cả hai thành công; log không gây false conflict hoặc tăng head |
| Hai application claims cùng Answer | Một claimed, một APPLICATION_CONFLICT; một active claim |
| Hai finalizations của cùng application command | Cả hai lookup/trả cùng final Run; đúng một applied event và model revision mới |

Đây là năm lịch **S02**, không phải mượn năm lịch revision S01. S01 vẫn chạy nguyên suite riêng. [Process artifacts](process-artifacts/) giữ **18 DB synthetic cuối**: mỗi backend 5 race + 4 kill cases. Lịch event gồm PID, monotonic timestamp, barrier ready/released, begin/commit boundaries, outcome và heads/counts/hashes. Không dùng sleep/tuần tự làm bằng chứng race.

Fault injection bao phủ sau stage/insert, trước commit, trước/sau final record insertion/finalization, mất acknowledgement sau commit, lost-ack T0/T2. Mỗi lần reopen/lookup xác nhận rollback hoặc committed outcome. Lỗi lock dùng SQLite lock thật. Kill dùng terminate process sau IPC xác nhận đúng trước/sau commit của capture/finalize; DB đọc lại bằng connection mới. Raw invalid UTF-8/JSON và chuỗi surrogate không serialize được giữ nguyên bytes; không sửa Unicode để cho qua.

Nhóm contract/unit còn kiểm exact numeric/unknowns, duplicate keys, W29, metadata ID/type/missing-null, source kinds/pointers, schema wrappers không là production export, typed refs, mapping inventory, immutable/FK/unique, parent/head/session, clock lùi, collisions, stale before no-op, revision edit/reorder/quay về nội dung cũ, lookup không tìm thấy/corruption, no future Artifact→Run, same-answer identity, F05 và ba oracle F04 multi-action bắt buộc. `test_document_record_shapes` chỉ shape-check 33 Record minh họa trong tám JSON; không import wrapper hoặc xác nhận trust/nghiệp vụ/render.

Trong phát triển đã có lỗi command path `.tools/uv/uv` và cách truyền tên package cho `pip wheel`; đã sửa thành executable/path local đúng. Các logs ban đầu giữ lại. Tests phát triển cũng phát hiện phân loại freshness bị bọc thành persistence error, đường dẫn đọc examples và expectation nhầm Artifact binding; đã sửa đúng code/test setup, không xóa/skip tests để đạt gate. Đối chiếu cuối bổ sung guard source kind/model ref, result-publication metadata và blocked-scope oracle theo draft.3.

## Package, dữ liệu bảo vệ và tái lập

[Manifest](manifest.json) ghi interpreter/GIL/SQLite/platform, toàn dependency versions/locks, wheel hashes và import paths. Đã so **16 file S01** và **14 file S02** giữa source, installed package và wheel, khớp từng file. S01 wheel hash giữ `e4ebbe7988d7cb5255d93845c94ba41aeb043900c762ca7636d4f7c093bff20b`. S02 wheel hash cuối xem manifest; không dùng hash build trung gian làm baseline bàn giao.

Collector còn tạo venv mới trong directory tạm ngoài checkout, install offline từ hash lock và wheel, kiểm pip/import paths/CLI init thật. [Build evidence](build-evidence.json) ghi build lại ngoài checkout, exit code và hash ZIP riêng; 14 file nội dung khớp wheel đã dùng chạy suite. Không thay wheel đã kiểm thử bằng ZIP build lại. [REPRODUCE.md](REPRODUCE.md) có lệnh build/install/tests/init/intake/lookup, phân biệt hướng dẫn với logs đã chạy. Môi trường và package S01 cũ giữ nguyên; venv S02 riêng.

[Protected after](protected-after.json) đối chiếu bytes hiện tại với baseline đầu lượt; [file inventory](file-inventory.json) liệt kê các file được phép sửa và file mới bàn giao, với hashes. Không copy toàn dataset; không sửa 8 JSON S02, 6 JSON S01, source/schema/baseline S01, LaTeX/PDF hay báo cáo audit cũ. Các DB mới chỉ ở vùng tests tạm và artifacts synthetic của báo cáo này.

## Điều khoản → code → tests → evidence

| Căn cứ | Implementation | Tests chính | Bằng chứng |
| --- | --- | --- | --- |
| §2–3 exact codec/refs/intake | codec_boundary, validation, s01_adapter, Service.start | test_boundary; test_repository intake/precise archive/no S01 writes; test_revision_contract typed sources | suite logs; source/installed/wheel manifest; protected hashes |
| F01 §6.1 / §7 | validate_set, publication head pair, freshness, indices/typed links | test_revision_contract scenario successor/bundle stale; test_repository log/set; test_processes model/set/log races | observations real_two_process_race; final DBs |
| F02 §4.3 | staging/events, promotions, reserved Run and atomic finalize | test_lifecycle T0–T3 invalid bytes/unknown; test_additional_guards future FK/recovery/lost-ack; test_processes capture/finalize kill | F02_invalid_captured/F02_unknown; lost_ack_boundary; real_process_termination |
| F03 §4.4 | Answer immutable, typed application chain, active claim, unique applied, atomic Change/Issue/model/set | test_lifecycle fixture apply/consent/recovery/fault; test_processes claim/finalization race | F03_atomic_application; application race DBs; no claim full business flow |
| F04 §9.1 | scope.closure/permitted_scope/reverse_impact | test_scope handwritten sets: multi-action blocked/clear/split; prerequisite, branch, cycles, shared/global/union; extra unreachable-choice guard | both suite logs; expected sets in test source, independent of production calculation |
| F05 §5 Action | action_initiator_actors invariant | test_boundary 6 initiator/actor combinations | both suite logs; external structural validity leaves permission rules unknown |
| §4,7 persistence/lifecycle | DDL, exact structure, explicit transactions, checked lookup/reconciliation | test_repository immutable/FK/hash/lock/fault/clock; test_additional_guards; revision chain | DDL.sql; manifest; fault/real lock/reopen logs |
| Plan §4 / minimal CLI | local_io/cli, ID before receipt, no import route | test_cli stdout/exit/config/path/receipt/lookup/probe | installed_cli_backend observations; clean environment command logs |

## Giới hạn và điểm auditor cần xem

- Chưa implement Đợt 2–5: không prompt phân tích, LLM/HTTP, full orchestrator, lời trả lời/consent thật, S02 điều phối S01 update, converter/renderer, review UI/workflow hoàn chỉnh, S03/KB, pilot/benchmark/dataset evaluation. Những schema/gates foundation cho các records tương lai không phải bằng chứng các bước đó đã chạy.
- Tests dùng dữ liệu synthetic và fixtures/stubs của application records. Quyền nghiệp vụ, rationale, completeness obligations/dependencies, independence evidence và nguồn suy luận vẫn cần review; structure passed không xác nhận các điều đó.
- Persistence dùng local trusted store, không chữ ký/authentication trước người có quyền sửa cả code/DB. Path guards xử lý symlink/hardlink/static aliases; không sandbox trước hostile concurrent filesystem rename.
- Chưa kiểm mất điện, disk-full, network filesystem, Windows/Linux hoặc durability ngoài SQLite/local environment đã chạy. Chưa có migration/backup/pruning/large-store performance; không tự reset DB hoặc xóa raw history.
- Không có transaction xuyên S01/S02/filesystem/provider. Recovery API nền tảng không tuyên bố API idempotency hay exactly-once provider. CLI `start` chỉ intake; lỗi trước T0 có thể để receipt nhưng không có command, cần lookup/đối soát.
- Internal `work` request và event payloads prepared/dispatch/capture/log được cụ thể hóa thành schema đóng để kiểm cơ chế. Đợt 2 thêm candidate/transport orchestration theo contract, không cho dữ liệu LLM ghi arbitrary Records. Secrets không là config artifact được tạo bởi Service.
- Auditor ưu tiên CAS hai head/current selection, thứ tự event/promotion và unknown commit; application claim/unique applied; full multi-action closure và minimum blocked-use representation; exact source archive/typed links và checked historical lookup; xem manifests/DB cuối thay vì chỉ test count.

**Đợt 1 S02 đã bàn giao, đang chờ audit; chưa nghiệm thu và chưa bắt đầu Đợt 2.**
