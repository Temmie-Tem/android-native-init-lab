# A90 H21 post-switch-root DRM path-loss incident

Date: 2026-08-12
Target: operator-owned Samsung Galaxy A90 5G only
Tier: H0
Status: `REFUTED_HOST_ONLY_BEFORE_QUALIFICATION`

## Incident

H21 `0.11.189` corrected H20's pre-intent DRM ownership by starting the native
HUD child without a DRM/card file descriptor. Independent review then found
that this was not sufficient. The UFS handoff moves `/proc` and `/sys` into the
Debian root and creates a private minimal Debian `/dev` with no DRM node. The
surviving old-root child therefore cannot use the absolute sysfs and dev paths
required by `a90_kms_begin_frame()` when the later UFS intent arrives.

The H21 build was never qualified. It received no execution adapter, manifest,
connected D0, approval, device command, flash, reboot, or handoff. Its initial
14-file capability closure `20957cd6...9583` and 142-file native closure
`affc7266...f49` are refuted and never live-eligible.

## Disposition

- H22 is a fresh identity and retains delayed DRM acquisition.
- Before handoff, the child inherits one exact open directory descriptor for
  the single mounted `/dev` devtmpfs, not `dri`, `card0`, or a DRM device.
- The immutable UFS firstboot cleanup predicate matches descriptor targets
  containing `dri`, `card0`, or `drm`; the exact `/dev` directory target does
  not match it.
- After a valid intent, KMS opens only `dri/card0` relative to the preserved
  directory descriptor. This avoids post-switch-root sysfs lookup and does not
  add DRM nodes or expose userdata in Debian's private `/dev`.
- H22 must fail closed on mount or descriptor-scan errors and independently
  prove exact descriptor inheritance, zero pre-intent DRM/card descriptors,
  intent-before-`openat`, and live same-PID DRM ownership after presentation.

## Evidence boundary

The cleanup predicate was confirmed from the exact immutable 12,092-byte A90
UFS firstboot source already bound by SHA-256 in the public content manifest.
No private bytes, paths, credentials, device identifiers, or raw logs are
recorded here. Device, /dev, USB, network, flash, reboot, handoff, and S22+
command counts are zero.
