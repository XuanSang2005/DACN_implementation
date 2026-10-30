# DACN implementation — S01 và S02

S01 `0.1.0a6` và S02 Đợt 1/P1/P2/P3/H1/H2-A/H2-C đã nghiệm thu kỹ thuật trong từng phạm vi. Baseline **`0.5.0a2` đạt H1 local/synthetic, fresh E1/full scope**, H1-01/02 đóng theo [audit 25/10/2026](docs/acceptance/s02-2a-h1-0.5.0a2-2026-10-25/AUDIT_REPORT.md) và [biên bản](docs/acceptance/s02-2a-h1-0.5.0a2-2026-10-25/S02_2A_H1_ACCEPTANCE.json). Mốc S01 test store + bốn mock qua handlers → draft Model/mapping/Issues, checkpoint/resume/blocked không chứng minh chất lượng nghiệp vụ/LLM. [Hướng dẫn H1](docs/S02_2A_H1_IMPLEMENTATION.md), [bàn giao lịch sử](reports/s02-phase2/2a-h1-fixes-0.5.0a2-2026-10-25/START_HERE.md). **[Thiết kế H2 draft.2](docs/S02_2A_H2_PARTIAL_SCOPE_DESIGN_PROPOSAL.md) đã đạt audit**, [D01/D02 đóng ở mức thiết kế](docs/acceptance/s02-2a-h2-design-draft2-2026-10-25/README.md); [biên bản](docs/acceptance/s02-2a-h2-design-draft2-2026-10-25/DESIGN_ACCEPTANCE.json). **H2-A `0.6.0a2` đã được người dùng nghiệm thu kỹ thuật pure policy local/synthetic ngày 26/10; findings 01/02/03 đã đóng** theo [audit và biên bản](docs/acceptance/s02-2a-h2-a-0.6.0a2-round1-2026-10-26/README.md). [API/phạm vi](docs/S02_2A_H2_A_IMPLEMENTATION.md), [wheel và evidence lịch sử](reports/s02-phase2/2a-h2-a-fixes-0.6.0a2-round1-2026-10-25/START_HERE.md). **H2-B 0.7.0a2 đã đóng findings01/02; [V01](/Users/macbookpro/.codex/.chatgpt-projects/g-p-68c38c8799f48191a101e19a975ca4f9/outputs/audits/s02-2a-h2-b-v01-0.7.0a2-2026-10-29/AUDIT_REPORT.md) xác minh an toàn deadline/recovery. Full lịch sử vẫn C959/959, Python958/959.** Người dùng đã biết giới hạn này và giao riêng **[H2-C merge/revalidation/stress](docs/S02_2A_H2_C_IMPLEMENTATION.md)** ngày29/10; [bàn giao implementer](reports/s02-phase2/2a-h2-c-0.8.0a1-2026-10-29/START_HERE.md) giữ trạng thái lịch sử. **H2-C `0.8.0a1` đã được người dùng nghiệm thu kỹ thuật local/synthetic ngày 29/10 theo [audit và biên bản](docs/acceptance/s02-2a-h2-c-0.8.0a1-2026-10-29/README.md)**. Auditor tự chạy **18+2 ca/backend**, full S02 **977/977** và S01 **986/986/backend** là supporting evidence của implementer, không phải full audit chạy mới. AS-only race dùng presealed plans ở T3; recovery từ failed DB thật không bảo đảm liveness mọi contention. H2-B V01/full lịch sử giữ nguyên. **[H3 draft.2](docs/S02_2A_H3_E1_HISTORY_DESIGN_PROPOSAL.md) đã đạt audit thiết kế; D1–D5 được chấp thuận, chỉ H3-A được giao, chưa nghiệm thu implementation**; 2B/2C/LLM/renderer/live/operational migration/cutover vẫn ngoài phạm vi, chưa nghiệm thu toàn S02.

