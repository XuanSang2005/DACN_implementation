# H3-A 0.9.0a1 — bàn giao để audit độc lập

**Hoàn tất implementation/kiểm local-synthetic trong scope A; chưa audit implementation hoặc người dùng nghiệm thu.** D1–D5 được người dùng chấp thuận; D01/D02 đóng design-only theo [biên bản](../../../docs/acceptance/s02-2a-h3-design-draft2-2026-10-29/README.md). Lượt bắt đầu 29/10/2026, kết quả mới có timestamps riêng trong logs/DELIVERY_RESULTS; không đổi lịch sử H2-C/H2-B/V01.

- [API/phạm vi](../../../docs/S02_2A_H3_A_IMPLEMENTATION.md), [closed contracts](CONTRACT_DETAILS.md), [coverage matrix](COVERAGE_MATRIX.md).
- [Failures/limits](FAILURES_AND_LIMITS.md), [reproduce](REPRODUCE.md), [commit plan chưa thực thi](COMMIT_PLAN.md).
- [Evidence START_HERE](/Users/macbookpro/.codex/.chatgpt-projects/g-p-68c38c8799f48191a101e19a975ca4f9/outputs/implementations/s02-2a-h3-a-0.9.0a1-2026-10-29/START_HERE.md), [DELIVERY_RESULTS](/Users/macbookpro/.codex/.chatgpt-projects/g-p-68c38c8799f48191a101e19a975ca4f9/outputs/implementations/s02-2a-h3-a-0.9.0a1-2026-10-29/DELIVERY_RESULTS.json), [TEST_RESULTS gồm mọi attempts](/Users/macbookpro/.codex/.chatgpt-projects/g-p-68c38c8799f48191a101e19a975ca4f9/outputs/implementations/s02-2a-h3-a-0.9.0a1-2026-10-29/TEST_RESULTS.json).
- [Delta source/navigation](/Users/macbookpro/.codex/.chatgpt-projects/g-p-68c38c8799f48191a101e19a975ca4f9/outputs/implementations/s02-2a-h3-a-0.9.0a1-2026-10-29/IMPLEMENTATION_DELTA.patch), [delta đầy đủ gồm docs mới](/Users/macbookpro/.codex/.chatgpt-projects/g-p-68c38c8799f48191a101e19a975ca4f9/outputs/implementations/s02-2a-h3-a-0.9.0a1-2026-10-29/H3_A_COMPLETE_DELTA.patch), [snapshot inventory](/Users/macbookpro/.codex/.chatgpt-projects/g-p-68c38c8799f48191a101e19a975ca4f9/outputs/implementations/s02-2a-h3-a-0.9.0a1-2026-10-29/REPOSITORY_SNAPSHOT_INVENTORY.json). Các delta tính từ working tree trước H3-A.
- [Bảo toàn](/Users/macbookpro/.codex/.chatgpt-projects/g-p-68c38c8799f48191a101e19a975ca4f9/outputs/implementations/s02-2a-h3-a-0.9.0a1-2026-10-29/PRESERVATION.json), [source inventory](/Users/macbookpro/.codex/.chatgpt-projects/g-p-68c38c8799f48191a101e19a975ca4f9/outputs/implementations/s02-2a-h3-a-0.9.0a1-2026-10-29/CURRENT_SOURCE_INVENTORY.json), [static checks](/Users/macbookpro/.codex/.chatgpt-projects/g-p-68c38c8799f48191a101e19a975ca4f9/outputs/implementations/s02-2a-h3-a-0.9.0a1-2026-10-29/STATIC_CHECKS.json), [manifest](/Users/macbookpro/.codex/.chatgpt-projects/g-p-68c38c8799f48191a101e19a975ca4f9/outputs/implementations/s02-2a-h3-a-0.9.0a1-2026-10-29/MANIFEST.json), [seal](/Users/macbookpro/.codex/.chatgpt-projects/g-p-68c38c8799f48191a101e19a975ca4f9/outputs/implementations/s02-2a-h3-a-0.9.0a1-2026-10-29/SEAL.json), [AUDIT_READY](/Users/macbookpro/.codex/.chatgpt-projects/g-p-68c38c8799f48191a101e19a975ca4f9/outputs/implementations/s02-2a-h3-a-0.9.0a1-2026-10-29/AUDIT_READY.json), [script kiểm byte read-only](/Users/macbookpro/.codex/.chatgpt-projects/g-p-68c38c8799f48191a101e19a975ca4f9/outputs/implementations/s02-2a-h3-a-0.9.0a1-2026-10-29/verify_handoff.py).

