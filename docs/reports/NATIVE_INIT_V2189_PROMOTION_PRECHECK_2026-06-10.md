# Native Init V2189 Promotion Precheck

## Summary

- Candidate: `v2189-security-p0-stage-fix`
- Init: `A90 Linux init 0.9.261 (v2189-security-p0-stage-fix)`
- Boot SHA256:
  `a7332612199cfd275f2dfc6fdb25843af401a1ecef2fa54ac0f52afe705f1ffe`
- Current promoted baseline before this precheck:
  `v2187-screenapp-ui-validation`
- Decision: `v2189-promotion-precheck-pass`
- Result: PASS
- Scope: pre-promotion evidence review only. This report does not by itself
  promote the baseline.

## Inputs

- Live validation:
  `docs/reports/NATIVE_INIT_V2189_SECURITY_P0_STAGE_FIX_LIVE_VALIDATION_2026-06-10.md`
- Fresh local security rescan:
  `docs/security/scans/SECURITY_FRESH_SCAN_V2189_2026-06-10.md`
- Architecture review:
  `docs/reports/NATIVE_INIT_ARCHITECTURE_REVIEW_2026-06-10.md`
- Current TODO/risk register:
  `docs/plans/NATIVE_INIT_CURRENT_TODO_2026-06-08.md`

## Security Gate

- Fresh local rescan result: PASS `10`, WARN `1`, FAIL `0`.
- New implementation blocker from local scan: `0`.
- Remaining warning: accepted trusted-lab local root-control boundary
  (`F021/F030`) for USB ACM, localhost bridge, and USB-local NCM tcpctl.
- V2189 live validation closed the V2188 staged Wi-Fi executable ownership gap:
  `supplicant.root_exec_ok=1`, root-owned `/cache/a90-wifi`, root-owned
  standalone supplicant bundle, and `selftest fail=0`.
- Flash identity gate is covered by caller-pinned `--expect-sha256`, sealed
  local copy, remote SHA check, boot partition readback SHA, and version check.

## Architecture Debt Disposition

The architecture review is valid as a cleanup map, but it is not a promotion
blocker for V2189.

| Item | Disposition | Reason |
| --- | --- | --- |
| `A90_WIFI_TEST_BOOT` research block in `v724/90_main.inc.c` | Defer as post-promotion source cleanup | Active builders do not define `-DA90_WIFI_TEST_BOOT`; the block is source readability debt, not current V2189 binary behavior. |
| Active no-op modem/QRTR/SSCTL boot calls | Defer with focused audit | These are low-surface default no-ops guarded by flags/state. Removing them now risks changing a validated Wi-Fi baseline without promotion value. |
| Builder monkeypatch/import tower | Defer as build-system refactor | It is a maintainability risk, but V2189 reproducibility currently depends on the existing chain. Refactor after the security baseline is promoted. |
| Stale `a90_config.h` default version/build strings | Defer as documentation/build hygiene | Build-time `-DINIT_VERSION`/`-DINIT_BUILD` override is verified; the stale defaults are confusing but not runtime behavior. |
| Dead `v319/90_main.inc.c` | Defer as low-risk cleanup | It is not included by the active init source, but deleting/moving it should be a separate reviewable cleanup commit. |

## Promotion Readiness

Cleared before promotion:

- V2189 source build exists and records the candidate SHA.
- V2189 live validation passed flash/readback/selftest/version checks.
- V2189 runtime P0 checks passed after staged artifact hardening.
- V2189 Wi-Fi smoke reached carrier and `wpa_state=COMPLETED`.
- Fresh local security rescan has no implementation blocker.
- Architecture P0 is reclassified as post-promotion cleanup debt, not a current
  runtime/security blocker.

Still required to actually promote:

1. Write a V2190 or next-run baseline promotion report for the V2189 artifact.
2. Update baseline pointers in runbooks/TODO/versioning docs from V2187 to the
   promoted V2189 tag and SHA.
3. Keep rollback image and emergency rollback image explicit.
4. Preserve the accepted-risk statement that bridge/tcpctl/rshell must stay
   USB-local/localhost-only unless a new auth/threat model is designed.

## Decision

`v2189-security-p0-stage-fix` is eligible for baseline promotion from a
security and architecture-disposition standpoint. The next step is the explicit
promotion documentation/update commit; do not silently replace the current
baseline pointer.
