# Audit độc lập DACN S02 2A-P1 — bản sửa 0.2.0a3

Ngày 22/10/2026, Asia/Ho_Chi_Minh. Đối tượng là wheel duy nhất trong bàn giao `reports/s02-phase2/2a-p1-fix04-0.2.0a3-2026-10-22/START_HERE.md`: `dacn_s02-0.2.0a3-py3-none-any.whl`, SHA-256 `678b6fdd6c54c221b162b60d519e8aaf92e9777fe5ef60a90fdf4f7f194b9117`.

## Kết luận

**Đóng S02-2A-P1-04. Nghiệm thu kỹ thuật 2A-P1 trên bản 0.2.0a3 trong phạm vi profiles và validators cấp thấp, local.** Findings 01/02/03 tiếp tục đóng sau khi chạy lại nguyên các oracle. Không phát hiện finding mới trong phạm vi review và kiểm thử của lượt này.

E1 được nghiệm thu ở API kiểm graph trong bộ nhớ; repository/CLI vẫn là L1/DB1. Kết luận không nghiệm thu toàn bộ S02, nghiệp vụ, E1 persistence, DB2/P2/P3, migration, 2C hoặc live và không cấp quyền triển khai các phần ấy. Baseline S01 a6 và S02 **0.1.0a3** Đợt 1 giữ nguyên; không nhầm baseline đó với package P1 **0.2.0a3** hiện tại.

Biên bản máy đọc: [S02_2A_P1_ACCEPTANCE.json](S02_2A_P1_ACCEPTANCE.json), [AUDIT_RESULT.json](AUDIT_RESULT.json).

| Finding | Mức khi mở | Kết luận |
| --- | --- | --- |
| S02-2A-P1-01 — TaskAttestation so nhầm hold | P2 | Tiếp tục Closed; oracle thiếu coverage và narrow-task hợp lệ đều pass |
| S02-2A-P1-02 — target mở rộng footprint vẫn complete | P2 | Tiếp tục Closed; target gate và controls được kiểm lại |
| S02-2A-P1-03 — command/reserved Run identity | P2 | Tiếp tục Closed; prepared-operation checks và DB1 control pass |
| S02-2A-P1-04 — thiếu liên kết Part–nguồn trong structural reuse | P2 | **Closed trên 0.2.0a3**; cả CARRY và REPLACEMENT được sửa |

## Căn cứ và review code

Đã đọc AGENTS hiện hành, START_HERE, FINDING_RESPONSE, diff, REPRODUCE, tài liệu API P1; đối chiếu actual repo và các biên bản a1/a2. Áp dụng phạm vi P1 đã giao và bảng §7 của storage proposal draft.2, cùng A1/A2 addendum §3.2/§3.6. Các yêu cầu storage/migration thuộc P2/P3 được tách khỏi điều kiện nghiệm thu P1; tests DB1 không thay bằng chứng E1 persistence.

Finding 04 trước đây xuất phát từ việc tách Part khỏi row chứa nó: swap nguồn giữa hai rows giữ nguyên Part JSON và tập source refs nên bị xem như unchanged. Bản sửa ở [resolution.py:139](/Users/macbookpro/Documents/DACN_implementation/packages/s02/src/dacn_s02/resolution.py:139) thêm comparison values riêng E1, gồm Part payload và mapping context: ID row, source_ref, assessment, issue_ids và tập Part IDs. Nó được dùng trong [scope proof](/Users/macbookpro/Documents/DACN_implementation/packages/s02/src/dacn_s02/resolution.py:174), tập changed đưa vào reverse impact và [target footprint](/Users/macbookpro/Documents/DACN_implementation/packages/s02/src/dacn_s02/resolution.py:351).

Phép so chuẩn hóa các danh sách ID dạng tập và thứ tự rows/Parts; không sắp xếp criterion trong source hoặc workflow sequence. Input không bị mutate. Nhãn pair “unchanged” vẫn kiểm payload; structural release cần thêm ngữ cảnh mapping không đổi. Do đó human-review/hold có thể xử lý payload còn nguyên nhưng liên kết đổi, trong khi không được release chỉ bằng structural proof. `validation.index_model`, closure và mọi helper legacy giữ nguyên byte.

