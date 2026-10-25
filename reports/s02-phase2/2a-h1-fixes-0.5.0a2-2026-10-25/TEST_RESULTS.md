# Kết quả mới trên wheel 0.5.0a2

Đã sửa, chờ audit lại. Thực chạy mới 24–25/10/2026, wheel non-editable, cwd ngoài source, runtime CPython3.13.16 GIL/SQLite3.53.1/macOS arm64. [Commands/cwd/env/exit](/Users/macbookpro/.codex/.chatgpt-projects/g-p-68c38c8799f48191a101e19a975ca4f9/outputs/implementations/s02-2a-h1-fixes-0.5.0a2-2026-10-24/commands/), [FINAL_RESULTS](/Users/macbookpro/.codex/.chatgpt-projects/g-p-68c38c8799f48191a101e19a975ca4f9/outputs/implementations/s02-2a-h1-fixes-0.5.0a2-2026-10-24/FINAL_RESULTS.json), [instrumentation](/Users/macbookpro/.codex/.chatgpt-projects/g-p-68c38c8799f48191a101e19a975ca4f9/outputs/implementations/s02-2a-h1-fixes-0.5.0a2-2026-10-24/instrumentation-summary.json).

| Bộ kiểm | C | Python | Evidence dưới output root |
| --- | --- | --- | --- |
| Full S02 | 769 pass | 769 pass | full-regression/s02-{c,python}.xml và logs |
| H1 subset trong full | 103 pass, gồm18 mới | 103 pass, gồm18 mới | Cùng JUnit; không cộng lại như lần chạy độc lập |
| Full S01 | 986 pass | 986 pass | full-regression/s01/ |
| V3 nguyên byte trên baseline a1 | 4 pass, 6 fail | 4 pass, 6 fail | baseline-oracle-v3/checks/; 5 production failures + 1 logger failure |
| V3 nguyên byte trên fixed a2 | 9 pass, 1 logger fail | 9 pass, 1 logger fail | fixed-oracle-v3/checks/; không skip/xfail |
| Regression ref-limit xuyên suốt trên a1 | 50.000 pass; 50.001 fail status completed | Tương tự | baseline-ref-integration-{c,python}.xml, 2 cases selected |
| Ref-limit xuyên suốt trên a2 | 50.000 completed; 50.001 rejected, raw/head/reopen đúng | Tương tự | Nằm trong18 regressions mới của full, có H1_REF_BOUNDARY evidence |
| Sáu P1 nguyên byte | 27 pass | 27 pass | oracle-p1-six/checks/ |
| P2 selection v2 + boundaries | 17 pass | 17 pass | oracle-current-boundaries/checks/audit-{1,2}-*.xml |
| P3 a3 boundaries | 4 pass | 4 pass | oracle-current-boundaries/checks/audit-3-*.xml |
| Bốn P3 bundle oracle + CLI controls | 22 + 14 pass | 22 + 14 pass | full-regression/p3-oracles/checks/ |
| Ba P2 gốc | 16 pass, 1 known setup fail | Tương tự | oracle-p2-original/checks/ |
| Differential L1 a3 → a2 | 413 outcomes bằng nhau | 413 outcomes bằng nhau | differential-*.json, differential-comparison.json |

Full suites không failure/error/skip. **Timeout harness từ audit a1 không tái hiện**: nguyên case reservation_durable-cli, nguyên30s pass cả hai backend trong full mới. Không focused retry, không sửa worker/timeouts; vẫn giữ failure lịch sử và chưa chứng minh root cause timing. Logger v3 và P2 setup failure được báo tách tại [HARNESS_NOTES](HARNESS_NOTES.md), không tính thành implementation pass.

Focused development suite chạy trước khi bổ sung2 ca xuyên suốt: **16 pass/backend**, logs giữ riêng. Full cuối chạy cả18 ca; không dùng số focused thay full hoặc cộng lại coverage. Baseline2-cases có16 deselected vì targeted -k, không phải skip/xfail; original v3 chạy đủ10 cases mỗi backend.

## Regression mới và oracle

