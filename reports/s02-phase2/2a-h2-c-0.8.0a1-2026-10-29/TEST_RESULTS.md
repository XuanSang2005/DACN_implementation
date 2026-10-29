# Kết quả thực chạy H2-C 0.8.0a1

**Full S02: C 977/977, Python 977/977; 18 ca H2-C mới nằm trong mỗi full suite.** Không skip/xfail, không retry full để thay kết quả. Đây là kiểm của implementer trên wheel installed, chưa phải kết luận audit độc lập/nghiệm thu người dùng. Full lịch sử H2-B vẫn **C959/959, Python958/959**.

## Môi trường, payload và gates

CPython 3.13.16 có GIL, SQLite 3.53.1, macOS arm64 local; ba venv mới/offline từ locks, S01 a6 non-editable và delivery wheel S02 a1. [Environment](/Users/macbookpro/.codex/.chatgpt-projects/g-p-68c38c8799f48191a101e19a975ca4f9/outputs/implementations/s02-2a-h2-c-0.8.0a1-2026-10-29/environment-v1/environment.json) ghi bundle hash và so sánh hai copied builds: S01 20 ZIP entries bằng nhau và bằng accepted a6 trước thay wheel cùng version; S02 48 entries bằng nhau giữa hai builds. [Collector](/Users/macbookpro/.codex/.chatgpt-projects/g-p-68c38c8799f48191a101e19a975ca4f9/outputs/implementations/s02-2a-h2-c-0.8.0a1-2026-10-29/final/package-evidence/manifest.json) xác nhận source = wheel = installed, metadata/WHEEL/direct URL; diff a2→a1 chỉ METADATA và `__init__.py` version/docstring. Không đổi logic handlers/policy/canonical schemas/DB2/S01/locks.

[Commands](/Users/macbookpro/.codex/.chatgpt-projects/g-p-68c38c8799f48191a101e19a975ca4f9/outputs/implementations/s02-2a-h2-c-0.8.0a1-2026-10-29/final/COMMANDS.json), [JUnit summary](/Users/macbookpro/.codex/.chatgpt-projects/g-p-68c38c8799f48191a101e19a975ca4f9/outputs/implementations/s02-2a-h2-c-0.8.0a1-2026-10-29/final/JUNIT_SUMMARY.json) và thư mục `final/commands` giữ argv/cwd/env/log/exit. Một suite nặng tại một thời điểm; C rồi Python. Bảng dưới là từng nhóm thực chạy; các nhóm overlap không cộng thành số unique tests. Tests nguồn/conftest và original oracles giữ nguyên, hashes tại [ORIGINAL_ORACLES](/Users/macbookpro/.codex/.chatgpt-projects/g-p-68c38c8799f48191a101e19a975ca4f9/outputs/implementations/s02-2a-h2-c-0.8.0a1-2026-10-29/final/ORIGINAL_ORACLES.json).

