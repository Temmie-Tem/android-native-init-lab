# Kernel Security Tier-2 Runtime Kernel REPL - Live Call Proof: __msecs_to_jiffies

- Date: 2026-07-01
- Decision: `a90-repl-live-call-proof-__msecs_to_jiffies-pass`
- Scope: separately gated one-target live-call proof after the REPL epic close.
- Device action: yes, boot partition only through `native_init_flash.py`.
- Candidate image: `workspace/private/inputs/boot_images/boot_linux_tier2_repl_v1_repl.img`
- Candidate SHA256: `b846ae9f74d8ceb922bbcd854d78b6795ef833d61e38465d3cc474cb6f0dfb65`
- Rollback image: `workspace/private/inputs/boot_images/boot_linux_v2321_usb_clean_identity_rodata.img`
- Rollback SHA256: `ca978551aabe4b39563abaf529ccf2522054952d8b2ad852e632d26da88168cb`
- Private evidence: `workspace/private/runs/kernel/live-call-proof-msecs-to-jiffies-20260701/proof/a90_repl_evidence.json`

## Candidate Selection

The current implemented `CALL_PROOF_TARGETS` inventory was fully covered by prior live reports, so
this unit expanded the one-target proof map with a new scalar candidate. Host-only triage compared
`__msecs_to_jiffies`, `__usecs_to_jiffies`, and the still-parked `nsec_to_clock_t`.
`nsec_to_clock_t` remained excluded because C1 identity verification is unavailable for that symbol
in the current map/image pair. `__msecs_to_jiffies` was selected because it is export-recovered,
leaf/no-BL, source scalar-only, and has high direct BL xref coverage.

The trusted contract is intentionally narrow: current-image scalar `unsigned int` millisecond input.
If bit 31 is set, the value follows the kernel "negative timeout" convention and saturates to
`MAX_JIFFY_OFFSET`. Otherwise the HZ=100 body returns `ceil(m / 10)`.

## Static Gate

Target:

- `__msecs_to_jiffies`: `0xffffff80081583ec`
- Resolution method: `export-recovery`
- Direct BL xrefs: `398`
- Next symbol boundary: `__usecs_to_jiffies` at `+0x28`
- Source declaration: `include/linux/jiffies.h:301`,
  `extern unsigned long __msecs_to_jiffies(const unsigned int m)`
- Source pointer contract: no pointer arguments.
- Call-safety tier: `SAFE-SCALAR`
- Required valid pointer args: none.
- Static word checks:
  - `0x529999a8`: load low halfword for divide-by-10 magic `0xcccccccd`.
  - `0x11002409`: add rounding constant `9`.
  - `0x72b99988`: load high halfword for divide-by-10 magic `0xcccccccd`.
  - `0x7201001f`: test bit 31 for signed-negative timeout semantics.
  - `0x9ba87d28`: unsigned multiply long.
  - `0xb27ff3e9`: load `MAX_JIFFY_OFFSET`.
  - `0xd363fd08`: logical shift right by `35`.
  - `0x9a881120`: select saturation or rounded divide-by-10 result.
  - `0xd65f03c0`: return.
  - `0x00be7bad`: next-entry guard before `__usecs_to_jiffies`.

## Host Validation

Commands:

```sh
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m py_compile \
  workspace/public/src/scripts/revalidation/a90_repl.py \
  tests/test_a90_repl.py

PYTHONPATH=tests PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m unittest \
  tests.test_a90_repl.CallSafetyClassificationTests.test_proven_live_call_targets_stay_safe \
  tests.test_a90_repl.CallSafetyClassificationTests.test_seed_inventory_summary_counts_tiers \
  tests.test_a90_repl.CallSafetyClassificationTests.test_source_signature_oracle_distinguishes_scalar_and_pointer_args \
  tests.test_a90_repl.SelftestIntegrationTests.test_call_proof_msecs_to_jiffies_passes_with_hz100_roundup_contract

PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 \
  workspace/public/src/scripts/revalidation/a90_repl.py call-safety-classify \
  --map workspace/private/runs/kernel/v2c-c2b-kallsyms-padding-fix/System.map \
  --image workspace/private/inputs/boot_images/boot_linux_tier2_repl_v1_repl.img \
  --no-objdump \
  __msecs_to_jiffies

PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 \
  workspace/public/src/scripts/revalidation/a90_repl.py call-safety-sweep \
  --map workspace/private/runs/kernel/v2c-c2b-kallsyms-padding-fix/System.map \
  --image workspace/private/inputs/boot_images/boot_linux_tier2_repl_v1_repl.img \
  --source-root workspace/private/inputs/kernel_source/SM-A908N_KOR_12_Opensource/Kernel \
  --no-objdump \
  __msecs_to_jiffies

PYTHONPATH=tests PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m unittest tests.test_a90_repl

git diff --check
```

Result:

- `py_compile`: pass.
- Focused tests: `Ran 4 tests`, `OK`.
- CLI classify: `SAFE-SCALAR`, verified by `export-recovery`, direct BL xrefs `398`, no required
  pointer args, first words matching the HZ=100 round-up/saturation body.
- CLI sweep: advisory `SAFE-SCALAR`, scalar-only source declaration selected from
  `include/linux/jiffies.h:301`, gate seeded and auto-call allowed only for this vetted target.
- Full `tests.test_a90_repl`: `Ran 157 tests`, `OK`.
- `git diff --check`: pass.

## Flash And Health

Preconditions:

- v1-repl candidate SHA matched `b846ae9f74d8ceb922bbcd854d78b6795ef833d61e38465d3cc474cb6f0dfb65`.
- v2321 rollback SHA matched `ca978551aabe4b39563abaf529ccf2522054952d8b2ad852e632d26da88168cb`.
- v2237 fallback SHA matched `b2ea2d26d160b7702ce7d4438b84367788eea26c6a5bbe4ed93f3d270292ac7f`.
- Final fallback `boot_linux_v48.img` existed with SHA
  `1c87fa59712395027c5c2e489b15c4f6ddefabc3c50f78d3c235c4508a63e042`.
- TWRP recovery image existed with SHA
  `b1ef377a52ec8ab43b49a5fcc7a0b27e8efff91bf2d8cccdc565ecadadcc646c`.
- TWRP recovery tar existed with SHA
  `6d9e929462ea4c85f257b080431d387d5bfb787ff800bd4178c823c3874d862a`.
- Bridge was connected.
- Baseline before flash: v2321 `version` OK, `status` OK, `selftest pass=11 warn=1 fail=0`.

Candidate flash:

```sh
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 \
  workspace/public/src/scripts/revalidation/native_init_flash.py \
  workspace/private/inputs/boot_images/boot_linux_tier2_repl_v1_repl.img \
  --expect-sha256 b846ae9f74d8ceb922bbcd854d78b6795ef833d61e38465d3cc474cb6f0dfb65 \
  --expect-readback-sha256 b846ae9f74d8ceb922bbcd854d78b6795ef833d61e38465d3cc474cb6f0dfb65 \
  --verify-protocol cmdv1 \
  --from-native
```

Result:

- Remote pushed image SHA matched candidate SHA.
- Boot readback SHA matched candidate SHA.
- Helper `version/status` verification passed after reboot.
- The v1-repl boot artifact intentionally keeps the native-init display string at the v2321
  checkpoint; the boot readback SHA and the subsequent REPL selftest are the artifact identity gate.
- First REPL selftest attempt hit serial input noise while writing the `panic_on_oops` guard; the
  slow-mode retry returned `a90-repl-v2a1-selftest-pass`.

## Live Proof

Command:

```sh
A90CTL_INPUT_MODE=slow PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 \
  workspace/public/src/scripts/revalidation/a90_repl.py call-proof __msecs_to_jiffies \
  --map workspace/private/runs/kernel/v2c-c2b-kallsyms-padding-fix/System.map \
  --image workspace/private/inputs/boot_images/boot_linux_tier2_repl_v1_repl.img \
  --source-root workspace/private/inputs/kernel_source/SM-A908N_KOR_12_Opensource/Kernel \
  --evidence-dir workspace/private/runs/kernel/live-call-proof-msecs-to-jiffies-20260701/proof
```

Public result:

```json
{
  "decision": "a90-repl-live-call-proof-__msecs_to_jiffies-pass",
  "ok": true,
  "proof_status": "trusted-under-hz100-round-up-divide-by-10-and-negative-saturation-contract",
  "input_contract": "scalar unsigned int millisecond value; if bit31 is set it is treated as negative and saturates to MAX_JIFFY_OFFSET; no pointer args",
  "return_contract": "unsigned long jiffies value equals MAX_JIFFY_OFFSET for bit31-set inputs, otherwise ceil(m / 10) for fixed proof cases",
  "all_returns_match_expected": true,
  "case_count": 6,
  "raw_runtime_values_redacted": true
}
```

Case table:

| Case | Input | Expected | Observed |
| --- | --- | --- | --- |
| msecs-to-jiffies-hz100-zero | `0x0` | `0x0` | `0x0` |
| msecs-to-jiffies-hz100-one | `0x1` | `0x1` | `0x1` |
| msecs-to-jiffies-hz100-ten | `0xa` | `0x1` | `0x1` |
| msecs-to-jiffies-hz100-eleven | `0xb` | `0x2` | `0x2` |
| msecs-to-jiffies-hz100-positive-boundary | `0x7fffffff` | `0xccccccd` | `0xccccccd` |
| msecs-to-jiffies-hz100-negative-bit | `0x80000000` | `0x3ffffffffffffffe` | `0x3ffffffffffffffe` |

Checks:

- `static-c1-identity`: OK, `__msecs_to_jiffies` resolved by `export-recovery`.
- `static-next-symbol-boundary`: OK, next symbol `__usecs_to_jiffies` at `+0x28`.
- `static-source-contract`: OK, scalar-only
  `extern unsigned long __msecs_to_jiffies(const unsigned int m)` source declaration selected from
  `include/linux/jiffies.h`.
- `static-call-safety-contract`: OK, tier `SAFE-SCALAR`.
- Static word checks: OK for divide-by-10 magic load, rounding add, bit31 test, multiply, saturation
  constant, shift, conditional select, return, and next guard.
- Fixed HZ=100 round-up and saturation cases: OK; all six returns matched the predeclared contract.
- Cleanup: not applicable. No owned resource was created, and no returned pointer exists.

Raw per-boot slide and target runtime address were written only to private evidence and are not
included in this report.

Candidate selftest after proof: `pass=11 warn=1 fail=0`.

## Rollback

Rollback command:

```sh
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 \
  workspace/public/src/scripts/revalidation/native_init_flash.py \
  workspace/private/inputs/boot_images/boot_linux_v2321_usb_clean_identity_rodata.img \
  --expect-sha256 ca978551aabe4b39563abaf529ccf2522054952d8b2ad852e632d26da88168cb \
  --expect-readback-sha256 ca978551aabe4b39563abaf529ccf2522054952d8b2ad852e632d26da88168cb \
  --verify-protocol cmdv1 \
  --from-native
```

Result:

- Remote pushed rollback image SHA matched rollback SHA.
- Boot readback SHA matched rollback SHA.
- Helper `version/status` verification passed after reboot.
- First standalone selftest after rollback hit serial input noise before the END marker. Slow-mode
  retry confirmed `pass=11 warn=1 fail=0`.

## Trust Boundary

`__msecs_to_jiffies` is trusted only under the current-image HZ=100 round-up divide-by-10 and
bit31-set saturation contract. This does not authorize alternate timer configurations where the
conversion body differs, `nsec_to_clock_t`, unverified map entries, or mass calling.