18 cases: mixed ref occurrences5, singular finding_handle boundary2, result/current-Issue guard1, xuyên suốt raw/head/reopen boundary2, local/base/pending × Model-change/AS-only6, fully-assigned/nonblocking control1, hai gaps chung mapping task1. Kiểm immutable old Records/current Issue keys/supersedes, giữ Model khi AS-only, blocked/next_step=null và không prepare4. Existing85 H1 tiếp tục kiểm CLI thực, receipt/T0/seal/T3/races/crash/lost ACK/stale/limits/hot journal.

V3 giữ hash **9b7d8379a6551e1bc4c868cf46e98b1de47940010346b83ce7a9fccb766e3f9e**; checks/commands.json lưu hash trước/sau. Không sửa assertions, helpers, skip/xfail hoặc monkeypatch production. E1 adapter đã có ghi input/output hashes và setup diff trong [ADAPTER](/Users/macbookpro/.codex/.chatgpt-projects/g-p-68c38c8799f48191a101e19a975ca4f9/outputs/implementations/s02-2a-h1-fixes-0.5.0a2-2026-10-24/full-regression/s02-test-inputs/ADAPTER.json); new tests/conftest byte-equal trong copied lane. Production không import test helpers.

## Instrumentation

Full S02: C **740636 calls, Python0**; Python **740640 calls, C0**. Full S01: C6597/Python0 và Python6597/C0. [Instrumentation summary](/Users/macbookpro/.codex/.chatgpt-projects/g-p-68c38c8799f48191a101e19a975ca4f9/outputs/implementations/s02-2a-h1-fixes-0.5.0a2-2026-10-24/instrumentation-summary.json) có **42 top-level observations** và **34 CLI child encoder observations**; worker kill/race hooks lưu riêng trong full-regression/process-artifacts. Historical reservation-CLI-only oracle có parent0/0, không gọi đó là coverage encoder ở parent; H1 CLI/P3 controls có observer trong child.

Wrappers **339 pass**; layout **18 commands, 6 guards, 31 examples**, exit0. Final layout sau docs mới có commands/logs ở final-layout/; không thay các kết quả application tests bằng layout smoke.

## Packaging và compatibility

Ba clean source builds: initial release và candidate-environment/build + rebuild; S01 toàn20 ZIP entries bằng accepted a6, S02 toàn37 entries bằng nhau giữa builds (METADATA/WHEEL/RECORD). ZIP timestamps khác được phép. [Final wheel selection](/Users/macbookpro/.codex/.chatgpt-projects/g-p-68c38c8799f48191a101e19a975ca4f9/outputs/implementations/s02-2a-h1-fixes-0.5.0a2-2026-10-24/final-wheel-selection.json) chứng minh final/wheels là byte copy đúng ZIP đã cài non-editable; [collector a1→a2](/Users/macbookpro/.codex/.chatgpt-projects/g-p-68c38c8799f48191a101e19a975ca4f9/outputs/implementations/s02-2a-h1-fixes-0.5.0a2-2026-10-24/package-evidence-final/manifest.json) kiểm source/wheel/installed, direct_url SHA, METADATA/WHEEL, S01 same-version equality và S02 cross-version diff. Pip check exit0.

Package/handler version a2; canonical contract/profile/rules/candidate/config/plan/limits IDs giữ nguyên. [Compatibility synthetic proof](/Users/macbookpro/.codex/.chatgpt-projects/g-p-68c38c8799f48191a101e19a975ca4f9/outputs/implementations/s02-2a-h1-fixes-0.5.0a2-2026-10-24/version-compatibility/RESULT.json): finalized a1 report nguyên, prepared a1 bị unsupported-version trước effects, store bytes không đổi. Không migration/repair/auto-replay a1.

Differential mới dùng corpus/script lịch sử nguyên byte: **67 accepted, 346 rejected**, so toàn outcomes/diagnostics/walk pointers trên baseline L1 a3 và a2, C/Python. Không chỉ so schema hash; không nới codec để cho tuple logger pass. S01, locks, schemas/registry, repository/DB2 và lịch sử kiểm byte qua inventory/seals riêng.

## Giới hạn

Chưa audit độc lập bản sửa, v3 còn logger failure cần auditor review; không tự đóng findings. Không benchmark/LLM/nghiệp vụ/render/live, H2/H3, real power loss/disk-full hoặc stress ngoài matrix local. Timeout lịch sử chưa có root cause dù lượt full mới đạt. Các suites có ca giao nhau, không gộp thành một tổng coverage độc nhất.