| Nhóm | Backend | Pass/tổng | Fail | Error | Skip |
| --- | --- | ---: | ---: | ---: | ---: |
| [full-s01](/Users/macbookpro/.codex/.chatgpt-projects/g-p-68c38c8799f48191a101e19a975ca4f9/outputs/implementations/s02-2a-h2-c-0.8.0a1-2026-10-29/final/full-s01) | c | 986/986 | 0 | 0 | 0 |
| [full-s01](/Users/macbookpro/.codex/.chatgpt-projects/g-p-68c38c8799f48191a101e19a975ca4f9/outputs/implementations/s02-2a-h2-c-0.8.0a1-2026-10-29/final/full-s01) | python | 986/986 | 0 | 0 | 0 |
| [full-s02](/Users/macbookpro/.codex/.chatgpt-projects/g-p-68c38c8799f48191a101e19a975ca4f9/outputs/implementations/s02-2a-h2-c-0.8.0a1-2026-10-29/final/full-s02) | c | 977/977 | 0 | 0 | 0 |
| [full-s02](/Users/macbookpro/.codex/.chatgpt-projects/g-p-68c38c8799f48191a101e19a975ca4f9/outputs/implementations/s02-2a-h2-c-0.8.0a1-2026-10-29/final/full-s02) | python | 977/977 | 0 | 0 | 0 |
| [oracle-current-boundaries](/Users/macbookpro/.codex/.chatgpt-projects/g-p-68c38c8799f48191a101e19a975ca4f9/outputs/implementations/s02-2a-h2-c-0.8.0a1-2026-10-29/final/oracle-current-boundaries) | c | 21/21 | 0 | 0 | 0 |
| [oracle-current-boundaries](/Users/macbookpro/.codex/.chatgpt-projects/g-p-68c38c8799f48191a101e19a975ca4f9/outputs/implementations/s02-2a-h2-c-0.8.0a1-2026-10-29/final/oracle-current-boundaries) | python | 21/21 | 0 | 0 | 0 |
| [oracle-h1-v4](/Users/macbookpro/.codex/.chatgpt-projects/g-p-68c38c8799f48191a101e19a975ca4f9/outputs/implementations/s02-2a-h2-c-0.8.0a1-2026-10-29/final/oracle-h1-v4) | c | 10/10 | 0 | 0 | 0 |
| [oracle-h1-v4](/Users/macbookpro/.codex/.chatgpt-projects/g-p-68c38c8799f48191a101e19a975ca4f9/outputs/implementations/s02-2a-h2-c-0.8.0a1-2026-10-29/final/oracle-h1-v4) | python | 10/10 | 0 | 0 | 0 |
| [oracle-h2-a](/Users/macbookpro/.codex/.chatgpt-projects/g-p-68c38c8799f48191a101e19a975ca4f9/outputs/implementations/s02-2a-h2-c-0.8.0a1-2026-10-29/final/oracle-h2-a) | c | 25/25 | 0 | 0 | 0 |
| [oracle-h2-a](/Users/macbookpro/.codex/.chatgpt-projects/g-p-68c38c8799f48191a101e19a975ca4f9/outputs/implementations/s02-2a-h2-c-0.8.0a1-2026-10-29/final/oracle-h2-a) | python | 25/25 | 0 | 0 | 0 |
| [oracle-h2-b](/Users/macbookpro/.codex/.chatgpt-projects/g-p-68c38c8799f48191a101e19a975ca4f9/outputs/implementations/s02-2a-h2-c-0.8.0a1-2026-10-29/final/oracle-h2-b) | c | 7/7 | 0 | 0 | 0 |
| [oracle-h2-b](/Users/macbookpro/.codex/.chatgpt-projects/g-p-68c38c8799f48191a101e19a975ca4f9/outputs/implementations/s02-2a-h2-c-0.8.0a1-2026-10-29/final/oracle-h2-b) | python | 7/7 | 0 | 0 | 0 |
| [oracle-h2-original-limits](/Users/macbookpro/.codex/.chatgpt-projects/g-p-68c38c8799f48191a101e19a975ca4f9/outputs/implementations/s02-2a-h2-c-0.8.0a1-2026-10-29/final/oracle-h2-original-limits) | c | 2/4 | 2 | 0 | 0 |
| [oracle-h2-original-limits](/Users/macbookpro/.codex/.chatgpt-projects/g-p-68c38c8799f48191a101e19a975ca4f9/outputs/implementations/s02-2a-h2-c-0.8.0a1-2026-10-29/final/oracle-h2-original-limits) | python | 2/4 | 2 | 0 | 0 |
| [oracle-p1-six](/Users/macbookpro/.codex/.chatgpt-projects/g-p-68c38c8799f48191a101e19a975ca4f9/outputs/implementations/s02-2a-h2-c-0.8.0a1-2026-10-29/final/oracle-p1-six) | c | 27/27 | 0 | 0 | 0 |
| [oracle-p1-six](/Users/macbookpro/.codex/.chatgpt-projects/g-p-68c38c8799f48191a101e19a975ca4f9/outputs/implementations/s02-2a-h2-c-0.8.0a1-2026-10-29/final/oracle-p1-six) | python | 27/27 | 0 | 0 | 0 |
| [oracle-p2-original](/Users/macbookpro/.codex/.chatgpt-projects/g-p-68c38c8799f48191a101e19a975ca4f9/outputs/implementations/s02-2a-h2-c-0.8.0a1-2026-10-29/final/oracle-p2-original) | c | 16/17 | 1 | 0 | 0 |
| [oracle-p2-original](/Users/macbookpro/.codex/.chatgpt-projects/g-p-68c38c8799f48191a101e19a975ca4f9/outputs/implementations/s02-2a-h2-c-0.8.0a1-2026-10-29/final/oracle-p2-original) | python | 16/17 | 1 | 0 | 0 |
| [oracle-p3](/Users/macbookpro/.codex/.chatgpt-projects/g-p-68c38c8799f48191a101e19a975ca4f9/outputs/implementations/s02-2a-h2-c-0.8.0a1-2026-10-29/final/oracle-p3) | c | 36/36 | 0 | 0 | 0 |
| [oracle-p3](/Users/macbookpro/.codex/.chatgpt-projects/g-p-68c38c8799f48191a101e19a975ca4f9/outputs/implementations/s02-2a-h2-c-0.8.0a1-2026-10-29/final/oracle-p3) | python | 36/36 | 0 | 0 | 0 |

