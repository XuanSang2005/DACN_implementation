# Evidence, tracking và restore

Cleanup GitHub chỉ đổi docs/tooling/tracking. Production payload, schemas, tests và locks giữ nguyên. Reports Markdown dùng tra cứu tiếp tục ở Git; nội dung/trạng thái lịch sử giữ nguyên. Các file sinh tự động (logs/JUnit/DB/wheels/JSON inventories), copied snapshots `before`/`originals` và `STATIC_CHECKS*.json` được archive trước khi bỏ tracking. `.gitignore` chặn đưa lại artifacts vào commit thường.

Archive evidence: `evidence-2026-10-23.tar.gz`, **12.893 members**, **2.267.394.570 bytes** file gốc, **195.295.587 bytes** nén. Gồm toàn bộ reports trước cleanup, năm STATIC_CHECKS và bản sao audit/findings/acceptance P3 a3. Không gồm toàn bộ external audit execution, venv/cache hoặc `.git`; những bản gốc vẫn giữ tại vị trí cũ. Không truy cập dataset hoặc operational stores để archive.

[Descriptor](../artifacts/evidence-archive.json) pin SHA-256 archive và inventory. Inventory `evidence-2026-10-23.inventory.json` nằm cạnh archive. Bundle/bootstrap có [descriptor riêng](../artifacts/bootstrap-bundle.json), không cần restore 2 GB evidence để chạy tests. Nhận các file đúng hash từ người giữ archive; chưa upload tự động lên dịch vụ nào.

```sh
python3 -B tools/restore_evidence.py \
  --archive /path/to/evidence-2026-10-23.tar.gz \
  --output /path/outside-checkout/evidence-restore-NEW
```

Tool kiểm toàn archive/inventory/member hashes trước effects. Đồ thị symlink được resolve từng thành phần: mở rộng target trước khi xét `..`, theo mọi chuỗi link, từ chối thoát root, target absolute/không hợp dạng, vòng lặp hoặc quá 40 lần mở rộng trên mỗi path. Chấp nhận target nội bộ chưa tồn tại, alias runtime cùng thư mục và `..` còn nằm trong root. Tên inventory được so bảo thủ theo Unicode NFD/casefold; leaves trùng alias hoặc member có file/symlink làm parent bị từ chối. Restore kiểm lại cùng đồ thị trước mkdir, có xét symlink sẵn trong đích; không chỉ tin target text. Phản ví dụ `a -> .`, `b -> a/../outside` bị từ chối trước khi có output, còn `b -> a/inside` hợp lệ. Giới hạn preflight: caller quản lý cây đích local ổn định trong lúc restore; chưa chứng minh chống tiến trình khác đổi cây đồng thời. Tool từ chối path traversal, hardlinks, symlink thoát root và overwrite. Restore trả `reports/`, các generated JSON tại `docs/...` và `external/p3-a3/`. Ưu tiên đọc bản restore ngoài checkout; không restore đè lên công việc mới hoặc dùng DB bằng chứng làm state vận hành. File gốc trong checkout hiện tại vẫn tồn tại sau `git rm --cached`.

`RESTORE.md`, `before.json`, `untrack.paths` NUL-delimited và `index.before` được giữ cùng archive. Muốn rollback tracking trước commit, kiểm đúng file/inventory rồi chạy `git add -f --pathspec-from-file=<archive-root>/untrack.paths --pathspec-file-nul`; không chép đè index cũ nếu đã có công việc mới. Git history/objects cũ không bị rewrite hay compact. Dung lượng giảm được báo cho **tree/checkout commit tiếp theo**, không phải dung lượng `.git` cũ hoặc evidence local đã giữ lại.