Đối chiếu wheel a2→a3 độc lập xác nhận chỉ hai package payload đổi: `resolution.py` và version trong `__init__.py`; metadata version đổi tương ứng. Không thêm/bớt payload, không đổi schema/registry/DB1. Thay đổi phù hợp sửa invariant E1 đã chốt, không mở rộng contract hoặc quyền persistence.

## Bằng chứng đóng finding 04

1. **Đối chứng trước sửa chạy mới:** tạo venv a2 từ locks, chạy nguyên hai file audit a2: 8 pass/2 fail trên mỗi backend, đúng hai assertions DID NOT RAISE. Phát lại hai graph gốc bằng script không import helpers: a2 accepted trên C và Python.
2. **Sau sửa:** năm file audit nguyên bản đạt 22/22 mỗi backend. Hai graph gốc bị từ chối bởi S02Error đúng invariant: `carry_structural_proof` và `replacement_structural_continuation`. Exit 1 của các replay này là kết quả từ chối mong đợi, không được tính như harness crash. Adapter chỉ chọn/instrument encoder và chạy nguyên script, không sửa graph.
3. **Controls cũ:** unchanged, review mới, undetermined/incomplete và task split vẫn pass. Các review chỉ là bindings synthetic để kiểm logic.
4. **Năm ca whole-graph độc lập mới:** dựng ba requirements và một vùng actions/mappings độc lập. Đổi mapping trong phần mở rộng của target, ngoài hold replacement, phải bị chặn đúng bởi `replacement_target_footprint`. Cùng thay đổi nằm ngoài cả target thì structural continuation vẫn hợp lệ. Unchanged, review mới và hold đều pass. Điều này kiểm cả target gate độc lập lẫn việc không chặn mọi Model mới. Xác nhận graph đầu vào không bị mutate.

File mới: [test_independent_a3.py](test_independent_a3.py). Logs/commands/instrumentation: `oracles/`, `extra-probes/`, `baseline-a2-oracles/`, `replay-summary.json` và `replay-*.log`. Hai graph và năm files audit cũ được dùng nguyên byte, ghim hashes; không thay expectations, skip/xfail hoặc sửa helpers để đạt kết quả.

39 regression mới của producer được review và thực chạy trong full suite: requirement/criterion source riêng biệt, swap/reparent, row identity/assessment, reorder, stale/fresh review và hold, closure/reverse impact. Hai ca helper-level target footprint và một ca scope/impact được ghi nhận đúng là unit tests, không trình bày chúng như whole-graph evidence. Năm ca bổ sung của auditor ở trên chạy qua whole-graph API.

## Kết quả auditor trực tiếp chạy trong lượt này

| Kiểm tra | C extension | Python fallback |
| --- | --- | --- |
| Full S01 | 986 pass | 986 pass |
| Full S02 P1 a3 | 383 pass | 383 pass |
| Năm file audit nguyên bản | 22 pass | 22 pass |
| Năm ca độc lập mới | 5 pass | 5 pass |
| Hai file audit a2 trên wheel a2 đối chứng | 8 pass / 2 fail đúng lỗi cũ | 8 pass / 2 fail đúng lỗi cũ |
| Hai graph gốc trên release a3 | 2 reject đúng invariant | 2 reject đúng invariant |
| Differential legacy 0.1.0a3/P1 0.2.0a3 | 413/413 outcomes khớp | 413/413 outcomes khớp |

Các suites release không fail/error/skip; tổng audit riêng **27 pass/backend**. Full S02 gồm 344 tests giữ nguyên và 39 regression producer mới; không gọi 39 ca ấy là oracle độc lập của auditor. Differential có 67 accepted/346 rejected, không unexpected exception; cùng corpus và diagnostics/walk paths, cả bốn lanes đã chạy mới. Đây là corpus hữu hạn, không chứng minh equivalence mọi graph hay chất lượng nghiệp vụ.

