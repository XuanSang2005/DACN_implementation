# Audit lại 2A-P2 — dacn-s02 0.3.0a2

Ngày kết luận: 2026-10-23T02:13:44.401223+07:00. **Nghiệm thu kỹ thuật P2 trong phạm vi local trên wheel 0.3.0a2; đóng S02-2A-P2-01 và S02-2A-P2-02.** Không phát hiện finding implementation mới trong lượt kiểm này. Một oracle lịch sử vẫn fail do thứ tự setup của chính oracle; không báo sai thành toàn bộ oracle nguyên bản pass.

## Đối tượng và giới hạn kết luận

Repo thực: `/Users/macbookpro/Documents/DACN_implementation`. Wheel duy nhất: `/Users/macbookpro/Documents/DACN_implementation/reports/s02-phase2/2a-p2-fixes-0.3.0a2-2026-10-23/release/dacn_s02-0.3.0a2-py3-none-any.whl`. SHA-256: `608b5734af7bb88aa3b06b4c113b52749cf131229ad36e2b9a69dcc11bd09de2`.

Đã đối chiếu AGENTS hiện hành, bàn giao a2, phản hồi findings, ORACLE_EXCEPTION, diff source/wheel và bằng chứng thực chạy mới. Snapshot ngày 22/10 chỉ là bối cảnh lịch sử. Phạm vi nghiệm thu gồm DB2, registry/owner-profile persistence, fresh activation, E1 A1/A2 ở tầng lưu trữ, DB1 checked read-only, invariants transaction/identity/unique/CAS, lookup/receipt guards và manifest reader theo schema/framing/mutable_baseline đã chốt.

Đây là nghiệm thu implementation cấp thấp/local, không phải chỉ audit thiết kế. Không phải nghiệm thu toàn bộ S02, chất lượng nghiệp vụ, copy/cutover/migration P3, orchestration 2B/2C, LLM, renderer hoặc live. Kết luận này không cấp quyền triển khai P3; prompt đề xuất bước tiếp theo chỉ có hiệu lực khi người dùng giao riêng.

## Đóng findings

| Finding | Mức độ gốc | Vị trí a2 | Kết luận và cách kiểm |
| --- | --- | --- | --- |
| S02-2A-P2-01 | High | repository.py:399–428, `_check_review_selection` | CLOSED cho DB2. Đối soát đủ inventory review/bundle, duy nhất một root, không fork, parent cùng lịch sử, toàn bộ graph nối được và selection đúng tip. SQL chỉ xóa/rewind `active_reviews` trên fresh DB2 và mixed L1→E1 bị từ chối ở checked reads/writes; graph lịch sử không bị ghi lại. |
| S02-2A-P2-02 | Medium | validation.py:231–235 | CLOSED cho E1. Review revoked không có predecessor bị từ chối; predecessor phải khác chính nó và cùng bundle. Controls root request_changes và successor revoked hợp lệ vẫn đạt. Gate đặt dưới owner E1, không thay semantics L1 đã pin. |

Cách tái hiện đầy đủ trước/sau nằm trong `run_independent.py`, `run_audit.py`, các `*.command.json` và JUnit/logs tương ứng. Trên wheel a1 cài mới, ba oracle P2 nguyên bản vẫn tái hiện 7 failures/17 tests/backend (6 selection, 1 revoked); trên a2 chỉ còn đúng lỗi harness bên dưới. Bộ selection v2 + boundary mới tái hiện 11 failures/17 tests/backend ở a1 và đạt 17/17 ở a2. Các controls pass ở a1 không bị gọi nhầm là lỗi đã sửa.

## Oracle lịch sử còn fail: lỗi setup của auditor

`test_writer_refuses_review_fork_after_selection_loss` trong file lịch sử gọi `repo.heads()` sau khi xóa selection, nhưng đặt lời gọi đó bên ngoài `pytest.raises`. A2 checked heads từ chối sớm đúng yêu cầu với `active_review_inventory`, vì vậy chưa tới guard dự kiến. Đây là lỗi thứ tự setup của oracle do auditor viết trước đó; phản chứng Astra bàn giao là hợp lệ. Không yêu cầu làm yếu checked heads để oracle cũ pass.

Giữ nguyên file/logs/hash lịch sử. File mới `test_independent_p2_v2.py` chỉ ghim heads và tạo operation trước mutation; assertions không đổi. Diff/hashes ở `oracle-v2-provenance.json`. Oracle v2 đạt 9/9/backend. Tám ca bổ sung gọi riêng heads/verify/lookup/store_info/freshness/prepare/append_event/finalize sau corruption, kiểm bytes không đổi; postcheck sau insert bị rewind phải rollback; valid fresh/mixed chains vẫn mở lại được, không sắp latest theo timestamp. Bộ bổ sung đạt 8/8/backend. Mixed mất selection đã bị manifest gate chặn ở a1 là control, không tính thành regression mới.

## Kết quả thực chạy của lượt này

Số lượng dưới đây là **mỗi backend**, đều chạy mới trong môi trường wheel non-editable ngoài checkout; không dùng số tests lịch sử thay cho kết quả mới.

