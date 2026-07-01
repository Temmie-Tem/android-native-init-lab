# Kernel Security Tier-2 Runtime Kernel REPL - Live Call Proof: getboottime64

- Date: 2026-07-01
- Decision: `a90-repl-live-call-proof-getboottime64-pass`
- Scope: one-target live-call proof; boot partition only; rollback to `v2321`
- Candidate image: `workspace/private/inputs/boot_images/boot_linux_tier2_repl_v1_repl.img`
- Candidate SHA256: `b846ae9f74d8ceb922bbcd854d78b6795ef833d61e38465d3cc474cb6f0dfb65`
- Rollback image: `workspace/private/inputs/boot_images/boot_linux_v2321_usb_clean_identity_rodata.img`
- Rollback SHA256: `ca978551aabe4b39563abaf529ccf2522054952d8b2ad852e632d26da88168cb`
- Private evidence: `workspace/private/runs/kernel/live-call-proof-getboottime64-20260701T042618Z/proof/a90_repl_evidence.json`
- Private timeline: `workspace/private/runs/kernel/live-call-proof-getboottime64-20260701T042618Z/timeline.json`

## Target

`getboottime64(struct timespec64 *ts)` was selected as a boot-time
result-slot state writer. It extends the timekeeping proof set from monotonic
and realtime `struct timespec64` writers to boot wall-clock state: the valid
result is checked against same-session `realtime_seconds - monotonic_seconds`
anchor pairs.

Trusted contract:

- x0 is an owned `kmalloc` result slot sized for `struct timespec64` plus a
  trailing canary.
- The proof initializes the slot before each call and frees it with `kfree`
  after validation.
- Each target call is bracketed by `ktime_get_real_seconds()` and
  `ktime_get_seconds()` anchor calls.
- A valid result has `tv_sec` near the anchor-derived boot-time range,
  `0 <= tv_nsec < 1e9`, repeated readings stable within the serial REPL proof
  budget, changed result-slot bytes, and preserved canary.

## Static Gate

- Address: `getboottime64=0xffffff800816181c`.
- Resolution: `export-recovery`, map agrees with recovered export, C1 verified.
- Source declaration: `extern void getboottime64(struct timespec64 *ts)` at
  `include/linux/timekeeping.h:49`.
- ABI: one pointer argument, x0.
- C1 safety tier: `SAFE-WITH-VALID-PTR`, requiring
  `x0=owned-timespec64-result-slot`.
- Direct BL xrefs: `3`.
- No pre-call x0 deref rows were found; x0 is moved into x19 and used as the
  final result-slot store base.
- Next-symbol boundary: `get_seconds` at `+0x40`.
- Static word checks pinned the full 16-word body through the stack-check
  guard, including `ns_to_timespec` and final `stp x0, x1, [x19]`.
- Anchors `ktime_get_real_seconds=0xffffff800815f694` and
  `ktime_get_seconds=0xffffff800815f66c` remained `SAFE-SCALAR`.

## Live Run

Flash gate:

- Fallback images `v2237` and `v48`, v2321 rollback image, and TWRP recovery
  were present before flash.
- Baseline v2321 `version/status/selftest` passed before candidate flash.
- Candidate flash used `native_init_flash.py --from-native`; pushed-image SHA
  and boot readback SHA both matched the candidate SHA.
- Candidate `version/status` passed in the flash helper. The explicit
  candidate `selftest` command returned END rc=0/status=ok; its body was noisy
  on that pre-proof attempt, so the clean pass body was taken from the later
  post-proof health check.

Observed public values:

| Case | realtime before | monotonic before | tv_sec | tv_nsec | monotonic after | realtime after | Boot anchor range | Result |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| read 1 | `0x5a524417` | `0x6c` | `0x5a5243ab` | `0x0ec384f8` | `0x70` | `0x5a52441b` | `0x5a5243a4..0x5a5243b2` | PASS |
| read 2 | `0x5a52441e` | `0x74` | `0x5a5243ab` | `0x0ec384f8` | `0x77` | `0x5a524423` | `0x5a5243a4..0x5a5243b2` | PASS |

Both reads stayed inside the anchor-derived boot-time range, had valid nsec
range, repeated the same total nsec value, changed the result slot from the fill
pattern, preserved the trailing canary, and completed `kfree` cleanup.

Post-proof candidate health remained clean:

- `status`: `selftest pass=11 warn=1 fail=0`.
- `selftest`: `pass=11 warn=1 fail=0`.

Rollback:

- Rollback to `boot_linux_v2321_usb_clean_identity_rodata.img` used
  `native_init_flash.py --from-native`.
- Pushed-image SHA and boot readback SHA matched the v2321 SHA.
- Helper `version/status` verification passed after reboot.
- Final resident `version` confirmed `v2321-usb-clean-identity-rodata`.
- Final resident `selftest` passed after one `hide` serial resync retry:
  `selftest pass=11 warn=1 fail=0`.

## Timing

Timeline source:

- `workspace/private/runs/kernel/live-call-proof-getboottime64-20260701T042618Z/timeline.json`.

| Phase | Elapsed |
| --- | ---: |
| candidate flash helper total | `63s` |
| candidate flash start to boot ready | `70s` |
| live call-proof | `21s` |
| post-proof candidate health | `1s` |
| rollback flash helper total | `64s` |
| rollback flash start to boot ready | `64s` |
| final health total | `23s` |
| final health retry | `1` retry |
| candidate start to final health done | `285s` |

Notes:

- Final explicit `selftest` first attempt printed
  `selftest: pass=11 warn=1 fail=0` but lost the END marker to serial noise;
  `hide` plus `selftest` retry passed.
- No post-proof `busybox dmesg` log probe was run for this target, avoiding the
  unrelated native-exec log-probe WARN seen in the previous `getnstimeofday64`
  report.

## Validation

Host validation:

- `PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m py_compile workspace/public/src/scripts/revalidation/a90_repl.py tests/test_a90_repl.py`
- Focused tests:
  - `CallSafetyClassificationTests.test_seed_inventory_summary_counts_tiers`
  - `SelftestIntegrationTests.test_call_proof_getboottime64_passes_with_owned_boottime_timespec64_slot`
- Full regression:
  - `PYTHONPYCACHEPREFIX=/tmp/a90_pycache PYTHONPATH=tests python3 -m unittest tests.test_a90_repl`
  - Result: `Ran 187 tests in 158.996s`, `OK`.
- Static classifier:
  - `getboottime64`: `SAFE-WITH-VALID-PTR`, `export-recovery`,
    `0xffffff800816181c`, required pointer arg
    `owned-timespec64-result-slot`.
  - `ktime_get_real_seconds`: `SAFE-SCALAR`, `export-recovery`,
    `0xffffff800815f694`.
  - `ktime_get_seconds`: `SAFE-SCALAR`, `export-recovery`,
    `0xffffff800815f66c`.

## Function Map Entry

`getboottime64` is live-proven under exactly this contract:

- x0 must be an owned `kmalloc` `struct timespec64` result slot with trailing
  canary.
- The caller must validate the result against same-session
  `ktime_get_real_seconds() - ktime_get_seconds()` anchor pairs.
- The result slot must be freed after validation.

This proof does not authorize arbitrary pointers, mass calls, or relaxing the
C1 fail-closed identity/safety gate.
