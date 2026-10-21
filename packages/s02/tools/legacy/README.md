# Scripts bàn giao S02 lịch sử

`run_checks.py` và `collect_evidence.py` ở đây là nguyên bytes của scripts a2 trước đổi layout. Chúng pin đường dẫn `root/s02`, package/root/report theo cấu trúc cũ; **không chạy trực tiếp trên workspace mới**. Giữ để đối chiếu bối cảnh lệnh đã chạy trong reports.

Dùng [runner hiện hành](../run_checks.py), [collector hiện hành](../collect_evidence.py) và [README workspace](../../../../README.md). Materializer hiện hành ở [../materialize_schema.py](../materialize_schema.py), chỉ check hoặc xuất file mới. Audit tests bên ngoài được runner hiện hành cung cấp helpers mới; không sửa audit để phù hợp layout.
