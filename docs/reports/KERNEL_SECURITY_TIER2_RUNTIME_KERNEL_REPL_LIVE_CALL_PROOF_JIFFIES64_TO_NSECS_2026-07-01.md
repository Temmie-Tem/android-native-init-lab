# Kernel Security Tier-2 Runtime Kernel REPL - Live Call Proof: jiffies64_to_nsecs

- Date: 2026-07-01
- Decision: `a90-repl-live-call-proof-jiffies64_to_nsecs-pass`
- Scope: separately gated one-target live-call proof after the REPL epic close.
- Device action: yes, boot partition only through `native_init_flash.py`.
- Candidate image: `workspace/private/inputs/boot_images/boot_linux_tier2_repl_v1_repl.img`
- Candidate SHA256: `b846ae9f74d8ceb922bbcd854d78b6795ef833d61e38465d3cc474cb6f0dfb65`
- Rollback image: `workspace/private/inputs/boot_images/boot_linux_v2321_usb_clean_identity_rodata.img`
- Rollback SHA256: `ca978551aabe4b39563abaf529ccf2522054952d8b2ad852e632d26da88168cb`
- Private evidence: `workspace/private/runs/kernel/live-call-proof-jiffies64-to-nsecs-20260701/proof/a90_repl_evidence.json`

## Candidate Selection

This unit selected `jiffies64_to_nsecs` after the adjacent scalar jiffies and nanosecond helpers
`jiffies_64_to_clock_t`, `jiffies_to_clock_t`, `clock_t_to_jiffies`, `jiffies_to_usecs`,
`jiffies_to_msecs`, `nsecs_to_jiffies64`, and `nsecs_to_jiffies` were already live-proven.
`nsec_to_clock_t` stayed parked because C1 identity remains unresolved for that symbol in the
current map/image pair.

The trusted contract is intentionally narrow: current-image scalar `u64` jiffies inputs, bounded so
`j * 10000000` fits in `u64`, return `j * 10000000`.

## Static Gate

Target:

- `jiffies64_to_nsecs`: `0xffffff80081585b4`
- Resolution method: `export-recovery`
- Direct BL xrefs: `1`
- Next symbol boundary: `nsecs_to_jiffies64` at `+0x18`
- Source declaration: `include/linux/jiffies.h:299`, `extern u64 jiffies64_to_nsecs(u64 j)`
- Source pointer contract: no pointer arguments.
- Call-safety tier: `SAFE-SCALAR`
- Required valid pointer args: none.
- Static word checks:
  - `0x5292d008`: load multiplier low halfword `0x9680`.
  - `0x72a01308`: load multiplier high halfword `0x0098`, producing `0x989680`.
  - `0x9b087c00`: 64-bit multiply.
  - `0xd65f03c0`: return.
  - `0xd503201f`: alignment NOP before next entry.
  - `0x00be7bad`: next-entry guard before `nsecs_to_jiffies64`.

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
  tests.test_a90_repl.SelftestIntegrationTests.test_call_proof_jiffies64_to_nsecs_passes_with_bounded_multiply_contract

PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 \
  workspace/public/src/scripts/revalidation/a90_repl.py call-safety-classify \
  --map workspace/private/runs/kernel/v2c-c2b-kallsyms-padding-fix/System.map \
  --image workspace/private/inputs/boot_images/boot_linux_tier2_repl_v1_repl.img \
  --no-objdump \
  jiffies64_to_nsecs

PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 \
  workspace/public/src/scripts/revalidation/a90_repl.py call-safety-sweep \
  --map workspace/private/runs/kernel/v2c-c2b-kallsyms-padding-fix/System.map \
  --image workspace/private/inputs/boot_images/boot_linux_tier2_repl_v1_repl.img \
  --source-root workspace/private/inputs/kernel_source/SM-A908N_KOR_12_Opensource/Kernel \
  --no-objdump \
  jiffies64_to_nsecs

PYTHONPATH=tests PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m unittest tests.test_a90_repl

git diff --check
```

Result:

- `py_compile`: pass.
- Focused tests: `Ran 4 tests`, `OK`.
- CLI classify: `SAFE-SCALAR`, verified by `export-recovery`, direct BL xrefs `1`, no required
  pointer args, first words matching the multiply-by-10000000 body.
- CLI sweep: advisory `SAFE-SCALAR`, scalar-only source declaration selected from
  `include/linux/jiffies.h:299`, gate seeded and auto-call allowed only for this vetted target.
- Full `tests.test_a90_repl`: `Ran 156 tests`, `OK`.
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
- Slow-mode REPL selftest returned `a90-repl-v2a1-selftest-pass`.

## Live Proof

Command:

```sh
A90CTL_INPUT_MODE=slow PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 \
  workspace/public/src/scripts/revalidation/a90_repl.py call-proof jiffies64_to_nsecs \
  --map workspace/private/runs/kernel/v2c-c2b-kallsyms-padding-fix/System.map \
  --image workspace/private/inputs/boot_images/boot_linux_tier2_repl_v1_repl.img \
  --source-root workspace/private/inputs/kernel_source/SM-A908N_KOR_12_Opensource/Kernel \
  --evidence-dir workspace/private/runs/kernel/live-call-proof-jiffies64-to-nsecs-20260701/proof
```

Public result:

```json
{
  "decision": "a90-repl-live-call-proof-jiffies64_to_nsecs-pass",
  "ok": true,
  "proof_status": "trusted-under-bounded-u64-multiply-by-10000000-contract",
  "input_contract": "scalar u64 jiffies value bounded so j * 10000000 fits in u64; no pointer args",
  "return_contract": "u64 nsec value equals j * 10000000 for fixed proof cases",
  "all_returns_match_expected": true,
  "case_count": 4,
  "raw_runtime_values_redacted": true
}
```

Case table:

| Case | Input | Expected | Observed |
| --- | --- | --- | --- |
| jiffies64-to-nsecs-mul10000000-zero | `0x0` | `0x0` | `0x0` |
| jiffies64-to-nsecs-mul10000000-one | `0x1` | `0x989680` | `0x989680` |
| jiffies64-to-nsecs-mul10000000-one-second-at-hz100 | `0x64` | `0x3b9aca00` | `0x3b9aca00` |
| jiffies64-to-nsecs-mul10000000-u64-safe-boundary | `0x1ad7f29abca` | `0xffffffffff6e4100` | `0xffffffffff6e4100` |

Checks:

- `static-c1-identity`: OK, `jiffies64_to_nsecs` resolved by `export-recovery`.
- `static-next-symbol-boundary`: OK, next symbol `nsecs_to_jiffies64` at `+0x18`.
- `static-source-contract`: OK, scalar-only `extern u64 jiffies64_to_nsecs(u64 j)` source
  declaration selected from `include/linux/jiffies.h`.
- `static-call-safety-contract`: OK, tier `SAFE-SCALAR`.
- Static word checks: OK for multiplier construction, multiply, return, alignment NOP, and next
  guard.
- Fixed bounded multiply cases: OK; all four returns matched `j * 10000000`.
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
- Final standalone selftest confirmed `pass=11 warn=1 fail=0`.

## Trust Boundary

`jiffies64_to_nsecs` is trusted only under the current-image bounded multiply-by-10000000 contract.
This does not authorize overflow-sensitive inputs above the bounded proof range, `nsec_to_clock_t`,
alternate timer configurations where the conversion body differs, or mass calling.
