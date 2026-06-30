# Kernel Security Tier-2 Runtime Kernel REPL - Live Call Proof: get_cpu_device

- Date: 2026-06-30
- Decision: `a90-repl-live-call-proof-get_cpu_device-pass`
- Scope: separately gated one-target live-call proof after the REPL epic close.
- Device action: yes, boot partition only through `native_init_flash.py`.
- Candidate image: `workspace/private/inputs/boot_images/boot_linux_tier2_repl_v1_repl.img`
- Candidate SHA256: `b846ae9f74d8ceb922bbcd854d78b6795ef833d61e38465d3cc474cb6f0dfb65`
- Rollback image: `workspace/private/inputs/boot_images/boot_linux_v2321_usb_clean_identity_rodata.img`
- Rollback SHA256: `ca978551aabe4b39563abaf529ccf2522054952d8b2ad852e632d26da88168cb`
- Private evidence: `workspace/private/runs/kernel/live-call-proof-get-cpu-device-20260630/proof/a90_repl_evidence.json`

## Candidate Selection

This unit moved from the completed bitmap mutation-helper sweep to the scalar `get_*` family and
selected `get_cpu_device` because C1 recovered one export candidate, the verified System.map agreed
with it, it has a high direct-call count, and the static shape is leaf/no-BL with no pointer input
arguments. The function returns a borrowed kernel pointer; this proof does not dereference, free, or
otherwise consume that pointer.

Rejected alternatives in this pass:

- `__bitmap_equal` and `__bitmap_intersects`: safe-looking leaf bitmap readers, but current C1 policy
  marks them unverified because direct BL xrefs are zero.
- `get_boot_stat_time`: scalar and C1-verified, but it calls logging machinery and has a weaker
  externally checkable return contract.

## Static Gate

Target:

- `get_cpu_device`: `0xffffff8008992a5c`
- Resolution method: `export-recovery`
- Direct BL xrefs: `38`
- Shape: JOPP entry, leaf/no-BL, no arg-derived memory bases.
- Source signature: `include/linux/cpu.h:38`,
  `extern struct device * get_cpu_device(unsigned cpu)`
- Source pointer contract: no pointer arguments; x0 is scalar `unsigned cpu`.
- Call-safety tier: `SAFE-SCALAR`
- Required valid pointer args: none.
- Static word checks:
  - `0x90011448` entry ADRP for the `nr_cpu_ids` region.
  - `0xb940f908` load of `nr_cpu_ids`.
  - `0x6b00011f` compare of `nr_cpu_ids` vs input CPU.
  - `0x54000229` invalid-range branch.
  - `0xf868d928` possible-mask word load.
  - `0x36000108` possible-bit test.
  - `0xf8605908` per-CPU base load.
  - `0xf8696900` returned device-pointer load.
  - `0xaa1f03e0` NULL return path.

The returned CPU0 pointer is treated as borrowed/read-only and is redacted from public output.

## Host Validation

Commands:

```sh
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m py_compile \
  workspace/public/src/scripts/revalidation/a90_repl.py \
  tests/test_a90_repl.py

PYTHONPATH=tests PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m unittest \
  tests.test_a90_repl.CallSafetyClassificationTests.test_proven_live_call_targets_stay_safe \
  tests.test_a90_repl.CallSafetyClassificationTests.test_source_signature_oracle_distinguishes_scalar_and_pointer_args \
  tests.test_a90_repl.SelftestIntegrationTests.test_call_proof_get_cpu_device_passes_with_scalar_contract

PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 \
  workspace/public/src/scripts/revalidation/a90_repl.py call-safety-classify \
  --map workspace/private/runs/kernel/v2c-c2b-kallsyms-padding-fix/System.map \
  --image workspace/private/inputs/boot_images/boot_linux_tier2_repl_v1_repl.img \
  --no-objdump \
  get_cpu_device

PYTHONPATH=tests PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m unittest tests.test_a90_repl
```

Result:

- `py_compile`: pass.
- Focused tests: static classification, source signature, and fake-transport scalar proof passed
  (`Ran 3 tests`, `OK`).
