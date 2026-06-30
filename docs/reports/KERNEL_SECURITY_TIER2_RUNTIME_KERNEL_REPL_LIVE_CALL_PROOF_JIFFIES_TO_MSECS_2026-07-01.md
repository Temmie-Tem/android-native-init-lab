# Kernel Security Tier-2 Runtime Kernel REPL - Live Call Proof: jiffies_to_msecs

- Date: 2026-07-01
- Decision: `a90-repl-live-call-proof-jiffies_to_msecs-pass`
- Scope: separately gated one-target live-call proof after the REPL epic close.
- Device action: yes, boot partition only through `native_init_flash.py`.
- Candidate image: `workspace/private/inputs/boot_images/boot_linux_tier2_repl_v1_repl.img`
- Candidate SHA256: `b846ae9f74d8ceb922bbcd854d78b6795ef833d61e38465d3cc474cb6f0dfb65`
- Rollback image: `workspace/private/inputs/boot_images/boot_linux_v2321_usb_clean_identity_rodata.img`
- Rollback SHA256: `ca978551aabe4b39563abaf529ccf2522054952d8b2ad852e632d26da88168cb`
- Private evidence: `workspace/private/runs/kernel/live-call-proof-jiffies-to-msecs-20260701/proof/a90_repl_evidence.json`

## Candidate Selection

This unit selected `jiffies_to_msecs` after the adjacent jiffies/time scalar helpers
`jiffies_to_usecs`, `jiffies_to_clock_t`, `clock_t_to_jiffies`, `jiffies_64_to_clock_t`,
`nsecs_to_jiffies64`, and `nsecs_to_jiffies` were already live-proven. The previously parked
`nsec_to_clock_t` stayed parked because C1 identity remains unresolved for that symbol in the current
map/image pair.

The only host-side blocker from the earlier sweep was the source-signature oracle attaching a
preprocessor continuation macro to the declaration. This unit fixed that parser bug by skipping
`#define ... \` continuation lines before signature extraction. After the fix, the source oracle
selected the exact scalar-only declaration from `include/linux/jiffies.h`.

The trusted contract is intentionally narrow: current-image scalar `unsigned long` jiffies inputs,
bounded so `j * 10` fits in `unsigned int`, return `j * 10`.

## Static Gate

Target:

- `jiffies_to_msecs`: `0xffffff8008158154`
- Resolution method: `export-recovery`
- Direct BL xrefs: `279`
- Next symbol boundary: `jiffies_to_usecs` at `+0x10`
- Source declaration: `include/linux/jiffies.h:291`,
  `extern unsigned int jiffies_to_msecs(const unsigned long j)`
- Source pointer contract: no pointer arguments.
- Call-safety tier: `SAFE-SCALAR`
- Required valid pointer args: none.
- Static word checks:
  - `0x0b000808`: add input to input shifted left by two, producing `j * 5`.
  - `0x531f7900`: logical shift left by one, producing `j * 10`.
  - `0xd65f03c0`: return.
  - `0x00be7bad`: next-entry guard before `jiffies_to_usecs`.

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
  tests.test_a90_repl.SelftestIntegrationTests.test_call_proof_jiffies_to_msecs_passes_with_bounded_multiply_contract

PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 \
  workspace/public/src/scripts/revalidation/a90_repl.py call-safety-classify \
  --map workspace/private/runs/kernel/v2c-c2b-kallsyms-padding-fix/System.map \
  --image workspace/private/inputs/boot_images/boot_linux_tier2_repl_v1_repl.img \
  --no-objdump \
  jiffies_to_msecs

PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 \
  workspace/public/src/scripts/revalidation/a90_repl.py call-safety-sweep \
  --map workspace/private/runs/kernel/v2c-c2b-kallsyms-padding-fix/System.map \
  --image workspace/private/inputs/boot_images/boot_linux_tier2_repl_v1_repl.img \
  --source-root workspace/private/inputs/kernel_source/SM-A908N_KOR_12_Opensource/Kernel \
  --regex '^jiffies_to_msecs$' \
  --no-objdump

PYTHONPATH=tests PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m unittest tests.test_a90_repl

git diff --check
```

Result:

- `py_compile`: pass.
- Focused tests: `Ran 4 tests`, `OK`.
- CLI classify: `SAFE-SCALAR`, verified by `export-recovery`, direct BL xrefs `279`, no required
  pointer args, first words matching the multiply-by-10 body.
- CLI sweep: advisory `SAFE-SCALAR`, scalar-only source declaration selected from
  `include/linux/jiffies.h:291`, gate seeded and auto-call allowed only for this vetted target.
- Full `tests.test_a90_repl`: `Ran 155 tests`, `OK`.
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
- First REPL selftest attempt hit serial input noise before the `A90P1 END` marker while writing the
  `panic_on_oops` guard. The retry using slow input mode returned `a90-repl-v2a1-selftest-pass`.

## Live Proof

Command:

```sh
A90CTL_INPUT_MODE=slow PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 \
  workspace/public/src/scripts/revalidation/a90_repl.py call-proof jiffies_to_msecs \
  --map workspace/private/runs/kernel/v2c-c2b-kallsyms-padding-fix/System.map \
  --image workspace/private/inputs/boot_images/boot_linux_tier2_repl_v1_repl.img \
  --source-root workspace/private/inputs/kernel_source/SM-A908N_KOR_12_Opensource/Kernel \
  --evidence-dir workspace/private/runs/kernel/live-call-proof-jiffies-to-msecs-20260701/proof
```

Public result:

```json
{
  "decision": "a90-repl-live-call-proof-jiffies_to_msecs-pass",
  "ok": true,
  "proof_status": "trusted-under-bounded-unsigned-long-multiply-by-10-contract",
  "input_contract": "scalar unsigned long jiffies value bounded so j * 10 fits in unsigned int; no pointer args",
  "return_contract": "unsigned int msec value equals j * 10 for fixed proof cases",
  "all_returns_match_expected": true,
  "case_count": 4,
  "raw_runtime_values_redacted": true
}
```

Case table:

| Case | Input | Expected | Observed |
| --- | --- | --- | --- |
| jiffies-to-msecs-mul10-zero | `0x0` | `0x0` | `0x0` |
| jiffies-to-msecs-mul10-one | `0x1` | `0xa` | `0xa` |
| jiffies-to-msecs-mul10-small-123 | `0x7b` | `0x4ce` | `0x4ce` |
| jiffies-to-msecs-mul10-uint-boundary | `0x19999999` | `0xfffffffa` | `0xfffffffa` |

Checks:

- `static-c1-identity`: OK, `jiffies_to_msecs` resolved by `export-recovery`.
- `static-next-symbol-boundary`: OK, next symbol `jiffies_to_usecs` at `+0x10`.
- `static-source-contract`: OK, scalar-only
  `extern unsigned int jiffies_to_msecs(const unsigned long j)` source declaration selected from
  `include/linux/jiffies.h`.
- `static-call-safety-contract`: OK, tier `SAFE-SCALAR`.
- Static word checks: OK for multiply-by-10 construction, return, and next guard.
- Fixed bounded multiply cases: OK; all four returns matched `j * 10`.
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
- A residual prompt token appeared once as an unknown command in the helper transcript, but the
  bounded helper verification passed.
- Final standalone selftest confirmed `pass=11 warn=1 fail=0`.

## Trust Boundary

`jiffies_to_msecs` is trusted only under the current-image bounded multiply-by-10 contract. This does
not authorize unbounded overflow-sensitive inputs, `nsec_to_clock_t`, alternate timer configurations
where the conversion body differs, or mass calling.
