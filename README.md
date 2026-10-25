# DACN implementation — S01 và S02

S01 `0.1.0a6` và S02 Đợt 1/P1/P2/P3/H1 đã nghiệm thu kỹ thuật trong từng phạm vi. S02 hiện hành **`0.5.0a2` đạt H1 local/synthetic, fresh E1/full scope**, H1-01/02 đóng theo [audit 25/10/2026](docs/acceptance/s02-2a-h1-0.5.0a2-2026-10-25/AUDIT_REPORT.md) và [biên bản](docs/acceptance/s02-2a-h1-0.5.0a2-2026-10-25/S02_2A_H1_ACCEPTANCE.json). Mốc S01 test store + bốn mock qua handlers → draft Model/mapping/Issues, checkpoint/resume/blocked không chứng minh chất lượng nghiệp vụ/LLM. [Hướng dẫn H1](docs/S02_2A_H1_IMPLEMENTATION.md), [bàn giao lịch sử](reports/s02-phase2/2a-h1-fixes-0.5.0a2-2026-10-25/START_HERE.md). **[Thiết kế H2 draft.2](docs/S02_2A_H2_PARTIAL_SCOPE_DESIGN_PROPOSAL.md) đã đạt audit**, [D01/D02 đóng ở mức thiết kế](docs/acceptance/s02-2a-h2-design-draft2-2026-10-25/README.md); [biên bản](docs/acceptance/s02-2a-h2-design-draft2-2026-10-25/DESIGN_ACCEPTANCE.json). H2 chưa triển khai/nghiệm thu implementation; bước tiếp theo đề nghị H2-A pure policy cần giao riêng. Chưa nghiệm thu toàn S02/renderer/live; không cấp quyền operational migration/cutover/H2/H3/2B/2C.

| Thành phần | Code / hướng dẫn | Căn cứ nghiệm thu |
| --- | --- | --- |
| S01 a6 | [packages/s01](packages/s01/), [CLI local](docs/s01/README.md) | [S01](docs/acceptance/S01_ACCEPTANCE.json) |
| S02 Đợt 1 a3 | [packages/s02](packages/s02/), [chỉ dẫn S02](docs/s02/README.md) | [Đợt 1](docs/acceptance/S02_PHASE1_ACCEPTANCE.json) |
| S02 profiles P1 a3, DB2 P2 a2 | [P1](docs/S02_2A_P1_IMPLEMENTATION.md), [P2](docs/S02_2A_P2_IMPLEMENTATION.md) | [P1](docs/acceptance/S02_2A_P1_ACCEPTANCE.json), [P2](docs/acceptance/S02_2A_P2_ACCEPTANCE.json) |
| S02 migration P3 a3 | [P3](docs/S02_2A_P3_IMPLEMENTATION.md) | [P3](docs/acceptance/S02_2A_P3_ACCEPTANCE.json) |
| S02 handlers H1 a2 | [H1](docs/S02_2A_H1_IMPLEMENTATION.md) | [H1 local/synthetic](docs/acceptance/s02-2a-h1-0.5.0a2-2026-10-25/S02_2A_H1_ACCEPTANCE.json) |

Root là workspace; build riêng từng package, không `pip install .` ở root. Distribution/namespaces vẫn `dacn-s01`/`dacn_s01`, `dacn-s02`/`dacn_s02`. Dataset và nguồn nghiên cứu là tài nguyên bên ngoài chỉ đọc. State, DB, receipts và kết quả chạy mới đặt ngoài checkout, tách kho S01/S02.

## Bootstrap từ checkout sạch

Cần Python hệ thống và **bundle macOS arm64 đã pin**, không tải hoặc resolve dependencies online. Nhận bundle đúng tên/hash theo [artifacts](artifacts/README.md). `tools/bootstrap.py` dưới đây giữ nguyên lane đối chiếu source P3 a3 đã nghiệm thu; nó không build source H1 thành wheel P3. **Với checkout H1 0.5.0a2 dùng driver môi trường H1 và commands tại [bàn giao](reports/s02-phase2/2a-h1-fixes-0.5.0a2-2026-10-25/REPRODUCE.md)**: restore cùng bundle, locks nguyên byte, copy source sạch, hai rebuild, cài non-editable, collector và verifier. Không sửa hash baseline để chấp nhận version mới.

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
