# Kết quả kiểm H2-A mới — 25/10/2026

Final wheel `0.6.0a1` được cài non-editable trong venv mới ngoài checkout, cwd ngoài source; CPython 3.13.16 GIL, SQLite 3.53.1, macOS arm64. S01 a6/dependencies từ locks/offline bundle nguyên byte. Không dùng số lịch sử làm kết quả mới. [Commands](/Users/macbookpro/.codex/.chatgpt-projects/g-p-68c38c8799f48191a101e19a975ca4f9/outputs/implementations/s02-2a-h2-a-0.6.0a1-2026-10-25/commands), [environment/build commands](/Users/macbookpro/.codex/.chatgpt-projects/g-p-68c38c8799f48191a101e19a975ca4f9/outputs/implementations/s02-2a-h2-a-0.6.0a1-2026-10-25/final-environment), [JUnit/tóm tắt máy đọc](/Users/macbookpro/.codex/.chatgpt-projects/g-p-68c38c8799f48191a101e19a975ca4f9/outputs/implementations/s02-2a-h2-a-0.6.0a1-2026-10-25/final/TEST_SUMMARY.json).

## Full regression từ final wheel

| Suite/backend | Kết quả thực chạy | Trong đó H2-A | Instrumentation parent process |
| --- | --- | --- | --- |
| s02-c | 878 pass; 0 fail/error/skip | 109 | S02_ENCODERS selected=c calls={'c': 745798, 'python': 0} |
| s02-python | 878 pass; 0 fail/error/skip | 109 | S02_ENCODERS selected=python calls={'c': 0, 'python': 745802} |
| s01-c | 986 pass; 0 fail/error/skip | 0 | Observed real encoder factory calls: {'c': 6597, 'python': 0}; selected=c |
| s01-python | 986 pass; 0 fail/error/skip | 0 | Observed real encoder factory calls: {'c': 0, 'python': 6597}; selected=python |

[Full verifier](/Users/macbookpro/.codex/.chatgpt-projects/g-p-68c38c8799f48191a101e19a975ca4f9/outputs/implementations/s02-2a-h2-a-0.6.0a1-2026-10-25/final/full-checks) exit 0; wrapper/layout/schema materializer và P3 oracle/CLI controls đều đạt. Các process/fault tests nền tảng dùng kho synthetic riêng, instrumentation con trong raw logs. Conftest/assertions/lane E1 adapter giữ nguyên; không đưa production source vào PYTHONPATH. S02 tổng 878/backend gồm 109 tests mới H2-A và 769 regression hiện có; S01 số thực trong bảng.

## Oracle và differential không sửa assertions

- Sáu file P1 nguyên bản: lần lượt **4, 5, 3, 6, 4, 5 pass/backend**, tổng 27/backend; [JUnit/commands/raw hash](/Users/macbookpro/.codex/.chatgpt-projects/g-p-68c38c8799f48191a101e19a975ca4f9/outputs/implementations/s02-2a-h2-a-0.6.0a1-2026-10-25/final/oracle-p1-six/checks). Không skip/xfail.
- P2 `test_independent_p2_v2.py` **9**, `test_independent_a2_boundaries.py` **8**, P3 `test_independent_a3_boundaries.py` **4 pass/backend**; [evidence](/Users/macbookpro/.codex/.chatgpt-projects/g-p-68c38c8799f48191a101e19a975ca4f9/outputs/implementations/s02-2a-h2-a-0.6.0a1-2026-10-25/final/oracle-current-boundaries/checks).
- H1 corrected official `test_independent_h1_v4.py`: **10 pass/backend**, SHA `6695b6a3ce9de8da6d3a8846c687b84e697253956f01bc499486639465d76897`; [evidence](/Users/macbookpro/.codex/.chatgpt-projects/g-p-68c38c8799f48191a101e19a975ca4f9/outputs/implementations/s02-2a-h2-a-0.6.0a1-2026-10-25/final/oracle-h1-v4/checks). V3 có erratum harness lịch sử, không được chỉnh hoặc dùng thay v4 trong lượt này; không chạy lại v3.
- Full verifier chạy bốn oracle P3 và CLI controls: **10 + 4 + 4 + 4 + 14 = 36 pass/backend**. Gate từ chối sớm có parent encoder count 0 là đúng đường không effects; instrumentation process con/CLI được giữ theo runner, không suy parent 0 thành đã chạy codec.
- Differential L1 nguyên script + fixture lịch sử: **413 cases, 67 accepted**, toàn outcomes/diagnostics bằng nhau giữa baseline `0.1.0a3` và candidate `0.6.0a1`, C và Python. Encoder: baseline C/P 748/748, candidate C/P 763/763 (backend đối diện 0). [So sánh](/Users/macbookpro/.codex/.chatgpt-projects/g-p-68c38c8799f48191a101e19a975ca4f9/outputs/implementations/s02-2a-h2-a-0.6.0a1-2026-10-25/final/differential-l1/COMPARISON.json).
- [Oracle/helper hashes](/Users/macbookpro/.codex/.chatgpt-projects/g-p-68c38c8799f48191a101e19a975ca4f9/outputs/implementations/s02-2a-h2-a-0.6.0a1-2026-10-25/final/oracle-inputs.json); runner tự rehash oracle trước/sau; [ADAPTER](/Users/macbookpro/.codex/.chatgpt-projects/g-p-68c38c8799f48191a101e19a975ca4f9/outputs/implementations/s02-2a-h2-a-0.6.0a1-2026-10-25/final/oracle-h1-v4/ADAPTER.json) chỉ điều chỉnh test-lane lookup/API hiện hành, không monkeypatch production. Harness P2 cũ dùng sai API không phải finding implementation và không chạy ở lượt này.

