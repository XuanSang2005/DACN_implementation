# Audit S02 Đợt 1 — 0.1.0a3

Ngày **21/10/2026**. **PASS — đóng S02-05 và LAYOUT-01; không có finding mới trong phạm vi kiểm. S02 Đợt 1 được nghiệm thu kỹ thuật trong phạm vi nền tảng và CLI local đã giao.**

S01 giữ nghiệm thu `0.1.0a6`. S02 giữ contract `s02/0.1.0-draft.3`, DB structure 1. Kết luận này không nghiệm thu toàn bộ S02, chất lượng suy luận nghiệp vụ, LLM hoặc diagram; không tự cấp quyền thực thi Đợt 2, gửi dữ liệu hoặc dùng ngân sách API.

Biên bản máy đọc: [S02_PHASE1_ACCEPTANCE.json](S02_PHASE1_ACCEPTANCE.json).

## 1. Kết luận findings

| Finding | Kết luận | Bằng chứng |
| --- | --- | --- |
| S02-05 — config của Run trước dispatch | **Closed trên a3** | Đối chiếu config trước nhánh return; staged/reused/request pin, identity/bytes, rollback, checked read và positive controls đạt; bốn test audit gốc đều passed/backend |
| LAYOUT-01 — override package ở wrappers | **Closed** | Fixed package truyền qua tham số nội bộ, parser wrapper không đăng ký selector, abbreviation tắt; 339 regression wrapper tests đạt và runner thực chạy đúng package |
| S02-01–S02-04 | **Giữ Closed** | Production logic liên quan giữ nguyên; bảy ca audit a1 và full regression đạt trên hai backend |

### S02-05

Đã đọc diff trực tiếp a2 → a3 và code liên quan. [events.py:30](/Users/macbookpro/Documents/DACN_implementation/packages/s02/src/dacn_s02/events.py:30) tách helper kiểm pin; gọi cho Run config trước khi xét không dispatch. Prepared staged config phải khớp identity từ promotion của đúng StageRef; reused config phải khớp ID đã pin. Pin request vẫn được đối chiếu riêng. Không tạo Attempt giả, không buộc các command hợp lệ trước đây phải có staged config.

Repository tiếp tục kiểm bytes/purpose/media type/producer của promotion và promotion manifest; kiểm cả khi finalize và checked read. Validation chạy trong transaction nên lỗi không công bố một phần T3 hoặc làm sai heads. Trong wheel, chỉ `events.py` đổi logic; `__init__.py` và METADATA đổi version. Schema, DDL, CLI, codec, dependencies và namespace giữ nguyên.

28 regression mới được review và chạy: positive interrupted/failed trước dispatch, staged/reused/request-only, sai identity kể cả cùng bytes, request pin mâu thuẫn, thiếu promotion/bytes sai, rollback publication, checked-read và positive sau dispatch. Oracle rollback so toàn SQL dump trước/sau và kiểm lại bằng connection mới. Fixture checked-read chỉ bypass validator để dựng DB sai trong vùng kiểm thử, rồi khôi phục trước khi gọi reader; không sửa dữ liệu audit gốc.

Auditor kiểm thêm **8 DB thật từ lần audit a2**, gồm bốn DB có lỗi và bốn DB đối chứng hợp lệ. Tạo bản sao và đọc mỗi DB bằng cả C/Python: **16 bản sao, 48 lượt verify/get_command/get_record**. Tất cả lịch sử sai bị từ chối với `PERSISTENCE_FAILED`; lịch sử hợp lệ đọc được. Hash DB gốc và bản sao trước/sau đọc không đổi. Đây là bằng chứng đọc lịch sử cũ thực tế, độc lập với fixture mới của implementation. Không chạy migration hoặc repair.

[Bằng chứng đọc lịch sử](legacy-config-verification.json), [script kiểm](check_legacy_config.py).

### LAYOUT-01 và collector

Bốn wrappers gọi `main(fixed_package=...)`; tham số CLI không thể ghi đè giá trị này. Workspace entrypoint vẫn có selector đầy đủ. Tests subprocess kiểm token tách, dấu bằng, mọi tiền tố và vị trí tham số, bao gồm điều kiện không tạo output khi bị từ chối. Không gộp conftest của S01/S02 hoặc bỏ instrumentation.

Collector mới tách hai nghĩa: source = installed = wheel hiện hành; baseline được so riêng. Cùng version phải bằng payload và metadata; khác version phải chọn baseline phù hợp và ghi diff/hash đầy đủ. Đã review và chạy năm tests bổ sung của collector. Manifest thực của audit xác nhận S01 bằng a6; S02 a3 khác a2 ở `events.py`, `__init__.py`, Version trong METADATA, không thêm/xóa file package.

Không coi diff cross-version là tự động phê duyệt mọi thay đổi; nội dung diff a3 đã được reviewer đối chiếu trong audit này.

## 2. Kiểm chứng độc lập

Tạo venv mới bằng runtime pin, cài offline từ locks nguyên bản và cài trực tiếp wheel S01 a6/S02 a3 non-editable. Runtime CPython 3.13.16 có GIL, SQLite 3.53.1, macOS arm64. `pip check` đạt; không thêm production source vào PYTHONPATH, mỗi suite/backend chạy trong process riêng và cwd ngoài checkout.

