# Security Documentation

This directory tracks Codex Cloud security findings, local triage, patch plans,
patch reports, and local rescan evidence for the A90 native init project.

## Current Status

- Imported findings through `F056` have no remaining actionable implementation
  blocker.
- `F021` and `F030` remain `accepted-lab-boundary`: USB ACM and the localhost
  serial bridge are intentional local rescue/control channels.
- Latest imported batch: `F054-F056`, mitigated in host tooling.
- Latest live validation for that batch is recorded in
  `batches/SECURITY_FINDINGS_F054_F056_PATCH_REPORT_2026-05-12.md`.
- Latest local active-workspace promotion-supporting scan:
  `scans/SECURITY_FRESH_SCAN_V2189_2026-06-10.md` with PASS `10`, WARN `1`,
  FAIL `0`; the remaining warning is the accepted trusted-lab local
  root-control boundary.

## Directory Map

- `findings/`: one file per Codex Cloud finding plus the canonical `FNNN`
  index.
- `batches/`: analysis, patch plans, relationship notes, and reports for
  grouped finding batches.
- `overviews/`: cross-cutting exposure map, original fix queue, relationship
  analysis, and closure review.
- `scans/`: raw Codex Cloud CSV exports and local `SECURITY_FRESH_SCAN_*`
  reports.
- `incoming/`: scratch area for newly pasted findings before triage.
- `templates/`: reusable finding-detail templates.

## Workflow

1. Put new Cloud CSV or pasted details under `scans/` or `incoming/`.
2. Split new findings into `findings/FNNN-*.md`.
3. Update `findings/README.md` with severity, status, title, and paths.
4. Write batch analysis and patch plan under `batches/`.
5. Patch code or docs, then write the batch report under `batches/`.
6. Run local checks and place any fresh scan output under `scans/`.

Do not add new security files directly under `docs/security/`; put them in the
appropriate subdirectory.
