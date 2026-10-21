# Tổ chức lại workspace DACN — 19/10/2026

Phạm vi: layout/tooling/hướng dẫn vận hành; không sửa production source, schema resources, dependencies, contract, DB structure hoặc S02-05. S01 `0.1.0a6`; S02 `0.1.0a2`, draft.3. Không tăng version sản phẩm và chưa mở S02 Đợt 2.

## Baseline và inventory đầu lượt

Đã đọc AGENTS, hai pyproject, locks, runner/collector, hướng dẫn CLI/tái lập và [audit S02 a2](/Users/macbookpro/.codex/.chatgpt-projects/g-p-68c38c8799f48191a101e19a975ca4f9/outputs/audits/s02-phase1-0.1.0a2-2026-10-19/AUDIT_REPORT.md). Trạng thái chuẩn: S01 đã nghiệm thu kỹ thuật CLI local; S02 chưa nghiệm thu Đợt 1, S02-01–04 closed, S02-05 còn mở. Không có khác biệt source/wheel với baseline trước di chuyển.

[inventory-before.json](inventory-before.json) ghi **8.264 entries workspace** (có cả directories/symlinks), category/type/size/mode/hash/target; **6.751 files ngoài workspace** được chụp hash để bảo vệ nguồn và audit liên quan. Con số có runtime/env/artifacts, không phải số file code hoặc tuyên bố kiểm toàn dataset. [baseline-status.json](baseline-status.json) giữ nguồn xác nhận/trạng thái. `git status --short` trả 128, “not a git repository”; không init/reset Git.

## Thay đổi layout

- Root source/tests/config S01 chuyển về `packages/s01/`; S02 source/tests/config chuyển từ `s02/` về `packages/s02/`. Namespaces/distributions/CLI/dependency S02 → S01 giữ nguyên.
- **97 file di chuyển** có hash trước/sau thao tác rename bằng nhau trong [path-mapping.json](path-mapping.json). Sau di chuyển chỉ sửa nội dung các tests/tooling được nêu ở diff; production/resources/locks không sửa.
- Root pyproject là TOML workspace `[tool.dacn-workspace]`, không còn `[project]`/`[build-system]`. AGENTS giữ thiết kế và bổ sung layout, trạng thái audit, cách chạy. Root guard S02 vẫn dựa AGENTS + pyproject.
- `requirements-tools.lock` chuyển nguyên bytes sang `tools/requirements-tools.lock`, một bản authoritative bootstrap uv; runtime/wheelhouse giữ nguyên. Không thêm manager, common package, Docker hoặc orchestration framework.
- 12 scripts S01 `run_phase*`/`collect_phase*` và hai scripts S02 bàn giao cũ chuyển nguyên bytes vào `packages/<stage>/tools/legacy/`, có README cảnh báo không chạy trên layout mới. Không chỉnh chúng để ghi lại báo cáo cũ.
- Tooling hiện hành cấp workspace build/check/collect; entry points package là wrappers cố định package. Runner tách process/package/backend và cwd tạm ngoài checkout. Report/build output phải là **thư mục chưa tồn tại**. Không thêm production src vào PYTHONPATH.
- `test_contract_artifacts.py` chỉ đổi `parents[2]` thành `parents[3]` để tìm workspace docs. Materializer vẫn dùng package root, bổ sung check read-only / output create-only. Không sửa assertions, skip/xfail hoặc kỳ vọng test cũ.
- [removed-generated.json](removed-generated.json): chỉ xóa năm thư mục build/egg-info/pytest cache đã nhận diện có thể tái tạo và không chứa wheel/report/DB bàn giao. Các build caches mới có thể sinh lại dưới package; không dùng chúng làm source/bằng chứng.

[Tree trước](tree-before.txt), [tree sau](tree-after.txt), [bảng old→new](PATH_MAPPING.md), [mapping có hashes](path-mapping.json) và [diff nội dung](content-changes.patch) được lưu riêng. `originals/` chỉ giữ bản trước của những file text có thể cần diff/hoàn tác; đây là evidence, không phải bản cấu hình authoritative thứ hai. Root pyproject trong diff là sự thay thế cấu hình workspace; pyproject S01 cũ vẫn nguyên bytes tại package.

## Đường dẫn legacy còn giữ

| Vị trí | Lý do |
| --- | --- |
| `.runtime/`, `.tools/` | Runtime/uv/wheelhouse/download artifacts đã pin; không đổi |
| `.venv/`, `s02/.venv/` | Môi trường non-editable cũ, không di chuyển venv hoặc sửa shebang; kiểm lượt mới dùng venv khác |
| `dist/`, `s02/dist/` | Wheels a1…a6 S01, a1/a2 S02 đã bàn giao; nguyên vị trí/bytes |
| `docs/*` trước đợt này, `reports/*` trước đợt này | Lịch sử bất biến, links/commands cũ giữ đúng bối cảnh. README mới hướng dẫn layout mới |
| Audit bên ngoài repo | Không sửa/move assertions, logs, DB hoặc venv audit |

Không tạo symlink alias `s02/tests` hoặc `src` để che đường dẫn cũ. Audit adapter thêm **chỉ** `packages/s02/tests` vào sys.path và load instrumentation conftest; file audit vẫn chạy từ đường dẫn gốc, hash trước/sau giữ nguyên.

## Build, môi trường và kiểm chứng

