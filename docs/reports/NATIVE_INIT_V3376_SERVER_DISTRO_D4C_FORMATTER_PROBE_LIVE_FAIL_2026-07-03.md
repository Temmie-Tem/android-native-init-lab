# Native Init V3376 Server-Distro D4C Formatter Probe Live Fail

- Cycle: `V3376`
- Decision: `v3375-server-distro-d4c-formatter-probe-live-failed`
- Candidate tested: `A90 Linux init 0.11.135 (v3375-server-distro-userdata-formatter-probe)`
- Candidate boot image: `workspace/private/inputs/boot_images/boot_linux_v3375_server_distro_userdata_formatter_probe.img`
- Candidate SHA256: `460fbbc137478695c9271a80fd9e0e5dedb96975ee9e69bd6b67c9a72db1ecdb`
- Flash path: `native_init_flash.py`
- Final rollback: v2321 clean

## Result

V3375 booted cleanly and the read-only D4 preflight passed, but the non-destructive formatter probe failed.
D4C format/populate remains blocked until the formatter command surface is fixed and re-proven.

## Flash And Candidate Health

The exact V3375 artifact was flashed through the checked helper.

```text
local_sha256=460fbbc137478695c9271a80fd9e0e5dedb96975ee9e69bd6b67c9a72db1ecdb
remote_sha256=460fbbc137478695c9271a80fd9e0e5dedb96975ee9e69bd6b67c9a72db1ecdb
boot_readback_sha256=460fbbc137478695c9271a80fd9e0e5dedb96975ee9e69bd6b67c9a72db1ecdb
candidate_version=A90 Linux init 0.11.135 (v3375-server-distro-userdata-formatter-probe)
candidate_status_selftest=pass=12 warn=1 fail=0
candidate_selftest=pass=12 warn=1 fail=0
```

The device-side read-only D4 preflight passed:

```text
A90D4 preflight target.source=partname-scan
target.devname=sda33
target.sysname=sda33
target.dev=259:17
target.sectors=231577432
target.size_bytes=118567645184
target.ro=0
target.mounted=0
target.node=/dev/block/a90-userdata
target.node_exists=0
target.byname_exists=0
target.byname_matches=0
A90D4 preflight=ok format_allowed=0 node_materialized=0
```

## Failure

The formatter probe created only an SD-runtime regular file, then failed before any `userdata` action:

```text
cmd=userdata-appliance-formatter-probe SERVER-DISTRO-D4-USERDATA-APPLIANCE \
  /mnt/sdext/a90/runtime/a90-d4c-formatter-probe.img 16777216

A90D4 formatter-probe=file-created path=/mnt/sdext/a90/runtime/a90-d4c-formatter-probe.img size_bytes=16777216
A90D4 formatter-probe=begin formatter=busybox-mke2fs-ext4 path=/mnt/sdext/a90/runtime/a90-d4c-formatter-probe.img size_bytes=16777216
mke2fs: invalid option -- 't'
Usage: mke2fs [-Fn] [-b BLK_SIZE] [-i INODE_RATIO] [-I INODE_SIZE] [-m RESERVED_PERCENT] [-L LABEL] BLOCKDEV [KBYTES]
A90D4 formatter-probe=fail stage=mke2fs rc=1
A90P1 END ... rc=-5 errno=5 ... status=error
```

Root cause: device BusyBox `mke2fs` does not support `-t ext4`. The current D4B/D4C formatter command
surface uses `busybox mke2fs -t ext4 -F ...`, so destructive D4C would fail if allowed to proceed.

## Non-Destructive Follow-Up Probe

Before rollback, a same-session SD regular-file syntax probe confirmed the supported BusyBox syntax:

```text
dd if=/dev/zero of=/mnt/sdext/a90/runtime/a90-d4c-mke2fs-syntax-probe.img bs=1M count=16
/bin/busybox mke2fs -F -L A90D4PROBE /mnt/sdext/a90/runtime/a90-d4c-mke2fs-syntax-probe.img 16384
superblock_magic=53 ef
A90D4_SYNTAX_PROBE_OK
```

A loop-mount probe failed because loop setup was unavailable in this boot context:

```text
losetup: -f: No such file or directory
mount: losetup failed 1
```

This does not prove the actual block-partition mount path either way; D4C still needs a corrected
formatter-probe command and live proof before any `userdata` format.

The SD probe files were then removed:

```text
A90D4_PROBE_CLEANUP_OK
```

## Rollback

The device was rolled back through `native_init_flash.py` to v2321.

```text
rollback_local_sha256=ca978551aabe4b39563abaf529ccf2522054952d8b2ad852e632d26da88168cb
rollback_remote_sha256=ca978551aabe4b39563abaf529ccf2522054952d8b2ad852e632d26da88168cb
rollback_boot_readback_sha256=ca978551aabe4b39563abaf529ccf2522054952d8b2ad852e632d26da88168cb
final_version=A90 Linux init 0.9.285 (v2321-usb-clean-identity-rodata)
final_status_selftest=pass=11 warn=1 fail=0
final_selftest=pass=11 warn=1 fail=0
```

One normal-input `selftest` capture was interrupted by serial `ATATAT` noise after printing
`fail=0`; the final `--input-mode slow` selftest completed with a valid `A90P1 END`.

## Safety Boundary

- No `userdata-appliance-format`.
- No `userdata-appliance-populate`.
- No `switch-root-to-userdata`.
- No `/dev/block/a90-userdata` materialization.
- No mount or write to `userdata`.
- Only SD-runtime temporary regular files were created and removed.

## Next

Build a new D4C formatter-fix candidate. The native-init formatter surface should stop using
`mke2fs -t ext4` for BusyBox and should prove the corrected command non-destructively on an SD-runtime
regular file before D4C format/populate can resume.
