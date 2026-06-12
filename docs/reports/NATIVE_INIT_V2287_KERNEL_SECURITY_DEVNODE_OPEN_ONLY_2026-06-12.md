# V2287 Kernel Security Recon: temporary devnode open-only check

Date: 2026-06-12
Scope: bounded live rootfs/devtmpfs mutation plus open-only classification. No flash, no reboot, no partition write, no ioctl, no mmap, no Binder transaction, no KGSL command, no FastRPC invoke, no read/write payload, no PoC.

## Preconditions

- Resident image responded as `A90 Linux init 0.9.268 (v2237-supplicant-terminate-poll)`.
- Kernel reported by native init: `Linux 4.14.190-25818860-abA908NKSU5EWA3 aarch64`.
- Pre-run `selftest verbose` completed with `fail=0`.
- V2286 had already established live kernel registration and missing `/dev` nodes for FastRPC, KGSL, and Binder.
- Evidence was collected under private run output:
  `workspace/private/runs/security/v2287-open-only-20260612-213117/`.

## Method

The test created only temporary char nodes using the V2286 live major/minor values:

| Node | Major | Minor |
| --- | ---: | ---: |
| `/dev/adsprpc-smd` | 480 | 0 |
| `/dev/adsprpc-smd-secure` | 480 | 1 |
| `/dev/kgsl-3d0` | 502 | 0 |
| `/dev/binder` | 10 | 81 |
| `/dev/hwbinder` | 10 | 80 |
| `/dev/vndbinder` | 10 | 79 |

Each successful open test used shell file-descriptor open/close only:

- `O_RDONLY`: `exec 9< /dev/<target>; close`
- `O_RDWR`: `exec 9<> /dev/<target>; close`

No read, write, ioctl, mmap, command submission, Binder transaction, or FastRPC invoke was issued.

## Results

| Surface | Temp node creation | `O_RDONLY` open | `O_RDWR` open | Cleanup | Classification |
| --- | --- | --- | --- | --- | --- |
| FastRPC `adsprpc-smd` | `rc=0` | `rc=0` | `rc=0` | removed | `devnode-materialized-openable` |
| FastRPC `adsprpc-smd-secure` | `rc=0` | `rc=0` | `rc=0` | removed | `devnode-materialized-openable` |
| KGSL `kgsl-3d0` | `rc=0` | did not return before command framing timeout/cancel | not attempted | removed after cancel | `devnode-materialized-open-blocked` |
| Binder `binder` | `rc=0` | `rc=0` | `rc=0` | removed | `devnode-materialized-openable` |
| Binder `hwbinder` | `rc=0` | `rc=0` | `rc=0` | removed | `devnode-materialized-openable` |
| Binder `vndbinder` | `rc=0` | `rc=0` | `rc=0` | removed | `devnode-materialized-openable` |

## KGSL blocking boundary

The initial combined run reached:

> `OPEN_TARGET name=kgsl-3d0 path=/dev/kgsl-3d0 mode=ro`

and did not produce an `OPEN_RESULT` or `A90P1 END` marker. The shell applet-level timeout did not complete the KGSL open attempt. The console was recovered by sending serial cancel input, after which `version` worked again.

KGSL `O_RDWR` was intentionally not attempted after the `O_RDONLY` block. This is a meaningful boundary: KGSL is live-registered and can be materialized, but simple native-init open-only probing is not safe enough to classify it as openable. Further KGSL work needs a dedicated bounded helper design or should remain shelved while FastRPC/Binder are available.

## Cleanup and health

- All six temporary nodes were removed after the run.
- Final cleanup verification reported all targets as `CLEAN`.
- Post-run `status` reported `selftest: pass=11 warn=1 fail=0`.
- Final `selftest verbose` completed with `fail=0`.

No persistent filesystem or partition change was made.

## Decision

V2287 open-only classifications:

- `fastrpc-devnode-materialized-openable`
- `binder-devnode-materialized-openable`
- `kgsl-devnode-materialized-open-blocked`

FastRPC remains the top candidate from V2284 and is now runtime-openable once its devnodes are materialized. Binder is also runtime-openable once materialized. KGSL remains a source/fix-marker candidate from V2285, but its runtime open path hit a blocking boundary and should not be retried with the same shell-redirection method.

The next safe step is not a PoC trigger. The practical next step is to decide whether to:

1. stop at reachability and commit V2285-V2287; or
2. design a stricter FastRPC-only ioctl-surface inventory that enumerates command availability without invoking vulnerable paths.
