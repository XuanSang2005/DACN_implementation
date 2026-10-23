# Artifact bundles

Các descriptor JSON trong thư mục này được track; archive binary được giữ ngoài repo và chưa upload tự động. Cần nhận file đúng tên/hash từ người quản lý archive hoặc chuyển file thủ công. Không có bước tự tải hoặc resolve online.

| Bundle | Bytes nén | SHA-256 |
| --- | ---: | --- |
| `bootstrap-macos-arm64-2026-10-23.tar.gz` | 65.353.334 | `06222091b5d518e194ba9a5da28f210ae9ed66096eca4ae9ae0def1fa2c87201` |
| `evidence-2026-10-23.tar.gz` | 195.295.587 | `daabbc883bb841fd3738d18b1e82508823ab202fe56ff6108f5159f671167d01` |

Bootstrap inventory được track trong `bootstrap.inventory.json` (1.905 members). Evidence inventory có 12.893 members và giữ cạnh archive; hash inventory được pin trong `evidence-archive.json`. Mọi file/mode/symlink đều có kiểm trước restore.

[Bootstrap](../docs/BOOTSTRAP.md), [restore evidence](../docs/ARTIFACTS.md), [kết quả cleanup](../docs/GITHUB_CLEANUP_2026-10-23.md). Bản sao biên bản đã nghiệm thu và hashes nguồn ở [docs/acceptance](../docs/acceptance/); raw evidence vẫn là lịch sử bất biến.