Các command exit khác 0 (không được gọi là pass):

- `oracle-p2-original` exit `1`.
- `oracle-h2-original-limits` exit `1`.

P2 original: failure đã biết gọi checked `heads()` trước vùng `pytest.raises`; current boundaries chạy riêng. H2-A original limits: hai ca đã biết dùng `.value.code`, gây AttributeError; corrected oracle của auditor chạy riêng. Giữ nguyên file/hash/assertions và failures gốc, không sửa chúng để đạt. Chi tiết ca fail:

- [oracle-h2-original-limits/checks/audit-1-c.xml](/Users/macbookpro/.codex/.chatgpt-projects/g-p-68c38c8799f48191a101e19a975ca4f9/outputs/implementations/s02-2a-h2-c-0.8.0a1-2026-10-29/final/oracle-h2-original-limits/checks/audit-1-c.xml): `test_result_model_and_current_issues_must_share_ref_limit[190-4-20]`.
- [oracle-h2-original-limits/checks/audit-1-c.xml](/Users/macbookpro/.codex/.chatgpt-projects/g-p-68c38c8799f48191a101e19a975ca4f9/outputs/implementations/s02-2a-h2-c-0.8.0a1-2026-10-29/final/oracle-h2-original-limits/checks/audit-1-c.xml): `test_result_model_and_current_issues_must_share_ref_limit[50000-25-1907]`.
- [oracle-h2-original-limits/checks/audit-1-python.xml](/Users/macbookpro/.codex/.chatgpt-projects/g-p-68c38c8799f48191a101e19a975ca4f9/outputs/implementations/s02-2a-h2-c-0.8.0a1-2026-10-29/final/oracle-h2-original-limits/checks/audit-1-python.xml): `test_result_model_and_current_issues_must_share_ref_limit[190-4-20]`.
- [oracle-h2-original-limits/checks/audit-1-python.xml](/Users/macbookpro/.codex/.chatgpt-projects/g-p-68c38c8799f48191a101e19a975ca4f9/outputs/implementations/s02-2a-h2-c-0.8.0a1-2026-10-29/final/oracle-h2-original-limits/checks/audit-1-python.xml): `test_result_model_and_current_issues_must_share_ref_limit[50000-25-1907]`.
- [oracle-p2-original/checks/audit-1-c.xml](/Users/macbookpro/.codex/.chatgpt-projects/g-p-68c38c8799f48191a101e19a975ca4f9/outputs/implementations/s02-2a-h2-c-0.8.0a1-2026-10-29/final/oracle-p2-original/checks/audit-1-c.xml): `test_writer_refuses_review_fork_after_selection_loss`.
- [oracle-p2-original/checks/audit-1-python.xml](/Users/macbookpro/.codex/.chatgpt-projects/g-p-68c38c8799f48191a101e19a975ca4f9/outputs/implementations/s02-2a-h2-c-0.8.0a1-2026-10-29/final/oracle-p2-original/checks/audit-1-python.xml): `test_writer_refuses_review_fork_after_selection_loss`.

