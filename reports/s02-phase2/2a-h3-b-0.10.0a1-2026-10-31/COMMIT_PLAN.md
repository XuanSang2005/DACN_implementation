# Commit plan — chưa stage/commit/push

HEAD đầu B và hiện hành phải đối chiếu bằng inventory: `9a1a44e8bebccda085604dc371b91c2db33b08f1`. Baseline audit A `b0d6ff26c2912c01ceea7a2d8f6a3fa163d3ce57` là mốc khác. Không reset/rewrite/split commit cũ.

Sau auditor độc lập và quyết định người dùng, review các nhóm:

1. Docs đã có trước lượt B: acceptance H3-A a2, B-P01 proposal/handoff và navigation; giữ provenance I02 riêng. Không gộp cleanup I02 thành nghiệm thu A/B.
2. B private contracts/pure checks/registry adapter/service/AS-only store và package version 0.10.0a1. Canonical schemas/registry/DB2/A1/A2/H1/H2/S01/locks không đổi.
3. B tests/harness/runner, current guide và bàn giao này; raw artifacts ngoài checkout theo archive policy, không đưa venv/DB/generated wheels vào Git.

Review full patch cộng untracked-file diff/inventory, package source/wheel/installed, failures/limits và safety matrix trước khi chọn file stage. Snapshot/audit/handoff/evidence lịch sử không sửa. Người dùng quyết định commit và scope tiếp theo; implementer không tự commit/push hoặc ghi B đã nghiệm thu.
