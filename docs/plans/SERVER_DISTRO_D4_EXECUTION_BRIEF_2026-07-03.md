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

Pending:

- D4C entry live prep: rootfs tarball staging plus V3375 formatter-probe live proof.
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
    stage SHA-pinned rootfs tarball under /mnt/sdext/a90/runtime/
    flash V3375 by checked helper
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
- The formatter path is device-proven, not assumed. V3375 proves it non-destructively by formatting a
  bounded SD-runtime regular file with BusyBox `mke2fs -t ext4 -F -L A90D4PROBE`, checking ext4 magic,
  unlinking the file, and reporting `userdata_touched=0`.
- A rootfs tarball exists under `/mnt/sdext/a90/runtime/` and its SHA-256 is pinned in the run record.
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