| Thành phần | Code / hướng dẫn | Căn cứ nghiệm thu |
| --- | --- | --- |
| S01 a6 | [packages/s01](packages/s01/), [CLI local](docs/s01/README.md) | [S01](docs/acceptance/S01_ACCEPTANCE.json) |
| S02 Đợt 1 a3 | [packages/s02](packages/s02/), [chỉ dẫn S02](docs/s02/README.md) | [Đợt 1](docs/acceptance/S02_PHASE1_ACCEPTANCE.json) |
| S02 profiles P1 a3, DB2 P2 a2 | [P1](docs/S02_2A_P1_IMPLEMENTATION.md), [P2](docs/S02_2A_P2_IMPLEMENTATION.md) | [P1](docs/acceptance/S02_2A_P1_ACCEPTANCE.json), [P2](docs/acceptance/S02_2A_P2_ACCEPTANCE.json) |
| S02 migration P3 a3 | [P3](docs/S02_2A_P3_IMPLEMENTATION.md) | [P3](docs/acceptance/S02_2A_P3_ACCEPTANCE.json) |
| S02 handlers H1 a2 | [H1](docs/S02_2A_H1_IMPLEMENTATION.md) | [H1 local/synthetic](docs/acceptance/s02-2a-h1-0.5.0a2-2026-10-25/S02_2A_H1_ACCEPTANCE.json) |
| S02 H2-B fixes a2 | [H2-B](docs/S02_2A_H2_B_FIXES_0_7_0a2.md) | Findings01/02 đóng; V01 safety verified, full lịch sử có giới hạn |
| S02 H2-C a1 | [H2-C](docs/S02_2A_H2_C_IMPLEMENTATION.md) | [Đã nghiệm thu local/synthetic](docs/acceptance/s02-2a-h2-c-0.8.0a1-2026-10-29/README.md), giữ giới hạn audit |
| S02 H3-A 0.9.0a2 | [Pure contracts/policy](docs/S02_2A_H3_A_IMPLEMENTATION.md) | Bàn giao để audit; chưa nghiệm thu implementation |
| S02 H3 design draft.2 | [Proposal](docs/S02_2A_H3_E1_HISTORY_DESIGN_PROPOSAL.md) | Đạt audit thiết kế; H3-A a2 đã bàn giao sửa ba findings để audit lại |
| S02 pure scope policy H2-A a2 | [H2-A](docs/S02_2A_H2_A_IMPLEMENTATION.md) | [H2-A local/synthetic](docs/acceptance/s02-2a-h2-a-0.6.0a2-round1-2026-10-26/S02_2A_H2_A_ACCEPTANCE.json) |

Root là workspace; build riêng từng package, không `pip install .` ở root. Distribution/namespaces vẫn `dacn-s01`/`dacn_s01`, `dacn-s02`/`dacn_s02`. Dataset và nguồn nghiên cứu là tài nguyên bên ngoài chỉ đọc. State, DB, receipts và kết quả chạy mới đặt ngoài checkout, tách kho S01/S02.

## Bootstrap từ checkout sạch

Source H3-A `0.9.0a2` dùng [driver offline và checks tuần tự H3-A](reports/s02-phase2/2a-h3-a-fixes-0.9.0a2-2026-10-30/REPRODUCE.md); [bàn giao/audit-ready](reports/s02-phase2/2a-h3-a-fixes-0.9.0a2-2026-10-30/START_HERE.md). Chỉ pure A, chưa H3-B/C/D. Baseline H2-C `0.8.0a1` dùng [driver offline và gates tuần tự H2-C](reports/s02-phase2/2a-h2-c-0.8.0a1-2026-10-29/REPRODUCE.md), với output/venv mới ngoài checkout. Không dùng lane accepted-only bên dưới để ép hash phiên bản mới.