## Wheel authoritative duy nhất

[Delivery wheel](/Users/macbookpro/.codex/.chatgpt-projects/g-p-68c38c8799f48191a101e19a975ca4f9/outputs/implementations/s02-2a-h3-a-0.9.0a1-2026-10-29/delivery/wheels/dacn_s02-0.9.0a1-py3-none-any.whl), 182245 bytes, SHA-256:

`12dfe52698fa24cfc80280a80b1e34afc5a612dab9cac9578243b3306a0744f5`

Mọi ZIP dưới environment-v*/build/rebuild và provisional final/wheels là build/trial artifacts, không release authority. Dùng delivery/WHEEL.json + AUDIT_READY pins; cài non-editable từ chính ZIP delivery, offline locks, fresh environment-v5. Hai copied builds S02 payload/METADATA/WHEEL bằng nhau; S01 rebuild toàn20 ZIP entries bằng a6 trước cài same-version rebuild. Collector mới kiểm source→wheel→installed/direct URL và baseline0.8→0.9 diff riêng; không ép ZIP0.9 bằng0.8.

## Kết quả đo mới của implementer

| Gate | C | Python |
| --- | --- | --- |
| Focused H3-A | 99/99 | 99/99 |
| Full S02 (gồm99 H3-A) | 1076/1076 | 1076/1076 |
| Full S01 | 986/986 | 986/986 |

Không failure/error/skip trong gates delivery trên; wrappers/layout/pip check/collector đạt. Một job nặng tại một thời điểm, C rồi Python; race/crash workers bên trong các tests cũ giữ nguyên. Full counts này là kết quả mới, không lấy counts lịch sử hoặc gọi là auditor tự chạy. Focused là subset của full, không cộng thành số ca độc lập.

V1 có20 failures/backend, V2 có1/backend; V3/V4 focused là precursor. Provisional full V4 **aborted**, partial JUnit374 cases không là full pass. Logs/JUnit/DB/sidecars giữ nguyên. Xem failures/TEST_RESULTS; không retry vào output cũ, skip/xfail/nới assertions/caps/timeouts hoặc che failures.

## Scope và điểm dừng

Chỉ pure contracts/bytes-data registry/history projection/typed transitions/holds/retained outputs; năm modules mới, tests và tooling kiểm đóng gói. Registry all-store R fixed, external trust tách semantic authority, no decisions từ DB. No-anchor không suy stage; missing proof hợp lệ giữ pending, proof sai reject; root/from/obsolete/current target và Part-row-source context được giữ. Không H3 loader/factory/CLI/writer/migration, Answer/application/source switch/human review mới, completed-output repair, operational/LLM/live.

H3-B/C/D cần giao riêng; §7.1 safety B-AS/C-Model+A2 chưa được pure A chứng minh. Hồ sơ thiết kế/snapshots/handoffs và canonical schemas/registry/DB2/H1/H2/S01/locks/tests cũ giữ byte theo inventory. Quan sát NEXT_PROMPT draft.1 mismatch giữ nguyên, không restore/reseal. HEAD vẫn b0d6ff2/index chưa stage; không commit/push. Sau seal và AUDIT_READY agent dừng sửa để auditor đọc đúng payload; người dùng nghiệm thu cuối.
