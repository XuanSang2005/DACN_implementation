# S02 Đợt 1 — bản sửa 0.1.0a3

Ngày bàn giao: **21/10/2026**. **Đã sửa, chờ audit**; không tự đóng S02-05/LAYOUT-01, chưa nghiệm thu S02 Đợt 1 hoặc bắt đầu Đợt 2. S01 giữ `0.1.0a6`; S02 `0.1.0a3`, contract `s02/0.1.0-draft.3`, DB structure không đổi.

## Căn cứ và khác biệt baseline

Đã đọc AGENTS/README, contract draft.3 §4.3 và kế hoạch T0–T3, [audit S02 a2](</Users/macbookpro/.codex/.chatgpt-projects/g-p-68c38c8799f48191a101e19a975ca4f9/outputs/audits/s02-phase1-0.1.0a2-2026-10-19/AUDIT_REPORT.md>) và [audit layout](</Users/macbookpro/.codex/.chatgpt-projects/g-p-68c38c8799f48191a101e19a975ca4f9/outputs/audits/repository-layout-2026-10-19/AUDIT_REPORT.md>). S02-01–04 đã đóng trên a2; không suy thành nghiệm thu a3.

Sản phẩm lúc bắt đầu đúng a6/a2. **LAYOUT-01 đã được implement trong lượt trước**, sau audit layout: wrappers dùng `fixed_package`, parser không đăng ký selector và tắt abbreviation. Hash các file đó khớp manifest [bản sửa trước](../../repository-layout/fixes-LAYOUT-01-2026-10-19/IMPLEMENTATION_REPORT.md). Giữ nguyên công việc này, không áp lại patch cũ. Lượt này chạy lại kiểm thử và tách bằng chứng tooling khỏi logic S02. Yêu cầu được tiếp tục sau gián đoạn; baseline/hash đầu lượt vẫn giữ nguyên trong [baseline.json](baseline.json), không thay bằng inventory mới để che thay đổi.

## S02-05 — config của Run trước dispatch

`check_attempts()` trước đây trả về khi chưa dispatch, nên bỏ qua config thuộc Run. Bản sửa tách kiểm pin thành helper nội bộ và gọi cho `Run.config_artifact_id` **trước** nhánh đó. Prompt/request/response và metadata của Attempt vẫn được kiểm khi có dispatch; chưa dispatch vẫn bắt buộc `attempts=[]`.

- Staged config: lấy identity Artifact từ promotion map của đúng StageRef ở prepared; Run phải trỏ đúng identity đó. Kiểm repository hiện có tiếp tục đối chiếu raw bytes, purpose/media type, producer Run và promotion manifest trong cùng T3.
- Reused config: Run phải dùng đúng ID prepared đã pin, giữ producer cũ. Artifact khác cùng purpose hoặc cùng bytes vẫn bị từ chối.
- Pin trong `operation.request`, nếu có, vẫn được đối chiếu với Run. Khi prepared cũng có pin thì cả hai phải đồng ý qua cùng Run. Không có config ở prepared thì giữ hành vi request-only trước đây; không tự yêu cầu config staged cho mọi command.
- Không đổi schema/DDL/contract, không tạo Attempt giả. Interrupted/failed trước dispatch hợp lệ vẫn finalize được. Invariants cũ `attempt_prepared_config`, `attempt_input_pin_inventory`, `run_intent_config`, `promotion_exact_bytes` được giữ.

[Diff S02](changes-s02.patch) chỉ đổi `events.py`, `__init__.py` và version pyproject. [Regression mới](regressions.patch) thêm **28 ca**: staged/reused/request-only, interrupted/failed, identity khác dù bytes bằng nhau, request pin mâu thuẫn, thiếu promotion/bytes sai, rollback publication, checked reads và dispatched positive controls.

Oracle rollback dùng `sqlite3.iterdump()` độc lập trước/sau để so toàn kho, thêm lookup Run/AnalysisSet/head ở connection mới; không chỉ nhìn exception. Ca publication đã có M1/AS1 rồi thử AS2 với config sai: T3 bị từ chối, AS2/Run/artifacts/promotions không lọt ra, head giữ nguyên. Checked-read dùng **DB tạm synthetic**, chỉ bypass operational validator lúc dựng lịch sử lỗi rồi khôi phục trước `verify/get_command/get_record`; cả ba từ chối PERSISTENCE_FAILED mà không sửa kho. Không đụng DB audit gốc. [Bằng chứng các invariants](config-pin-evidence.json) được trích từ output test thật, có hash SQL trước/sau.

## LAYOUT-01 và collector — hai phạm vi tooling riêng

**Wrappers:** bản sửa đã có giữ nguyên. Package truyền bằng tham số Python nội bộ; parser wrapper không có selector. Các dạng tách token, dấu bằng và mọi tiền tố `--p`…`--package`, ở trước/sau required args, với s01/s02/all đều bị từ chối trước tạo report/chạy suite. [Diff LAYOUT-01 đã giữ](layout01-retained.patch) đối chiếu với wrappers/tooling trước sửa; không coi đây là thay đổi mới của production a3. 339 tests stdlib về wrappers được chạy lại; lệnh bình thường của cả runner/collector thực sự chạy đúng package. Workspace collector được chạy riêng với s01, s02, all.

