# A90 H23 Debian devtmpfs exposure incident

Date: 2026-08-12
Target: operator-owned Samsung Galaxy A90 5G only
Tier: H0
Status: `REFUTED_HOST_ONLY_BEFORE_LIVE_EXECUTION`

## Incident

The first H23 UFS handoff design reused the older D4 core-mount mover. When native
`/dev` was a mountpoint, that code moved the complete native devtmpfs into the
Debian root. The compiled binding nevertheless called Debian device exposure
`card0-only-no-userdata-v1`, while card0 actually belonged only to the isolated
HUD child. The binding was semantically false and the Debian parent could have
received block and userdata device nodes.

The defect was found before any H23 candidate transfer or D1 dispatch. The old
H23 capability qualification, binding v10, A/B receipt, and boot hash are
retired and never live-eligible.

## Closure

- D4 always mounts a fresh tmpfs at the new root `/dev`; it never moves native
  `/dev` into Debian.
- Only exact core character nodes plus optional `ttyGS0` are created. `devpts`
  is mandatory; preparation and cleanup fail closed.
- The persistent observer requires an unchanged exact top-level device tree,
  exact node types, rdevs and modes, zero block devices, one tmpfs `/dev`, and
  one devpts `/dev/pts` before it can publish live proof.
- Binding v11 separately states HUD `card0-only-no-userdata-v1`, Debian `/dev`
  `minimal-core-char-no-drm-no-userdata-v1`, and the remaining privileged
  `/proc/<hud-pid>/root` view as card0 plus shared public run with no block or
  userdata exposure.

## Evidence boundary

No device, `/dev`, USB, network, flash, reboot, handoff, S22+, or private
artifact contact was required to discover or repair the incident.
