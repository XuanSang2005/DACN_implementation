# START HERE — 2A-P3 0.4.0a1

**P3 đã triển khai, chờ audit độc lập.**

Chỉ audit wheel: [dacn_s02-0.4.0a1-py3-none-any.whl](audit-wheel/dacn_s02-0.4.0a1-py3-none-any.whl).

SHA-256: `6c9caa88803d75079bd1eef3852161b355a03023170e138f0dac545935c5ae56`

Các wheel trong `release/`, `release-final/` và rebuild chỉ là development/đối chiếu, không thay wheel trên.

- [Báo cáo phạm vi, code, trước/sau, tests và giới hạn](IMPLEMENTATION_REPORT.md).
- [Kết quả tests thực tế](test-summary.json), [instrumentation](instrumentation.json), [process/identity/crash observations](migration-observations.json).
- [Diff pre-edit](implementation.diff), [input inventory](input-inventory.json), [bảo toàn](protected-inventory.json), [L1 preservation](legacy-preservation.json), [oracle/helper hashes](oracle-preservation.json).
- [Differential L1](differential-summary.json), [source–wheel–installed](package-audit-evidence/manifest.json), [rebuild METADATA/WHEEL](rebuild-comparison.json), [pip check](final-pip-check.log).
- [Hot-journal C](final-hot-journal-c/RESULT.json), [Python](final-hot-journal-python/RESULT.json); giữ DB/journal forensic nguyên byte.
- [Tái lập vào output mới](REPRODUCE.md), [commands inventory](commands-index.json), [artifact hashes](ARTIFACT_HASHES.json).

Chỉ synthetic/test migration local; không operational migration, dataset, LLM/live, 2B/2C. P2 a2 đã nghiệm thu theo audit cũ; P3 chưa nghiệm thu.
