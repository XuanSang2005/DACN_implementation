# Tái lập H2-B — offline, tuần tự

Dùng source snapshot/diff và **wheel duy nhất được chỉ định trong START_HERE**. CPython 3.13.16 có GIL, SQLite 3.53.1, macOS arm64. Mọi output/venv phải mới và ngoài checkout/dataset; không di chuyển venv, import production source, cài editable hoặc resolve online.

Driver `reproduce_environment.py` trong evidence root nhận:

```sh
python3 -B /path/to/reproduce_environment.py \
  --checkout /path/to/checkout \
  --bundle /path/to/bootstrap-macos-arm64-2026-10-23.tar.gz \
  --output /outside-checkout/h2b-env-NEW \
  --expected-wheel /path/to/dacn_s02-0.6.0a2-py3-none-any.whl
```

Bundle SHA-256 `06222091b5d518e194ba9a5da28f210ae9ed66096eca4ae9ae0def1fa2c87201`. Trên máy đã restore, có thể bỏ `--bundle`: driver kiểm lại toàn inventory đã pin trước khi dùng runtime/wheelhouse; không coi việc file có sẵn là proof. Giữ locks nguyên byte. Wheel baseline H2-A phải có SHA-256 `d4e824d66c3066c29d63792d60116c6e8596d96593037bc15f97ff5470ee08e2`.

Driver tạo candidate/P1/legacy venv từ locks, build/rebuild copied-source tuần tự, so toàn ZIP entries. Chỉ thay wheel S01 rebuild cùng version sau khi chứng minh toàn payload/METADATA/WHEEL/RECORD bằng a6; lưu log thay wheel và direct URL. S02 a2 khác version là baseline diff, không ép equality với H2-B. Lane `tools/bootstrap.py` accepted-only giữ nguyên.

Bản phát hành dùng `final-environment-v3`; các môi trường trước là iterations có log riêng, không là wheel bàn giao. `final_checks.py` cài chính ZIP ở `final/wheels`, chạy collector/pip check, pure H2 oracles, full S02/S01, wrappers/layout, P1/P2/P3/H1, original harness diagnostics, differential L1 và demo CLI. C rồi Python tuần tự; mỗi lúc một suite/build nặng. Các đường dẫn local trong drivers là provenance; copy/adapt root/output mới khi tái lập, không chạy vào evidence cũ.

Full S02 dùng **nguyên E1 adapter** `prepare_p2_tests.py`. Runner ngoài checkout chỉ đổi capture stdout thành tee để theo dõi tiến độ; cùng pytest argv, conftest, assertions, timeout và thứ tự backend. `final/full-s02/runner-stream-only.diff` và `runner-hashes.json` ghi đúng delta; root tooling và oracle không đổi. Có thể dùng runner gốc để tái lập:

```sh
/path/to/env/candidate/bin/python -B packages/s02/tools/run_p2_checks.py \
  --baseline-python /path/to/env/p1/bin/python \
  --baseline-helpers /path/to/checkout/.bootstrap/p1-helpers \
  --legacy-python /path/to/env/legacy/bin/python \
  --report-dir /outside-checkout/full-s02-NEW
```

Không chạy `tools/verify_checkout.py` mặc định vì lane đó parallel full S02. Raw suite S02 không thay E1 adapter. Test helpers có thể vào sys.path; production packages luôn từ installed wheels.

Sau full suite, `boundary_checks.py` chạy riêng ba release-boundary cases (Model/revalidation CAS và hot-journal recovery) trên cùng installed wheel, C rồi Python. Chúng được thêm sau snapshot full đầu tiên, nên JUnit supplement được báo riêng. Khi tái lập từ final source, full suite mới sẽ thu thập cả supplement; không dùng số đếm snapshot cũ làm expected cho checkout mới.

Lượt `final_checks.py` đã hoàn tất full/oracles nhưng dừng ở differential vì bản copy input thiếu `canonical-fixtures/l1-root.json`. Giữ nguyên lượt lỗi. `finish_release.py` tiếp tục tuần tự bằng `differential_checks_v2.py`, demo và supplement. Khi tái lập differential, copy nguyên byte cả `differential_l1.py` lẫn `canonical-fixtures/l1-root.json` theo nguồn/hash trong `final/differential-l1-v2/INPUTS.json` vào thư mục output mới; không sửa oracle. Hai oracle P2 gốc review-contract/persistence được chạy bổ sung bằng `p2_original_controls.py` khi đối soát danh sách với audit trước; giữ outputs riêng. Bốn lane dùng installed legacy/candidate × C/Python; `COMPARISON.json` lưu kết quả và encoder counts.

`demo_cli.py` chạy source S01 synthetic và bốn mock qua CLI thật, giữ raw/approvals/receipts/DB/output/encoder evidence tại `final/demo-cli`. Không dùng thư mục demo làm operational state. Finalized progress và replay không cần provider; muốn semantic command mới cần current tuple/raw/approval mới.

Giữ nguyên hai oracle gốc có lỗi harness đã biết và raw failures; corrected limits oracle là bản erratum của auditor. [TEST_RESULTS](TEST_RESULTS.md) ghi riêng các failure/iterations. Đối chiếu seal và marker đặt sau seal trước khi audit; marker không tự thay việc rehash source/wheel/evidence hoặc quyết định nghiệm thu.
