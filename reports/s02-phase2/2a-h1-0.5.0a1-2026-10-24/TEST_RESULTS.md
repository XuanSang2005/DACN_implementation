# Kết quả mới — H1 0.5.0a1

Tất cả số dưới đây từ lượt chạy 24/10/2026 trên wheel release non-editable, cwd ngoài source, CPython3.13.16 GIL/SQLite3.53.1/macOS arm64. Không lấy số lịch sử làm kết quả mới. Commands/cwd/env/exit: [evidence index](/Users/macbookpro/.codex/.chatgpt-projects/g-p-68c38c8799f48191a101e19a975ca4f9/outputs/implementations/s02-2a-h1-0.5.0a1-2026-10-24/EVIDENCE_INDEX.md); [FINAL_RESULTS](/Users/macbookpro/.codex/.chatgpt-projects/g-p-68c38c8799f48191a101e19a975ca4f9/outputs/implementations/s02-2a-h1-0.5.0a1-2026-10-24/FINAL_RESULTS.json), [instrumentation](/Users/macbookpro/.codex/.chatgpt-projects/g-p-68c38c8799f48191a101e19a975ca4f9/outputs/implementations/s02-2a-h1-0.5.0a1-2026-10-24/instrumentation-summary.json).

| Bộ kiểm | C | Python | Evidence dưới output root |
| --- | --- | --- | --- |
| Full S02 E1 lane | 751 pass | 751 pass | `full-regression/s02-{c,python}.xml` và logs |
| H1 nằm trong full S02 | 85 pass | 85 pass | candidate19, CLI3, flow2, integrity11, limits29, safety21; không chạy rồi cộng lại |
| Full S01 | 986 pass | 986 pass | `full-regression/s01/s01-{c,python}.xml` |
| Sáu oracle P1 nguyên byte | 27 pass | 27 pass | `oracle-p1-six/checks/` — lần lượt4/5/3/6/4/5 |
| Ba oracle P2 gốc nguyên byte | 16 pass, 1 fail harness | 16 pass, 1 fail harness | `oracle-p2-original/checks/` — selection8/9, review2/2, persistence v2 6/6 |
| Oracle P2 selection v2 + boundaries | 9+8 pass | 9+8 pass | `oracle-current-boundaries/checks/audit-{1,2}-*.xml` |
| Oracle P3 a3 boundaries | 4 pass | 4 pass | `oracle-current-boundaries/checks/audit-3-*.xml` |
| P3 bundle bốn oracle + CLI controls | 10+4+4+4+14 pass | 10+4+4+4+14 pass | `full-regression/p3-oracles/checks/` |
| M1 CLI source→bốn mock + blocked | pass | pass | `m1-final-{c,python}/SUMMARY.json` và từng CLI stdout/counts |
| Differential L1 baseline a3 ↔ H1 | 413 outcomes bằng nhau | 413 outcomes bằng nhau | `differential-*.json`, `differential-comparison.json` |

Không skip/xfail trong các nhóm trên. Wrappers **339 pass**, layout **18 commands/6 guards/31 examples**, cả hai exit0. Layout được kiểm lại sau navigation/handoff mới trong `commands/final-layout.*`. Số guide links có thể đổi vì docs mới; lấy JSON cuối thay số lịch sử. Không cộng các bộ oracle có ca trùng hoặc H1 subset vào tổng test độc nhất.

## Instrumentation

Factory observation thật, không chỉ flags: full S02 C `{'c':669884,'python':0}`; full S02 Python `{'c':0,'python':669886}`. S01 C `6597/0`, Python `0/6597`. `instrumentation-summary.json` chứa **68 CLI process observations** từ H1/full lane + demo với backend được chọn có calls>0, backend kia0; worker crash/race evidence và top-level logs được giữ riêng. Counts có thể khác giữa hai backend vì code path/fault schedule, không ép bằng nhau.

