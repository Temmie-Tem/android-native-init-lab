# Kernel Security Tier-2 Runtime Kernel REPL - Live Call Proof: getnstimeofday64

- Date: 2026-07-01
- Decision: `a90-repl-live-call-proof-getnstimeofday64-pass`
- Scope: one-target live-call proof; boot partition only; rollback to `v2321`
- Candidate image: `workspace/private/inputs/boot_images/boot_linux_tier2_repl_v1_repl.img`
- Candidate SHA256: `b846ae9f74d8ceb922bbcd854d78b6795ef833d61e38465d3cc474cb6f0dfb65`
- Rollback image: `workspace/private/inputs/boot_images/boot_linux_v2321_usb_clean_identity_rodata.img`
- Rollback SHA256: `ca978551aabe4b39563abaf529ccf2522054952d8b2ad852e632d26da88168cb`
- Private evidence: `workspace/private/runs/kernel/live-call-proof-getnstimeofday64-20260701T040907Z/proof/a90_repl_evidence.json`
- Private timeline: `workspace/private/runs/kernel/live-call-proof-getnstimeofday64-20260701T040907Z/timeline.json`

## Target

`getnstimeofday64(struct timespec64 *tv)` was selected as a realtime
result-slot state writer. It extends the current timekeeping proofs beyond the
previous no-arg seconds getter and the monotonic `ktime_get_ts64()` result-slot
writer by proving a wall-clock `struct timespec64` write into owned memory.

Trusted contract:

- x0 is an owned `kmalloc` result slot sized for `struct timespec64` plus a
  trailing canary.
- The proof initializes the slot before each call and frees it with `kfree`
  after validation.
- Each target call is bracketed by same-session `ktime_get_real_seconds()`
  anchor calls.
- A valid result has `tv_sec` inside the anchor range, `0 <= tv_nsec < 1e9`,
  repeated readings nondecreasing with bounded short delta, changed result-slot
  bytes, and preserved canary.

## Static Gate

- Address: `getnstimeofday64=0xffffff800815f174`.
- Resolution: `export-recovery`, map agrees with recovered export, C1 verified.
- Source declaration: `extern void getnstimeofday64(struct timespec64 *tv)` at
  `include/linux/timekeeping.h:48`.
- ABI: one pointer argument, x0.
- C1 safety tier: `SAFE-WITH-VALID-PTR`, requiring
  `x0=owned-timespec64-result-slot`.
- Direct BL xrefs: `88`.
- Early x0-derived deref/store is accepted only under the owned result-slot
  contract.
- Next-symbol boundary: `ktime_get` at `+0x128`.
- Static word checks pinned the prologue, clocksource read springboard, result
  slot stores, final `stp x9, x8, [x19]`, return, stack-check path, and guard.
- Anchor `ktime_get_real_seconds=0xffffff800815f694` remained
  `SAFE-SCALAR`.

## Live Run

Flash gate:

- Fallback images `v2237` and `v48`, v2321 rollback image, and TWRP recovery
  were present before flash.
- Baseline v2321 `version/status/selftest` passed before candidate flash.
- Candidate flash used `native_init_flash.py --from-native`; pushed-image SHA
  and boot readback SHA both matched the candidate SHA.
- Candidate `version/status` passed in the flash helper.
- Explicit candidate health passed after one serial resync retry:
  `version/status/selftest`, `selftest pass=11 warn=1 fail=0`.

Observed public values:

| Case | anchor before | tv_sec | tv_nsec | anchor after | Result |
| --- | ---: | ---: | ---: | ---: | --- |
| read 1 | `0x5a524059` | `0x5a524059` | `0x232e4641` | `0x5a52405d` | PASS |
| read 2 | `0x5a524060` | `0x5a524061` | `0x0e3e62b1` | `0x5a524064` | PASS |

The second reading was nondecreasing from the first with
`delta_nsec_from_previous=0x1c7e66c70`. The result slot changed from the fill
pattern, the trailing canary was preserved, and `kfree` cleanup succeeded.

Post-proof candidate health remained clean:

- `status`: `selftest pass=11 warn=1 fail=0`.
- `selftest`: `pass=11 warn=1 fail=0`.

Log note:

- A post-proof `busybox dmesg` collection command exposed a kernel WARN in
  `a90_android_exe` on the `subsystem_put()` close path for `esoc0`
  (`Reference count mismatch`). The call trace is not in the REPL target path
  and occurred during log collection after the proof had passed. A follow-up
  selftest still returned `pass=11 warn=1 fail=0`. This is recorded as a
  residual native-exec/log-probe warning, not a `getnstimeofday64` contract
  failure.

Rollback:

- Rollback to `boot_linux_v2321_usb_clean_identity_rodata.img` used
  `native_init_flash.py --from-native`.
- Pushed-image SHA and boot readback SHA matched the v2321 SHA.
- Helper `version/status` verification passed after reboot.
- Final resident health passed after `hide` serial resync:
  `selftest pass=11 warn=1 fail=0`, `version` confirmed
  `v2321-usb-clean-identity-rodata`.

## Timing

Timeline source:

- `workspace/private/runs/kernel/live-call-proof-getnstimeofday64-20260701T040907Z/timeline.json`.

| Phase | Elapsed |
| --- | ---: |
| candidate flash helper total | `64s` |
| candidate flash start to boot ready | `71s` |
| live call-proof | `21s` |
| post-proof candidate health/log probe | `7s` |
| rollback flash helper total | `64s` |
| rollback flash start to boot ready | `75s` |
| final health total | `75s` |
| final health retry | `2s` |
| candidate start to final health done | `433s` |

Notes:

- Candidate explicit `selftest` first attempt lost the END marker to `ATATAT`
  serial noise; `hide` plus `version/status/selftest` retry passed.
- Final explicit `selftest` first attempt printed
  `selftest: pass=11 warn=1 fail=0` but lost the END marker to `AT` serial
  noise; `hide` plus `selftest/version` retry passed.

## Validation

Host validation:

- `PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m py_compile workspace/public/src/scripts/revalidation/a90_repl.py tests/test_a90_repl.py`
- Focused tests:
  - `CallSafetyClassificationTests.test_seed_inventory_summary_counts_tiers`
  - `SelftestIntegrationTests.test_call_proof_getnstimeofday64_passes_with_owned_realtime_timespec64_slot`
- Full regression:
  - `PYTHONPYCACHEPREFIX=/tmp/a90_pycache PYTHONPATH=tests python3 -m unittest tests.test_a90_repl`
  - Result: `Ran 186 tests in 157.197s`, `OK`.
- Static classifier:
  - `getnstimeofday64`: `SAFE-WITH-VALID-PTR`, `export-recovery`,
    `0xffffff800815f174`, required pointer arg
    `owned-timespec64-result-slot`.
  - `ktime_get_real_seconds`: `SAFE-SCALAR`, `export-recovery`,
    `0xffffff800815f694`.

## Function Map Entry

`getnstimeofday64` is live-proven under exactly this contract:

- x0 must be an owned `kmalloc` `struct timespec64` result slot with trailing
  canary.
- The caller must validate the result against same-session
  `ktime_get_real_seconds()` anchors.
- The result slot must be freed after validation.

This proof does not authorize arbitrary pointers, mass calls, or relaxing the
C1 fail-closed identity/safety gate.