| Lane | C | Python | Bằng chứng |
| --- | --- | --- | --- |
| Full S02 a2 | 488 pass | 488 pass | p2-regression/checks |
| S01 a6 | 986 pass | 986 pass | s01-regression |
| Sáu oracle P1 nguyên byte | 27 pass | 27 pass | p1-oracles/checks |
| Ba oracle P2 nguyên bản trên a2 | 16 pass, 1 fail setup đã giải thích | 16 pass, 1 fail setup đã giải thích | original-p2-oracles/checks |
| Selection v2 + boundaries bổ sung trên a2 | 17 pass | 17 pass | independent-a2/checks |
| Ba oracle P2 nguyên bản trên a1 | 10 pass, 7 fail | 10 pass, 7 fail | original-a1-oracles/checks |
| Selection v2 + boundaries bổ sung trên a1 | 6 pass, 11 fail | 6 pass, 11 fail | independent-a1/checks |

Không skip; failure âm trên a1 và failure setup nguyên bản trên a2 được ghi tách biệt. Trong ba oracle P2 nguyên bản: selection 8/9, review contract 2/2, persistence/framing 6/6 trên a2. `execution-summary.json` tổng hợp từ commands/JUnit. Không cộng các bộ có ca trùng nhau thành số test độc nhất.

Full suite chạy lại 5 races và 4 process terminations/backend, có IPC/PID/timeline và DB hash trong `race-fault-observations.json`. Đây là fault tests trên kho synthetic, không chứng minh mất điện phần cứng. Runner có encoder instrumentation để kiểm C/Python thực sự được dùng, tắt plugin autoload, bỏ PYTHONPATH/PYTEST_ADDOPTS/PYTEST_PLUGINS. Môi trường CPython 3.13.16 có GIL, SQLite 3.53.1, macOS arm64.

## Đối chiếu code, semantics và đóng gói

- Diff payload a1→a2 chỉ đổi version, repository review selection và nhánh E1 review validation; không thêm/bớt payload. Schemas L1/E1/registry, DDL1/DDL2, manifest reader, framing và A1/A2 modules giữ nguyên. Có bằng chứng riêng trong `wheel-diff-independent.json`.
- L1 schema nguyên byte so Đợt 1 a3. Legacy verifier AST giữ nguyên; toàn module validation AST bằng a1 sau khi bỏ đúng nhánh E1 mới. Differential mới trên phase1 a3, P1 a3 và candidate a2: 413/413 outcomes khớp ở C/Python, 67 accepted/346 rejected, không unexpected exception. Hai graph phản ví dụ P1-04 tiếp tục bị từ chối đúng invariant. Corpus hữu hạn không phải chứng minh mọi đầu vào.
- Sáu oracle P1 đạt lại cho owner-profile dispatch, A1 source archive/observed context, A2 DIRECT/CARRY/REPLACEMENT và graph dependencies. Oracle persistence bổ sung thực ghi A1 cùng/khác snapshot, kiểm missing context rollback; mixed DIRECT→CARRY→REPLACEMENT và review bindings; framing độc lập đối chiếu SQLite BINARY order. Không coi metadata review synthetic là người thật đồng ý.
- Source–wheel–installed khớp 24 payload S02 và 16 S01; collector kiểm package identity/METADATA/WHEEL/direct URL. `pip check` đạt. Rebuild sạch từ copy source khớp 26 entries payload + METADATA/WHEEL. ZIP SHA rebuild khác release do đóng gói; không tuyên bố hai ZIP nguyên byte bằng nhau.
- Adapter P2 khai báo trong `ADAPTER.json`, gồm setup E1 fields, receipt/config pins và helpers cho mixed store; các oracle ngoài giữ nguyên assertions/bytes, trừ v2 mới đã công bố riêng. Baseline helpers được lấy từ snapshot P1 trước P2, không lấy nhầm bản P2 đã sửa. Không tuyên bố toàn bộ test inputs legacy nguyên byte chạy dưới writer E1.

## Bảo toàn và điều chưa được chứng minh

Đầu/cuối đối chiếu khớp 1.212 artifacts bàn giao a2, 10 release inputs, 3.624 protected files, 6 file oracle P1 và 865 files audit a1. Git HEAD/status trước/sau bằng nhau. Repo có thay đổi sẵn từ implementation; kết luận ghim wheel và file hashes, không suy HEAD là toàn bộ nội dung đã kiểm. Không sửa implementation, locks, schema, S01, dataset, DB operational hoặc evidence lịch sử. Tất cả ghi mới nằm trong thư mục audit/temp và dùng kho synthetic.

L1 vẫn giữ hành vi root revoked từng được tái hiện ở P1; gate sửa này thuộc E1. DB1 đọc được theo compatibility không mặc nhiên đủ điều kiện copy sang DB2: P3 phải chạy kiểm eligibility và toàn bộ invariants DB2, không tự repair lịch sử. Chưa có bằng chứng migration writer/copy/receipt durability/cutover/activation migrated; manifest reader và mixed fixtures không thay thế bằng chứng đó. Chưa kiểm live, LLM, renderer, mất điện thật, disk-full thật, hiệu năng lớn hoặc xác thực danh tính reviewer.

Baseline full P1 383 và Đợt 1 217 từng chạy ở audit a1 được giữ là kết quả lịch sử; lượt này không gọi chúng là tests mới. Những gì mới với baseline là differential 413 và replay a1 nêu trên.

## Bước tiếp theo

Có thể giao riêng **2A-P3 migration local** theo proposal đã chốt, chỉ trên kho synthetic/test. Phải bảo toàn L1, nguồn read-only từ connection đầu, receipt bền vững với ba IDs, copy inactive và activation explicit tách biệt, reconcile lost ACK/crash và eligibility. Chưa tự triển khai P3 trong audit này. Xem prompt ngắn tại `NEXT_PROMPT.md`.
