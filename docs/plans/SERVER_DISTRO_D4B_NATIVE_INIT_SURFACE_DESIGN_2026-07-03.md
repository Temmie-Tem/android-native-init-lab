# Server-Distro D4B Native-Init Surface Design

- Date: `2026-07-03`
- Scope: D4B source/build design
- Device action in this document: none
- Parent runbook: `docs/plans/SERVER_DISTRO_D4_USERDATA_APPLIANCE_PLAN_2026-07-03.md`
- D4A report: `docs/reports/SERVER_DISTRO_D4A_USERDATA_PREFLIGHT_2026-07-03.md`

## 1. Objective

D4B adds the native-init command surface needed for the destructive D4C userdata appliance step, but
D4B itself is not the format step. The D4B deliverable is a checked boot candidate that can:

- re-derive the userdata target from sysfs;
- materialize a verified block node when needed;
- format only the verified userdata partition;
- populate the fresh filesystem from a SHA-pinned rootfs artifact;
- hand off to the userdata root with `switch_root`.

D4C remains blocked until this surface is statically validated and the candidate boots cleanly.

## 2. D4A Facts That D4B Must Honor

D4A passed read-only on resident v2321:

```text
source=PARTNAME scan
devname=sda33
dev=259:27
size_bytes=118567645184
size_gib=110.42
ro=0
mounted=0
```

The current native-init `/dev` tree does not materialize `/dev/block/sda33`, and the current busybox
does not provide `mkfs.ext4`. D4B must not assume either exists.

## 3. Target Identity Rule

The target resolver must scan `/sys/class/block/*/uevent` and accept exactly one entry with
`PARTNAME=userdata`. For the accepted target it must capture:

- `DEVNAME`;
- `MAJOR`;
- `MINOR`;
- sector count from `/sys/class/block/<dev>/size`;
- read-only state from `/sys/class/block/<dev>/ro`;
- mounted state from `/proc/mounts`.

Fail closed if:

- zero or multiple `PARTNAME=userdata` entries exist;
- `ro != 0`;
- size is outside the D4A-derived expected window;
- the target is already mounted before format;
- any forbidden partition name appears in the accepted identity chain;
- an optional by-name cross-check exists but resolves to a different device.

The mutating commands must compare caller-pinned identity before touching storage:

```text
expected_devname=sda33
expected_dev=259:27
expected_sectors=231577432
```

`rdev` is not treated as stable across all future boots, but it is a useful same-session guard. If the
host and device disagree in the D4C session, stop before format.

## 4. Runtime Block Node

D4B should materialize a private node such as:

```text
/dev/block/a90-userdata
```

The node must be created from the verified `MAJOR:MINOR` only after target identity passes. If a node
already exists, verify that it points to the same block device. Do not silently reuse or overwrite a
wrong node.

## 5. Command Contract

### `userdata-appliance-preflight <token>`

Read-only. It must print a parseable target identity record and must not create the block node.

Required markers:

```text
A90D4 preflight=ok
target.devname=sda33
target.dev=<live-major>:<live-minor>
target.sectors=231577432
target.size_bytes=118567645184
target.mounted=0
target.node_exists=<0|1>
```

The `target.dev` value is a same-session guard, not a cross-boot constant. D4A saw `259:27`, while the
D4B candidate-health boot later saw the same `sda33`/sector/size target as `259:17`. D4C must parse the
live preflight result and pass that same-session value to mutating commands; it must not reuse an older
major:minor literal from a prior boot.

### `userdata-appliance-format <token> <expected-devname> <expected-dev> <expected-sectors>`

Destructive. It must:

1. Re-run target identity resolution.
2. Compare all caller-pinned values.
3. Refuse if mounted.
4. Materialize the private block node.
5. Run the selected formatter.
6. Return a parseable success marker only after the formatter exits cleanly.

Formatter policy:

- preferred: staged or bundled `mkfs.ext4` with SHA-pinned provenance;
- allowed alternative: device-proven BusyBox `mke2fs -t ext4` path;
- disallowed: entering D4C with only an assumed formatter path.

### `userdata-appliance-populate <token> <source-tar> <sha256>`

Mutating. It must:

1. Accept only a source artifact under the approved SD runtime root.
2. Verify the tarball SHA-256 before extraction.
3. Mount the formatted userdata filesystem at `/mnt/a90-userdata-root`.
4. Extract with ownership and permissions preserved.
5. Verify `/sbin/init` and write or verify `/etc/a90-appliance-stage`.

Use a tarball derived from the clean D3 rootfs source rather than loop-mounting the D3 image inside the
device population step. That keeps D4C to one target filesystem and one source artifact.

### `switch-root-to-userdata <token> <expected-marker>`

PID1 handoff. It must:

1. Re-run target identity resolution.
2. Mount userdata if it is not already mounted.
3. Verify the appliance marker and `/sbin/init`.
4. Move `/proc`, `/sys`, and `/dev` into the new root as D3B did.
5. Execute BusyBox `switch_root /mnt/a90-userdata-root /sbin/init`.

The first D4D proof must retain a timed recovery path until the handoff is stable.

## 6. Dispatch and Safety Shape

Register commands in the native shell dispatcher with this policy:

- `userdata-appliance-preflight`: read-only, normal completion marker;
- `userdata-appliance-format`: dangerous, normal completion marker;
- `userdata-appliance-populate`: dangerous, normal completion marker;
- `switch-root-to-userdata`: dangerous and no normal completion marker after successful PID1 handoff.

All four commands require the long D4 token. Mutating commands must print target identity before action.

## 7. D4B Validation

Host/source validation:

- compile the touched C;
- run focused static tests for dispatcher registration, token gating, target resolver strings, formatter
  policy, and forbidden partition deny strings;
- build the boot image with the checked build path;
- record artifact SHA-256.

Candidate-health validation before D4C:

- confirm v2321/v2237/v48 and TWRP/recovery;
- flash only through `native_init_flash.py`;
- run `version`, `status`, and `selftest`;
- run only `userdata-appliance-preflight` as the first D4B live command;
- roll back to v2321 unless the next bounded D4C run starts immediately under the same controlled plan.

## 8. D4C Entry Gate

D4C may start only when all of these are true:

- D4A public report exists and passed;
- D4B static validation passed;
- D4B candidate boot health passed;
- device-side `userdata-appliance-preflight` agrees with the host target identity;
- the selected formatter path is proven, not assumed;
- the rootfs population tarball exists on SD and matches its host-pinned SHA-256.
