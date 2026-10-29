# H2-C 0.8.0a1 — merge/revalidation/stress

**Bàn giao implementer cho audit độc lập; chưa audit hoặc nghiệm thu người dùng.** Dùng [AUDIT_READY.json](AUDIT_READY.json) để kiểm trạng thái seal; marker chỉ tạo sau khi gates kết thúc và manifest được rehash. Phạm vi riêng ngày 29/10/2026: H2-C local/synthetic, baseline repo `ecc51bc09219a35e3d7aba7e22292d2ed7b316bc`, working tree ban đầu sạch.

Đã thêm 18 ca kiểm H2-C và runner giữ evidence. Full S02 mới **C977/977, Python977/977**; full S01 **986/986 mỗi backend**, wrappers339/339. [TEST_RESULTS](TEST_RESULTS.md) ghi từng gate, gồm failures gốc P2/H2-A và các lượt phát triển; không gọi toàn bộ diagnostics là pass. Kết quả này không thay audit/nghiệm thu và không sửa lịch sử H2-B.

Kịch bản chính chạy thật qua handlers/checkpoint/reopen/resume: bảy units/17 obligations, **20 publication trong23 finalized commands**, bốn OS workers riêng cùng base pair, một winner/ba stale. Ba stale chỉ được resubmit bằng command/current pair/raw input/approval mới. U held, bốn V độc lập tới stage4/current; hai vòng guard/revalidation giữ output IDs và guard lineage. Expected sets/counts/dispositions viết riêng từ topology/source/script, không lấy thuật toán đang kiểm làm oracle.

## Đọc và kiểm bàn giao

1. [Phạm vi và phương pháp](../../../docs/S02_2A_H2_C_IMPLEMENTATION.md), [ORACLE_MAP](ORACLE_MAP.md).
2. [Kết quả thực chạy](TEST_RESULTS.md), [HARNESS_NOTES](HARNESS_NOTES.md), [tái lập offline](REPRODUCE.md).
3. [MANIFEST](/Users/macbookpro/.codex/.chatgpt-projects/g-p-68c38c8799f48191a101e19a975ca4f9/outputs/implementations/s02-2a-h2-c-0.8.0a1-2026-10-29/MANIFEST.json), [SEAL](/Users/macbookpro/.codex/.chatgpt-projects/g-p-68c38c8799f48191a101e19a975ca4f9/outputs/implementations/s02-2a-h2-c-0.8.0a1-2026-10-29/SEAL.json), [SEAL_CHECK](/Users/macbookpro/.codex/.chatgpt-projects/g-p-68c38c8799f48191a101e19a975ca4f9/outputs/implementations/s02-2a-h2-c-0.8.0a1-2026-10-29/SEAL_CHECK.json); marker audit-ready loại khỏi manifest để tránh vòng hash. Manifest gồm các lượt lỗi, DB/journals, copied tests, logs/commands, wheel và snapshot bàn giao; venv/cache được loại rõ.
4. [Delta before/after](/Users/macbookpro/.codex/.chatgpt-projects/g-p-68c38c8799f48191a101e19a975ca4f9/outputs/implementations/s02-2a-h2-c-0.8.0a1-2026-10-29/handoff/changes.diff), [inventory bàn giao](/Users/macbookpro/.codex/.chatgpt-projects/g-p-68c38c8799f48191a101e19a975ca4f9/outputs/implementations/s02-2a-h2-c-0.8.0a1-2026-10-29/handoff/after-inventory.json), [bảo toàn baseline](/Users/macbookpro/.codex/.chatgpt-projects/g-p-68c38c8799f48191a101e19a975ca4f9/outputs/implementations/s02-2a-h2-c-0.8.0a1-2026-10-29/final/PRESERVATION.json), [trace/readback H2-C](/Users/macbookpro/.codex/.chatgpt-projects/g-p-68c38c8799f48191a101e19a975ca4f9/outputs/implementations/s02-2a-h2-c-0.8.0a1-2026-10-29/final/H2_C_TRACES.json).

Evidence root mới: `/Users/macbookpro/.codex/.chatgpt-projects/g-p-68c38c8799f48191a101e19a975ca4f9/outputs/implementations/s02-2a-h2-c-0.8.0a1-2026-10-29`.

Delivery [dacn_s02-0.8.0a1-py3-none-any.whl](/Users/macbookpro/.codex/.chatgpt-projects/g-p-68c38c8799f48191a101e19a975ca4f9/outputs/implementations/s02-2a-h2-c-0.8.0a1-2026-10-29/final/wheels/dacn_s02-0.8.0a1-py3-none-any.whl), SHA-256:

```text
89904528b6978217b3237a560389188805577a625d80e0e5cbe1e2058b5c1a14
```

## Delta và giới hạn cần audit

Đây là đợt mở rộng kiểm chứng trên H2-B, **production logic không đổi**. Wheel0.8.0a1 khác0.7.0a2 ở package metadata và `__init__.py` version/docstring; handler vẫn `s02-2a-h2-b/0.7.0a2`. File mới gồm fixture/worker, ba test modules `test_h2_c_*`, `run_h2_c_checks.py`, hướng dẫn và bàn giao. Ba README điều hướng cập nhật mốc hiện hành. Giữ nguyên H1/H2-A/canonical schemas/registry/DB2/S01/locks, tests cũ/conftest/oracles và evidence lịch sử. HEAD giữ `ecc51bc`, không stage/commit/push.

Auditor cần kiểm oracle independence, scope/union/fixed point, retained-output/guard lifecycle và publication thực so với plan; không chỉ dựa status hoặc tổng passes. Domain race có bốn concurrent builders/sealers. **AS-only race cuối seal trước rồi bốn process tranh T3**. Lượt phát triển concurrent AS-only seal ở state lớn gặp lock/barrier timeout, giữ nguyên log/DB; readback cho thấy không publication, chưa chứng minh liveness cho mọi contention. Workload sáu V stress-v3 pass riêng nhưng gần Budget30s; workload cuối bốn V/hai guard cycles được ghi riêng, không đánh tráo kết quả. Chi tiết ở HARNESS_NOTES/TEST_RESULTS.

H2-B findings01/02 đã đóng; V01 safety verified theo audit29/10. Full lịch sử H2-B vẫn **C959/959, Python958/959**. Người dùng đã cho tiếp tục H2-C sau khi biết giới hạn này. Mọi approvals/analysis/fixtures trong đợt này là synthetic; chưa xác nhận nghiệp vụ/chất lượng LLM hoặc toàn S02. Không H3/2B/2C/LLM/renderer/live/operational migration, không source switch/Answer/application hoặc bước5–9. Quyết định nghiệm thu thuộc auditor độc lập và người dùng theo đúng phạm vi.