| Nhóm | C | Python | Errors / skipped |
| --- | ---: | ---: | ---: |
| S01 đầy đủ | 986 passed | 986 passed | 0 / 0 |
| S02 đầy đủ | 217 passed | 217 passed | 0 / 0 |
| Audit a1 nguyên bản | 7 passed | 7 passed | 0 / 0 |
| Audit S02-05 nguyên bản | 4 passed | 4 passed | 0 / 0 |

Tooling: **344 unittest tests passed** trong một lần chạy, gồm 339 wrapper tests và 5 collector tests; không ghi là 344 mỗi backend. Smoke đạt **18 lệnh, 6 guards, 15 JSON examples, 33 record shapes và 95 guide links**. Các ca race/CAS/lock/kill/recovery hiện có chạy lại trong full suites; không thay bằng mock hoặc tuần tự hóa tests.

Source hiện tại, wheel bàn giao và package đã cài khớp toàn bộ inventory/hash: **16 file S01, 14 file S02**; metadata và provenance non-editable khớp. Auditor build lại S02 bằng bản sao nguyên bytes source/pyproject/builder giữ đúng layout, ghi caches trong thư mục audit. Payload/METADATA/WHEEL rebuild khớp wheel bàn giao. Không chạy build ghi vào checkout gốc.

Wheel được nghiệm thu:

`dacn_s02-0.1.0a3-py3-none-any.whl`

SHA-256: `0b9df6bd99e63efb25786aaf3bea58b0da7678d066fae20a2e01e90c8d97d1cf`.

[Lệnh thực chạy](audit-commands.json), [suite summary](suite-summary.json), [package manifest](packages/manifest.json), [diff a2 → a3](packages/s02-baseline.diff), [rebuild verification](rebuild-verification.json), [build provenance](build-input-provenance.json), [tooling log](tooling.log), [smoke checks](smoke/checks.json).

## 3. Bảo toàn và độ tin cậy bằng chứng

Kiểm hashes trước và sau các lượt chạy: 7.606 workspace file/symlink entries theo inventory a3, trong đó tám edits đã kê khai và 7.598 entries còn lại giữ nguyên; 10.577 file nguồn/audit bên ngoài được liệt kê giữ hash. Đối chiếu thêm 179 artifacts bàn giao a3 và 16 current files. Không có sai lệch ngoài phạm vi.

Để tránh chỉ dựa inventory do implementation lập mới, đối chiếu thêm **7.339 entries của layout đã audit trước**: chỉ khác các source/version/tooling/docs đã được giao sửa; tests cũ, schema, locks và artifacts lịch sử không bị sửa ngoài phạm vi. 164 artifacts của audit layout độc lập cũng giữ nguyên hashes. Các số đếm có runtime/env/artifacts, không phải số file code hoặc khẳng định kiểm toàn dataset/filesystem.

Hai lỗi trong lịch sử chuẩn bị a3 được giữ log và giải thích đúng: fixture Error.stage ngoài enum, và thiếu direct_url khi cài S01 qua uv lock. Không thấy sửa assertions audit hoặc nới product validator để che lỗi. Các kết quả audit hiện tại được đo mới trong môi trường riêng.

[Preservation trước](preservation-before.json), [preservation sau](preservation-after.json), [đối chiếu baseline audit cũ](prior-audit-anchor.json), [audit artifact integrity](previous-audit-integrity.json).

## 4. Phạm vi nghiệm thu và bước tiếp theo

Đối chiếu Đợt 1 tại [implementation plan:251](/Users/macbookpro/Documents/DACN_implementation/docs/S02_IMPLEMENTATION_PLAN_PROPOSAL.md:251), nghiệm thu kỹ thuật bao gồm nền tảng package/schema/typed refs; checked S01 intake và archive; repository/revision/AnalysisSet heads; staging/promotions/operational/application invariants; closure thuần; CLI local tối thiểu và tooling liên quan. Kết luận kế thừa các audit nền tảng a1/a2 và layout, cộng review bản sửa và hồi quy a3.

Chưa nghiệm thu: LLM adapter/live generation, prompt quality, đầy đủ orchestration làm rõ/consent/source-switch qua S01, toàn flow review/handoff, renderer/fidelity/readability, đánh giá ngữ nghĩa phòng khám, KB/S03, triển khai production hoặc durability mất điện/disk-full. Không suy full unit/contract suite thành xác nhận nghiệp vụ hoặc mọi lịch cạnh tranh có thể xảy ra.

Có thể chuyển sang chuẩn bị kế hoạch chi tiết Đợt 2 (bước 1–4). Theo plan, cần chốt dữ liệu/split và quyền dùng dữ liệu/ngân sách trước phần live tương ứng. Audit này không bắt đầu implementation Đợt 2 và không xác nhận những quyết định đó thay người dùng.

Auditor không sửa implementation, AGENTS hoặc báo cáo bàn giao; trạng thái hiện hành của lần audit này nằm trong report và acceptance JSON riêng. Để tái lập, copy hai script audit sang một thư mục audit mới cùng cấp rồi chạy bằng runtime đã pin; scripts tạo venv/report mới và không hỗ trợ ghi đè kết quả cũ. Không chạy lại vào thư mục bằng chứng này.