**Collector cho version mới:** [diff riêng](changes-collector.patch). Bắt buộc source a3 = installed a3 = wheel a3, đủ inventory/hash, METADATA/WHEEL, version và direct URL non-editable. Baseline a2 được chọn rõ qua `--baseline-wheel s02=PATH`; ghi đủ before/after hashes và unified diff, không ép a3 bằng a2. Cùng version vẫn bắt buộc bằng baseline; thiếu baseline không tự bỏ so sánh. Thêm 5 unit tests synthetic wheel, cùng probes thực từ chối wheel hiện hành sai, baseline cùng version sai và thiếu baseline. Đây là phần mở rộng thu bằng chứng phiên bản, không đổi semantics S02.

## Build, môi trường và payload

Venv mới từ CPython **3.13.16 có GIL**, SQLite **3.53.1**, S02 dev lock nguyên bản; cài offline từ wheelhouse và wheel S01 a6 lịch sử. Build S02 trên bản sao **đúng bytes** của src/pyproject và builder vào thư mục tạm ngoài checkout: [provenance](build-input-provenance.json). Không đổi build caches/source/env legacy. [Lệnh môi trường/build](environment-commands.json), [build logs](builds/commands.json), [bước cài wheel trực tiếp và collector](packaging-commands.json) giữ argv/cwd/exit.

Wheel mới: [dacn_s02-0.1.0a3-py3-none-any.whl](builds/dacn_s02-0.1.0a3-py3-none-any.whl), SHA-256 `0b9df6bd99e63efb25786aaf3bea58b0da7678d066fae20a2e01e90c8d97d1cf`. Wheel S01 trong `builds/` là **bản sao byte-identical wheel a6 lịch sử**, không phải rebuild hoặc release S01 mới. `pip check` đạt; không nâng dependencies.

[Manifest](package-verification/manifest.json) xác nhận đủ **14 S02 + 16 S01 files**, source = installed = wheel. S01 còn bằng historical a6. [Diff wheel a2 → a3](package-verification/s02-baseline.diff) chỉ có `events.py`, `__init__.py` và Version trong METADATA; WHEEL/schema/DDL/CLI/namespace/dependency S02 → S01 giữ nguyên. Diff khác version là bằng chứng cho audit xem, không tự chứng nhận thay đổi đã duyệt.

## Kiểm thử, lỗi phát hiện khi chuẩn bị và giới hạn

[TEST_RESULTS.md](TEST_RESULTS.md) ghi các suite đã chạy, exit codes và số liệu; [REPRODUCE.md](REPRODUCE.md) chỉ cách cài wheel và chạy ngoài checkout. Toàn suite S01/S02 trên C/Python giữ instrumentation, concurrency/CAS/lock/kill/recovery cũ; không gộp hai conftest. Hai file audit ngoài chạy nguyên bản, chỉ thêm đường dẫn helpers, không sửa assertions/skip/xfail.

Hai lỗi chuẩn bị được giữ log, không xóa hoặc trình bày thành pass:

1. [Targeted lần đầu](targeted-config.log): 7 failed, 21 passed vì fixture mới dùng `Error.stage="processing"` ngoài enum. Sửa **fixture** thành `schema`, không đổi kỳ vọng hoặc code sản phẩm. Bản fixture trước sửa trong `development/`; [lần chạy sau](targeted-config-corrected.log) đạt 28/28.
2. [Collector S01 lần đầu](s01-collector.log): fail vì uv cài wheel từ lock không sinh `direct_url.json`. Giữ guard provenance; dùng pip cài trực tiếp **cùng wheel a6 nguyên byte**, `--no-deps --force-reinstall`, rồi collector đạt. Không thay dependency/version hoặc bỏ kiểm.

[Preservation](preservation.json) đối chiếu hash đầu/cuối: tám file sửa đã kê khai, **7.598 file/symlink entries workspace còn lại và 10.577 file nguồn/audit bên ngoài được liệt kê không đổi**, gồm báo cáo/wheels lịch sử. Hai file tests mới nằm ngoài inventory đầu lượt, có trong patch/manifest; không sửa tests/audit cũ. [Diff hướng dẫn](changes-docs.patch) chỉ cập nhật phạm vi/version/trạng thái/chạy collector. [Artifact manifest](artifact-manifest.json) giữ hashes bàn giao. Không tuyên bố kiểm toàn filesystem/dataset.

Chưa chạy LLM/renderer, full clarification orchestration, semantic evaluation, S03 hoặc mất điện/disk-full; fault injection/kill synthetic không thay bằng chứng ấy. Chưa thực hiện migration/repair lịch sử sai; checked read từ chối thay vì sửa âm thầm. Agent audit cần review pin identity/bytes trước dispatch, rollback/checked-read, collector khác version và các logs mới; người dùng/audit quyết định đóng finding.

**Đã sửa S02-05 và LAYOUT-01, bàn giao S02 0.1.0a3 để audit lại; chưa nghiệm thu S02 Đợt 1 và chưa bắt đầu Đợt 2.**
