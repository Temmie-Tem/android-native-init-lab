# Kernel Security Tier-2 Runtime Kernel REPL - Live Call Proof: get_ddr_vendor_name

- Date: 2026-07-01
- Decision: `a90-repl-live-call-proof-get_ddr_vendor_name-pass`
- Scope: separately gated one-target live-call proof after the REPL epic close.
- Device action: yes, boot partition only through `native_init_flash.py`.
- Candidate image: `workspace/private/inputs/boot_images/boot_linux_tier2_repl_v1_repl.img`
- Candidate SHA256: `b846ae9f74d8ceb922bbcd854d78b6795ef833d61e38465d3cc474cb6f0dfb65`
- Rollback image: `workspace/private/inputs/boot_images/boot_linux_v2321_usb_clean_identity_rodata.img`
- Rollback SHA256: `ca978551aabe4b39563abaf529ccf2522054952d8b2ad852e632d26da88168cb`
- Private evidence: `workspace/private/runs/kernel/live-call-proof-get-ddr-vendor-name-20260701/proof/a90_repl_evidence.json`

## Candidate Selection

The operator steering for the post-epic proof loop now prefers read-only kernel-state observation
queries over additional saturated scalar/lib helpers. This unit therefore selected
`get_ddr_vendor_name`, a no-argument Samsung SMEM DDR identity getter that returns a borrowed
`char *`.

The trusted contract is intentionally narrow: call with no arguments, never free the returned pointer,
and only perform a bounded read of the borrowed string pointer to confirm that it is non-NULL, stable
across a short repeat, NUL-terminated within 32 bytes, and printable ASCII.

## Static Gate

Target:

- `get_ddr_vendor_name`: `0xffffff80086ef6ac`
- Resolution method: `disasm-signature+xref+map`
- Direct BL xrefs: `2`
- Next symbol boundary: `get_ddr_DSF_version` at `+0xc8`
- Source declaration: `include/linux/samsung/sec_smem.h:194`,
  `extern char* get_ddr_vendor_name(void)`
- Source pointer contract: no pointer arguments.
- Call-safety tier: `SAFE-SCALAR`
- Required valid pointer args: none.
- Return kind: borrowed kernel string pointer or NULL.
- Static word checks:
  - `0xd100c3ff`: stack allocation.
  - `0x528010c1`: SMEM vendor-info ID.
  - `0x910003e2`: stack size-buffer argument.
  - `0x97fe8984`: BL to `qcom_smem_get`.
  - `0xf94003e8`: load returned SMEM size.
  - `0xaa0003f3`: save returned SMEM pointer.
  - `0xb9401268`: load DDR vendor word from SMEM.
  - `0x9000a449` / `0x913c2129`: vendor table address materialization.
  - `0x92400d08`: mask vendor index to 4 bits.
  - `0xf8687920`: load vendor string pointer from table.
  - `0xaa1f03e0`: NULL return on error path.
  - `0xd65f03c0`: return.
  - `0x00be7bad`: next-entry guard before `get_ddr_DSF_version`.

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
  tests.test_a90_repl.SelftestIntegrationTests.test_call_proof_get_ddr_vendor_name_passes_with_borrowed_string_contract

PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 \
  workspace/public/src/scripts/revalidation/a90_repl.py call-safety-classify \
  --map workspace/private/runs/kernel/v2c-c2b-kallsyms-padding-fix/System.map \
  --image workspace/private/inputs/boot_images/boot_linux_tier2_repl_v1_repl.img \
  --evidence-dir workspace/private/runs/kernel/live-call-proof-get-ddr-vendor-name-20260701/static-classify \
  --no-objdump \
  get_ddr_vendor_name

PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 \
  workspace/public/src/scripts/revalidation/a90_repl.py call-safety-sweep \
  --map workspace/private/runs/kernel/v2c-c2b-kallsyms-padding-fix/System.map \
  --image workspace/private/inputs/boot_images/boot_linux_tier2_repl_v1_repl.img \
  --source-root workspace/private/inputs/kernel_source/SM-A908N_KOR_12_Opensource/Kernel \
  --evidence-dir workspace/private/runs/kernel/live-call-proof-get-ddr-vendor-name-20260701/static-sweep \
  --no-objdump \
  get_ddr_vendor_name

