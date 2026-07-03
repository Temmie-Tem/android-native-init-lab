# Server-Distro D4 Execution Brief

- Date: `2026-07-03`
- Scope: current D4 state, gates, and next execution path
- Device action in this document: none
- Parent runbook: `docs/plans/SERVER_DISTRO_D4_USERDATA_APPLIANCE_PLAN_2026-07-03.md`
- Surface design: `docs/plans/SERVER_DISTRO_D4B_NATIVE_INIT_SURFACE_DESIGN_2026-07-03.md`

## 1. Current State

D4 is the first destructive server-distro step. It disposes of Android `/data` by formatting only the
`userdata` partition and using it as the persistent Debian appliance root.

Completed:

- D3B live `switch_root` proof passed on the SD-backed rootfs.
- D4A read-only userdata preflight passed.
- D4B source/build passed and produced V3373.
- D4B candidate-health passed live and rolled back cleanly.
- D4C formatter-probe source/build passed and produced V3375.
- D4C rootfs tarball staging runner passed static validation.
- D4C rootfs tarball was staged live under SD runtime and SHA-verified.
- V3375 formatter-probe live failed safely: BusyBox `mke2fs` rejected `-t ext4`; v2321 rollback clean.
- V3377 formatter syntax fix source/build passed; live proof still pending.
- V3377 formatter-fix live failed safely: `probe_argv` lacked a final NULL after adding KBYTES; v2321 rollback clean.
- V3379 formatter argv fix source/build passed; live proof still pending.
- V3379 formatter argv fix live proof passed; v2321 rollback clean.

Pending:

- D4C format and populate.
- D4D appliance handoff proof.

## 2. Carried Facts

Authoritative D4A userdata identity:

```text
source=sysfs PARTNAME=userdata scan
devname=sda33
dev=259:27  (D4A boot; same-session only, not a cross-boot constant)
sectors=231577432
size_bytes=118567645184
ro=0
mounted=0
```

D4B candidate:

```text
init=A90 Linux init 0.11.134 (v3373-server-distro-userdata-appliance)
boot=workspace/private/inputs/boot_images/boot_linux_v3373_server_distro_userdata_appliance.img
sha256=78e3297063b1957626075bc8c22223ef7a195d0de684fdbd7f51deb824a49f6d
token=SERVER-DISTRO-D4-USERDATA-APPLIANCE
```

D4C formatter-probe candidate:

```text
init=A90 Linux init 0.11.135 (v3375-server-distro-userdata-formatter-probe)
boot=workspace/private/inputs/boot_images/boot_linux_v3375_server_distro_userdata_formatter_probe.img
sha256=460fbbc137478695c9271a80fd9e0e5dedb96975ee9e69bd6b67c9a72db1ecdb
probe=userdata-appliance-formatter-probe SERVER-DISTRO-D4-USERDATA-APPLIANCE <sd-runtime-image> <size-bytes>
status=live-failed; BusyBox mke2fs rejects -t ext4
live-fail-report=docs/reports/NATIVE_INIT_V3376_SERVER_DISTRO_D4C_FORMATTER_PROBE_LIVE_FAIL_2026-07-03.md
```

D4C formatter-fix candidate:

```text
init=A90 Linux init 0.11.136 (v3377-server-distro-userdata-formatter-fix)
boot=workspace/private/inputs/boot_images/boot_linux_v3377_server_distro_userdata_formatter_fix.img
sha256=65575d4166896d9ffd4e38594ac1776583b6087c5ff79c8eebb140ea07a15dfd
probe=userdata-appliance-formatter-probe SERVER-DISTRO-D4-USERDATA-APPLIANCE <sd-runtime-image> <size-bytes>
status=live-failed; probe_argv missing final NULL after KBYTES
source-report=docs/reports/NATIVE_INIT_V3377_SERVER_DISTRO_D4C_FORMATTER_FIX_SOURCE_BUILD_2026-07-03.md
live-fail-report=docs/reports/NATIVE_INIT_V3378_SERVER_DISTRO_D4C_FORMATTER_FIX_LIVE_FAIL_2026-07-03.md
```

D4C formatter argv-fix candidate:

```text
init=A90 Linux init 0.11.137 (v3379-server-distro-userdata-formatter-argv-fix)
boot=workspace/private/inputs/boot_images/boot_linux_v3379_server_distro_userdata_formatter_argv_fix.img
sha256=a58c07bca01c74ba97653a7cd3d3681788674fa8a6eb912a4fe64a84fb42112e
probe=userdata-appliance-formatter-probe SERVER-DISTRO-D4-USERDATA-APPLIANCE <sd-runtime-image> <size-bytes>
status=live-pass; rollback-clean
source-report=docs/reports/NATIVE_INIT_V3379_SERVER_DISTRO_D4C_FORMATTER_ARGV_FIX_SOURCE_BUILD_2026-07-03.md
live-report=docs/reports/NATIVE_INIT_V3380_SERVER_DISTRO_D4C_FORMATTER_ARGV_FIX_LIVE_PASS_2026-07-03.md
```

D4C rootfs tarball staging runner:

```text
runner=workspace/public/src/scripts/server-distro/prepare_d4c_userdata_rootfs_tarball.py
source-rootfs=workspace/private/builds/server-distro/d3-sysvinit-usrmerge-20260703T101657Z-rootfs
remote-tarball=/mnt/sdext/a90/runtime/a90-d4c-userdata-rootfs.tar
report=docs/reports/SERVER_DISTRO_D4C_ROOTFS_TARBALL_STAGING_RUNNER_2026-07-03.md
```

D4C staged rootfs tarball:

