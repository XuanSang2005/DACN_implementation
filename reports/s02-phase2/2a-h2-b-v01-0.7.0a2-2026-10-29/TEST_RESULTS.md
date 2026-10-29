# Kết quả thực thi V01

Môi trường mới CPython3.13.16 GIL/SQLite3.53.1/macOS arm64; exact a2 noneditable/locks offline. C rồi Python tuần tự từng lượt; giữ concurrency CAS/crash. Synthetic software tests, không nghiệp vụ/LLM/live.

| Nhóm | C | Python |
| --- | --- | --- |
| Release original nguyên byte + timing | 3pass | 3pass |
| Release mới trong corrected-harness-v2 | 3pass | 3pass |
| Negative cache_spill=OFF thử nghiệm cùng lượt | 1fail | 1fail |
| Deadline auditor nguyên byte trong final-controls | 2pass | 2pass |
| Before-write negative trong final-controls | 1pass | 1pass |
| Hot journal + real wall deadline/readback v3 | 2pass | 2pass |
| Writer evidence v1 | 2fail | 2fail |
| Writer evidence v2 trong final-controls | 2fail | 2fail |
| Harness worker import v1 | 4fail | 4fail |

Không skip/xfail; không tăng caps/timeouts hoặc hạ assertions. Nhóm có overlap, không cộng thành unique full suite. [RESULTS.json](/Users/macbookpro/.codex/.chatgpt-projects/g-p-68c38c8799f48191a101e19a975ca4f9/outputs/implementations/s02-2a-h2-b-v01-0.7.0a2-2026-10-29/RESULTS.json) và từng thư mục backend có command.json/pytest.log/junit.xml với outcome thực tế. Failures không bị xóa khỏi số liệu.

Full **auditor lịch sử** vẫn C959pass/Python958pass+1deadline fail. **Không chạy lại** full S02/S01, P1/P2/P3/H1/H2-A/differential/live trong đợt này. Kết quả cũ giữ version/phạm vi, không ghi là chạy mới. Byte preservation/collector không thay behavioral full regression.

| Fixture/pha | C wall | Python wall | Python CPU |
| --- | ---: | ---: | ---: |
| Gốc: recovery invocation | 3.193s | 21.866s | 21.833s |
| Gốc: report sau finalize (trong invocation) | 0.672s | 4.677s | 4.668s |
| Mới: recovery invocation | 1.056s | 4.228s | 4.220s |
| Mới: report sau finalize | 0.222s | 0.889s | 0.888s |

Không dùng số đo làm SLA/đảm bảo luôn dưới30s. Wall deadline v3 có sleep chủ đích tới deadline+0.05s, ghi riêng trong readback; không tính là tốc độ tự nhiên. Bốn control giữ một Budget và invariants trước/sau publication.
