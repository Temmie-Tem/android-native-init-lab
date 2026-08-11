# A90 H22 preserved-dev-dir proc capability incident

Date: 2026-08-12
Target: operator-owned Samsung Galaxy A90 5G only
Tier: H0
Status: `REFUTED_HOST_ONLY_BEFORE_QUALIFICATION`

## Incident

H22 `0.11.190` replaced H21's lost absolute DRM paths with an inherited open
directory descriptor for the mounted native `/dev` devtmpfs. It also changed
the pre-intent DRM scan to propagate errors rather than treating them as zero.

Independent review found the directory descriptor itself is an unacceptable
capability. After `/proc` moves into Debian, root can duplicate and traverse it
through `/proc/<hud-pid>/fd/<n>`, reaching arbitrary native devtmpfs entries,
including block and userdata nodes that Debian's private minimal `/dev`
deliberately excludes. Closing it after card0 opens would only shorten the
exposure window; it would not remove the pre-intent violation.

H22 was never qualified. It received no execution adapter, manifest, connected
D0, approval, device command, flash, reboot, or handoff. All H22 closures and
private builds are refuted and never live-eligible.

## Disposition

- H23 is a fresh identity and preserves no native `/dev` directory descriptor.
- The HUD child enters a private mount namespace and a minimal tmpfs root that
  bind-mounts only the exact card0 node and shared HUD intent/status directory.
- The child `pivot_root`s into that root and detaches the complete old root
  before reporting ready. Its namespace and `/proc/<pid>/root` therefore expose
  only `card0` and shared HUD state, never native `/dev`, block, or userdata.
- Card0 remains unopened until a valid intent is parsed; all process-FD scans
  and minimal-root validations fail closed.

## Evidence boundary

No private bytes, paths, credentials, device identifiers, or raw logs are
recorded here. Device, /dev, USB, network, flash, reboot, handoff, and S22+
command counts are zero.
