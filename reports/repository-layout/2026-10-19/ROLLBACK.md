# Hoàn tác layout mà không ghi đè công việc mới

**Đây là hướng dẫn, chưa thực thi rollback.** Không dùng Git reset (workspace không có Git), không chạy một vòng `mv`/copy mù. Nếu đã có người sửa code sau bàn giao, dừng để đối chiếu và chuyển các sửa đó cùng file, không phục hồi bytes cũ lên chúng.

## Chuẩn bị

1. Dừng tiến trình build/test đang ghi trong checkout; không cần chạy hoặc sửa DB evidence. Sao lưu workspace hiện tại vào vị trí mới do người thực hiện chọn. Giữ nguyên thư mục báo cáo layout này và mọi công việc mới.
2. Đọc [path-mapping.json](path-mapping.json), [preservation.json](preservation.json), [content-changes.patch](content-changes.patch), [inventory sau](inventory-after.json). So hash hiện tại của **từng file sẽ đụng tới** với `after_layout_sha256` hoặc `sha256` trong inventory sau. Xem cả file mới nằm trong `packages/` hoặc `tools/` mà inventory sau chưa biết. Hash khác, đường dẫn đích đã có nội dung lạ, symlink hoặc files mới ⇒ dừng, không ghi đè.
3. Bản trước của file thực sự chỉnh text nằm trong `originals/`, hash gốc ở inventory-before. Chỉ dùng khi current hash vẫn bằng bản layout đã bàn giao; không dùng nó để “sửa” code vừa thay về sau. Các bản này là evidence, không phải cấu hình authoritative hiện hành.

## Thứ tự phục hồi có điều kiện

- Chuyển riêng root `pyproject.toml` workspace hiện tại và tooling/README mới sang một thư mục backup mới, **sau khi** so hash; không xóa. Như vậy đích `pyproject.toml` cũ mới trống để nhận `packages/s01/pyproject.toml`.
- Đảo mapping của **tất cả files đã di chuyển**, kiểm trước đích không tồn tại (ngoại lệ root pyproject vừa được backup). Di chuyển source/tests/package config/locks nguyên bytes về old paths. Không đảo những artifacts mới không có trong mapping.
- Với test tìm docs và materializer đã sửa, có thể phục hồi phần chỉnh đường dẫn/tooling bằng `originals/` chỉ khi hash chưa thay đổi. Không đảo production semantics; production bytes không hề thay trong lượt layout.
- Scripts S01 trong `packages/s01/tools/legacy/` quay về root `tools/`; hai scripts S02 legacy quay về `s02/tools/`; materializer quay về `s02/tools/`. Backup wrappers/workspace tools mới trước, tránh nhầm chúng với scripts lịch sử cùng basename.
- `tools/requirements-tools.lock` quay về root theo mapping. Khôi phục AGENTS/.gitignore từ originals **chỉ khi** current hash khớp bản layout và người thực hiện đã lưu bản mới; nếu có sửa tiếp thì merge hẹp phần layout.
- README/mục lục mới nên được giữ trong backup hoặc sửa trạng thái để chỉ đúng layout đã quay về; không sửa/xóa tài liệu lịch sử. Không xóa thư mục còn file mới. Chỉ `rmdir` thư mục rỗng.

Venv `.venv`, `s02/.venv`, runtime, wheelhouse, `dist`, `s02/dist`, docs cũ, reports cũ và audit ngoài chưa di chuyển nên **không cần restore/replace**. Không rollback DB hoặc nâng/hạ product version. Năm thư mục cache/build/egg-info đã xóa là tái tạo được; 30 file build payload đã được đối chiếu với historical wheels trong [removed-build-payload-proof.json](removed-build-payload-proof.json). Không cần phục hồi cache để chạy sản phẩm.

Sau rollback, đối chiếu các files quay về với `before_sha256`, kiểm lại full inventories và chạy kiểm chứng trong thư mục kết quả **mới**. Nếu có công việc mới phải giữ, expected hashes cần một inventory mới có giải thích; không sửa báo cáo layout này để làm khớp. Hướng dẫn không bảo đảm hoàn tác tự động mọi công việc phát sinh về sau.
