# Server-Distro D4C E2fsprogs Toolroot Staging

- Date: `2026-07-03`
- Decision: `server-distro-d4c-e2fsprogs-toolroot-staged`
- Device action: SD-runtime extraction and read-only verification
- Flash action: none
- Userdata action: none
- Toolroot: `/mnt/sdext/a90/runtime/d4c-format-toolroot`
- Source tarball: `/mnt/sdext/a90/runtime/a90-d4c-userdata-rootfs.tar`

## Result

The D4C destructive format remains paused after the operator filesystem-type correction. The previous
BusyBox formatter probe proved only that a filesystem with ext-family magic can be created; it did not
prove an ext4 journal. To prepare the journaled path, the staged D3 rootfs tarball was extracted on SD
runtime as a formatter toolroot and the e2fsprogs binaries were verified on-device by SHA-256.

This is a non-destructive checkpoint. It did not flash boot and did not materialize, mount, format, or
write `userdata`.

## Device Health

Resident before and after this staging checkpoint:

```text
init=A90 Linux init 0.9.285 (v2321-usb-clean-identity-rodata)
selftest=pass=11 warn=1 fail=0
runtime=sd rw=yes
storage=sd present=yes mounted=yes rw=yes
```

## Toolroot Extraction

The extraction target is intentionally under the approved SD runtime path:

```text
source_tarball=/mnt/sdext/a90/runtime/a90-d4c-userdata-rootfs.tar
toolroot=/mnt/sdext/a90/runtime/d4c-format-toolroot
rootfs_debian_version=12.14
stage_marker=/mnt/sdext/a90/runtime/d4c-format-toolroot/etc/a90-server-distro-stage
```

Device-side extraction completed successfully and printed:

```text
A90D4_TOOLROOT_READY root=/mnt/sdext/a90/runtime/d4c-format-toolroot
```

## E2fsprogs Pin

Device-side verification of the staged binaries:

```text
92721c9a402ba8015ec6321acffaac187ce32fd2772a54690b46dfe94b8f6589  /mnt/sdext/a90/runtime/d4c-format-toolroot/usr/sbin/mke2fs
6e22ed6668e336a891621de3e18b8915e56545351c20c06bafb6682ac1de9aae  /mnt/sdext/a90/runtime/d4c-format-toolroot/usr/sbin/dumpe2fs
f4bd3a7e56772236ec0dd8f6a4c5fa2b9dfa52cf70d2af0fa1eb50cfeafa34ad  /mnt/sdext/a90/runtime/d4c-format-toolroot/usr/sbin/tune2fs
mkfs.ext4 -> mke2fs
debian_version=12.14
A90D4_TOOLROOT_VERIFY root=/mnt/sdext/a90/runtime/d4c-format-toolroot stage=present
```

These hashes match the host-side D3 rootfs e2fsprogs files that were selected for the journaled D4C path.

## Safety Boundary

- No boot image was flashed.
- No `userdata-appliance-format`.
- No `userdata-appliance-populate`.
- No `switch-root-to-userdata`.
- No `/dev/block/a90-userdata` materialization.
- No mount or write to `userdata`.
- All writes in this checkpoint were limited to SD runtime under `/mnt/sdext/a90/runtime/`.

## Next

Do not enter destructive D4C with the BusyBox ext-family formatter. The next bounded unit is a new
native-init D4C e2fsprogs surface that uses this SHA-pinned toolroot to prove a journaled ext4 formatter
non-destructively, then exposes a destructive format command whose DoD verifies the actual on-disk
`has_journal` feature with `dumpe2fs`.
