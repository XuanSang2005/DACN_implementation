# Đường dẫn S02 legacy còn giữ

Code/config/tests/tools đã chuyển sang [`packages/s02/`](../packages/s02/). Thư mục này chỉ còn `.venv/` và `dist/` lịch sử; không di chuyển môi trường hoặc ghi đè wheels a1/a2 đã bàn giao. Không còn `s02/tests` để dùng như source/helpers hiện hành.

Xem [README workspace](../README.md), [hướng dẫn S02](../docs/s02/README.md). Các lệnh tuyệt đối cũ trong reports/audit giữ nguyên như bằng chứng; adapter runner chỉ đổi nơi tìm test helpers khi chạy lại audit.
