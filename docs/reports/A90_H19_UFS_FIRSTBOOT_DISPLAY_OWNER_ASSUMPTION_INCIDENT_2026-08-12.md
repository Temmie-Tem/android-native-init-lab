# A90 H19 UFS firstboot display-owner assumption incident

Date: 2026-08-12
Target: operator-owned Samsung Galaxy A90 5G only
Tier: H0
Status: `REFUTED_HOST_ONLY_BEFORE_EXECUTION`

## Incident

H19 `0.11.187` disabled both the boot firstboot bind and the persistent native
HUD, then described the existing immutable UFS firstboot as the Debian display
owner. Before any H19 execution runner, approval, connected D0, flash, reboot,
or handoff existed, host-only inspection disproved that ownership assumption.

The inspected UFS firstboot source was one regular 12,092-byte file whose
SHA-256 exactly matched the public content binding
`fd8625402c76b2ee0cc4a2aff07eed3b182c6dd12eba1a022a445ea428c8c84a`.
Its split-HUD branch launches the intent producer, records the presenter owner
as `native-init`, and records the presenter as not started. It does not launch
the staged presenter from Debian. The exact UFS content manifest also binds the
intent producer and presenter binaries.

Therefore H19 could not claim Debian display ownership. With its native
presenter disabled, a successful switch-root could still expose PID 1 and SSH,
but the intended HUD/display consumer would be absent. This is a newly
discovered execution-critical hazard, so the earlier H19 `PASS_GO` is not
reusable under the repository review-lifetime rule.

## Disposition

- H19 received no device authority and is never live-eligible.
- Do not rebuild or rebind another candidate under H19's version/build/marker
  identity.
- H20 is a fresh identity. It disables only the failing boot firstboot file
  overlay while retaining observer auth, the shared HUD run binding, and the
  native HUD presenter that consumes the immutable UFS firstboot intent.
- H20 must receive a fresh independent capability review, execution binding,
  connected D0, and attended F1/D1 approvals before any device effect.
- Successful display/server ownership remains a live D1 observation, not a
  conclusion derived from this host inspection.

## Evidence boundary

The inspection opened only the exact A90 firstboot source already represented
by the public size and SHA-256 binding. No source bytes, credentials, device
identifiers, raw device logs, or private paths are recorded here. Device, /dev,
USB, network, flash, reboot, handoff, and S22+ command counts are zero.
