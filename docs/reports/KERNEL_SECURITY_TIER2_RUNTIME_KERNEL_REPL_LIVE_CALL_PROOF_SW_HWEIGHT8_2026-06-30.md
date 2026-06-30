# Kernel Security Tier-2 Runtime Kernel REPL - Live Call Proof: __sw_hweight8

- Date: 2026-06-30
- Decision: `a90-repl-live-call-proof-__sw_hweight8-pass`
- Scope: separately gated one-target live-call proof after the REPL epic close.
- Device action: yes, boot partition only through `native_init_flash.py`.
- Candidate image: `workspace/private/inputs/boot_images/boot_linux_tier2_repl_v1_repl.img`
- Candidate SHA256: `b846ae9f74d8ceb922bbcd854d78b6795ef833d61e38465d3cc474cb6f0dfb65`
- Rollback image: `workspace/private/inputs/boot_images/boot_linux_v2321_usb_clean_identity_rodata.img`
- Rollback SHA256: `ca978551aabe4b39563abaf529ccf2522054952d8b2ad852e632d26da88168cb`
- Private evidence: `workspace/private/runs/kernel/live-call-proof-sw-hweight8-20260630/proof/a90_repl_evidence.json`

## Candidate Selection

This unit continued the scalar bit-helper sweep after `__sw_hweight32` and `__sw_hweight16`.
The advisory sweep over the remaining adjacent helpers produced:

- `__sw_hweight8`: `SAFE-SCALAR`, source signature found, C1 verified by `export-recovery`.
- `__sw_hweight64`: parked because source signature lookup was missing, despite export recovery.

The one-target proof selected `__sw_hweight8` because it has a verified scalar-only source/ABI
contract and no pointer inputs.

## Static Gate

Target:

- `__sw_hweight8`: `0xffffff800856d8b4`
- Resolution method: `export-recovery`
- Direct BL xrefs: `23`
- Shape: JOPP entry, leaf/no-BL, RET observed at offset `0x24`.
- Disasm contract: x0 is used only as a scalar word; no argument memory dereference and no
  tainted-argument call were observed.
- Source signature: `include/linux/bitops.h:10`, `extern unsigned int __sw_hweight8(unsigned int w)`
- Source pointer contract: none; x0 is a scalar unsigned word, with this proof constraining inputs to
  the low 8 bits.
- Call-safety tier: `SAFE-SCALAR`
- Required valid pointer args: none.

The target was not called with any host-supplied pointer. The proof calls only the verified
`__sw_hweight8` entry with fixed scalar low-8-bit words and checks a bounded population-count case
table.

## Host Validation

Commands:

```sh
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m py_compile \
  workspace/public/src/scripts/revalidation/a90_repl.py \
  tests/test_a90_repl.py

PYTHONPATH=tests PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m unittest \
  tests.test_a90_repl.CallSafetyClassificationTests.test_proven_live_call_targets_stay_safe \
  tests.test_a90_repl.SelftestIntegrationTests.test_call_proof_sw_hweight8_passes_with_scalar_contract

PYTHONPATH=tests PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m unittest tests.test_a90_repl
```

Result:

- `py_compile`: pass.
- Focused tests: `Ran 2 tests`, `OK`.
- Full `tests.test_a90_repl`: `Ran 127 tests`, `OK`.

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
- The first REPL selftest attempt hit a transient serial END-marker timeout while setting
  `panic_on_oops`.
- Immediate device health stayed `selftest pass=11 warn=1 fail=0`.
- A repeated REPL selftest returned `a90-repl-v2a1-selftest-pass`.

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
  --source-root workspace/private/inputs/kernel_source/SM-A908N_KOR_12_Opensource/Kernel \
  --evidence-dir workspace/private/runs/kernel/live-call-proof-sw-hweight8-20260630/proof \
  __sw_hweight8
```

Public result:

```json
{
  "decision": "a90-repl-live-call-proof-__sw_hweight8-pass",
  "ok": true,
  "proof_status": "trusted-under-scalar-input-contract",
  "input_contract": "scalar unsigned 8-bit byte in the low x0 bits",
  "return_contract": "unsigned int == population count of the low 8 input bits",
  "raw_runtime_values_redacted": true
}
```

Case table:

| Case | Input | Expected | Observed |
| --- | --- | --- | --- |
| zero | `0x00` | `0x0` | `0x0` |
| all-ones | `0xff` | `0x8` | `0x8` |
| alternating-a | `0xaa` | `0x4` | `0x4` |
| single-high-bit | `0x80` | `0x1` | `0x1` |
| a9 | `0xa9` | `0x4` | `0x4` |

Checks:

- `static-c1-identity`: OK, `__sw_hweight8` resolved by `export-recovery`.
- `static-source-contract`: OK, signature `extern unsigned int __sw_hweight8(unsigned int w)`, no pointer args.
- `static-call-safety-contract`: OK, tier `SAFE-SCALAR`, no required pointer args.
- `__sw_hweight8-scalar-case-table`: OK, all 5 scalar case calls returned the expected values.

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
- The first final standalone selftest read hit transient serial `ATATAT` capture noise.
- A repeated final standalone selftest returned `pass=11 warn=1 fail=0`.

## Conclusion

`__sw_hweight8` is now live-proven under a scalar unsigned 8-bit low-byte contract. The proof confirms
the intended helper was reached, returned the expected population count for zero, all-ones,
alternating, single-high-bit, and mixed marker cases, required no pointer inputs, and left the device
healthy. This does not authorize arbitrary target calls, broader bitops state, high-bit widening
outside the stated low-8-bit input contract, or mass calling. The device was rolled back to clean
v2321 with final `selftest fail=0`.
