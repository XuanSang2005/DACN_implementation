# Tái lập — offline/non-editable

Evidence root: `/Users/macbookpro/.codex/.chatgpt-projects/g-p-68c38c8799f48191a101e19a975ca4f9/outputs/implementations/s02-2a-h3-c-0.11.0a1-2026-11-02`. Release duy nhất: `delivery/wheels/dacn_s02-0.11.0a1-py3-none-any.whl`, SHA `f73eb03f156b337638b85655beb23c5e1224bcf451d362d6b0b087489bc33706`.

`delivery/commands.json` ghi nguyên argv/cwd/exit; `delivery/BUNDLE_RECHECK.json` kiểm lại inventory bundle đã pin; `S01_PAYLOAD_BEFORE_REPLACEMENT.json` so đủ20 ZIP entries của S01 rebuild với accepted a6 trước thay wheel. `delivery/package-evidence/manifest.json` chứa import paths, dependencies, source=wheel=installed, METADATA/WHEEL/direct URL và diff baseline B a2 riêng. Không import production từ source.

Tạo venv mới bằng runtime/locks đã pin, cài wheel non-editable bằng driver mới ngoài checkout; không di chuyển venv hoặc resolve online. Driver `install_release.py --wheel <wheel SHA ở trên> --output <thư mục mới ngoài checkout>` không rebuild khi payload không đổi. P1/legacy helper venvs đến từ bootstrap offline đã pin; S02→S01 giữ nguyên.

Các argv thực đã chạy nằm trong `final-regression/commands.json` và từng runner `commands.json`:

```text
<delivery candidate python> -B packages/s02/tools/run_h3_c_checks.py --scope full --environment <delivery/environment.json> --report-dir <thư mục mới ngoài checkout>
<delivery candidate python> -B tools/run_checks.py --package s01 --report-dir <thư mục mới ngoài checkout>
<delivery candidate python> -B tools/verify_checkout.py --environment <delivery/environment.json> --output <thư mục mới ngoài checkout> --focused-only
```

Runner C giữ basetemp/DB/journals/stages/readbacks, C rồi Python tuần tự. Không dùng full verifier mặc định chạy hai backend song song. Tooling focused dùng các oracle P3 cũ nguyên byte, wrapper/layout; không gọi đó là full S02. Full regression chỉ chạy một lượt trên payload cuối.

Focused development: `build_round.py` sao source vào input mới, build/install/collector offline; `run_selected.py` kiểm installed payload trước khi chạy từng spec, C rồi Python. Mỗi output mới; bản source/test adapter và argv đã lưu theo lượt. Không chạy lại để đổi failure; mọi failure/giới hạn được phân loại riêng.

API C cần `Settings`, external `ReviewTrustContext` trước checked read và authority C riêng khi pending. Từ `inspect`, lấy exact binding cho nguyên candidate/analysis bytes; `prepare` pin T0; `resume` dùng command/receipt cùng store. Revalidate phải truyền `goal='admission'` hoặc `'retained_output'`, candidate null. Finalized report/resume không cần semantic authority/raw files nhưng vẫn cần original historical registry. Không suy trust từ DB.

`C_WORKERS.json` dẫn PID/argv/backend/phase/action/spec/DB; spec dẫn raw input files và external trust/control. `READBACK_INDEX.json` dẫn exact allocations, promotions, current/history roles và application readbacks. Đọc raw qua checked C store hoặc DB mode=ro để diagnostics; không sửa DB/registry/Answer/events.

Control recovery phụ ban đầu copy receipt sang locator mới bị chặn đúng bởi receipt_store_binding; original logs/exit giữ nguyên. `recover_failed_identity_corrected.py` copy failed DB vào output mới, dùng explicit same-command prepare tạo receipt mới cho bản sao, không rewrite receipt cũ hoặc T0. Kiểm nguyên config/raw/reserved Run/started_at, then one seal/T3/providerless replay. Đây là control corrected riêng, không ghi đè failure hoặc rerun full.

Development venv đã dùng nhiều build có cùng version candidate; đối chiếu từng lượt bằng wheel hash/copied source/collector tại thời điểm ấy. Final delivery venv mới chỉ cài release wheel SHA nêu trên. Development wheels không là release thứ hai.

Reporter của corrected recovery ban đầu lỗi exact-codec vì timer float, sau khi T3 và các assertions đã xong. Giữ exit failure/logs/script/DB; `read_recovered_identity.py` và `run_recovery_readbacks.py` chỉ đọc DB đã finalized, dùng timer integer ns. `recovery-readbacks/RESULT.json` và từng `RECOVERY.json` chứa proof mới, không retry recovery hoặc đổi counts cũ.
