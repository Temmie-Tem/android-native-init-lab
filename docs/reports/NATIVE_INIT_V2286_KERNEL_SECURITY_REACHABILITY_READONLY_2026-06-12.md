# V2286 Kernel Security Recon: read-only runtime reachability snapshot

Date: 2026-06-12
Scope: live read-only metadata collection through the existing serial bridge. No flash, no reboot, no mknod, no devnode open, no ioctl, no mmap, no Binder transaction, no KGSL command, no FastRPC invoke, no PoC.

## Preconditions

- Resident image responded as `A90 Linux init 0.9.268 (v2237-supplicant-terminate-poll)`.
- Kernel reported by native init: `Linux 4.14.190-25818860-abA908NKSU5EWA3 aarch64`.
- `selftest verbose` completed with `fail=0`.
- Evidence was collected under private run output:
  `workspace/private/runs/security/v2286-reachability-readonly-20260612-212112/`.

## Collection method

Only metadata reads were used:

- `cat /proc/devices`
- `cat /proc/misc`
- `ls -ld /sys/class/...`
- `cat /sys/class/.../dev`
- `cat /sys/class/.../uevent`
- `ls -l /dev/...`
- `stat /dev/...` only if a target devnode existed

No target devnode existed, so the `stat` branch was not reached for the security targets.

## Runtime metadata

| Surface | Kernel registration evidence | Sysfs evidence | `/dev` node | Classification |
| --- | --- | --- | --- | --- |
| FastRPC `adsprpc-smd` | `/proc/devices`: major `480` `adsprpc-smd` | `/sys/class/fastrpc/adsprpc-smd`, `MAJOR=480`, `MINOR=0`, `DEVNAME=adsprpc-smd` | missing | `registered-missing-devnode` |
| FastRPC `adsprpc-smd-secure` | same `adsprpc-smd` major | `/sys/class/fastrpc/adsprpc-smd-secure`, `MAJOR=480`, `MINOR=1`, `DEVNAME=adsprpc-smd-secure` | missing | `registered-missing-devnode` |
| KGSL `kgsl-3d0` | `/proc/devices`: major `502` `kgsl` | `/sys/class/kgsl/kgsl-3d0`, `MAJOR=502`, `MINOR=0`, `DEVNAME=kgsl-3d0` | missing | `registered-missing-devnode` |
| Binder `binder` | `/proc/misc`: minor `81` `binder`; char major `10` misc | `/sys/class/misc/binder`, `MAJOR=10`, `MINOR=81`, `DEVNAME=binder` | missing | `registered-missing-devnode` |
| Binder `hwbinder` | `/proc/misc`: minor `80` `hwbinder`; char major `10` misc | `/sys/class/misc/hwbinder`, `MAJOR=10`, `MINOR=80`, `DEVNAME=hwbinder` | missing | `registered-missing-devnode` |
| Binder `vndbinder` | `/proc/misc`: minor `79` `vndbinder`; char major `10` misc | `/sys/class/misc/vndbinder`, `MAJOR=10`, `MINOR=79`, `DEVNAME=vndbinder` | missing | `registered-missing-devnode` |

Nearby `/dev` scan for `adsprpc`, `kgsl`, `binder`, `hwbinder`, and `vndbinder` returned no entries.

## Interpretation

The read-only snapshot resolves the first runtime reachability layer:

- The FastRPC, KGSL, and Binder drivers are registered in the live kernel.
- Sysfs exposes stable major/minor metadata for every target.
- Native-init's current `/dev` tree does not materialize these nodes.
- Therefore, the next gate is not source/config registration. It is devnode materialization.

This does not prove openability or triggerability. It also does not prove any exploitability claim from V2284/V2285. It only proves that the relevant kernel device registrations exist live and that the native userspace currently lacks the corresponding `/dev` entries.

## Next gate

The next bounded live step, if selected, should be **devnode materialization + open-only**:

1. Create only the six candidate char nodes in a temporary native rootfs/devtmpfs context using the exact live major/minor values above.
2. Run open-only checks against those nodes.
3. Do not issue any ioctl, mmap, Binder transaction, KGSL command, FastRPC invoke, or payload.
4. Remove or ignore the temporary nodes after the check; do not persist them to partitions.

This is a live rootfs mutation, even though it is not a partition write and not a driver trigger. It should remain a separate approval boundary from this read-only snapshot.

## Decision

V2286 read-only reachability result:

> `fastrpc-kgsl-binder-registered-missing-devnode`

FastRPC remains the first candidate from V2284. KGSL and Binder remain ranked second and third from V2285. The practical next step is not PoC work; it is open-only classification after bounded devnode materialization.
