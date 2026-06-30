# Kernel Security Tier-2 Runtime Kernel REPL - Live Call Proof: nsecs_to_jiffies

- Date: 2026-07-01
- Decision: `a90-repl-live-call-proof-nsecs_to_jiffies-pass`
- Scope: separately gated one-target live-call proof after the REPL epic close.
- Device action: yes, boot partition only through `native_init_flash.py`.
- Candidate image: `workspace/private/inputs/boot_images/boot_linux_tier2_repl_v1_repl.img`
- Candidate SHA256: `b846ae9f74d8ceb922bbcd854d78b6795ef833d61e38465d3cc474cb6f0dfb65`
- Rollback image: `workspace/private/inputs/boot_images/boot_linux_v2321_usb_clean_identity_rodata.img`
- Rollback SHA256: `ca978551aabe4b39563abaf529ccf2522054952d8b2ad852e632d26da88168cb`
- Private evidence: `workspace/private/runs/kernel/live-call-proof-nsecs-to-jiffies-20260701/proof/a90_repl_evidence.json`

## Candidate Selection

This unit selected `nsecs_to_jiffies` after the adjacent `nsecs_to_jiffies64` contract was proven.
`nsec_to_clock_t` stayed parked because C1 identity verification remains unresolved for that symbol
in the current map/image pair. `nsecs_to_jiffies` was selected because it is scalar-only,
C1-verified by `export-recovery`, has no pre-call argument memory dereference, has seven direct BL
xrefs, and its current-image body is the same compact fixed-point divide-by-10000000 leaf used by
`nsecs_to_jiffies64`.

The trusted contract is intentionally narrow: current-image scalar `u64` nanosecond inputs return
`(n * 0xd6bf94d5e57a42bd) >> 87` as an `unsigned long` jiffies value for the fixed proof cases.

## Static Gate

Target:

- `nsecs_to_jiffies`: `0xffffff80081585ec`
- Resolution method: `export-recovery`
- Direct BL xrefs: `7`
- Next symbol boundary: `timespec_add_safe` at `+0x20`
- Source declaration: `include/linux/jiffies.h:454`,
  `extern unsigned long nsecs_to_jiffies(u64 n)`
- Source pointer contract: no pointer arguments.
- Call-safety tier: `SAFE-SCALAR`
- Required valid pointer args: none.
- Static word checks:
  - `0xd28857a8`, `0xf2bcaf48`, `0xf2d29aa8`, `0xf2fad7e8`: build magic
    `0xd6bf94d5e57a42bd`.
  - `0x9bc87c08`: `umulh`.
  - `0xd357fd00`: logical shift right by `23`, making the total fixed-point shift `87`.
  - `0xd65f03c0`: return.
  - `0x00be7bad`: next-entry guard before `timespec_add_safe`.

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
  tests.test_a90_repl.SelftestIntegrationTests.test_call_proof_nsecs_to_jiffies_passes_with_fixed_point_contract

PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 \
  workspace/public/src/scripts/revalidation/a90_repl.py call-safety-classify \
  --map workspace/private/runs/kernel/v2c-c2b-kallsyms-padding-fix/System.map \
  --image workspace/private/inputs/boot_images/boot_linux_tier2_repl_v1_repl.img \
  --no-objdump \
  nsecs_to_jiffies

PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 \
  workspace/public/src/scripts/revalidation/a90_repl.py call-safety-sweep \
  --map workspace/private/runs/kernel/v2c-c2b-kallsyms-padding-fix/System.map \
  --image workspace/private/inputs/boot_images/boot_linux_tier2_repl_v1_repl.img \
  --source-root workspace/private/inputs/kernel_source/SM-A908N_KOR_12_Opensource/Kernel \
  --regex '^nsecs_to_jiffies$' \
  --no-objdump

PYTHONPATH=tests PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m unittest tests.test_a90_repl

