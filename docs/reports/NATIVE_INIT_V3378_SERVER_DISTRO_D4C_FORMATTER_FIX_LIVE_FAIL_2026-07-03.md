# Native Init V3378 Server-Distro D4C Formatter Fix Live Fail

- Cycle: `V3378`
- Decision: `v3377-server-distro-d4c-formatter-fix-live-failed`
- Candidate tested: `A90 Linux init 0.11.136 (v3377-server-distro-userdata-formatter-fix)`
- Candidate boot image: `workspace/private/inputs/boot_images/boot_linux_v3377_server_distro_userdata_formatter_fix.img`
- Candidate SHA256: `65575d4166896d9ffd4e38594ac1776583b6087c5ff79c8eebb140ea07a15dfd`
- Flash path: `native_init_flash.py`
- Final rollback: v2321 clean by `status`

## Result

V3377 fixed the unsupported BusyBox `-t ext4` option, booted cleanly, and passed read-only preflight. The
formatter-probe still failed safely because the C `probe_argv` array lost its final NULL terminator after
adding the KBYTES argument.

D4C format/populate remains blocked. No `userdata` action was executed.

## Flash And Candidate Health

The exact V3377 artifact was flashed through the checked helper.

```text
local_sha256=65575d4166896d9ffd4e38594ac1776583b6087c5ff79c8eebb140ea07a15dfd
remote_sha256=65575d4166896d9ffd4e38594ac1776583b6087c5ff79c8eebb140ea07a15dfd
boot_readback_sha256=65575d4166896d9ffd4e38594ac1776583b6087c5ff79c8eebb140ea07a15dfd
candidate_version=A90 Linux init 0.11.136 (v3377-server-distro-userdata-formatter-fix)
candidate_status_selftest=pass=12 warn=1 fail=0
```

One standalone candidate `selftest` command printed `fail=0` but lost the `A90P1 END` marker to serial
noise, so candidate health is taken from the checked helper's `version/status` verification.

The device-side read-only D4 preflight passed:

```text
A90D4 preflight target.source=partname-scan
target.devname=sda33
target.sysname=sda33
target.dev=259:30
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
A90D4 formatter-probe=begin formatter=busybox-mke2fs path=/mnt/sdext/a90/runtime/a90-d4c-formatter-probe.img size_bytes=16777216 kbytes=16384
server-distro-d4: execve(/bin/busybox): Bad address
A90D4 formatter-probe=fail stage=mke2fs rc=127
A90P1 END ... rc=-5 errno=5 ... status=error
```

Root cause from source inspection:

```c
char *probe_argv[] = { busybox, "mke2fs", "-F", "-L", "A90D4PROBE", NULL, NULL };
probe_argv[5] = probe_path;
probe_argv[6] = size_kb_arg;  // overwrote the only final NULL
```

Fix: make `probe_argv` long enough for `probe_path`, `size_kb_arg`, and a final NULL terminator.

## Cleanup And Rollback

The SD probe file was removed:

```text
A90D4_V3377_PROBE_CLEANUP_OK
```

The device was rolled back through `native_init_flash.py` to v2321.

```text
rollback_local_sha256=ca978551aabe4b39563abaf529ccf2522054952d8b2ad852e632d26da88168cb
rollback_remote_sha256=ca978551aabe4b39563abaf529ccf2522054952d8b2ad852e632d26da88168cb
rollback_boot_readback_sha256=ca978551aabe4b39563abaf529ccf2522054952d8b2ad852e632d26da88168cb
final_version=A90 Linux init 0.9.285 (v2321-usb-clean-identity-rodata)
final_status_selftest=pass=11 warn=1 fail=0
```

A final standalone `selftest` retry was itself corrupted by serial input noise (`cmdv1 selfes...`) and is
not used as health evidence; final rollback health is the valid `status` frame with `selftest fail=0`.

## Safety Boundary

- No `userdata-appliance-format`.
- No `userdata-appliance-populate`.
- No `switch-root-to-userdata`.
- No `/dev/block/a90-userdata` materialization.
- No mount or write to `userdata`.
- Only an SD-runtime temporary regular file was created and removed.

## Next

Build the next formatter-fix candidate with the corrected `probe_argv` NULL terminator, then re-run the
same bounded live proof: exact checked-helper flash, candidate health, read-only preflight, formatter-probe
only, and rollback unless destructive D4C starts immediately under the D4 runbook.
