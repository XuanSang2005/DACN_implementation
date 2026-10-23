# Bàn giao implementation S02 2A-P1

Ngày 22/10/2026, Asia/Ho_Chi_Minh. **Package `dacn-s02 0.2.0a1`, phạm vi profiles và validators; chờ auditor độc lập, chưa được audit/ nghiệm thu P1.** Căn cứ giao việc: [yêu cầu người dùng](P1_ASSIGNMENT.txt). Nghiệm thu kỹ thuật S01 a6/S02 a3 Đợt 1 giữ nguyên phạm vi lịch sử; kết luận thiết kế A1/A2/storage draft.2 không được dùng làm nghiệm thu code này.

## Phạm vi và kết quả

Đã triển khai registry L1/E1 và E1 materialized từ baseline ghim byte; profile dispatch trong shape/walking/typed links/graph; A1 kiểm archive quan sát; DIRECT/CARRY/REPLACEMENT và source/scope/lineage/coverage/blockers; fixtures canonical, tests, packaging đệ quy, hướng dẫn và evidence. E1 contract `s02/0.1.0-draft.4`, rules `s02-rules/a1a2-v1`. L1 giữ schema a3 nguyên byte và oracle legacy. `CONTRACT_VERSION`/config intake legacy vẫn draft.3.

**Repository, storage_schema, DB_VERSION=1, service/CLI, locks và dependencies không đổi.** E1 chỉ được kiểm trong bộ nhớ bằng API nội bộ có owner maps tường minh. Không triển khai E1 writes/mixed-store persistence, DB2, P2/P3, migration/cutover/activation, orchestration 2C, G3/G4, LLM live, renderer, KB hoặc S03. `check_base_pair` là checker thuần, không giả transaction CAS; claim/paired heads/unique application legacy vẫn do repository/SQL hiện hành bảo vệ.

[Hướng dẫn thiết kế implementation](../../../docs/S02_2A_P1_IMPLEMENTATION.md) mô tả API, dispatch, nguồn thẩm quyền, schema/required/nullability/typed refs, ba nhánh resolution và fixtures/oracle mapping. [Schema diff máy đọc](schema-changes.json) có 16 thay đổi ở cây schema, gồm các defs mới đầy đủ; không sửa resource L1 hoặc draft.3 lịch sử.

## Artifact bàn giao duy nhất

Dùng `release/`, không dùng các wheel trung gian trong `build-*`, `wheels` hoặc `wheels-final`.

| Artifact | SHA-256 |
| --- | --- |
| [S02 wheel P1](release/dacn_s02-0.2.0a1-py3-none-any.whl) | `38ed24de6769d9bcaf76927c8c5ffbcaf587972192d1fe0f24f16435b6d24df2` |
| [S01 wheel rebuild cùng a6](release/dacn_s01-0.1.0a6-py3-none-any.whl) | `1f9bac4c4175eda8520a58ee9bc754612c41806b7d34e59d579904cfd8448027` |
| L1 schema | `dd32824ab03c5e4d5faae3eb3888bdea3cacd5ba4735a4a5df19416b024f70b7` |
| E1 schema | `bd8eb8e838b709edfa6f5ac3d710fb5e3414985270cad35f5aa86acf7f5ebf6d` |
| Registry resource | `d36d80be7f768dd84ccd64306f8f7a32a5f9734be6332961a2daf0ed4cf50f7e` |
| [Rules bundle thực tế](rules-bundle-release.json) | `241c0233d05357ae503431338afdab82036f7957ff9e4a27bb042273e57c36aa` |

Rules bundle là manifest các module thực tế; hash của nó không được diễn giải thành chứng nhận semantics. [Package evidence](release-package-evidence/manifest.json) kiểm đủ source = wheel = installed: S01 16 payload files, S02 20 payload files, có hai resources profile lồng thư mục, cùng METADATA/WHEEL và direct_url artifact hash. [Diff a3 → P1](release-package-evidence/s02-baseline.diff) riêng với phép so cùng phiên bản. S01 cài lock từ wheel lịch sử rồi chỉ thay bằng rebuild sau [đối chiếu payload/METADATA/WHEEL](s01-before-wheel-replacement.json); không ép ZIP hash rebuild bằng ZIP cũ, không sửa lock.

Release build từ cây copy mới, có [provenance](release-build-provenance.json). Release venv `/tmp/dacn-2a-p1-20261022/release-venv` tạo mới từ locks, cài non-editable; runner chạy tests bằng process/package/backend riêng, cwd tạm ngoài source, không đưa production src vào sys.path. [pip check](release-pip-check.log) đạt. [Các lệnh tái lập](REPRODUCE.md) dùng output mới.

## Thay đổi và lý do

