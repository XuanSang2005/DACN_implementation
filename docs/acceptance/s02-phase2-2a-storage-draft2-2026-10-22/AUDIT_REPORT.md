# Audit lại S02 2A storage proposal draft.2

Ngày: 22/10/2026. Phiên bản: `s02-2a-storage-plan/0.1.0-draft.2`. Phạm vi: S02-2A-01/02 và tính nhất quán của các sửa đổi, ví dụ, bằng chứng tĩnh. Không sửa repository implementation.

## Kết luận

**Đóng S02-2A-01 và S02-2A-02 ở mức thiết kế.** Không phát hiện finding chặn mới trong phạm vi audit lại. Đề xuất schema/profile/migration 2A draft.2 đạt review thiết kế trong phạm vi đã nêu, có thể dùng làm căn cứ giao implementation theo từng tiểu đợt.

Kết luận gắn với hashes trong [proposal-hashes.json](proposal-hashes.json), không phải nghiệm thu code E1/DB2 hoặc migration. A1/A2/G2 và nghiệm thu S01 a6/S02 a3 Đợt 1 giữ nguyên phạm vi trước đó. Không tự cấp quyền migration operational store hoặc triển khai toàn Đợt 2.

## S02-2A-01 — đóng ở mức thiết kế

[Proposal §6.2](/Users/macbookpro/Documents/DACN_implementation/docs/S02_PHASE2_2A_SCHEMA_MIGRATION_PROPOSAL.md:155) đã thay đường gọi public a3 verify bằng chính sách connection nguồn `mode=ro` từ lần mở đầu. Chính sách bao phủ inspect/preflight/copy/verification/resume/reconcile và helpers; cấm rw/rwc fallback, query_only sau mở rw, immutable và ATTACH mặc định có quyền ghi. Logic L1 vẫn phải kiểm đầy đủ, không rút validation xuống chỉ version/hash.

Nguồn cần recovery bị dừng trước tạo/ghi đích; DB/journal được giữ nguyên. Có phân biệt recovery-required với busy hoặc lỗi khác. Recovery nguồn là công việc riêng, sau đó inspect đầy đủ và so root đã pin trước resume. Các ca RO01–RO03 mô tả kiểm connection, hash DB/sidecars, negative DDL/hash/graph và cả hai trạng thái đích khi resume.

Đây là sửa đúng nguyên nhân đã chứng minh bởi probe a3 trước đây. [Probe lịch sử](/Users/macbookpro/.codex/.chatgpt-projects/g-p-68c38c8799f48191a101e19a975ca4f9/outputs/audits/s02-phase2-2a-storage-draft1-2026-10-21/preflight-probe.json) được kiểm hash, không chạy lại. Chưa có tool migration mới để xác minh rằng mọi source open thực sự tuân theo chính sách.

## S02-2A-02 — đóng ở mức thiết kế

[Receipt §5.1](/Users/macbookpro/Documents/DACN_implementation/docs/S02_PHASE2_2A_SCHEMA_MIGRATION_PROPOSAL.md:125) yêu cầu đầy đủ migration_id/target_store_id/activation_id trong receipt create-only, fsync và đọc lại trước effects đích. Resume lấy IDs từ receipt đã kiểm, không sinh mới hoặc lấy ID từ đích để bù receipt thiếu. Manifest sau copy giữ cùng ba IDs; activation so identity/basis/profile thông qua metadata trong [§6.3](/Users/macbookpro/Documents/DACN_implementation/docs/S02_PHASE2_2A_SCHEMA_MIGRATION_PROPOSAL.md:173).

Thiết kế đã phân biệt:

- Trước copy: receipt giữ IDs, paths, version và root nguồn đã biết; chưa có hash manifest tương lai.
- Copy commit: manifest/metadata đối chiếu receipt và hash bytes manifest; đích vẫn chưa active.
- Activation commit: trả lại đúng row khi retry cùng identity/basis/profile, giữ operator/timestamp. Identity khác hoặc basis/profile sai không được coi là replay thành công.