Build hai package từ layout mới trong venv sạch từ lock S02; vì lock pin hash ZIP S01 lịch sử, bootstrap dùng `dist/dacn_s01-0.1.0a6...whl`. Sau khi [đối chiếu payload trước install](build-comparison-before-install.json) bằng nhau, cài lại **chỉ hai product wheels rebuild** với `--no-deps --force-reinstall` vào chính venv sạch. Không sửa lock để thêm hash ZIP mới. METADATA/WHEEL và package payload giống lịch sử; ZIP hashes có thể khác. [environment.json](environment.json), [build commands](builds/commands.json), [install commands](install-commands.json), [manifest](package-verification/manifest.json) ghi exact argv/cwd/exit/import/dependencies.

Full suite [commands](suites/commands.json): **S01 986 passed/backend, S02 189 passed/backend**, không skipped/errors/failures. Hai conftest được chạy process riêng, instrumentation thật còn hoạt động; logs/JUnit và events ở `suites/`. Các lịch cạnh tranh/CAS/real lock/kill/recovery thuộc suite cũ chạy lại, không thay bằng mock hoặc tuần tự.

Audit [commands](independent-audits/commands.json): file a1 nguyên bản **7 passed/backend**; file followup a2 **2 passed, 2 failed/backend**. Hai failures vẫn là S02-05 config mismatch khi không dispatch, không phải regression layout; runner giữ exit **1**, không sửa assertions/skip/xfail. DB synthetic của audit chạy lại được archive riêng dưới `independent-audits/` trước dọn vùng tạm.

Manifest xác nhận đủ **16 S01 + 14 S02 files**: source = rebuilt wheel = installed = historical wheel, inventory cũng bằng nhau, imports từ site-packages, không editable. S01/S02 versions không đổi, dependencies/DB schema/resources không đổi. [Kết quả chi tiết](TEST_RESULTS.md) và [summary máy đọc](execution-summary.json) phân biệt suite đạt với S02-05 còn failed.

[CLI/guard/docs checks](layout-checks/checks.json) thực chạy **18 lệnh**: S01 init/submit/lookup → S02 init/start/lookup/context, sáu guard cases cho workspace và hai package (exact root + descendant mới), materializer và bốn ca từ chối ghi đè output. Guard từ chối bằng API path check và CLI exit 3, không tạo DB/state tại các đích bị cấm. **15 JSON examples**, **33 S02 Record shapes**, **85 links** trong hướng dẫn resolve/parse được; không gọi shape check là xác nhận đầy đủ ngữ nghĩa hoặc toàn graph.

## Bảo toàn và các file thực sự sửa nội dung

[preservation.json](preservation.json) đối chiếu toàn bộ entries file/symlink trước theo vị trí mới: **95 moved unchanged**, **7.240 unchanged**, **4 authorized content edits**, **45 files generated đã dọn**, **0 thay đổi ngoài dự kiến**. Hai trong 97 file di chuyển được sửa hẹp sau rename: `test_contract_artifacts.py` và materializer. Bốn content edits của files gốc là hai file đó, AGENTS và `.gitignore`; root pyproject cũ được bảo toàn ở package, root pyproject workspace là file thay thế mới đã diff riêng.

Trong tập bảo toàn có **30 production source/resources**, **7 dependency locks/inputs**, **8 wheels lịch sử**, **24 tài liệu/examples cũ**, **238 report/evidence files cũ**, toàn bộ runtime/tool artifacts và venvs cũ. **6.751 files ngoài repo được liệt kê** giữ hash. Không suy những số này thành kiểm toàn filesystem/dataset. 30 files trong build directories đã dọn đều khớp payload của historical wheels: [bằng chứng](removed-build-payload-proof.json); còn lại là metadata egg-info/cache tái tạo được.

AGENTS chỉ thêm section layout/quy trình/trạng thái audit; đã kiểm bỏ section mới thì text thiết kế trước đó khớp nguyên bản. `.gitignore` thêm `.venvs/`. Phần tooling mới gồm bốn workspace tools, hai wrappers mỗi package; files legacy giữ bytes. README mới là mục lục/hướng dẫn, không thay contract hoặc rewrite trạng thái lịch sử. [Inventory sau](inventory-after.json) ghi cả files mới/generated với phân loại; [artifact manifest](artifact-manifest.json) giữ hashes của handoff và phạm vi tự loại trừ rõ ràng.

## Hoàn tác và giới hạn

[ROLLBACK.md](ROLLBACK.md) hướng dẫn hoàn tác có kiểm hash: không chạy `mv`/restore mù, không reset Git, không ghi đè code mới hoặc report hiện có. **Chưa thực thi rollback.** Venv/wheels/report/audit gốc chưa di chuyển nên không cần restore chúng. Build caches đã xóa là tái tạo được, không phải dữ liệu cần khôi phục. [REPRODUCE.md](REPRODUCE.md) chỉ cách chạy lại trong môi trường và thư mục kết quả mới.

Chỉ kiểm layout/tooling và hồi quy trên baseline local. Không sửa S02-05, không kiểm LLM/renderer/semantic quality/full clarification/review/S03; không tự nghiệm thu S02. Các kết quả synthetic và lỗi đã biết phải được đọc riêng với audit độc lập về nghiệp vụ.

**Đã tổ chức lại, chờ audit.** S02-05 còn mở; chưa nghiệm thu S02 Đợt 1 và chưa bắt đầu Đợt 2.
