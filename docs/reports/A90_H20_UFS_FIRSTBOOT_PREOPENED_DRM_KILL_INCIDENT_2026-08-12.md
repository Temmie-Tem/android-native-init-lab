# A90 H20 UFS firstboot preopened-DRM kill incident

Date: 2026-08-12
Target: operator-owned Samsung Galaxy A90 5G only
Tier: H0
Status: `REFUTED_HOST_ONLY_BEFORE_EXECUTION`

## Incident

H20 `0.11.188` retained the native HUD child and disabled only the boot
firstboot file overlay. Its native HUD child preopened DRM before `switch_root`
and survived with `/init` as its executable identity. The H20 capability assumed
that this child would later consume the intent written by the exact immutable
UFS firstboot.

Before any H20 execution manifest, connected D0, approval, flash, reboot, or
handoff, deeper host-only inspection of the same regular 12,092-byte UFS
firstboot source disproved that assumption. Before producing the HUD intent, it
enumerates non-PID1 processes whose executable is `/init` and kills each one
that owns a DRM/card file descriptor. The H20 presenter exactly matches that
predicate. The UFS firstboot would therefore kill the H20 presenter, then write
an intent while starting no replacement presenter.

This is a new execution-critical hazard. H20's earlier `PASS_GO` cannot be
reused, and H20 is never live-eligible.

## Disposition

- H20 received no execution manifest, D0, approval, device command, flash,
  reboot, or handoff.
- The unqualified H20 execution-adapter working files were removed; no durable
  device or approval evidence was removed.
- H21 is a fresh identity. Its native HUD child must start without a DRM file
  descriptor, survive the UFS firstboot cleanup scan, and acquire DRM only after
  a valid UFS intent arrives.
- H21 review and live observation must bind the same HUD PID to the status PID,
  exact intent path, native owner, process model, positive consumed sequence,
  successful presentation, and a live DRM file descriptor.
- Display and persistent-server success remain D1 observations.

## Evidence boundary

The inspection opened only the exact A90 UFS firstboot source already bound by
size and SHA-256 in the public content manifest. No source bytes, credentials,
device identifiers, raw device logs, or private paths are recorded here.
Device, /dev, USB, network, flash, reboot, handoff, and S22+ command counts are
zero.
