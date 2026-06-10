# Security Scan Inputs And Outputs

This directory stores raw Codex Cloud CSV exports and local rescan reports.

## Raw Cloud Exports

- `codex-security-findings-2026-05-05T16-26-57.929Z.csv`: initial import.
- `codex-security-findings-2026-05-07T20-00-44.982Z.csv`: longsoak follow-up.
- `codex-security-findings-2026-05-08T18-39-05.112Z.csv`: mixed-soak follow-up.
- `codex-security-findings-2026-05-11T07-54-55.648Z.csv`: post-v184 follow-up.
- `codex-security-findings-2026-05-11T19-48-19.047Z.csv`: post-v200 follow-up.
- `codex-security-findings-2026-05-12T08-30-30.417Z.csv`: F054-F056 follow-up.
- `codex-security-findings-2026-05-20T23-13-29.481Z.csv`: later Codex Cloud
  export retained as raw input; use batch/fresh-scan reports for repository
  disposition.

## Local Rescans

`SECURITY_FRESH_SCAN_*` files are local targeted scans. They are evidence
snapshots, not the canonical finding index. Canonical status stays in
`../findings/README.md`.

- Latest local active-workspace promotion-supporting scan:
  `SECURITY_FRESH_SCAN_V2189_2026-06-10.md`.
