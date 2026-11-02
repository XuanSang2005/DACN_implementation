# Tái lập mốc gate

Evidence root: `/Users/macbookpro/.codex/.chatgpt-projects/g-p-68c38c8799f48191a101e19a975ca4f9/outputs/implementations/s02-local-llm-gate-0.12.0a1-2026-11-02`. CPython3.13.16 GIL, SQLite3.53.1, offline locked deps. [Build/install/collector commands](/Users/macbookpro/.codex/.chatgpt-projects/g-p-68c38c8799f48191a101e19a975ca4f9/outputs/implementations/s02-local-llm-gate-0.12.0a1-2026-11-02/delivery/commands.json), [focused commands](/Users/macbookpro/.codex/.chatgpt-projects/g-p-68c38c8799f48191a101e19a975ca4f9/outputs/implementations/s02-local-llm-gate-0.12.0a1-2026-11-02/checks-round2/commands.json). Production import từ wheel installed, test helpers được copy bằng adapter P2 nguyên byte.

Seal kiểm read-only:

```sh
python3 -B /Users/macbookpro/.codex/.chatgpt-projects/g-p-68c38c8799f48191a101e19a975ca4f9/outputs/implementations/s02-local-llm-gate-0.12.0a1-2026-11-02/verify_seal.py /Users/macbookpro/.codex/.chatgpt-projects/g-p-68c38c8799f48191a101e19a975ca4f9/outputs/implementations/s02-local-llm-gate-0.12.0a1-2026-11-02
```

Để tái lập, tạo **thư mục mới** cùng parent outputs/implementations, copy `build_release.py`, `run_focused_round2.py`, `render_demo.py`, `preflight.py` từ evidence. Phải đối chiếu repo payload với snapshot `after/` trước khi chạy; scripts dùng pinned local checkout/runtime/wheelhouse/baseline paths của máy này. Không chạy đè thư mục đã seal. Nếu repo đã tiến version, dùng isolated copy đúng snapshot và điều chỉnh biến R trong bản sao harness; không rollback working tree.

Chạy tuần tự `python3 -B NEW/build_release.py`, `python3 -B NEW/run_focused_round2.py`. Dùng `NEW/delivery/candidate/bin/python -B NEW/render_demo.py` để tạo mock output và `... -B NEW/preflight.py` cho probe GET-only. Các scripts mkdir exist_ok=False; output cũ không bị ghi đè. `preflight.py` mở/dừng daemon riêng, không pull/inference; cần installed Ollama/model đang có. `render_demo.py` dùng fixtures mock được copy, không thực hiện LLM.

Không tái tạo AUDIT_READY bằng cách chạy lại harness vào evidence cũ. Seal mới cho lần kiểm mới; giữ first-run failure lịch sử. Chưa có lệnh local-analyze đang chạy được; README chỉ có probe và cấu hình đề nghị chờ LP-01.
