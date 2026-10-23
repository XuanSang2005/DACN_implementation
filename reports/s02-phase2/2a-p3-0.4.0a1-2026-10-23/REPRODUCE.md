# Tái lập vào output mới

Dùng Python 3.13.16 đã pin và wheelhouse/locks hiện hành. Không chạy campaign hardcoded lần hai: các labels/output là create-only.

Chạy script sau với hai đường dẫn **chưa tồn tại**, ngoài checkout/dataset/operational stores:

```sh
/Users/macbookpro/Documents/DACN_implementation/.runtime/python/bin/python3.13 -B \
  /Users/macbookpro/Documents/DACN_implementation/reports/s02-phase2/2a-p3-0.4.0a1-2026-10-23/reproduce.py \
  --output /private/tmp/dacn-p3-audit-new-evidence \
  --work /private/tmp/dacn-p3-audit-new-work
```

Script kiểm build-input hashes rồi tạo venv mới từ locks; build từ copy sạch; cài non-editable; chạy full S02/S01, sáu oracle P1, ba oracle P2 gốc, P2 v2 + boundaries, baselines và differential L1, rebuild/collector/pip check và hot-journal forensic copies. Cwd tests nằm ngoài source; chỉ test helpers trên sys.path. Không có tham số nhận operational store. Không gọi LLM hoặc S01 provider; các S01 calls là local fixture generation từ input synthetic.

Ba oracle P2 gốc cố ý giữ nguyên lỗi setup đã được auditor xác nhận: một case/backend thất bại khi gọi checked `heads()` sau khi xóa active selection. Campaign ghi exit 1 riêng và kiểm đúng expected status; v2 do auditor cung cấp phải pass. Không xfail/skip hoặc sửa assertion.

UUID/timestamps/files SQLite giữa các lần thực thi khác nhau. Đối chiếu semantics, table manifests, raw preservation trong từng lần và source–wheel–installed; không ép ZIP hash rebuild hoặc DB file bytes giữa hai lần độc lập bằng nhau. Cùng build phải có payload/METADATA/WHEEL bằng nhau. Biên bản này chỉ hướng dẫn tái lập; chạy lại đầy đủ script là công việc audit tiếp theo, không được tính như một lần test đã thực thi ở bàn giao này.

Hot-journal archive trong `hot-journal-{c,python}/` là bản sao forensic **sau** khi process bị kill và tool từ chối. Giữ DB cùng journal để xem bytes; không mở archive bằng SQLite rw vì sẽ recovery/mutate evidence. Manifest giữ runtime path cũ; archive không phải kho đã được di chuyển để vận hành. Muốn replay phải tạo output mới bằng script.
