# A90 H12 finalizer prepublication partial host incident

Date: 2026-08-10
Target: Samsung Galaxy A90 5G only
Classification: H0 host-only incident; no device effect

## Incident

The run07 finalizer copied the selected candidate and rollback into the private
run directory, wrote `host-preparation.json`, and wrote
`prepared-manifest.json` before its final local-closure verification rejected
the then-current staging adapter. The command therefore failed after publishing
a partial host preparation bundle.

No F1 approval receipt or candidate intent existed. No rootfs transfer, boot
partition transfer, flash, reboot, or other device write occurred. The partial
run07 bundle grants no live authority and is not eligible for retry or reuse.

## Cause

The finalizer validated the fully assembled orchestrator closure only after its
exclusive output writes. Earlier checks did not independently execute the
finalizer, staging adapter, and F1 orchestrator source-contract validators
before copying artifacts. A staging self-contract defect could therefore be
detected too late to keep the run directory output-free.

## Containment and correction

- The run07 partial bundle remains preserved under `workspace/private/`; it is
  neither overwritten nor treated as a prepared campaign.
- The successor uses a fresh H13 candidate identity, fresh state paths, fresh
  run08 rootfs identity, and a fresh run directory. H12 is not rebound.
- The finalizer now executes all three source-contract validators before the
  first candidate or rollback copy and fails closed on any issue.
- The existing post-publication orchestrator verification remains in place as
  defense in depth.
- Focused tests inject a staging source-contract failure and prove rejection,
  while the finalizer source self-check requires the prepublication gate to
  occur after candidate selection and before the first artifact copy.

## Safety judgment

This incident did not cross the device boundary. Its hazard was ambiguous host
candidate preparation caused by non-atomic publication order. Fresh H13
identity plus the new prepublication gate removes reuse ambiguity and blocks
the observed failure class before new private preparation artifacts are
published. Independent review is required before H13 finalization or live use.
