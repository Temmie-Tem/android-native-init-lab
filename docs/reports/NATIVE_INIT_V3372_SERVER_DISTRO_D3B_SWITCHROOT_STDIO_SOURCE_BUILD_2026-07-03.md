# Native Init V3372 Server-Distro D3B Switchroot Stdio Source Build

- Cycle: `V3372`
- Decision: `v3372-server-distro-d3b-switchroot-stdio-source-build`
- Init: `A90 Linux init 0.11.133 (v3372-server-distro-switchroot-stdio)`
- Boot image: `workspace/private/inputs/boot_images/boot_linux_v3372_server_distro_switchroot_stdio.img`
- Boot SHA256: `09db071ae6bebe538d0f9c6c62f6e86b28a4b1a2a6954f1910f8d189675cc653`
- Helper SHA256: `fa395d3ecb6944a57487f3966948a634596157e4de3fdc39575a2fc502d1ceef`
- Base boot: `workspace/private/inputs/boot_images/boot_linux_v3368_hot_reload_autohud.img`

## Change

- Adds the gated PID1 command `switch-root-to-distro SERVER-DISTRO-D3B-SWITCHROOT <image> <sha256>`.
- The command accepts only images under `/mnt/sdext/a90/runtime/`, rejects unpinned or mismatched SHA-256, loop-mounts the ext4 rootfs at `/mnt/sdext/a90/runtime/distro-root`, verifies `/sbin/init`, moves `/proc` and `/sys`, prepares `/dev` nodes when host `/dev` is not a mountpoint, then execs BusyBox `switch_root` so Debian sysvinit becomes PID1.
- Keeps the V3370 loop-major parser fix and V3371 `/dev` preparation for the A90 native rootfs, where `/dev` is a plain rootfs directory rather than a movable mount.
- Removes BusyBox `switch_root -c /dev/console`; the A90 boot uses `console=null`, and live V3371 proved `/dev/console` opens with `ENODEV`. V3372 reuses inherited PID1 stdio instead.
- Adds failure cleanup that unmounts the D3 rootfs before detaching the loop device on pre-handoff failures.
- The command is registered as `CMD_DANGEROUS | CMD_NO_DONE`; a successful handoff intentionally has no normal serial END marker.
- This is a D3B source-build/static gate only. Live D3B still requires the amended one checked boot flash, D3 image/key staging, SSH marker observation, mandatory auto-reboot, and rollback to v2321.

## Static Validation Contract

- Boot image strings must contain the V3372 identity, `switch-root-to-distro`, `SERVER-DISTRO-D3B-SWITCHROOT`, `A90D3B`, the approved SD runtime prefix, and the `exec_switch_root_now` / `console=reuse-stdio` markers.
- Source contract must show the command table registration with `CMD_DANGEROUS | CMD_NO_DONE` and no `/data`/`userdata` write path in the D3 handoff module.
- Live contract remains: exactly one D3 candidate flash via `native_init_flash.py`, Debian `A90D3_MARKER` over NCM SSH with `/proc/1/comm=init`, mandatory auto-reboot back to the candidate, then rollback flash to v2321 with `selftest fail=0`.

## Metadata

- Helper flags: `-DA90_WIFI_TEST_BOOT_SERVICE_OBJECT_POST_FW_READY_FWCLASS_BRIDGE=1`
- Init extra flags: ``
- Candidate type: `server-distro-d3b-switchroot`.
