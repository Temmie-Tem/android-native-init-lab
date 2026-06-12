# V2290 Kernel Security Recon: FastRPC B1 dispatch-only liveness

Date: 2026-06-12
Scope: bounded B1 dispatch-only liveness. No flash, no reboot, no partition write, no real `FASTRPC_IOCTL_*` command, no `mmap(2)`, no DSP invoke, no payload, no map/session ioctl, no loop, no retry, no exploit trigger.
Baseline: resident rollback checkpoint remained `A90 Linux init 0.9.268 (v2237-supplicant-terminate-poll)`.

## Purpose

V2288 classified the FastRPC ioctl surface and V2289 split Stage B into:

- B0: design gate;
- B1: dispatch-only liveness with one unknown invalid ioctl;
- B2: crash-only vulnerable-path trigger, requiring separate explicit approval.

This run executed B1 only. B2 was not attempted.

## Private evidence

Raw run artifacts are private and not committed:

- `workspace/private/runs/security/v2290-fastrpc-b1-invalid-ioctl-20260612-222513/`

The helper source and binary remain in the private run directory only. They are not staged, not committed, and were removed from the device after the run.

## Helper constraints

The B1 helper was purpose-built for one invalid ioctl only:

- target path argument default: `/dev/adsprpc-smd`;
- opens the target `O_RDWR | O_CLOEXEC`;
- issues exactly one unknown invalid ioctl command, not any `FASTRPC_IOCTL_*` value;
- closes the fd and exits;
- treats `ENOTTY` or `EINVAL` as the expected dispatch-only result;
- contains no FastRPC payload, no map/unmap/init/invoke structs, no fd-backed DMA-buf setup, no loop, no retry, no heap/reclaim logic, and no privilege-escalation logic.

Build metadata:

- compiler: `aarch64-linux-gnu-gcc -O2 -static -Wall -Wextra`
- binary type: static AArch64 ELF
- helper SHA256: `0562ef7e8911e0c38f3213fbdd3044542b33c421c386f625465060699f32b0b3`

## Preflight

Preflight passed before the ioctl step:

- `version`: `A90 Linux init 0.9.268 (v2237-supplicant-terminate-poll)`
- `status`: `selftest: pass=11 warn=1 fail=0`
- `selftest verbose`: `fail=0`
- `/proc/devices`: `480 adsprpc-smd`
- `/sys/class/fastrpc/adsprpc-smd/dev`: `480:0`
- `/dev/adsprpc-smd`: absent before this run's temporary node creation

One operational note: host-side NCM IPv4 was not configured during transfer, so the helper was installed over NCM IPv6 link-local using the existing device `busybox nc` receive path. This was a file transfer issue only; no target driver call occurred before helper execution.

## Live B1 action

Temporary state created:

- `/dev/adsprpc-smd` as char `480:0`
- `/cache/bin/a90_fastrpc_invalid_ioctl_b1` helper

Single ioctl result:

```text
A90_B1_IOCTL path=/dev/adsprpc-smd cmd=0xdeadbeef rc=-1 errno=25 strerror=Inappropriate ioctl for device
A90_B1_CLOSE rc=0 errno=25 strerror=Inappropriate ioctl for device
```

Interpretation:

- `errno=25` is `ENOTTY`.
- The kernel log contained the expected default-path marker: `bad ioctl: -559038737`.
- This confirms `fastrpc_device_ioctl` default dispatch is reachable through the materialized `adsprpc-smd` devnode.
- It does not enter any vulnerable command family and does not change the V2288 Stage-B avoid-list.

## Cleanup

Cleanup completed immediately after the single helper run:

- `/dev/adsprpc-smd`: removed
- `/cache/bin/a90_fastrpc_invalid_ioctl_b1`: removed

Verification reported both paths missing after cleanup.

## Post-run health

Post-run health remained clean:

- `status`: `selftest: pass=11 warn=1 fail=0`
- `selftest verbose`: `fail=0`
- no reboot, panic, hang, retry, or rollback occurred.

## Decision

V2290 result:

> `fastrpc-b1-dispatch-only-live-enotty-clean`

B1 is now complete. The device accepts an openable temporary `adsprpc-smd` node and reaches the driver's unknown-ioctl default path, returning `ENOTTY`, with cleanup and health checks clean.

This does not authorize B2. The next decision remains one of:

1. stop at FastRPC recon/B1;
2. design a diagnostic `slub_debug` boot first, because stock config lacks `KASAN`, `PAGE_POISONING`, and `SLUB_DEBUG_ON`, so a naive B2 no-crash result would be inconclusive;
3. proceed to B2 only with the exact V2289 approval phrase and a watched crash-only single shot.

Subsequent note: V2291 ran the read-only DSP/rpmsg liveness gate and classified the
resident native-init boot as `dsp-channel-down-for-fastrpc`. For the current boot, that
supersedes the B1 decision menu: no naive B2 and no FastRPC `slub_debug` image should be
run unless FastRPC DSP-channel liveness is reopened by a separate explicit unit.