Wrappers **339/339**, layout và pip check exit0. [L1 comparison](/Users/macbookpro/.codex/.chatgpt-projects/g-p-68c38c8799f48191a101e19a975ca4f9/outputs/implementations/s02-2a-h2-c-0.8.0a1-2026-10-29/final/differential-l1/COMPARISON.json) xác nhận **413/413 outcomes bằng nhau ở cả bốn tổ hợp legacy/current ×C/Python**, cùng corpus nguyên byte và có encoder factory counts; không thay codec bằng assert tên backend.

## Checkpoints, process stress và số đo

[H2_C_TRACES.json](/Users/macbookpro/.codex/.chatgpt-projects/g-p-68c38c8799f48191a101e19a975ca4f9/outputs/implementations/s02-2a-h2-c-0.8.0a1-2026-10-29/final/H2_C_TRACES.json) được đọc trực tiếp SQLite mode=ro sau khi các H2-C cases hoàn tất. Mỗi backend có tám handler traces và 59 workers H2-C có PID/phase/encoder instrumentation. Trace chính có **23 finalized commands: 1 completed, 19 blocked, 3 stale**, tức20 publication; bảy units/17 obligations, cuối trace1 actor/4 actions/4 responsibilities/17 mapping rows. U held, bốn V stage4/current; hai guard resolved kỹ thuật không xóa business hold/global mapping task. Từng stale không có planned Model/Change/Issue/AS trong Records thực. Ba lần resubmit có command/current pair/raw input/approval mới, approval cũ bị từ chối trước T0.

Mỗi backend có hai nhóm bốn OS PIDs độc lập, một winner/ba stale: domain race chạy build/seal/T3; AS-only race seal trước qua handler rồi bốn process mới reopen/resume tranh T3, giữ Model/output/stage và sealed plan hash. Những controls khác không đếm bootstrap/race trong `recorded_checkpoints`; trường `actual_h2_run_statuses` ghi đầy đủ Runs thực, không lấy số dòng trace phụ làm tổng publication của store.

Trace chính có max config104372 bytes, plan156123 bytes, candidate+analysis322648 bytes; controls có tối đa config108583 bytes, plan144736 bytes, raw615130 bytes. Giữ DEFAULTS: raw1048576, config2097152, plan16777216 bytes, Budget30s; không tăng caps, reset theo unit/phase hoặc cắt closure. Max worker resume quan sát trong workload cuối: **C 17.683016s, Python 18.682447s**. Thời gian này gồm instrumentation/barrier, không SLA, benchmark CPU hoặc bảo đảm mọi payload dưới trần hoàn tất trong30s. Full suite JUnit wall time: C1896.585s, Python2013.256s.

## Failures phát triển và giới hạn

[HARNESS_NOTES](HARNESS_NOTES.md) giữ focused-v1/v2 failures, workload sáu V stress-v3 và lý do chọn workload cuối bốn V/hai guard cycles. Đặc biệt concurrent AS-only seal ở state lớn đã có SQLite lock timeout5s và barrier timeout20s; không sửa production timeouts để đạt. [Readback](/Users/macbookpro/.codex/.chatgpt-projects/g-p-68c38c8799f48191a101e19a975ca4f9/outputs/implementations/s02-2a-h2-c-0.8.0a1-2026-10-29/failed-race-readback/READBACK.json) trên copies của bốn DB lỗi cho thấy4 pending,3 sealed/1 chưa seal, không promotions/planned domain publication, head giữ base. Đây là quan sát fail-closed ở các snapshots ấy, không chứng minh liveness/recovery cho mọi contention. Workload AS-only cuối preseal được ghi rõ, không gọi nó là bốn concurrent builders.

Mọi source fixtures/projections/approvals/analysis đều synthetic; pure graph Dependency/Support controls không phải handler step5. Expected sets/counts/dispositions được viết từ topology/source/script, không gọi thuật toán đang kiểm để sinh expected; [ORACLE_MAP](ORACLE_MAP.md) ghi từng invariant. Chưa đánh giá semantic quality/nghiệp vụ, LLM, renderer, live hoặc operational power loss; chưa H3/Answer/application/source switch hay các bước5–9. Auditor độc lập và người dùng còn phải quyết định nghiệm thu đúng phạm vi này.
