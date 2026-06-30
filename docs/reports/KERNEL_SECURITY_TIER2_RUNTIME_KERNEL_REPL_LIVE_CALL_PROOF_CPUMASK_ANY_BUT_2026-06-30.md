# Kernel Security Tier-2 Runtime Kernel REPL - Live Call Proof: cpumask_any_but

- Date: 2026-06-30
- Decision: `a90-repl-live-call-proof-cpumask_any_but-pass`
- Scope: separately gated one-target live-call proof after the REPL epic close.
- Device action: yes, boot partition only through `native_init_flash.py`.
- Candidate image: `workspace/private/inputs/boot_images/boot_linux_tier2_repl_v1_repl.img`
- Candidate SHA256: `b846ae9f74d8ceb922bbcd854d78b6795ef833d61e38465d3cc474cb6f0dfb65`
- Rollback image: `workspace/private/inputs/boot_images/boot_linux_v2321_usb_clean_identity_rodata.img`
- Rollback SHA256: `ca978551aabe4b39563abaf529ccf2522054952d8b2ad852e632d26da88168cb`
- Private evidence: `workspace/private/runs/kernel/live-call-proof-cpumask-any-but-20260630/proof/a90_repl_evidence.json`

## Candidate Selection

This unit continued the cpumask wrapper sweep after `cpumask_next`. `cpumask_any_but` was selected
because it has one cpumask pointer, one scalar excluded CPU, a verified export identity, and a small
wrapper shape over the already proven `find_next_bit` path.

Wider candidates stayed parked:

- `cpumask_next_and`: two cpumask pointers and direct memory flow from the second mask.
- `cpumask_next_wrap`: wrap semantics and four arguments.
- `bitmap_ord_to_pos`: C1 identity remained unverified by direct xref evidence.

The selected target is not trusted as a general cpumask facility. The proof creates an owned kernel
cpumask buffer, verifies the wrapper loads compiled `nr_cpumask_bits=8`, reads runtime
`nr_cpu_ids`, calls bounded scalar exclusion cases, checks the return table, re-peeks the
cpumask/canary after every call, and frees the allocation.

## Static Gate

Target:

- `cpumask_any_but`: `0xffffff80099a9ebc`
- Resolution method: `export-recovery`
- Direct BL xrefs: `1`
- Shape: JOPP entry, non-leaf wrapper, one BL to `find_next_bit`.
- Wrapper evidence: first words include `0x52800101` (`mov w1,#8`), gating the compiled
  `nr_cpumask_bits=8` contract.
- Source signature: `include/linux/cpumask.h:217`,
  `int cpumask_any_but(const struct cpumask *mask, unsigned int cpu)`
- Source pointer contract: x0 is `const struct cpumask *mask`; x1 is scalar excluded CPU.
- Call-safety tier: `SAFE-WITH-VALID-PTR`
- Required valid pointer args: x0 `cpumask-buffer`.
- Static `nr_cpu_ids`: `8`.

The target was not called with an arbitrary numeric pointer. The proof requires an owned cpumask
buffer and scalar excluded CPU values inside runtime `nr_cpu_ids`.

## Host Validation

Commands:

```sh
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m py_compile \
  workspace/public/src/scripts/revalidation/a90_repl.py \
  tests/test_a90_repl.py

PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 \
  workspace/public/src/scripts/revalidation/a90_repl.py call-safety-classify \
  --map workspace/private/runs/kernel/v2c-c2b-kallsyms-padding-fix/System.map \
  --image workspace/private/inputs/boot_images/boot_linux_tier2_repl_v1_repl.img \
  --no-objdump \
  cpumask_any_but

PYTHONPATH=tests PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m unittest \
  tests.test_a90_repl.CallSafetyClassificationTests.test_proven_live_call_targets_stay_safe \
  tests.test_a90_repl.CallSafetyClassificationTests.test_seed_inventory_summary_counts_tiers \
  tests.test_a90_repl.CallSafetyClassificationTests.test_source_signature_oracle_distinguishes_scalar_and_pointer_args \
  tests.test_a90_repl.SelftestIntegrationTests.test_call_proof_cpumask_any_but_passes_with_owned_cpumask_contract

PYTHONPATH=tests PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m unittest tests.test_a90_repl
```

Result:

- `py_compile`: pass.
- CLI classify: `SAFE-WITH-VALID-PTR`, verified by `export-recovery`, direct-BL xrefs `1`,
  non-leaf wrapper, required x0 `cpumask-buffer`, first words include `0x52800101`.
- Focused tests: static classification/source tests and the new fake-transport proof passed.
- Full `tests.test_a90_repl`: `Ran 133 tests`, `OK`.

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
- Baseline before flash: `v2321`, `version` OK, `status` OK, `selftest pass=11 warn=1 fail=0`.

Candidate flash:

```sh
python3 workspace/public/src/scripts/revalidation/native_init_flash.py \
  --from-native \
  --expect-sha256 b846ae9f74d8ceb922bbcd854d78b6795ef833d61e38465d3cc474cb6f0dfb65 \
  --expect-readback-sha256 b846ae9f74d8ceb922bbcd854d78b6795ef833d61e38465d3cc474cb6f0dfb65 \
  workspace/private/inputs/boot_images/boot_linux_tier2_repl_v1_repl.img
```