| Nhóm file | Thay đổi / lý do |
| --- | --- |
| AGENTS.md | Ghi quyền riêng P1 và trạng thái audit thiết kế storage draft.2 đã đóng; vẫn giữ gate P2/P3/live |
| pyproject, `__init__.py` | Package 0.2.0a1 và include resources lồng thư mục; không đổi dependencies hoặc marker contract legacy |
| profiles.py, resources, materialize_profiles.py | Allowlist profiles/descriptor/hash/capabilities; schema immutable theo request, không union/fallback; E1 Export không khả dụng |
| validation.py, events.py | Explicit owner profile; DIRECT root giữ a3; lịch sử đúng path, phần còn lại current; event/stage kế thừa operation; A1 dispatch theo snapshot |
| observed_source.py | Base/request/consent/run/source identities, raw run bytes/hash so consent, phân biệt Cmodel/Cobserved; no-resend qua ancestor |
| resolution.py | CARRY và REPLACEMENT riêng; lineage/current selection, source/criterion và footprint coverage, matrix method–assessment, task evidence, re-hold; không retarget root |
| profile_graph.py | Pure whole-graph checks qua owner maps, session/archive/refs/publication/inventory; new records cùng profile operation, reused records giữ profile cũ; không storage API |
| scope.py | Thêm E1 revalidation blocker ở gate; thuật toán closure fixed point và mở mọi Part.action_ids giữ nguyên |
| Tests mới, profile_fixtures.py | Canonical synthetic cases và mutation negatives riêng; không sửa suite/assertions a3 |
| Tài liệu P1 và thư mục này | Dispatch/schema/oracle mapping, actual logs, hashes, giới hạn và handoff |

[Diff riêng lượt P1](implementation-release.diff) so **trạng thái trước sửa thực tế**, không gom các tài liệu dirty sẵn vào thay đổi của lượt này. [Source inputs](source-inputs-release.json), [test inputs](test-inputs-release.json), [before inventory](before-inventory.json), [Git trước](before-status.txt) và [Git bàn giao](git-status-release.txt) cho phép đối chiếu. Không commit hoặc reset công việc người dùng.

832 files trước sửa: [826 giữ nguyên, 6 thay đổi đúng phạm vi, không mất file](protected-inventory-release.json); thêm 12 files implementation/docs mới, ngoài evidence. Những tài liệu/ví dụ dirty sẵn, baseline wheels, production repository/storage, tests cũ, toàn bộ S01 và locks trong inventory đều giữ nguyên byte. Exclusions inventory là `.git`, `.venv`, `.runtime`, `.tools`, `__pycache__`, `.pytest_cache`; không tuyên bố đã snapshot toàn filesystem/dataset.

## Kiểm chứng thực chạy

Kết quả tổng hợp, counts, backend instrumentation và từng log nằm trong [TEST_RESULTS](TEST_RESULTS.md) và [machine summary](test-results-release.json). Các `*.command.json` có argv/cwd/exit_code; runner logs/JUnit/observations giữ kết quả cụ thể. Các kiểm thử này thực sự chạy, không phải bảng kỳ vọng.

- Lane a3: wheel a3 trong venv riêng, bản sao suite nguyên byte từ trước sửa; cả hai backends. Không đổi oracle để thích nghi E1.
- Lane P1: toàn suite S02 hiện tại, gồm 217 tests legacy và tests P1 mới, hai backends. Audit regression files a1/a2 chạy nguyên file bằng adapter helper, không sửa assertions. Đây là chạy lại oracle lịch sử, **không phải audit độc lập P1**.
- S01 regression a6 chạy riêng process/backend, trên wheel rebuild cùng payload baseline. Không diễn giải số tests lịch sử như kết quả mới; logs lần này được dẫn cụ thể.
- Differential L1: [413 trường hợp](differential-release-summary.json), 67 accepted và 346 rejected; outcomes, diagnostics và walk paths khớp giữa a3/P1 trên C/Python, không unexpected exceptions. Đây là corpus hữu hạn, không chứng minh equivalence mọi input.
- E1 tests gồm thiếu/null/unknown profiles, concurrent dispatch không mutate SCHEMA, T3 owner mismatch; A1 cùng snapshot và unchanged với Model dùng snapshot khác; run/raw/request/hash/base/no-resend negatives; DIRECT legacy/E1; carry lineage/history/current refs, method matrix, missing proof, source switch; replacement initial/continuation/re-hold, obsolete root, current target, source-only/removal, coverage/task attestation, review binding, set fork/stale base; full Part closure và gate blocker.
- [Năm canonical graphs cuối](canonical-fixtures-final/) được tạo và đọc lại bằng wheel release; [log xác minh](release-verify-fixtures.log). Đây là graphs/bytes hợp schema và graph validators, có synthetic review inputs riêng, không phải canonical production exports. `Export` E1 bị chặn; không có trusted-import endpoint.

