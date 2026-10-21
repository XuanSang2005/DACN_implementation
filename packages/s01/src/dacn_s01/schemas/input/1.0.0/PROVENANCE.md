# Input schema 1.0.0

Copied byte-for-byte on 2026-10-13 from the reference artifact:

`/Users/macbookpro/.codex/.chatgpt-projects/g-p-68c38c8799f48191a101e19a975ca4f9/outputs/system-input-v1/system-input.schema.json`

SHA-256: `0a7cda79ac2d949579c0a2279df3d60c18b8f0cd6335e28fac6d51d46248613d`.
Dialect: JSON Schema Draft 2020-12. Not regenerated from Pydantic.
The source path records provenance only; runtime uses importlib.resources.

Supplemental profile: `docs/S01_OUTPUT_CONTRACT_PROPOSAL.md`, version
`0.1.0-draft.2`, document SHA-256
`39027bfdeeed0c880ccda35cd307eaf4d9729031bf0f80bfe8b8758b03eeb926`.
This profile fixes the 29-code-point W set for nonblank and ID boundaries,
global requirement-ID uniqueness and the other cross-field/version rules.
Schema annotations do not authorize filling optional defaults.

Phase 1 checks this artifact's integrity, duplicate keys and metaschema only.
It does not implement the W adapter, requirements validation, cross-field
rules or S01 handoff. Do not use load_schema() as proof of input validity.
All `$ref` values in this fixed artifact are local fragments; runtime does
not download the input schema or its requirement definitions.
