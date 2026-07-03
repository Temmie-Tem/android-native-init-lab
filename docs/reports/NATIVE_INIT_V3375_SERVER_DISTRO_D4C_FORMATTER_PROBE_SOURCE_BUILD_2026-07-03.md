# Native Init V3375 Server-Distro D4C Formatter Probe Source Build

- Cycle: `V3375`
- Decision: `v3375-server-distro-d4c-userdata-formatter-probe-source-build`
- Init: `A90 Linux init 0.11.135 (v3375-server-distro-userdata-formatter-probe)`
- Boot image: `workspace/private/inputs/boot_images/boot_linux_v3375_server_distro_userdata_formatter_probe.img`
- Boot SHA256: `460fbbc137478695c9271a80fd9e0e5dedb96975ee9e69bd6b67c9a72db1ecdb`
- Helper SHA256: `fa395d3ecb6944a57487f3966948a634596157e4de3fdc39575a2fc502d1ceef`
- Base boot: `workspace/private/inputs/boot_images/boot_linux_v3368_hot_reload_autohud.img`

## Change

- Adds `userdata-appliance-formatter-probe`, a non-destructive D4C entry probe that writes only an approved SD-runtime regular file, formats it with the same BusyBox `mke2fs -t ext4` path, checks the ext4 superblock magic, unlinks the probe file, and reports `userdata_touched=0`.
- Keeps the D4B command surface: `userdata-appliance-preflight`, `userdata-appliance-format`, `userdata-appliance-populate`, and `switch-root-to-userdata`.
- All D4 commands require `SERVER-DISTRO-D4-USERDATA-APPLIANCE`; mutating commands re-derive sysfs `PARTNAME=userdata` and compare host-pinned `devname`, `dev`, and `sectors` before touching storage.
- The surface does not rely on `/dev/block/by-name/userdata`; it materializes `/dev/block/a90-userdata` from verified `MAJOR:MINOR` only after target identity passes.
- The format path is deliberately explicit as `busybox mke2fs -t ext4 -F -L A90D4ROOT`; D4C remains gated on proving that formatter path on-device.
- Populate accepts only SHA-pinned source tarballs under `/mnt/sdext/a90/runtime/`, mounts userdata at `/mnt/a90-userdata-root`, extracts the rootfs, verifies `/sbin/init`, and writes `userdata=appliance-root`.
- `switch-root-to-userdata` verifies the appliance marker, prepares/moves `/proc`, `/sys`, and `/dev`, then execs BusyBox `switch_root` so userdata Debian init becomes PID1.
- This is a D4C entry-prep source-build/static gate. D4C format/populate still requires live formatter-probe pass, rootfs tarball staging, fresh same-session preflight, and rollback readiness.

## Static Validation Contract

- Boot image strings must contain the V3375 identity, all five D4 command names, `SERVER-DISTRO-D4-USERDATA-APPLIANCE`, `A90D4`, `/sys/class/block`, `PARTNAME=`, `userdata`, `/dev/block/a90-userdata`, `/mnt/a90-userdata-root`, and the formatter-probe/format/populate/switch markers.
- Source contract must show command table registration with `CMD_DANGEROUS` on mutating D4 commands and `CMD_DANGEROUS | CMD_NO_DONE` on `switch-root-to-userdata`.
- Live contract before destructive D4C: flash only through `native_init_flash.py`, prove candidate health, run device-side `userdata-appliance-preflight` plus `userdata-appliance-formatter-probe`, and roll back to v2321 unless the destructive D4C unit starts immediately under the same controlled plan.

## Metadata

- Helper flags: `-DA90_WIFI_TEST_BOOT_SERVICE_OBJECT_POST_FW_READY_FWCLASS_BRIDGE=1`
- Init extra flags: ``
- Candidate type: `server-distro-d4c-formatter-probe`.
