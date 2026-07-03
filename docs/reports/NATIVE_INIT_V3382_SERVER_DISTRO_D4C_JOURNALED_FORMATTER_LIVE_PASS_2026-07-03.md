# Native Init V3382 Server-Distro D4C Journaled Formatter Live Pass

- Cycle: `V3382`
- Decision: `v3381-server-distro-d4c-journaled-formatter-live-pass`
- Candidate tested: `A90 Linux init 0.11.138 (v3381-server-distro-journaled-formatter)`
- Candidate boot image: `workspace/private/inputs/boot_images/boot_linux_v3381_server_distro_journaled_formatter.img`
- Candidate SHA256: `c99be26deb3ca872de444e1f34ab602938a68381fe84c338bf29ead7ed9f1c4f`
- Flash path: `native_init_flash.py`
- Final rollback: v2321 clean

## Result

V3381 passed the D4C journaled formatter live proof:

- exact candidate flash through the checked helper;
- candidate boot health passed;
- read-only `userdata-appliance-preflight` passed;
- non-destructive SD regular-file `userdata-appliance-formatter-probe` passed through the SHA-pinned e2fsprogs toolroot;
- `mkfs.ext4` created a journal, `dumpe2fs -h` reported `has_journal`, and the native-init feature-bit check reported `has_journal=1`;
- probe file cleanup succeeded inside the command;
- rollback to v2321 completed with final `version`, `status`, and `selftest` passing.

D4C format/populate has not yet run.

## Flash And Candidate Health

```text
local_sha256=c99be26deb3ca872de444e1f34ab602938a68381fe84c338bf29ead7ed9f1c4f
remote_sha256=c99be26deb3ca872de444e1f34ab602938a68381fe84c338bf29ead7ed9f1c4f
boot_readback_sha256=c99be26deb3ca872de444e1f34ab602938a68381fe84c338bf29ead7ed9f1c4f
candidate_version=A90 Linux init 0.11.138 (v3381-server-distro-journaled-formatter)
candidate_status_selftest=pass=12 warn=1 fail=0
candidate_explicit_selftest=pass=12 warn=1 fail=0
candidate_flash_total_sec=64.516
```

## Read-Only Preflight

The first preflight attempt stopped at the auto-menu busy gate and did not execute the command body.
The `--hide-on-busy` retry completed with a valid `A90P1 END`:

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
rc=0 status=ok
```

The `target.dev` value is same-session evidence only and must be re-derived before any destructive
D4C format run.

## Journaled Formatter Probe

The non-destructive formatter probe used only an approved SD-runtime regular file under the e2fsprogs
toolroot:

```text
probe_path=/mnt/sdext/a90/runtime/d4c-format-toolroot/tmp/a90-v3381-live-probe.img
probe_size_bytes=16777216
mke2fs_sha=92721c9a402ba8015ec6321acffaac187ce32fd2772a54690b46dfe94b8f6589 expected_sha_match=1
dumpe2fs_sha=6e22ed6668e336a891621de3e18b8915e56545351c20c06bafb6682ac1de9aae expected_sha_match=1
tune2fs_sha=f4bd3a7e56772236ec0dd8f6a4c5fa2b9dfa52cf70d2af0fa1eb50cfeafa34ad expected_sha_match=1
e2fs-toolroot=ok root=/mnt/sdext/a90/runtime/d4c-format-toolroot mkfs.ext4=mke2fs
formatter=e2fsprogs-mkfs.ext4 target=/tmp/a90-v3381-live-probe.img label=A90D4PROBE
Creating journal (1024 blocks): done
formatter-probe=ext4-magic-ok magic=53ef offset=1080
Filesystem features: has_journal ext_attr resize_inode dir_index filetype extent 64bit flex_bg sparse_super large_file huge_file dir_nlink extra_isize metadata_csum
formatter-probe=has-journal-ok feature_compat=0x0000003c has_journal=1
formatter-probe=done formatter=e2fsprogs-mkfs.ext4 cleanup=ok userdata_touched=0 has_journal=1
rc=0 status=ok
```

This closes the journaled-formatter proof that superseded the V3379 BusyBox ext-family probe. It
proves the native-init journaled formatter path on a removable-SD regular file, not the destructive
userdata format itself.

## Rollback

The device was rolled back through `native_init_flash.py` to v2321.

```text
rollback_local_sha256=ca978551aabe4b39563abaf529ccf2522054952d8b2ad852e632d26da88168cb
rollback_remote_sha256=ca978551aabe4b39563abaf529ccf2522054952d8b2ad852e632d26da88168cb
rollback_boot_readback_sha256=ca978551aabe4b39563abaf529ccf2522054952d8b2ad852e632d26da88168cb
rollback_total_sec=63.687
final_version=A90 Linux init 0.9.285 (v2321-usb-clean-identity-rodata)
final_status_selftest=pass=11 warn=1 fail=0
final_explicit_selftest=pass=11 warn=1 fail=0
```

## Operational Notes

- One candidate explicit `selftest` read timed out before a bridge restart; the immediately preceding
  candidate `status` already showed `selftest fail=0`, and the post-restart `version/status/selftest`
  sequence passed cleanly.
- A final rollback health check was accidentally issued in parallel and caused serial framing noise.
  After bridge restart, the sequential final `version/status/selftest` sequence passed cleanly.

## Safety Boundary

- No `userdata-appliance-format`.
- No `userdata-appliance-populate`.
- No `switch-root-to-userdata`.
- No `/dev/block/a90-userdata` materialization.
- No mount or write to `userdata`.
- Only an SD-runtime temporary regular file was created and removed by the formatter-probe command.

## Next

D4C entry prep is now closed under the operator's journaled-formatter correction: D4B candidate health
passed, the rootfs tarball is staged and SHA-pinned, the e2fsprogs toolroot is staged and SHA-pinned,
and the V3381 journaled formatter-probe path is live-proven. The next bounded unit is destructive D4C
format+populate under a fresh same-session preflight.