## Tests H2-A và lịch sử phát triển

109 cases/backend trong full suite. Focused development cuối cũng 109/backend, 0 skip/xfail; input wheel payload bằng final. Expected scopes viết bằng sets/conditions trong tests, không gọi chính closure để sinh oracle. Controls bao phủ full criteria/NFR/constraints, graph rỗng/lớn, unknown-global/source holds, mọi action của mọi Part, row–source swap/reparent/membership, shared context/explicit blocker, Support/branch/cycles/removals, stale pins/grants, construction vs business/gap, union bridge/append rights và bounded counts/deadline.

[Development iteration 01](/Users/macbookpro/.codex/.chatgpt-projects/g-p-68c38c8799f48191a101e19a975ca4f9/outputs/implementations/s02-2a-h2-a-0.6.0a1-2026-10-25/dev-iteration01) giữ **38 fail + 45 pass/backend**: private metadata check nhầm exact-codec Decimal integral với Python int. Đã sửa parser metadata riêng H2, không đổi codec/source values; iteration 02–09 lần lượt **83, 86, 98, 99, 104, 106, 108, 109 pass/backend**. Không xóa failure logs; driver dev thu cả hai backend nên outer status không thay child exit/JUnit.

## Đóng gói và bảo toàn

Hai clean copied-source build S02 bằng cả **42 ZIP entries**, gồm METADATA/WHEEL/RECORD; S01 rebuild 20 entries bằng accepted a6. [Build comparisons](/Users/macbookpro/.codex/.chatgpt-projects/g-p-68c38c8799f48191a101e19a975ca4f9/outputs/implementations/s02-2a-h2-a-0.6.0a1-2026-10-25/final-environment/environment.json). [Source–wheel–installed/METADATA/WHEEL/direct URL](/Users/macbookpro/.codex/.chatgpt-projects/g-p-68c38c8799f48191a101e19a975ca4f9/outputs/implementations/s02-2a-h2-a-0.6.0a1-2026-10-25/final/package-evidence/manifest.json) đạt, final pip check exit 0. [Delta wheel với H1 a2](/Users/macbookpro/.codex/.chatgpt-projects/g-p-68c38c8799f48191a101e19a975ca4f9/outputs/implementations/s02-2a-h2-a-0.6.0a1-2026-10-25/final/wheel-baseline-delta.json): chỉ thêm năm module H2, đổi `__init__` version/mô tả; old resources/modules không đổi. ZIP rebuild có thể khác SHA do timestamps, không ép bằng ZIP lịch sử.

Timeout harness: lượt kiểm final **không phát sinh TimeoutExpired hoặc failure timeout**; không tăng timeout/sửa assertion/skip để đạt. Thời gian suite trong JUnit là thời gian thực; cooperative budget H2 30 giây không phải timeout hard của harness. Nếu tái lập gặp timeout, giữ lần thất bại riêng, phân biệt retry focused với full pass.

Chưa chứng minh H2 pipeline, provider file I/O/restart, receipt/seal/CAS/crash/revalidation publisher hoặc chất lượng phân tích nghiệp vụ. H1 safety pass chỉ bảo toàn H1. **H2-A đã triển khai pure policy, chờ audit độc lập**.
