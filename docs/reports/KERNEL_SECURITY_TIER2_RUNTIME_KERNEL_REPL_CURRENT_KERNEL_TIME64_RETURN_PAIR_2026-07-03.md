# Kernel Security Tier-2 Runtime Kernel REPL - current_kernel_time64 Return Pair

Date: 2026-07-03 KST / 2026-07-02 UTC

## Summary

- Target proved: `current_kernel_time64`.
- Decision: `a90-repl-live-call-proof-current_kernel_time64-return-pair-pass`.
- Contract: no arguments; arm64 small-aggregate return captured as
  `x0=struct timespec64.tv_sec` and `x1=struct timespec64.tv_nsec`.
- Result: live PASS. Two same-session target calls returned valid, nondecreasing
  `timespec64` pairs bounded by `ktime_get_real_seconds()` anchor calls.
- End state: rolled back to `v2321-usb-clean-identity-rodata`; final
  `selftest pass=11 warn=1 fail=0`.

This closes the REPL ABI-shape gap called out in `GOAL.md`: the previous
`current_kernel_time64` proof trusted only the x0 seconds lane because the
normal v1 REPL prints a single return register. This unit added a narrow
call-pair REPL image that prints post-call x0:x1 from the same `blr` return.

## Public Changes

- Added `build_kernel_tier2_repl_v1_call_pair.py`, a source builder for a
  narrow v1-repl companion image.
- Added `a90_repl_current_kernel_time64_pair.py`, a bounded live proof driver
  for the `timespec64` return-pair contract.
- Added focused tests for the call-pair stub encoding and the fake-transport
  return-pair proof path.

The normal v1-repl image remains the default resident REPL. The call-pair image
is not a general replacement; it exists only for bounded aggregate-return proofs.

## Candidate Selection

`current_kernel_time64()` was already parked by the earlier
`is_current_pgrp_orphaned` report because the then-current v1 REPL captured only
x0. It is the cleanest representative for the remaining ABI shape:

- no arguments;
- source declaration `struct timespec64 current_kernel_time64(void)`;
- read-only timekeeping state;
- return value is a small aggregate that arm64 returns in x0/x1;
- no file-node equivalent that would retire the target under the VFS-read policy.

This is not same-shape breadth. The already-proven `ktime_get_ts64`,
`getnstimeofday64`, and `getboottime64` result-slot proofs cover caller-owned
`struct timespec64 *` writes. This unit covers the distinct by-value aggregate
return lane.

## Static Gate

| Symbol | Link address | Gate | Source |
| --- | ---: | --- | --- |
| `current_kernel_time64` | `0xffffff8008161894` | `SAFE-SCALAR`; export-recovery; JOPP entry; leaf; direct BL xrefs `26`; no arg deref; 20-word body match | `struct timespec64 current_kernel_time64(void)` at `include/linux/timekeeping.h:27` |
| `ktime_get_real_seconds` | `0xffffff800815f694` | existing `SAFE-SCALAR` anchor; export-recovery; JOPP entry | `extern time64_t ktime_get_real_seconds(void)` |

Additional static checks:

- Next symbol boundary: `get_monotonic_coarse64` at `+0x50`.
- `current_kernel_time64` source signature has no pointer arguments.
- All pinned first 20 words matched the static image.
- Runtime pointers and KASLR slide were captured only in private evidence.

## Call-Pair Image

Candidate image:

- `workspace/private/inputs/boot_images/boot_linux_tier2_repl_v1_call_pair.img`
- SHA256:
  `2c9c3a1638a98fc134158f49de80d1501f0d1eab50e59e828dc8d4b853e3c495`
- Base image SHA256:
  `ca978551aabe4b39563abaf529ccf2522054952d8b2ad852e632d26da88168cb`
- Stub body SHA256:
  `ff19439375c1c08427858c0804be40c384c4b2984a41d6c9f3ecf1c3eddbd566`
- Patch room: `212` bytes; patch length: `212` bytes.
- Hijacked handler: `kgsl_pwrctrl_force_no_nap_store`, same as v1-repl.
- Format literal: `R%llx:%llx\n`.

Disassembly of the call return path:

```text
9c: d63f0120  blr x9
a0: aa0103e2  mov x2, x1
a4: aa0003e1  mov x1, x0
a8: 10000100  adr x0, 0xc8
ac: 97e04e67  bl ...
```