- CLI classify: `SAFE-SCALAR`, verified by `export-recovery`, direct-BL xrefs `38`, leaf/no-BL.
- Full `tests.test_a90_repl`: `Ran 143 tests`, `OK`.

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
- Baseline before flash: `v2321`, `version` OK, `selftest pass=11 warn=1 fail=0`.

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
- Post-flash helper `version/status` verification passed.
- A transient candidate standalone selftest parse miss was cleared by restarting the serial bridge.
- Candidate standalone selftest returned `pass=11 warn=1 fail=0`.
- REPL selftest completed and returned `a90-repl-v2a1-selftest-pass`.

## Live Proof

Command:

```sh
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 \
  workspace/public/src/scripts/revalidation/a90_repl.py call-proof \
  --map workspace/private/runs/kernel/v2c-c2b-kallsyms-padding-fix/System.map \
  --image workspace/private/inputs/boot_images/boot_linux_tier2_repl_v1_repl.img \
  --timeout 180 --dmesg-tail 80 --safe-op-retries 5 --retry-delay-sec 0.75 \
  --source-root workspace/private/inputs/kernel_source/SM-A908N_KOR_12_Opensource/Kernel \
  --evidence-dir workspace/private/runs/kernel/live-call-proof-get-cpu-device-20260630/proof \
  get_cpu_device
```

Public result:

```json
{
  "decision": "a90-repl-live-call-proof-get_cpu_device-pass",
  "ok": true,
  "proof_status": "trusted-under-scalar-input-contract",
  "input_contract": "scalar CPU index; returned pointer is borrowed/read-only and is not dereferenced or freed",
  "return_contract": "struct device * is non-NULL for CPU0 and NULL for an out-of-range unsigned CPU index",
  "valid_cpu_return_nonzero": true,
  "valid_cpu_return_kernel_lowmem": true,
  "invalid_cpu_return_null": true,
  "raw_runtime_values_redacted": true,
  "borrowed_pointer_redacted": true
}
```

Case table:

| Case | CPU | Expected | Observed |
| --- | ---: | --- | --- |
| cpu0-valid-device | 0 | non-NULL borrowed kernel lowmem pointer | pass, pointer redacted |
| uint-max-out-of-range | `0xffffffff` | NULL | `0x0` |

Checks:

- `static-c1-identity`: OK, `get_cpu_device` resolved by `export-recovery`.
- `static-source-contract`: OK, scalar-only source signature selected from `include/linux/cpu.h`.
- `static-call-safety-contract`: OK, tier `SAFE-SCALAR`.
- Static word checks: OK for range check, possible-mask check, per-CPU device pointer load, and NULL
  return path.
- Case table: OK.
- Cleanup: not applicable. Returned CPU0 pointer is borrowed and was not dereferenced or freed.

Raw per-boot slide, target runtime address, and returned CPU0 pointer were written only to private
evidence and are not included in this report.

Candidate selftest after proof: `pass=11 warn=1 fail=0`.

## Rollback

Rollback command:

```sh
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 \
  workspace/public/src/scripts/revalidation/native_init_flash.py \
  workspace/private/inputs/boot_images/boot_linux_v2321_usb_clean_identity_rodata.img \
  --expect-sha256 ca978551aabe4b39563abaf529ccf2522054952d8b2ad852e632d26da88168cb \
  --expect-readback-sha256 ca978551aabe4b39563abaf529ccf2522054952d8b2ad852e632d26da88168cb \
  --expect-version v2321-usb-clean-identity-rodata \
  --verify-protocol cmdv1 \
  --from-native
```

Result:

- Remote pushed image SHA matched rollback SHA.
- Boot readback SHA matched rollback SHA.
- Post-rollback helper `version/status` verification passed.
- A transient final standalone `version` parse miss was cleared by restarting the serial bridge.
- Final standalone `version` confirmed `v2321-usb-clean-identity-rodata`.
- Final standalone selftest returned `pass=11 warn=1 fail=0`.

## Function Map Update

Add `get_cpu_device` as `live-proven` only under this contract:

- Static link identity: `0xffffff8008992a5c`, `export-recovery`, direct BL xrefs `38`.
- Trusted input contract: scalar CPU index; returned pointer is borrowed/read-only and is not
  dereferenced or freed.
- Observed result: CPU0 returned a non-NULL kernel lowmem borrowed pointer, redacted in public
  output; `UINT_MAX` returned NULL.
- Cleanup: `n/a-borrowed-pointer-not-owned`.

This does not authorize arbitrary pointer use, dereferencing the returned pointer, freeing the
returned pointer, CPU hotplug state mutation, or mass calling.