Source inventory root được thêm vào receipt là bổ sung phù hợp: crash trước copy vẫn có mốc nguồn bền vững để so lại. Nó không tạo vòng phụ thuộc với manifest và không cho phép đổi source head âm thầm. Giới hạn mất receipt phải đối soát thủ công được ghi rõ.

[JSON 02](/Users/macbookpro/Documents/DACN_implementation/docs/examples/s02-phase2-2a/02-readonly-preflight-and-activation-recovery.json) đã có receipt đủ fields, manifest/metadata projection, activation row và C1–C4. Kiểm độc lập xác nhận UUIDv4 canonical, equality của ba IDs, paths/version/source root, hash payload, activation basis/profile và cùng IDs khi resume. Ba negative receipts khớp kết quả kỳ vọng về thiếu/sai dạng/sai identity. Đây là kiểm assertion trên artifact minh họa; không phải validator ứng dụng đã chạy.

Quy tắc race đã đúng hơn draft.1: cùng identity có thể cùng nhận một kết quả đã commit; khác identity bị chặn theo identity manifest đã pin, không dùng thứ tự đến để chấp nhận yêu cầu sai. ID01–ID08 ghi rõ crash, ACK, receipt sai/mất, source đổi và concurrency cần kiểm khi triển khai.

## Bằng chứng độc lập

[check_documents.py](check_documents.py) tạo [document-checks.json](document-checks.json).

| Hạng mục | Kết quả |
| --- | --- |
| File được bảo vệ trong inventory | 4.634/4.634 khớp hash và kích thước |
| Artifacts hiện hành | 5/5 khớp manifest; lưu thêm hash chính manifest mới |
| Ba file sửa | Before text/hash khớp bản đã audit draft.1; after hash khớp hiện trạng |
| Sections profile/version và binding L1/E1 | Nguyên văn so với before text đã được neo bằng hash audit cũ |
| Plan/addendum/contract và 7 ví dụ cũ | 10 file nguyên hash theo inventory |
| JSON | 2 ví dụ mới/hiện hành và 7 ví dụ cũ strict parse đạt |
| Bindings / liên kết local | 8 resolve / 98 tồn tại |
| Receipt–manifest–metadata–activation | Identity và hai payload hash/length nhất quán; 4 checkpoint groups; 3 negative receipts phù hợp |
| Ca dự kiến | 23 đều đánh dấu chưa thực thi, gồm 11 ca mới |
| Source–wheel baseline | S01 16 payload, S02 14 payload khớp byte |

Đã đọc phần sửa của proposal, response, JSON và diff AGENTS/JSON 01. AGENTS chỉ cập nhật trạng thái; việc thay UUID synthetic và kỳ vọng recovery/race trong JSON 01 phù hợp hai findings. Manifest lịch sử và probe audit cũ nằm trong inventory được bảo vệ.

Inventory có các exclusions được khai báo, không đại diện toàn filesystem hoặc dataset. Manifest example là identity projection có lược inventory/resources/DDL; hash minh họa không chứng minh DB thực đã copy. Schema E1 và DDL2 chưa tồn tại để validate.

Không import production modules, mở DB, chạy probe lại, application tests, migration, build/install, LLM hoặc renderer trong audit này. Không coi kiểm tĩnh là bằng chứng durability/fsync, race, recovery hoặc chống mất điện thực.

## Bước tiếp theo đề nghị

Không cần thêm vòng sửa tài liệu cho S02-2A-01/02. Có thể giao **2A-P1 — profiles và validators** trước: materialize E1/schema/registry, giữ L1 nguyên byte, truyền owner profile tường minh và kiểm A1/A2 cấp thấp với fixtures canonical, differential L1, hai codec backends và source–wheel–installed. Cập nhật trạng thái AGENTS dựa trên biên bản này trong lượt triển khai được giao.

P1 chưa bao gồm DB2 persistence, migration hoặc activation runtime; P2/P3 có phạm vi và audit riêng. Các assertions, tests và bằng chứng trong proposal vẫn là nghĩa vụ bàn giao khi code được triển khai, không phải kết quả đã đạt. G3/G4 và quyền live tiếp tục ngoài phạm vi.
