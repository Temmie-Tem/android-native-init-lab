# Server-Distro D4C Rootfs Tarball Staging Live

- Date: `2026-07-03`
- Decision: `server-distro-d4c-rootfs-tarball-staged`
- Device action: SD-runtime file staging only
- Flash action: none
- Userdata action: none
- Runner: `workspace/public/src/scripts/server-distro/prepare_d4c_userdata_rootfs_tarball.py`
- Private run dir: `workspace/private/runs/server-distro/d4c-rootfs-tarball-20260703T121035Z`

## Result

The D4C rootfs tarball was created from the clean D3 sysvinit rootfs source, staged under SD runtime,
and SHA-verified on-device.

```text
rootfs=workspace/private/builds/server-distro/d3-sysvinit-usrmerge-20260703T101657Z-rootfs
debian_version=12.14
stage=etc/a90-server-distro-stage
tarball=workspace/private/runs/server-distro/d4c-rootfs-tarball-20260703T121035Z/a90-d4c-userdata-rootfs.tar
tarball_size_bytes=268349440
tarball_sha256=0875b8bd6e58298f644735e5d7ee12c0286e3057a7744b05064fc34829412603
remote_tarball=/mnt/sdext/a90/runtime/a90-d4c-userdata-rootfs.tar
remote_sha256=0875b8bd6e58298f644735e5d7ee12c0286e3057a7744b05064fc34829412603
staged_this_run=true
flash_performed=false
userdata_touched=false
```

## Device Health

Baseline resident before staging:

```text
A90 Linux init 0.9.285 (v2321-usb-clean-identity-rodata)
selftest: pass=11 warn=1 fail=0
```

Final resident after staging:

```text
A90 Linux init 0.9.285 (v2321-usb-clean-identity-rodata)
selftest: pass=11 warn=1 fail=0
```

## Transfer Evidence

The runner created a deterministic tar stream with root ownership metadata, verified required entries,
uploaded through the existing SD/NCM path, checked the temporary-file SHA, then atomically moved the file
into place.

Relevant private-run facts:

```text
tar_required_entries_present=[
  ./etc/a90-server-distro-stage,
  ./etc/debian_version,
  ./etc/inittab,
  ./sbin,
  ./usr/sbin/init
]
tar_entry_count=8604
device_receive=/mnt/sdext/a90/runtime/.a90-d4c-userdata-rootfs.tar.tmp.*
device_dd=268349440 bytes copied, 9.153 s, 28 M/s
remote_sha_after=0875b8bd6e58298f644735e5d7ee12c0286e3057a7744b05064fc34829412603
```

## Safety Boundary

This unit did not enter destructive D4C:

- no boot flash;
- no `userdata-appliance-format`;
- no `userdata-appliance-populate`;
- no `switch-root-to-userdata`;
- no formatter execution;
- no mount or write to `userdata`.

## Next Gate

The next bounded live prep is V3375 formatter proof:

1. Confirm rollback/TWRP preconditions.
2. Flash exact V3375 through `native_init_flash.py`.
3. Verify candidate `version`, `status`, and `selftest fail=0`.
4. Run read-only `userdata-appliance-preflight`.
5. Run `userdata-appliance-formatter-probe` against an SD-runtime regular file only.
6. Roll back to v2321 unless destructive D4C format starts immediately under the D4 runbook.

D4C format/populate remains disallowed until the formatter-probe live pass is reported.