Historical oracle reservation CLI (`p3-oracles/checks/audit-4-*`) chỉ gọi subprocess nên parent có0/0; không gọi đó là coverage factory ở parent. H1 CLI và handwritten P3 CLI controls có observer riêng trong child processes. Aggregator từng dừng vì giả định mọi parent đều phải có calls; bản summary02 ghi rõ các parent0/0 thay vì chỉnh tests hoặc suy coverage từ flag.

## Oracle P2 gốc còn fail đã được giải thích

`test_writer_refuses_review_fork_after_selection_loss` gọi checked `repo.heads()` **sau** xóa selection và **ngoài** pytest.raises. Checked heads từ chối sớm với `active_review_inventory`, đúng contract. [Audit P2 a2 ngày23/10, mục “Oracle lịch sử còn fail”](/Users/macbookpro/.codex/.chatgpt-projects/g-p-68c38c8799f48191a101e19a975ca4f9/outputs/audits/s02-2a-p2-0.3.0a2-2026-10-23-015238/AUDIT_REPORT.md) đã xác nhận lỗi thứ tự setup và công bố file `test_independent_p2_v2.py` riêng. Lượt H1 giữ nguyên file cũ và failure logs/JUnit, không monkeypatch production, skip, xfail hoặc sửa assertions. V2+boundaries pass cả hai backend. File persistence sai API không hậu tố v2 không được dùng.

Runner lưu `audit_sha256` trước/sau cho từng oracle trong checks/commands.json. [Oracle/helper inventory](/Users/macbookpro/.codex/.chatgpt-projects/g-p-68c38c8799f48191a101e19a975ca4f9/outputs/implementations/s02-2a-h1-0.5.0a1-2026-10-24/oracle-helper-inventory.json) kiểm lại bytes, helpers đối chiếu bundle pin. [ADAPTER](/Users/macbookpro/.codex/.chatgpt-projects/g-p-68c38c8799f48191a101e19a975ca4f9/outputs/implementations/s02-2a-h1-0.5.0a1-2026-10-24/full-regression/s02-test-inputs/ADAPTER.json) là adapter E1 đã có trước task; chỉ setup legacy có diff tường minh. H1 inputs/conftest copy byte-equal; production source không vào sys.path.

## Packaging và bảo toàn

Hai copies release/rebuild sạch: S01 20/S02 37 ZIP entries bằng nhau; S01 bằng accepted a6. Một lần driver reproduction offline mới cũng build đôi và đối chiếu bằng payload/METADATA/WHEEL với release. Source→wheel→installed pass cho cả hai packages; S01 baseline mode same_version_equal, S02 cross_version_diff đúng version. Pip check exit0. Direct URL/import paths và đầy đủ source file hashes trong [manifest](/Users/macbookpro/.codex/.chatgpt-projects/g-p-68c38c8799f48191a101e19a975ca4f9/outputs/implementations/s02-2a-h1-0.5.0a1-2026-10-24/package-evidence/manifest.json).

Differential dùng baseline L1 `0.1.0a3` trong venv riêng, corpus/script lịch sử nguyên byte: **67 accepted, 346 rejected**, so cả kết quả diagnostic/walk pointers. Factory baseline C748/Python748, candidate C763/Python763; backend không chọn0. Canonical schema resources/registry, DB2 DDL/repository/shared validators, S01, locks và historical evidence được kiểm byte inventory riêng, không chỉ suy từ tests pass.

## Giới hạn

Fault injection là process kill/commit hooks/SQLite journal thật trên máy local, không hardware power loss hoặc disk-full thật. Deadline cooperative30s, không hard timeout hay benchmark. Synthetic mocks không chứng minh phân tích đủ rõ/đúng nghiệp vụ hoặc xác nhận người dùng. Chưa có audit implementation H1 độc lập; H2/H3/2B/2C/LLM/renderer/live ngoài phạm vi.