Môi trường release, đối chứng a2 và legacy a3 đều tạo mới từ locks offline. CPython 3.13.16 có GIL, SQLite 3.53.1, macOS arm64; production import từ non-editable wheel trong site-packages, cwd ngoài source. Mỗi package/backend là process riêng, có instrumentation encoder thực. Test helpers chỉ phục vụ dựng synthetic fixtures. Xem [execution-summary.json](execution-summary.json) và `regression/observations.json`.

Source–wheel–installed đạt S01 16 payload, S02 20 payload, kèm METADATA/WHEEL và direct wheel identity. Dependency check đạt. Rebuild từ copy sạch trong audit workspace bằng dependencies đã pin khớp 22 entries (20 payload + METADATA/WHEEL) với release; ZIP hash rebuild riêng, không ép ZIP timestamps bằng release. Xem [package manifest](package-evidence/manifest.json) và [rebuild comparison](rebuild-comparison.json). Materializer chạy kiểm mặc định và khớp resources.

## Bảo toàn và niêm phong

- 584 file handoff, 86 release inputs, 1.739 protected files và 103 oracle/helper inputs khớp actual files trước và sau audit.
- Manifest audit a1 có 140 file và a2 có 212 file tiếp tục khớp. Năm bản sao file trước sửa khớp before inventory; actual files sau sửa khớp release. Git HEAD/status trước và sau audit không đổi.
- L1 schema nguyên byte baseline S02 0.1.0a3; E1 schema/registry nguyên byte các bản P1 trước. S01, locks, storage/repository/service/CLI và helpers legacy thuộc inventory giữ nguyên.
- Không chỉnh implementation, nguồn/dataset, artifacts bàn giao hoặc evidence lịch sử. Mọi output mới nằm trong thư mục audit này; DB thử nghiệm đều synthetic/tạm. Inventory có exclusions; không suy rằng toàn filesystem đã được kiểm.

Xem `integrity-before.json`, `integrity-after.json`, `before-copies-verification.json`, `wheel-diff-independent.json` và `ARTIFACT_HASHES.json`. Harness audit ban đầu dùng tên `audit-inputs.json` của layout a2; a3 đặt bảng ấy trong `oracle-preservation.json`. Đã sửa đường đọc ở harness trước khi chạy tests; không phải lỗi package hoặc thay oracle.

## Phạm vi nghiệm thu và giới hạn

Nghiệm thu **implementation P1** gồm explicit owner profiles/resources/rules dispatch; giữ L1 bytes và semantics trong các checks đã thực hiện; A1 archive/snapshot/source checks cấp thấp; A2 DIRECT/CARRY/REPLACEMENT, typed history/current refs, coverage/task/review gates và whole-graph identity checks; package/wheel local. Những phần không đổi được kế thừa review a1/a2 và kiểm lại qua full regression/oracles, không tuyên bố mỗi dòng được review lại từ đầu.

Đây không phải xác nhận requirement→responsibility đúng nghiệp vụ, không chứng minh model không thiếu dependencies/permissions, không xác thực người thật review bằng metadata/digest, không phải quality evaluation LLM. Tests/mock/synthetic archive là bằng chứng thực thi code, không phải run nghiệp vụ thật.

E1 vẫn chỉ ở bộ nhớ; chưa nghiệm thu writer, transaction CAS/claims E1, mixed-store FK, DB2, migration/read-only source/cutover/activation/recovery, orchestration 2C, live LLM, renderer, S03 hoặc toàn S02. Không gọi LLM, mở operational store hay chạy migration trong lượt này. Mọi đợt tiếp theo cần người dùng giao phạm vi riêng; kết luận audit này không tự cấp quyền ấy.

Tái lập bằng các argv/cwd trong `oracles/commands.json`, `extra-probes/commands.json`, `regression/commands.json` và các `*.command.json`; chọn report-dir mới. Không chạy lại scripts tạo output tại thư mục audit đã niêm phong.