git diff --check
```

Result:

- `py_compile`: pass.
- Focused tests: `Ran 4 tests`, `OK`.
- CLI classify: `SAFE-SCALAR`, verified by `export-recovery`, direct BL xrefs `7`, no required
  pointer args, first words matching the fixed-point conversion body.
- CLI sweep: advisory `SAFE-SCALAR`, scalar-only source declaration selected from
  `include/linux/jiffies.h:454`, gate seeded and auto-call allowed only for this vetted target.
- Full `tests.test_a90_repl`: `Ran 154 tests`, `OK`.
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
- First standalone candidate selftest read hit serial input noise before the `A90P1 END` marker; the
  sequential retry captured the END marker and confirmed `pass=11 warn=1 fail=0`.
- REPL selftest completed and returned `a90-repl-v2a1-selftest-pass`.

## Live Proof

Command:

```sh
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 \
  workspace/public/src/scripts/revalidation/a90_repl.py call-proof nsecs_to_jiffies \
  --map workspace/private/runs/kernel/v2c-c2b-kallsyms-padding-fix/System.map \
  --image workspace/private/inputs/boot_images/boot_linux_tier2_repl_v1_repl.img \
  --source-root workspace/private/inputs/kernel_source/SM-A908N_KOR_12_Opensource/Kernel \
  --evidence-dir workspace/private/runs/kernel/live-call-proof-nsecs-to-jiffies-20260701/proof
```

Public result:

```json
{
  "decision": "a90-repl-live-call-proof-nsecs_to_jiffies-pass",
  "ok": true,
  "proof_status": "trusted-under-current-image-fixed-point-divide-by-10000000-contract",
  "input_contract": "scalar u64 nanosecond value; no pointer args; current image leaf body is fixed-point divide-by-10000000",
  "return_contract": "unsigned long jiffies value equals (n * 0xd6bf94d5e57a42bd) >> 87 for fixed proof cases",
  "all_returns_match_expected": true,
  "case_count": 6,
  "raw_runtime_values_redacted": true
}
```

Case table:

| Case | Input | Expected | Observed |
| --- | --- | --- | --- |
| nsecs-to-jiffies-div10000000-zero | `0x0` | `0x0` | `0x0` |
| nsecs-to-jiffies-div10000000-sub-tick | `0x98967f` | `0x0` | `0x0` |
| nsecs-to-jiffies-div10000000-one-tick | `0x989680` | `0x1` | `0x1` |
| nsecs-to-jiffies-div10000000-mixed-123456789 | `0x75bcd15` | `0xc` | `0xc` |
| nsecs-to-jiffies-div10000000-one-second | `0x3b9aca00` | `0x64` | `0x64` |
| nsecs-to-jiffies-div10000000-max-u64 | `0xffffffffffffffff` | `0x1ad7f29abca` | `0x1ad7f29abca` |

Checks:

- `static-c1-identity`: OK, `nsecs_to_jiffies` resolved by `export-recovery`.
- `static-next-symbol-boundary`: OK, next symbol `timespec_add_safe` at `+0x20`.
- `static-source-contract`: OK, scalar-only `extern unsigned long nsecs_to_jiffies(u64 n)` source
  declaration selected from `include/linux/jiffies.h`.
- `static-call-safety-contract`: OK, tier `SAFE-SCALAR`.
- Static word checks: OK for magic construction, `umulh`, `lsr #23`, return, and next guard.
- Fixed-point conversion cases: OK; all six returns matched `(n * 0xd6bf94d5e57a42bd) >> 87`.
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
- First final standalone selftest read hit serial input noise before the `A90P1 END` marker; the
  sequential retry captured the END marker and confirmed `pass=11 warn=1 fail=0`.

## Trust Boundary

`nsecs_to_jiffies` is trusted only under the current-image fixed-point divide-by-10000000 contract.
This does not authorize `nsec_to_clock_t`, alternate timer configurations where the conversion body
differs, or mass calling.
