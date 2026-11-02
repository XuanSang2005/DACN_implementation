# I02 — provenance cleanup riêng, không thuộc nghiệm thu H3-A

Audit ghi đúng observation: hai files đổi bytes ngoài sealed release A trong lúc audit. Nguồn hiện đã xác định từ chính lượt làm việc này: người dùng yêu cầu “rà soát repo, xóa dead code, gọn trước GitHub”; implementer thêm ignore patterns cache/local env và bỏ unused `shutil` import của E1 test adapter. Lượt cleanup bị ngắt khi người dùng chuyển sang giao B. Auditor không thực hiện hai edits này.

| File | Snapshot/audit-start SHA-256 | Cleanup/current SHA-256 |
| --- | --- | --- |
| `.gitignore` | `1fb8b5c50e8482ac3a522097feca551d3d672b201fa7e37b125d979bea56eeed` | `c46f5256d589b2563885bd54013390ea8dc2da0d2e2e1e788579efdf41f57ada` |
| `packages/s02/tools/prepare_p2_tests.py` | `f1ddd980bc0c911a6ad905cd396bbe18521f008c3eaf39aa54c66220137f094b` | `9b05a6ff40b6c2a929fe8ffede563ead02a144d45162df6aab3c058bd4d89865` |

Baseline đầu B: HEAD `9a1a44e8bebccda085604dc371b91c2db33b08f1` (`feat: add H3A`), working tree sạch; hai bytes cleanup đã có trong HEAD đó. Không rewrite/split commit, rollback hoặc thay index. Audit baseline vẫn `b0d6ff26c2912c01ceea7a2d8f6a3fa163d3ce57`, không gọi hai HEAD bằng nhau.

Evidence riêng lượt cleanup: `/Users/macbookpro/.codex/.chatgpt-projects/g-p-68c38c8799f48191a101e19a975ca4f9/outputs/implementations/github-cleanup-2026-10-31/`: BEFORE, PREEXISTING.diff, STATIC_CHECKS, tooling-unittest.log, CACHE_BACKUP/CACHE_REMOVAL. Có 370 tooling unittests pass và adapter output66 files byte-equal trước/sau ở lượt ấy; đây là evidence implementer cleanup, **không auditor/H3-A/B tests mới**. 46 files cache/build/egg-info tái tạo được (516014 bytes) đã archive và verify hashes trước khi xóa; không xóa historical evidence/runtime/baseline wheels.

[Observation gốc và diff](../../../docs/acceptance/s02-2a-h3-a-0.9.0a2-2026-10-31/README.md) copy nguyên byte. Ghi nhận provenance/đối soát, **không tự đóng I02 hoặc gộp cleanup vào acceptance A**. B dùng current adapter đã đối chiếu; snapshots/oracles/release A nguyên trạng. User/auditor review cleanup riêng; không cần sửa production để xóa observation.
