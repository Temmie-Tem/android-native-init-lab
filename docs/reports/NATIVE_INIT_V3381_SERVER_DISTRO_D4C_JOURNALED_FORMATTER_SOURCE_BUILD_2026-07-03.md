# Native Init V3381 Server-Distro D4C Journaled Formatter Source Build

- Cycle: `V3381`
- Decision: `v3381-server-distro-d4c-userdata-journaled-formatter-source-build`
- Init: `A90 Linux init 0.11.138 (v3381-server-distro-journaled-formatter)`
- Boot image: `workspace/private/inputs/boot_images/boot_linux_v3381_server_distro_journaled_formatter.img`
- Boot SHA256: `c99be26deb3ca872de444e1f34ab602938a68381fe84c338bf29ead7ed9f1c4f`
- Helper SHA256: `fa395d3ecb6944a57487f3966948a634596157e4de3fdc39575a2fc502d1ceef`
- Base boot: `workspace/private/inputs/boot_images/boot_linux_v3368_hot_reload_autohud.img`

## Change

- Replaces the BusyBox ext-family formatter path with the staged e2fsprogs toolroot at `/mnt/sdext/a90/runtime/d4c-format-toolroot`.
- Verifies the SHA-256 of `mke2fs`, `dumpe2fs`, and `tune2fs`, and requires `mkfs.ext4 -> mke2fs` before any probe or format action.
- Keeps the probe non-destructive: it writes only an approved SD-runtime regular file under the toolroot, formats it through `busybox chroot ... /usr/sbin/mkfs.ext4`, runs `dumpe2fs -h`, checks ext magic, verifies the `has_journal` feature bit, unlinks the probe file, and reports `userdata_touched=0 has_journal=1`.
- Keeps the D4 command surface: `userdata-appliance-preflight`, `userdata-appliance-formatter-probe`, `userdata-appliance-format`, `userdata-appliance-populate`, and `switch-root-to-userdata`.
- All D4 commands require `SERVER-DISTRO-D4-USERDATA-APPLIANCE`; mutating commands re-derive sysfs `PARTNAME=userdata` and compare host-pinned `devname`, `dev`, and `sectors` before touching storage.
- The surface does not rely on `/dev/block/by-name/userdata`; it materializes `/dev/block/a90-userdata` from verified `MAJOR:MINOR` only after target identity passes.
- Changes the destructive format path to the same e2fsprogs `mkfs.ext4` flow, with the existing sysfs `PARTNAME=userdata` re-derivation and host-pinned `devname/dev/sectors` comparison before materializing any block node.
- Creates a private matching userdata block node inside the e2fsprogs toolroot before running chrooted `mkfs.ext4`, then verifies ext magic and `has_journal` on the real block device before reporting `format=done`.
- Populate accepts only SHA-pinned source tarballs under `/mnt/sdext/a90/runtime/`, mounts userdata at `/mnt/a90-userdata-root`, extracts the rootfs, verifies `/sbin/init`, and writes `userdata=appliance-root`.
- `switch-root-to-userdata` verifies the appliance marker, prepares/moves `/proc`, `/sys`, and `/dev`, then execs BusyBox `switch_root` so userdata Debian init becomes PID1.
- This is a D4C journaled formatter source-build/static gate. Destructive D4C format/populate still requires a live V3381 probe pass, fresh same-session preflight, and rollback readiness.

## Static Validation Contract

- Boot image strings must contain the V3381 identity, all five D4 command names, `SERVER-DISTRO-D4-USERDATA-APPLIANCE`, `A90D4`, `/sys/class/block`, `PARTNAME=`, `userdata`, `/dev/block/a90-userdata`, `/mnt/a90-userdata-root`, the e2fsprogs toolroot path, the pinned formatter hashes, and the `has_journal` markers.
- Source contract must show command table registration with `CMD_DANGEROUS` on mutating D4 commands and `CMD_DANGEROUS | CMD_NO_DONE` on `switch-root-to-userdata`.
- Live contract before destructive D4C: flash only through `native_init_flash.py`, prove candidate health, run device-side `userdata-appliance-preflight` plus the e2fsprogs `userdata-appliance-formatter-probe`, and roll back to v2321 unless the destructive D4C unit starts immediately under the same controlled plan.

## Validation

- `py_compile`: builder and V3381 test module.
- `unittest`: V3373, V3375, V3377, V3379, and V3381 D4 build/surface tests (`20` tests).
- Build: AArch64 helper/native-init compile, required-string audit, preserved-ramdisk overlay, boot image pack, and SHA256 capture.
- Device-side pre-build proof on clean v2321: chrooted `/usr/sbin/mkfs.ext4` from `/mnt/sdext/a90/runtime/d4c-format-toolroot` formatted an SD regular file, `dumpe2fs -h` reported `Filesystem features: has_journal ...`, the probe was removed, and `userdata_touched=0`.

## Metadata

- Helper flags: `-DA90_WIFI_TEST_BOOT_SERVICE_OBJECT_POST_FW_READY_FWCLASS_BRIDGE=1`
- Init extra flags: ``
- Candidate type: `server-distro-d4c-journaled-formatter`.
