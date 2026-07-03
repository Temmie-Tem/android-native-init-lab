# Native Init V3380 Server-Distro D4C Formatter Argv Fix Live Pass

- Cycle: `V3380`
- Decision: `v3379-server-distro-d4c-formatter-argv-fix-live-pass`
- Candidate tested: `A90 Linux init 0.11.137 (v3379-server-distro-userdata-formatter-argv-fix)`
- Candidate boot image: `workspace/private/inputs/boot_images/boot_linux_v3379_server_distro_userdata_formatter_argv_fix.img`
- Candidate SHA256: `a58c07bca01c74ba97653a7cd3d3681788674fa8a6eb912a4fe64a84fb42112e`
- Flash path: `native_init_flash.py`
- Final rollback: v2321 clean

## Result

V3379 passed the D4C formatter entry live proof:

- exact candidate flash through the checked helper;
- candidate boot health passed;
- read-only `userdata-appliance-preflight` passed;
- non-destructive SD regular-file `userdata-appliance-formatter-probe` passed;
- probe file cleanup succeeded inside the command;
- rollback to v2321 completed with final `status` selftest fail=0.

D4C format/populate has not yet run.

## Flash And Candidate Health

```text
local_sha256=a58c07bca01c74ba97653a7cd3d3681788674fa8a6eb912a4fe64a84fb42112e
remote_sha256=a58c07bca01c74ba97653a7cd3d3681788674fa8a6eb912a4fe64a84fb42112e
boot_readback_sha256=a58c07bca01c74ba97653a7cd3d3681788674fa8a6eb912a4fe64a84fb42112e
candidate_version=A90 Linux init 0.11.137 (v3379-server-distro-userdata-formatter-argv-fix)
candidate_status_selftest=pass=12 warn=1 fail=0
```

## Read-Only Preflight

The first preflight attempt was corrupted by serial/menu noise after printing a partial success line. It
was not used as evidence. The slow-input retry completed with a valid `A90P1 END`:

```text
A90D4 preflight target.source=partname-scan
target.devname=sda33
target.sysname=sda33
target.dev=259:36
target.sectors=231577432
target.size_bytes=118567645184
target.ro=0
target.mounted=0
target.node=/dev/block/a90-userdata
target.node_exists=0
target.byname_exists=0
target.byname_matches=0
A90D4 preflight=ok format_allowed=0 node_materialized=0
rc=0 status=ok
```

## Formatter Probe

The non-destructive formatter probe used only an approved SD-runtime regular file:

```text
A90D4 formatter-probe=file-created path=/mnt/sdext/a90/runtime/a90-d4c-formatter-probe.img size_bytes=16777216
A90D4 formatter-probe=begin formatter=busybox-mke2fs path=/mnt/sdext/a90/runtime/a90-d4c-formatter-probe.img size_bytes=16777216 kbytes=16384
Filesystem label=A90D4PROBE
Block size=1024
4096 inodes, 16384 blocks
A90D4 formatter-probe=ext4-magic-ok magic=53ef offset=1080
A90D4 formatter-probe=done formatter=busybox-mke2fs path=/mnt/sdext/a90/runtime/a90-d4c-formatter-probe.img cleanup=ok userdata_touched=0
rc=0 status=ok
```

This closes the formatter assumption that blocked D4C after V3375/V3377. It proves the native-init
formatter-probe command path, not the destructive userdata format itself.

## Rollback

The device was rolled back through `native_init_flash.py` to v2321.

```text
rollback_local_sha256=ca978551aabe4b39563abaf529ccf2522054952d8b2ad852e632d26da88168cb
rollback_remote_sha256=ca978551aabe4b39563abaf529ccf2522054952d8b2ad852e632d26da88168cb
rollback_boot_readback_sha256=ca978551aabe4b39563abaf529ccf2522054952d8b2ad852e632d26da88168cb
final_version=A90 Linux init 0.9.285 (v2321-usb-clean-identity-rodata)
final_status_selftest=pass=11 warn=1 fail=0
```

## Safety Boundary

- No `userdata-appliance-format`.
- No `userdata-appliance-populate`.
- No `switch-root-to-userdata`.
- No `/dev/block/a90-userdata` materialization.
- No mount or write to `userdata`.
- Only an SD-runtime temporary regular file was created and removed by the formatter-probe command.

## Next

D4C entry prep is now closed: D4B candidate health passed, the rootfs tarball is staged and SHA-pinned,
and the formatter-probe path is live-proven. The next bounded unit is destructive D4C format+populate.