Cần Python hệ thống và **bundle macOS arm64 đã pin**, không tải hoặc resolve dependencies online. Nhận bundle đúng tên/hash theo [artifacts](artifacts/README.md). `tools/bootstrap.py` dưới đây giữ nguyên lane đối chiếu source P3 a3 đã nghiệm thu; nó không build source H2-A thành wheel P3. **Với checkout H2-A 0.6.0a2 dùng driver offline và commands tại [bàn giao H2-A](reports/s02-phase2/2a-h2-a-fixes-0.6.0a2-round1-2026-10-25/REPRODUCE.md)**: restore cùng bundle, locks nguyên byte, copy source sạch, hai rebuild, cài non-editable và collector. Vòng sửa H2-A a2 dùng driver checks tuần tự trong bàn giao; verifier mặc định dưới đây vẫn parallel full S02 và không được dùng cho vòng sửa này. Không sửa hash baseline để chấp nhận version mới.

```sh
python3 -B tools/bootstrap.py \
  --bundle /path/to/bootstrap-macos-arm64-2026-10-23.tar.gz \
  --environment-root /path/outside-checkout/dacn-env-NEW
python3 -B tools/verify_checkout.py \
  --environment /path/outside-checkout/dacn-env-NEW/environment.json \
  --output /path/outside-checkout/dacn-checks-NEW
```

Mỗi output phải mới. Bootstrap kiểm SHA-256 archive, inventory và từng member trước khi restore; từ chối overwrite hoặc symlink thoát root. Runtime CPython 3.13.16 GIL/SQLite 3.53.1, uv 0.13.0 và wheelhouse có sẵn trong bundle. Giữ nguyên [tool lock](tools/requirements-tools.lock) và locks S01/S02. Bundle có wheel S01 a6, S02 Đợt 1/P1 để tạo DB1/old-reader fixtures và wheel S02 P3 đã nghiệm thu.

Bootstrap tạo ba venv non-editable ngoài checkout, build từ copied inputs sạch, so mọi ZIP entry với wheel được nghiệm thu, rồi kiểm source–wheel–installed/METADATA/WHEEL/direct URL bằng collector. ZIP hash rebuild có thể khác; không sửa hash locks để chấp nhận rebuild. [Chi tiết bootstrap/commands](docs/BOOTSTRAP.md).

Verifier chạy nguyên bốn oracle P3, CLI controls có backend instrumentation, wrapper/layout smoke và full S01/S02 trên C/Python. S02 dùng [E1 test adapter đã có](packages/s02/tools/prepare_p2_tests.py) và baseline helpers từ bundle; production source không vào Python path. Không gộp hai conftest vào một pytest process. Có thể dùng `--focused-only` để chỉ chạy nhóm focused/smoke; không gọi đó là full regression.

## Code, tài liệu và artifacts

- [Docs/contract/examples](docs/README.md), [AGENTS](AGENTS.md), [báo cáo lịch sử](reports/README.md).
- [Build/check/collect tooling](tools/), [S01 legacy tools](packages/s01/tools/legacy/README.md), [S02 legacy tools](packages/s02/tools/legacy/README.md).
- [Archive/restore policy](docs/ARTIFACTS.md), [cleanup GitHub và kết quả kiểm](docs/GITHUB_CLEANUP_2026-10-23.md).

Repository giữ production payload, tests (gồm CLI regression viết tay của P3 a3), locks, tài liệu và reports Markdown. Logs, JUnit, DB synthetic, wheels, inventories lớn, copied snapshots và generated STATIC_CHECKS có archive/inventory/SHA-256 trước khi ngừng tracking. **File gốc vẫn giữ trên đĩa**; không sửa evidence lịch sử theo trạng thái mới. Runtime/venv/build outputs không thuộc source GitHub. Thay đổi cleanup không rewrite lịch sử Git hoặc tự commit/push.

H3-A a1 có [ba findings OPEN theo audit độc lập](/Users/macbookpro/.codex/.chatgpt-projects/g-p-68c38c8799f48191a101e19a975ca4f9/outputs/audits/s02-2a-h3-a-0.9.0a1-2026-10-30/AUDIT_REPORT.md); a2 chỉ sửa đúng ba findings, chưa nghiệm thu. Auditor a1 tự chạy focused99 pass/backend, oracle13 có8 fail/5 pass/backend; full1076/986/backend thuộc implementer a1. Không H3-B/C/D.
