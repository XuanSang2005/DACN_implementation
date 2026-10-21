# Scripts bàn giao S01 lịch sử

Các `run_phase*_checks.py` / `collect_phase*_evidence.py` được chuyển nguyên bytes từ root `tools/`. Chúng pin layout cũ, report directory và baseline của từng đợt; **không chạy trực tiếp trên layout mới** và không coi là runner hiện hành. Muốn tái lập một đợt cũ, dựng bản sao layout cũ trong workspace tạm theo mapping/bằng chứng, không sửa reports gốc.

Lệnh hiện hành: [workspace README](../../../../README.md), [run_checks.py](../run_checks.py), [collect_evidence.py](../collect_evidence.py). Runtime/wheelhouse/venv/wheels lịch sử giữ nguyên vị trí; scripts này không được tự chỉnh report cũ để chạy được.