Bản mẫu dùng test data synthetic. Trong các ca A1 có S01 Service/checked lookup **thật trên kho tạm**, không orchestration 2C hay operational update. Review/consent trong fixtures là giả định để kiểm code, không người dùng đồng ý. Không gọi LLM/API/renderer, không có kết quả đo p95 hoặc đánh giá ngữ nghĩa/held-out.

## Tự kiểm, lỗi trung gian và bảo toàn workspace

Logs trung gian giữ nguyên để audit, không trộn vào kết quả release:

1. Lượt đầu refactor có biến schema bị che trong vòng walk events; regression phát hiện, sửa trước các build tiếp theo. Không nới assertions.
2. Ca current Trace trỏ predecessor phát hiện miễn kiểm theo giá trị ID quá rộng cho E1. Đã giới hạn E1 theo **đường dẫn field**; L1 giữ oracle a3. Thêm guards set fork/stale base và profile của publication. Lượt `s02-final-checks` còn dùng wheel trước guard profile trong lúc tests mới đã được thêm; nó là diagnostic, không phải lane release. Release dùng venv/wheel và bộ test-input hashes riêng được giữ ổn định.
3. Generator fixture ban đầu thiếu thư mục temp; serializer report differential ban đầu chứa tuple không phải JSON. Sửa harness và chạy lại ở output mới. Các lỗi này không được báo là kết quả validator nghiệp vụ.
4. Workspace builder dù có wheel output mới vẫn ghi setuptools cache đã có. So inventory phát hiện cache thực là a2. Đã phục hồi **đúng hash trước sửa** sáu file cache, giữ bytes sinh ra ở `build-cache-produced/`; cache mới do lượt này sinh được lưu evidence trước loại khỏi cache. [Script](restore_build_cache.py) kiểm toàn before images trước ghi; lần thử dùng a3 bị từ chối trước writes, lần a2 đúng hashes thành công. [Restoration evidence](build-cache-restoration.json). Wheel baseline/evidence lịch sử không bị ghi đè; release build chuyển sang cây copy riêng. Inventory cuối xác nhận caches cũ nguyên byte.

Các output tên `build-*`, `wheels*`, `checks-01`, `final-checks`, `s02-final-checks`, `canonical-fixtures` và rules manifests trước release là lịch sử tự kiểm. Riêng `final-checks/s01-*` là kết quả S01 được dùng vì code/wheel S01 không đổi sau đó; fixture L1 cũ giữ làm corpus differential cố định. Chỉ wheel trong `release/` và test results được chỉ rõ trong TEST_RESULTS là đối tượng bàn giao cuối.

## Giới hạn và nội dung auditor cần xem

Chưa chứng minh E1 database persistence/atomic CAS/claims/mixed-store FK, migration readonly/activation/receipts/IPC/durability của P2/P3. Legacy DB1 concurrency/fault/recovery chỉ là regression trong phạm vi a3, không mở rộng nghiệm thu. P1 không đổi luật nguồn readonly của migration vì không có code migration.

`HumanReviewEvidence` ngoài payload chỉ ghim một quyết định do caller tin cậy cung cấp vào dependency digest; nó không xác thực danh tính, không chứng minh người thật đã review, không thay consent S01 hoặc Review bước 9. Không có persisted review/authentication adapter mới; phần tích hợp thuộc đợt được giao sau. Caller không được tạo trusted evidence từ metadata LLM.

Code kiểm shape, versions, correspondence, scope/coverage được biểu diễn và liên kết evidence. Nó không chứng minh đủ nghĩa vụ ngữ nghĩa, task evidence đúng nội dung nghiệp vụ, permission/workload/SLA hoặc thiết kế tốt. Các footprint/proof checks bảo thủ; chưa đo hiệu năng graph/histories lớn, chưa có corpus semantic/held-out hay ngưỡng chất lượng. Với thiếu proof, giữ blocker hoặc từ chối graph lỗi; không tự bổ sung nghiệp vụ.

Auditor cần đối chiếu đặc biệt: owner maps và T3 inheritance; DIRECT root a3 nguyên nghĩa; ngoại lệ history đúng field; A1 observed archive/full raw/request/consent với snapshot branch; carry/replacement current-key lineage và coverage/TaskAttestation/re-hold; ranh giới metadata reviewer; L1 differential và payload resources. Các lựa chọn API/hash proof trong implementation này cần review code độc lập, không tự ghi đã được auditor xác nhận.

Không có phụ thuộc P2/P3 buộc mở rộng quyền để hoàn tất lớp P1 thuần. Công việc P2/P3/2C/live chỉ được bắt đầu khi người dùng giao riêng, sau kết quả audit phần liên quan.
