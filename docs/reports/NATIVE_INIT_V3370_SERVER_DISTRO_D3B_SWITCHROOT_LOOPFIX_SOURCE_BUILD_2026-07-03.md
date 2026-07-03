# Native Init V3370 Server-Distro D3B Switchroot Loopfix Source Build

- Cycle: `V3370`
- Decision: `v3370-server-distro-d3b-switchroot-loopfix-source-build`
- Init: `A90 Linux init 0.11.131 (v3370-server-distro-switchroot-loopfix)`
- Boot image: `workspace/private/inputs/boot_images/boot_linux_v3370_server_distro_switchroot_loopfix.img`
- Boot SHA256: `df30ac45b5dbb7c8ba05f663c394e5ad31d49aab046a5128e3e663e89d33a6f2`
- Helper SHA256: `fa395d3ecb6944a57487f3966948a634596157e4de3fdc39575a2fc502d1ceef`
- Base boot: `workspace/private/inputs/boot_images/boot_linux_v3368_hot_reload_autohud.img`

## Change

- Adds the gated PID1 command `switch-root-to-distro SERVER-DISTRO-D3B-SWITCHROOT <image> <sha256>`.
- The command accepts only images under `/mnt/sdext/a90/runtime/`, rejects unpinned or mismatched SHA-256, loop-mounts the ext4 rootfs at `/mnt/sdext/a90/runtime/distro-root`, verifies `/sbin/init`, moves `/proc`, `/sys`, and `/dev`, then execs BusyBox `switch_root` so Debian sysvinit becomes PID1.
- Fixes the native loop-major parser so `/proc/devices` section headers do not stop scanning before the `loop` block-device entry.
- The command is registered as `CMD_DANGEROUS | CMD_NO_DONE`; a successful handoff intentionally has no normal serial END marker.
- This is a D3B source-build/static gate only. Live D3B still requires the amended one checked boot flash, D3 image/key staging, SSH marker observation, mandatory auto-reboot, and rollback to v2321.

## Static Validation Contract

- Boot image strings must contain the V3370 identity, `switch-root-to-distro`, `SERVER-DISTRO-D3B-SWITCHROOT`, `A90D3B`, the approved SD runtime prefix, and the `exec_switch_root_now` marker.
- Source contract must show the command table registration with `CMD_DANGEROUS | CMD_NO_DONE` and no `/data`/`userdata` write path in the D3 handoff module.
- Live contract remains: exactly one D3 candidate flash via `native_init_flash.py`, Debian `A90D3_MARKER` over NCM SSH with `/proc/1/comm=init`, mandatory auto-reboot back to the candidate, then rollback flash to v2321 with `selftest fail=0`.

## Metadata

- Helper flags: `-DA90_WIFI_TEST_BOOT_SERVICE_OBJECT_POST_FW_READY_FWCLASS_BRIDGE=1`
- Init extra flags: ``
- Candidate type: `server-distro-d3b-switchroot`.
