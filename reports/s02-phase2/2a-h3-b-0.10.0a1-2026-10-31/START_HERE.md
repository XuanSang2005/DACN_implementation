# H3-B 0.10.0a1 — bàn giao candidate để audit

**Implementer đã hoàn thành validation local/synthetic; chưa nghiệm thu runtime B.** Auditor kiểm độc lập, người dùng nghiệm thu cuối. Mốc sẵn sàng chỉ có hiệu lực khi file AUDIT_READY tồn tại sau MANIFEST/SEAL/SEAL_CHECK ở evidence root; trước marker không coi là đã seal. Chưa H3-C/D/CLI/live.

[Evidence root](/Users/macbookpro/.codex/.chatgpt-projects/g-p-68c38c8799f48191a101e19a975ca4f9/outputs/implementations/s02-2a-h3-b-0.10.0a1-2026-10-31): authoritative delivery-release-v2, release-env-v2, release-focused-v2, release-full-v2, logs/JUnit/DBs/sidecars/readbacks và final review inventories/patches. Đọc [contract/API delta](CONTRACT_API_DELTA.md), [coverage/safety matrix](COVERAGE_SAFETY_MATRIX.md), [failures/limits](FAILURES_AND_LIMITS.md), [tái lập](REPRODUCE.md), [commit plan](COMMIT_PLAN.md), [hướng dẫn API](../../../docs/S02_2A_H3_B_IMPLEMENTATION.md).

## Phạm vi và baseline

B-P01 được người dùng chấp thuận theo [audit thiết kế](../../../docs/acceptance/s02-2a-h3-b-contract-draft1-2026-10-31/README.md). Private Config/Plan/Admission/policy/work/authority/analysis B draft.3, separate result/config/publisher checks; old A projection/checkers/oracles nguyên hành vi. API checked inspect/adopt/revalidate/prepare/resume/report, bounded external historical-review loader/factory trước checked reads, AS-only T0/seal/T3/paired CAS. Model/completed outputs giữ byte; adopt giữ current Issues, revalidate chỉ supported code-origin guard successors, giữ task origins/target predicates và all keys. Không human decision/Answer/application/source switch mới hoặc Model/Change edit.

HEAD đầu B và cuối phải khớp `9a1a44e8bebccda085604dc371b91c2db33b08f1`; audit A baseline `b0d6ff26c2912c01ceea7a2d8f6a3fa163d3ce57` là mốc khác. Before431 files, giữ valid working tree/docs; không reset/stage/commit/push. I02 cleanup provenance riêng, không rollback hoặc gộp acceptance A/B. Canonical schemas/registry/DB2/A1/A2/H1/H2/S01/locks và evidence cũ được kiểm riêng.

## Wheel duy nhất và môi trường

[Release wheel](/Users/macbookpro/.codex/.chatgpt-projects/g-p-68c38c8799f48191a101e19a975ca4f9/outputs/implementations/s02-2a-h3-b-0.10.0a1-2026-10-31/delivery-release-v2/wheels/dacn_s02-0.10.0a1-py3-none-any.whl), **209683 bytes**, SHA-256:

`5d7625f2445172b5d789fb51e4765c747cc1bb7a2994a7ab6b6416118ed0004b`

[WHEEL inventory](/Users/macbookpro/.codex/.chatgpt-projects/g-p-68c38c8799f48191a101e19a975ca4f9/outputs/implementations/s02-2a-h3-b-0.10.0a1-2026-10-31/delivery-release-v2/WHEEL.json), [source–wheel–installed/direct URL cuối](/Users/macbookpro/.codex/.chatgpt-projects/g-p-68c38c8799f48191a101e19a975ca4f9/outputs/implementations/s02-2a-h3-b-0.10.0a1-2026-10-31/release-package-final-v2), [fresh environment](/Users/macbookpro/.codex/.chatgpt-projects/g-p-68c38c8799f48191a101e19a975ca4f9/outputs/implementations/s02-2a-h3-b-0.10.0a1-2026-10-31/release-env-v2/environment.json), [serial commands/logs](/Users/macbookpro/.codex/.chatgpt-projects/g-p-68c38c8799f48191a101e19a975ca4f9/outputs/implementations/s02-2a-h3-b-0.10.0a1-2026-10-31/release-orchestration-v2/commands.json). Hai rebuild bằng toàn58 ZIP payload/METADATA/WHEEL entries; S01 rebuild bằng toàn20 entries a6 trước same-version replacement. Offline locks, CPython3.13.16/GIL/SQLite3.53.1, non-editable, cài chính delivery ZIP. ZIP khác chỉ development/rebuild provenance; release v1 đã superseded, không dùng SHA/counts partial của nó cho candidate cuối.

## Kết quả mới — implementer chạy, không phải audit độc lập

| Lane | C | Python |
| --- | --- | --- |
| Focused B | 111/111 | 111/111 |
| Original focused A | 129/129 | 129/129 |
| Original oracle A | 13/13 | 13/13 |
| Original supplement A | 8/8 | 8/8 |
| Original A mismatch diagnostics | 3/3 | 3/3 |
| Full S02 | 1217/1217 | 1217/1217 |
| Full S01 | 986/986 | 986/986 |

Tất cả lanes trên **0 failures/errors/skips**, C rồi Python tuần tự, một job nặng; concurrency giữ trong race/crash tests. Focused B gồm36 pure +35 runtime +40 OS-process safety/backend. S1–S6/E18/HR-P/E20/E21 kiểm same-command preparers/resumers, seal/finalize races, AS-only/valid Model+AS opponents, T0/seal/T3 rollback/kill/lost ACK/unknown, registry ancestor/other-session loss/tamper/restore và providerless finalized report. Exact DB readbacks có planned/actual Records, base/current Issues, allocations/times/raw/config/plan/registry pins/promotions và old application rows. Human-history control có4 external entries/hai session và2 application events giữ nguyên.

[Case→phase/path/backend/PID/oracle matrix](/Users/macbookpro/.codex/.chatgpt-projects/g-p-68c38c8799f48191a101e19a975ca4f9/outputs/implementations/s02-2a-h3-b-0.10.0a1-2026-10-31/CASE_MATRIX_FINAL.json). Wrappers339 cases, layout, pip check và collector có logs riêng. Original diagnostics3 chỉ xác nhận mismatch A đã giữ nguyên, không B safety pass. A129/13/8 ở bảng là implementer tái chạy mới trên wheel B; các auditor counts lịch sử vẫn gắn đúng version/scope trong acceptance A. H2-B V01 và H2-C giới hạn lịch sử không bị mở lại hoặc đổi counts.

## Integrity và audit tiếp

Final review có HEAD/index/status, HEAD→current và before-B→current patches (gồm untracked), inventory và source/tests/docs snapshots. Static links/JSON/TOML/Python/hash/diff checks; original audit manifest/oracle bytes và accepted A2 wheel được đối chiếu read-only. Không sửa/restore/reseal NEXT_PROMPT draft.1 có mismatch đã ghi nhận.

Ở evidence root: FINAL_RESULTS.json / RELEASE_SELECTION.json / MANIFEST.json / SEAL.json / SEAL_CHECK.json / AUDIT_READY. AUDIT_READY ghi cuối sau seal verification; sau marker dừng sửa. [Failures/limits](FAILURES_AND_LIMITS.md) giữ mọi precursor failure và superseded/partial run, không dùng chúng như kết quả cuối hoặc hạ assertions/caps/timeouts. Auditor kiểm independently; user quyết định nghiệm thu/commit/scope tiếp. Không tự đóng finding hoặc ghi B đã nghiệm thu.