PYTHONPATH=tests PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m unittest tests.test_a90_repl
```

Result:

- `py_compile`: pass.
- Focused tests: `Ran 4 tests`, `OK`.
- CLI classify: `SAFE-SCALAR`, verified by `disasm-signature+xref+map`, direct BL xrefs `2`,
  no required pointer args, and first words matching the SMEM getter body.
- CLI sweep: advisory `SAFE-SCALAR`, scalar-only source declaration selected from
  `include/linux/samsung/sec_smem.h:194`, gate seeded and auto-call allowed only for this vetted
  target.
- Full `tests.test_a90_repl`: `Ran 159 tests`, `OK`.

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
- Candidate standalone selftest confirmed `pass=11 warn=1 fail=0`.
- First REPL selftest attempt hit a known host-side serial framing loss on a `cmdv1x` shell command
  before any REPL op completed. A short `version` resync and minimal `cmdv1x` run check passed, then
  REPL selftest retry returned `a90-repl-v2a1-selftest-pass`.

## Live Proof

Command:

```sh
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 \
  workspace/public/src/scripts/revalidation/a90_repl.py call-proof get_ddr_vendor_name \
  --map workspace/private/runs/kernel/v2c-c2b-kallsyms-padding-fix/System.map \
  --image workspace/private/inputs/boot_images/boot_linux_tier2_repl_v1_repl.img \
  --source-root workspace/private/inputs/kernel_source/SM-A908N_KOR_12_Opensource/Kernel \
  --evidence-dir workspace/private/runs/kernel/live-call-proof-get-ddr-vendor-name-20260701/proof
```

Public result:

```json
{
  "decision": "a90-repl-live-call-proof-get_ddr_vendor_name-pass",
  "ok": true,
  "proof_status": "trusted-under-smem-borrowed-printable-vendor-string-contract",
  "input_contract": "no arguments; Samsung SMEM DDR vendor info is read-only; returned char pointer is borrowed/read-only and is not freed",
  "return_contract": "char * is non-NULL, stable across repeated calls, and points to a bounded NUL-terminated printable DDR vendor string",
  "observed_vendor_string": "SEC",
  "repeat_count": 2,
  "all_return_pointers_stable": true,
  "all_strings_stable": true,
  "raw_runtime_values_redacted": true,
  "borrowed_pointer_redacted": true
}
```

Case table:

| Case | Expected | Observed vendor | Pointer status |
| --- | --- | --- | --- |
| ddr-vendor-name-stable-1 | non-NULL borrowed printable C string pointer | `SEC` | redacted, non-NULL |
| ddr-vendor-name-stable-2 | same pointer and same string as first call | `SEC` | redacted, stable |

Checks:

- `static-c1-identity`: OK, `get_ddr_vendor_name` resolved by `disasm-signature+xref+map`.
- `static-next-symbol-boundary`: OK, next symbol `get_ddr_DSF_version` at `+0xc8`.
- `static-source-contract`: OK, no-argument
  `extern char* get_ddr_vendor_name(void)` source declaration selected from
  `include/linux/samsung/sec_smem.h`.
- `static-call-safety-contract`: OK, tier `SAFE-SCALAR`.
- Static word checks: OK for stack setup, SMEM getter call, SMEM field load, vendor-table lookup,
  NULL error return, RET, and next-entry guard.
- Runtime borrowed-string check: OK; two calls returned a stable non-NULL borrowed pointer whose
  bounded 32-byte read decoded to the same printable NUL-terminated vendor string `SEC`.
- Cleanup: not applicable. The pointer is borrowed, not owned, and was not freed.

Raw per-boot slide, target runtime address, and borrowed pointer value were written only to private
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
  --verify-protocol cmdv1 \
  --from-native
```

Result:

- Remote pushed rollback image SHA matched rollback SHA.
- Boot readback SHA matched rollback SHA.
- Helper `version/status` verification passed after reboot.
- Final standalone selftest confirmed `pass=11 warn=1 fail=0`.

## Trust Boundary

`get_ddr_vendor_name` is trusted only under the no-argument Samsung SMEM DDR vendor query contract:
the proof may call it, require a non-NULL stable borrowed string pointer, and bounded-read that string
for printable NUL-terminated content. This does not authorize freeing the returned pointer,
unbounded string reads, dereferencing arbitrary returned addresses as structs, other DDR SMEM getters,
unverified map entries, or mass calling.