```text
remote-tarball=/mnt/sdext/a90/runtime/a90-d4c-userdata-rootfs.tar
sha256=0875b8bd6e58298f644735e5d7ee12c0286e3057a7744b05064fc34829412603
size_bytes=268349440
source-report=docs/reports/SERVER_DISTRO_D4C_ROOTFS_TARBALL_STAGING_LIVE_2026-07-03.md
```

Rollback images that must be confirmed before any D4 flash:

```text
v2321=ca978551aabe4b39563abaf529ccf2522054952d8b2ad852e632d26da88168cb
v2237=b2ea2d26d160b7702ce7d4438b84367788eea26c6a5bbe4ed93f3d270292ac7f
v48=present and checksum-recorded by the runner/report
```

## 3. Execution Picture

```text
D4B candidate-health
  flash V3373 by checked helper
  boot health: version/status/selftest
  run read-only userdata-appliance-preflight
  prove node not materialized and target identity agrees
  rollback to v2321 unless D4C starts immediately

D4C format+populate
  first close D4C entry prep:
    rootfs tarball is already staged under /mnt/sdext/a90/runtime/
    flash V3379 by checked helper
    run preflight plus formatter-probe only
    rollback unless destructive D4C starts immediately
  restage or keep V3373 live under the same gated run
  prove formatter path on device
  verify SD rootfs tarball path and SHA-256
  run userdata-appliance-format with pinned devname/dev/sectors
  run userdata-appliance-populate with pinned tarball SHA
  verify marker: userdata=appliance-root

D4D handoff
  run switch-root-to-userdata with expected marker
  observe Debian PID1 and local SSH over USB/NCM
  prove root filesystem is userdata
  keep timed recovery or rollback path for the first proof
```

## 4. D4B Candidate-Health Gate

Allowed device actions:

- checked-helper boot flash of the exact V3373 artifact;
- candidate `version`, `status`, and `selftest`;
- read-only `userdata-appliance-preflight`;
- checked-helper rollback to v2321.

Forbidden in this gate:

- no `userdata-appliance-format`;
- no `userdata-appliance-populate`;
- no `switch-root-to-userdata`;
- no mount, no format, no rootfs extraction, no userdata node materialization.

Pass evidence:

```text
candidate version == A90 Linux init 0.11.134 (v3373-server-distro-userdata-appliance)
candidate selftest fail=0
A90D4 preflight=ok
target.devname=sda33
target.dev=<live-major>:<live-minor>
target.sectors=231577432
target.size_bytes=118567645184
target.mounted=0
node_materialized=0
final rollback version == v2321-usb-clean-identity-rodata
final selftest fail=0
```

Use the live `target.dev` value only within the same D4C session. The stable cross-checks are
`PARTNAME=userdata`, `devname=sda33`, sector count, size, `ro=0`, and `mounted=0`; the major:minor value
guards against in-session target substitution but may drift across boots.

## 5. D4C Entry Gate

D4C may start only after all of these are true:

- D4B candidate-health passed and was reported.
- Device-side preflight agrees with the D4A target identity.
- The formatter path is device-proven, not assumed. V3375 failed because BusyBox `mke2fs` rejected
  `-t ext4`; the next candidate must prove the corrected syntax non-destructively by formatting a bounded
  SD-runtime regular file, checking ext magic, unlinking the file, and reporting `userdata_touched=0`.
- **OPERATOR GATE-2 NOTE (2026-07-03): filesystem-TYPE divergence must be resolved before D4C live
  format.** V3377 "fixed" the V3375 syntax failure by *dropping* `-t ext4` from the busybox `mke2fs`
  argv. BusyBox `mke2fs` with no `-t` produces **ext2 (no journal)**, not ext4. That still mounts (the
  ext4 driver mounts ext2) and will pass functional tests, but it silently violates locked design
  decision C ("userdata is plain **ext4**", DoD lines 30/124/177) and — for an always-on headless server
  appliance — removes journaling, so an unclean power loss risks filesystem corruption and an unbootable
  appliance. The `superblock_magic=53 ef` probe does NOT distinguish ext2/3/4. **Before the destructive
  D4C format, consciously choose and REPORT the formatter that yields a journaled filesystem:**
  (a) *preferred* — the plan's own SHA-pinned e2fsprogs `mkfs.ext4` (D4 plan line 140 / D4B design line
  119), which produces real ext4 with a journal; or (b) format ext2 with busybox `mke2fs`, then add a
  journal with `tune2fs -j` (only if a provenance-pinned `tune2fs` is proven on-device); or (c) if
  ext2/no-journal is knowingly accepted, record the power-loss/fsck tradeoff explicitly and do NOT label
  the result "ext4". D4C DoD must verify the *actual* on-disk feature set (e.g. `has_journal`) of the
  formatted userdata, not just that it mounts.
- A rootfs tarball exists under `/mnt/sdext/a90/runtime/` and its SHA-256 is pinned in the run record.
- The rootfs tarball was produced by `prepare_d4c_userdata_rootfs_tarball.py`, which checks the D3
  sysvinit rootfs markers, forces numeric root ownership in the tar stream, uploads to SD runtime, and
  verifies the remote SHA without flashing or touching `userdata`.
- Recovery envelope is re-confirmed immediately before the destructive format.

D4C stop rules:

- stop before format on any identity mismatch, mounted target, missing rollback artifact, missing TWRP,
  or unproven formatter;
- if format begins and a later check fails, do not retry-loop; record the transcript and stop.

## 6. D4D Proof Shape

D4D is not complete merely because `switch_root` returns no error. The proof needs observable appliance
state from the new root:

- Debian version and stage marker;
- `/proc/1/comm` and `/proc/1/exe`;
- root mount backed by `userdata`;
- local USB/NCM SSH reachable;
- bounded recovery path still works.

Public exposure is still out of scope. `D-public` remains a separate operator gate after the local
userdata appliance is proven.