Result:

- Remote pushed image SHA matched candidate SHA.
- Boot readback SHA matched candidate SHA.
- Post-flash `version/status` verification passed.
- Candidate standalone selftest returned `pass=11 warn=1 fail=0`.
- REPL selftest completed and returned `a90-repl-v2a1-selftest-pass`.

The v1-repl image intentionally keeps the v2321 native-init identity string, so `version` alone does
not distinguish it from the clean rollback image. The REPL selftest is the functional proof that the
candidate kernel REPL path is resident.

## Live Proof

Command:

```sh
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 \
  workspace/public/src/scripts/revalidation/a90_repl.py call-proof \
  --map workspace/private/runs/kernel/v2c-c2b-kallsyms-padding-fix/System.map \
  --image workspace/private/inputs/boot_images/boot_linux_tier2_repl_v1_repl.img \
  --timeout 180 --dmesg-tail 80 --safe-op-retries 5 --retry-delay-sec 0.75 \
  --source-root workspace/private/inputs/kernel_source/SM-A908N_KOR_12_Opensource/Kernel \
  --evidence-dir workspace/private/runs/kernel/live-call-proof-cpumask-any-but-20260630/proof \
  cpumask_any_but
```

Public result:

```json
{
  "decision": "a90-repl-live-call-proof-cpumask_any_but-pass",
  "ok": true,
  "proof_status": "trusted-under-owned-input-contract",
  "input_contract": "owned cpumask buffer with compiled nr_cpumask_bits=8 + scalar excluded CPU inside runtime nr_cpu_ids",
  "return_contract": "int == first set CPU not equal to excluded CPU, or runtime nr_cpu_ids when no other CPU is set",
  "raw_runtime_values_redacted": true,
  "owned_pointer_redacted": true,
  "observed_bytes_redacted": true
}
```

Case table:

| Case | Set CPU bits | Excluded CPU | Expected | Observed |
| --- | --- | ---: | --- | --- |
| first-set-not-excluded | `2,6` | 1 | `0x2` | `0x2` |
| exclude-first-set | `2,6` | 2 | `0x6` | `0x6` |
| exclude-later-set-keeps-first | `2,6` | 6 | `0x2` | `0x2` |
| only-excluded-set | `2` | 2 | `0x8` | `0x8` |
| empty-mask | empty | 2 | `0x8` | `0x8` |

Checks:

- `static-c1-identity`: OK, `cpumask_any_but` resolved by `export-recovery`.
- `static-source-contract`: OK, signature matches the source oracle and pointer arg indices are `[0]`.
- `static-call-safety-contract`: OK, tier `SAFE-WITH-VALID-PTR`, x0 `cpumask-buffer`.
- `static-compiled-nr-cpumask-bits`: OK, wrapper word `0x52800101` matched compiled 8-bit mask.
- `static-nr-cpu-ids-initial-value`: OK, static `nr_cpu_ids` value was `8`.
- `runtime-nr-cpu-ids`: OK, runtime `nr_cpu_ids` value was `8`.
- `kmalloc-owned-cpumask-any-but-mask`: OK, owned kernel cpumask allocation returned sane lowmem.
- `cpumask-any-but-case-table`: OK, all 5 calls returned expected CPU indices or sentinel `8`.
- Per-case immutability: OK, cpumask and canary stayed unchanged after every call.
- `kfree-owned-cpumask-any-but-mask`: OK.

Raw per-boot slide, target runtime address, `nr_cpu_ids` runtime address, owned allocation pointer,
and observed bytes were written only to private evidence and are not included in this report.

Candidate selftest after proof: `pass=11 warn=1 fail=0`.

## Rollback

Rollback command:

```sh
python3 workspace/public/src/scripts/revalidation/native_init_flash.py \
  --from-native \
  --expect-sha256 ca978551aabe4b39563abaf529ccf2522054952d8b2ad852e632d26da88168cb \
  --expect-readback-sha256 ca978551aabe4b39563abaf529ccf2522054952d8b2ad852e632d26da88168cb \
  workspace/private/inputs/boot_images/boot_linux_v2321_usb_clean_identity_rodata.img
```

Result:

- Remote pushed image SHA matched v2321 SHA.
- Boot readback SHA matched v2321 SHA.
- Post-rollback `version/status` verification passed.
- Final resident: `v2321-usb-clean-identity-rodata`.
- Final standalone selftest returned `pass=11 warn=1 fail=0`.

## Conclusion

`cpumask_any_but` is now live-proven under an owned cpumask buffer plus scalar excluded CPU
contract, and only for the compiled `nr_cpumask_bits=8` / runtime `nr_cpu_ids=8` path that calls
`find_next_bit`. The proof confirms the intended exported helper was reached, returned the expected
first set CPU not equal to the excluded CPU or sentinel `8`, did not modify the cpumask/canary, and
cleaned up the owned allocation. This does not authorize arbitrary cpumask pointers, wider masks,
other cpumask wrappers, arbitrary CPU-topology state, or mass calling. The device was rolled back to
clean v2321 with final `selftest fail=0`.
