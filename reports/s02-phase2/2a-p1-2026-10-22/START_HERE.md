# START HERE — audit implementation S02 2A-P1

Ngày 22/10/2026. **Bàn giao P1 `dacn-s02 0.2.0a1`, chờ audit độc lập; chưa nghiệm thu P1.** Quyền riêng theo [P1_ASSIGNMENT](P1_ASSIGNMENT.txt), không phải giao toàn 2A/Đợt 2.

1. Đọc [IMPLEMENTATION_REPORT](IMPLEMENTATION_REPORT.md), [TEST_RESULTS](TEST_RESULTS.md), [hướng dẫn dispatch/schema/oracles](../../../docs/S02_2A_P1_IMPLEMENTATION.md).
2. Đối chiếu [AGENTS hiện hành](../../../AGENTS.md), [storage proposal draft.2](../../../docs/S02_PHASE2_2A_SCHEMA_MIGRATION_PROPOSAL.md), [A1/A2](../../../docs/S02_PHASE2_CONTRACT_AMENDMENT_PROPOSAL.md), [plan](../../../docs/S02_PHASE2_IMPLEMENTATION_PLAN_PROPOSAL.md), [contract legacy draft.3](../../../docs/S02_OUTPUT_CONTRACT_PROPOSAL.md). Trạng thái cũ trong proposal giữ nguyên lịch sử; audit thiết kế ngày 22/10 đã đóng S02-2A-01/02, quyền P1 nằm trong giao việc mới.
3. Đối tượng duy nhất để cài: [release/dacn_s02-0.2.0a1-py3-none-any.whl](release/dacn_s02-0.2.0a1-py3-none-any.whl), SHA-256 `38ed24de6769d9bcaf76927c8c5ffbcaf587972192d1fe0f24f16435b6d24df2`. Không dùng các wheel trung gian cùng version nằm ở thư mục khác.
4. Xem [source–wheel–installed](release-package-evidence/manifest.json), [diff riêng P1](implementation-release.diff), [inventory bảo vệ](protected-inventory-release.json), [schema diff](schema-changes.json), [rules bundle](rules-bundle-release.json), [test inputs](test-inputs-release.json) và [MANIFEST](MANIFEST.json).
5. Tái lập theo [REPRODUCE](REPRODUCE.md), tạo venv/output mới ngoài source; không chạy generator hoặc script lịch sử vào output có sẵn. Kiểm actual repo hiện tại so source-inputs/manifest trước audit; snapshot không thay kiểm hiện trạng.

E1 chỉ là schema/validators/whole-graph checks thuần trong bộ nhớ. Repository/CLI vẫn DB1/L1; test từ chối E1 write. Không DB2/migration/cutover/activation, live LLM/renderer/KB/S03. Source S01 a6, locks/dependencies, schema L1 và suite a3 giữ nguyên. Nghiệm thu a3 Đợt 1 vẫn giới hạn local foundation.

Các tests mới chạy thật trên fixtures synthetic; S01 runs trong A1 là local temp thực. `SYNTHETIC REVIEWER`, consent fixtures và `HumanReviewEvidence` không phải người thật xác nhận. Các oracle audit lịch sử được chạy lại nguyên assertions, **không phải kết quả auditor độc lập cho P1**. Không tự suy code-pass thành business acceptance hoặc quyền P2/P3.

Auditor xem kỹ profile ownership, history/current refs, DIRECT root, A1 full raw/request/consent và source branch; CARRY/REPLACEMENT coverage, lineage, blockers/tasks/review binding; ranh giới CAS/persistence. Giữ evidence/reports lịch sử; tạo báo cáo audit mới. Các lỗi/harness/build-cache trung gian và cách khắc phục đã công khai trong implementation report.