The image keeps the v2321 version banner unchanged. Identity for this candidate
is the built SHA/readback SHA plus the body disassembly above.

## Input And Return Contract

Input contract:

- Call `current_kernel_time64()` with no arguments.
- Treat timekeeping state as read-only.
- Do not dereference or free returned values.

Return contract:

- x0 is interpreted as `timespec64.tv_sec`.
- x1 is interpreted as `timespec64.tv_nsec`.
- `tv_sec` is nonnegative and nondecreasing across two short-repeat calls.
- `tv_nsec <= 999999999`.
- Each `tv_sec` lies between same-session `ktime_get_real_seconds()` before/after
  anchors.
- Anchor delta stays within the short-proof bound.

## Live Result

Private run:

`workspace/private/runs/kernel/live-call-proof-current-kernel-time64-return-pair-20260702T183219Z/`

Flash gate:

- Baseline v2321 `version/status/selftest` passed before flash.
- Candidate flashed only through `native_init_flash.py --from-native`.
- Candidate readback SHA matched
  `2c9c3a1638a98fc134158f49de80d1501f0d1eab50e59e828dc8d4b853e3c495`.
- Candidate helper selftest and explicit candidate health passed with
  `selftest fail=0`.
- Post-proof candidate health passed.
- Rollback to v2321 used only `native_init_flash.py --from-native`.
- Rollback readback SHA matched
  `ca978551aabe4b39563abaf529ccf2522054952d8b2ad852e632d26da88168cb`.
- Final v2321 `version/status/selftest` passed. The first final selftest parse
  lost the A90P1 END marker due serial noise; `hide` plus selftest retry passed.

Observed public proof values:

| Case | x0 `tv_sec` | x1 `tv_nsec` | Result |
| --- | ---: | ---: | --- |
| anchor before: `ktime_get_real_seconds()` | `0x5a545b2f` | n/a | pass |
| `current_kernel_time64()` call 1 | `0x5a545b2f` | `0x389fd96d` | pass |
| `current_kernel_time64()` call 2 | `0x5a545b30` | `0x1c03a16d` | pass |
| anchor after: `ktime_get_real_seconds()` | `0x5a545b30` | n/a | pass |

Checks:

- `all_returns_nondecreasing=true`
- `all_tv_nsec_in_range=true`
- `all_tv_sec_within_anchor_range=true`
- `anchor_delta=0x1`
- `repeat_count=2`
- `raw_runtime_values_redacted=true`

## Timing

Timeline source:

`workspace/private/runs/kernel/live-call-proof-current-kernel-time64-return-pair-20260702T183219Z/timeline.json`

The timeline uses the canonical top-level `events:[{name,timestamp_utc}]` shape
and includes the eight required phase events.

Key durations from the helper transcript and timeline:

| Phase | Elapsed |
| --- | ---: |
| candidate flash helper total | `66.455s` |
| live return-pair proof | `~2s` |
| rollback flash helper total | `63.948s` |
| candidate flash start to final rollback boot ready | `187s` |

## Validation

Host validation:

- `PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 workspace/public/src/scripts/revalidation/build_kernel_tier2_repl_v1_call_pair.py`
- `PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m py_compile ...`
- `PYTHONPATH=tests PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m unittest tests.test_kernel_tier2_repl_v1_call_pair tests.test_a90_repl_current_kernel_time64_pair`
  - `Ran 3 tests ... OK`
- `aarch64-linux-gnu-objdump` confirmed `blr x9` followed by x1/x0 lane moves.
- `git diff --check` rerun before commit.

Device validation:

- Preflight confirmed rollback/fallback boot image SHA values and TWRP artifacts.
- Bridge was reachable on the native-init serial endpoint.
- Baseline, candidate, post-proof, rollback, and final health checks all ended
  with `selftest fail=0`.

## Function-Map Outcome

`current_kernel_time64` is promoted from the earlier x0-only proof to a full
same-call `timespec64` x0/x1 aggregate-return proof:

- status: `live-proven`
- trusted input contract: no-argument read-only timekeeping state
- trusted return contract: x0=`tv_sec`, x1=`tv_nsec`
- auto-call policy: bounded call-pair proof only; not a mass-call target

With this result, the REPL ABI-shape matrix now has a representative for the
previously uncovered struct-return shape. The remaining REPL close criteria are
the finite observation bundles already recorded in `GOAL.md`; no additional
same-shape call-proof breadth is needed.
