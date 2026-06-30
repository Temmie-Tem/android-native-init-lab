# Kernel Security Tier-2 Runtime Kernel REPL - Live Call Proof: __sw_hweight64

- Date: 2026-06-30
- Decision: `a90-repl-live-call-proof-__sw_hweight64-pass`
- Scope: separately gated one-target live-call proof after the REPL epic close.
- Device action: yes, boot partition only through `native_init_flash.py`.
- Candidate image: `workspace/private/inputs/boot_images/boot_linux_tier2_repl_v1_repl.img`
- Candidate SHA256: `b846ae9f74d8ceb922bbcd854d78b6795ef833d61e38465d3cc474cb6f0dfb65`
- Rollback image: `workspace/private/inputs/boot_images/boot_linux_v2321_usb_clean_identity_rodata.img`
- Rollback SHA256: `ca978551aabe4b39563abaf529ccf2522054952d8b2ad852e632d26da88168cb`
- Private evidence: `workspace/private/runs/kernel/live-call-proof-sw-hweight64-20260630/proof/a90_repl_evidence.json`

## Candidate Selection

This unit continued the scalar bit-helper sweep after `__sw_hweight32`, `__sw_hweight16`,
and `__sw_hweight8`. `__sw_hweight64` had already shown strong static C1 identity, but it was
previously parked because source signature lookup failed closed.

Root cause was host-side parser coverage: the source signature exists in `include/linux/bitops.h`,
but the source-oracle typed-argument recognizer did not include kernel typedef spellings such as
`__u64`. This unit added `__u8`, `__u16`, `__u32`, and `__u64` to typed-argument recognition and
added the exact `include/linux/bitops.h` source hint for `__sw_hweight64`.

The one-target proof selected only `__sw_hweight64` after source lookup found
`extern unsigned long __sw_hweight64(__u64 w)` with no pointer arguments.

## Static Gate

Target:

- `__sw_hweight64`: `0xffffff800856d8e4`
- Resolution method: `export-recovery`
- Direct BL xrefs: `228`
- Shape: JOPP entry, leaf/no-BL, RET observed at offset `0x38`.
- Disasm contract: x0 is used only as a scalar word; no argument memory dereference and no
  tainted-argument call were observed.
- Source signature: `include/linux/bitops.h:13`, `extern unsigned long __sw_hweight64(__u64 w)`
- Source pointer contract: none; x0 is a scalar unsigned 64-bit word.
- Call-safety tier: `SAFE-SCALAR`
- Required valid pointer args: none.

The target was not called with any host-supplied pointer. The proof calls only the verified
`__sw_hweight64` entry with fixed scalar 64-bit words and checks a bounded population-count case
table.

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
  tests.test_a90_repl.SelftestIntegrationTests.test_call_proof_sw_hweight64_passes_with_scalar_contract

PYTHONPATH=tests PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m unittest tests.test_a90_repl

PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 \
  workspace/public/src/scripts/revalidation/a90_repl.py call-safety-classify \
  --map workspace/private/runs/kernel/v2c-c2b-kallsyms-padding-fix/System.map \
  --image workspace/private/inputs/boot_images/boot_linux_tier2_repl_v1_repl.img \
  --no-objdump \
  __sw_hweight64
```

Result:

- `py_compile`: pass.
- Focused tests: `Ran 4 tests`, `OK`.
- Full `tests.test_a90_repl`: `Ran 128 tests`, `OK`.
- CLI classify: `SAFE-SCALAR`, verified by `export-recovery`, direct-BL xrefs `228`, no pointer
  derefs before first BL/RET, scalar arg-taint stayed out of memory-base use.

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
- REPL selftest returned `a90-repl-v2a1-selftest-pass`.

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
  --evidence-dir workspace/private/runs/kernel/live-call-proof-sw-hweight64-20260630/proof \
  __sw_hweight64
```

Public result:

```json
{
  "decision": "a90-repl-live-call-proof-__sw_hweight64-pass",
  "ok": true,
  "proof_status": "trusted-under-scalar-input-contract",
  "input_contract": "scalar unsigned 64-bit word",
  "return_contract": "unsigned long == population count of the 64 input bits",
  "raw_runtime_values_redacted": true
}
```

Case table:

| Case | Input | Expected | Observed |
| --- | --- | --- | --- |
| zero | `0x0000000000000000` | `0x0` | `0x0` |
| all-ones | `0xffffffffffffffff` | `0x40` | `0x40` |
| alternating-a | `0xaaaaaaaaaaaaaaaa` | `0x20` | `0x20` |
| single-high-bit | `0x8000000000000000` | `0x1` | `0x1` |
| a90f00dc-pair | `0xa90f00dca90f00dc` | `0x1a` | `0x1a` |

Checks:

- `static-c1-identity`: OK, `__sw_hweight64` resolved by `export-recovery`.
- `static-source-contract`: OK, signature `extern unsigned long __sw_hweight64(__u64 w)`, no pointer args.
- `static-call-safety-contract`: OK, tier `SAFE-SCALAR`, no required pointer args.
- `__sw_hweight64-scalar-case-table`: OK, all 5 scalar case calls returned the expected values.

Raw per-boot slide and target runtime address were written only to private evidence and are not
included in this report.

Candidate selftest after proof: `pass=11 warn=1 fail=0`.

## Rollback

Rollback command:

```sh
python3 workspace/public/src/scripts/revalidation/native_init_flash.py \
  --from-native \
  --expect-version v2321-usb-clean-identity-rodata \
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

`__sw_hweight64` is now live-proven under a scalar unsigned 64-bit contract. The proof confirms the
intended helper was reached, returned the expected population count for zero, all-ones, alternating,
single-high-bit, and mixed marker cases, required no pointer inputs, and left the device healthy. The
host-side source oracle now recognizes kernel `__u*` typedef spellings, which unblocks this family
without widening pointer-call policy. This does not authorize arbitrary target calls, broader bitops
state, malformed pointers, or mass calling. The device was rolled back to clean v2321 with final
`selftest fail=0`.
