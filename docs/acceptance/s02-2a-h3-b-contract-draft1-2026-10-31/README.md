# B-P01 — thiết kế được chấp thuận, implementation chưa nghiệm thu

Người dùng chấp thuận B-P01 ngày31/10 theo [quyết định](DECISION.json), sau [audit thiết kế](AUDIT_REPORT.md). [Sources/hashes](SOURCES.json) pin bản sao nguyên byte; các link evidence trong bản audit resolve tại original root, không sửa bản copy. G1–G3 bắt buộc trước writer, G4/S1–S6 trước handoff implementation. Không nhận ba diagnostics/backend trên A a2 là B pass.

[API/version/checker B đang triển khai](../../S02_2A_H3_B_IMPLEMENTATION.md). Chỉ H3-B, chưa C/D/CLI/live. H3-A a2 giữ acceptance pure/local/synthetic; I02 review riêng.
