# Kernel Security Tier-2 Runtime Kernel REPL - Live Call Proof: get_ddr_DSF_version

- Date: 2026-06-30
- Decision: `a90-repl-live-call-proof-get_ddr_DSF_version-pass`
- Scope: separately gated one-target live-call proof after the REPL epic close.
- Device action: yes, boot partition only through `native_init_flash.py`.
- Candidate image: `workspace/private/inputs/boot_images/boot_linux_tier2_repl_v1_repl.img`
- Candidate SHA256: `b846ae9f74d8ceb922bbcd854d78b6795ef833d61e38465d3cc474cb6f0dfb65`
- Rollback image: `workspace/private/inputs/boot_images/boot_linux_v2321_usb_clean_identity_rodata.img`
- Rollback SHA256: `ca978551aabe4b39563abaf529ccf2522054952d8b2ad852e632d26da88168cb`
- Private evidence: `workspace/private/runs/kernel/live-call-proof-get-ddr-dsf-version-20260630/proof/a90_repl_evidence.json`

## Candidate Selection

This unit continued the Samsung SMEM DDR getter sweep after `get_ddr_total_density` passed and
`get_ddr_revision_id_1` was parked for a raw return contract mismatch. `get_ddr_DSF_version` was
selected because its source declaration is a no-argument `uint32_t` getter, C1 resolves the symbol by
disassembly shape and xref, and the disassembly returns the loaded field directly in `w0` instead of
applying the shifted-word pattern that invalidated the `get_ddr_revision_id_1` raw `uint8_t` contract.

Rejected alternative in this pass:

- `get_ddr_revision_id_1`: static identity remained useful, but the previous live call proved the raw
  REPL return is a shifted SMEM word (`0x60106`) rather than the source-level byte contract. It stays
  DENY/not seeded until a future unit defines a different, disassembly-faithful contract.

## Static Gate

Target:

- `get_ddr_DSF_version`: `0xffffff80086ef774`
- Resolution method: `disasm-signature+xref+map`
- Direct BL xrefs: `4`
- Next symbol boundary: `get_ddr_revision_id_1` at `+0xb8`
- Source signature: `include/linux/samsung/sec_smem.h:195`,
  `extern uint32_t get_ddr_DSF_version(void)`
- Source pointer contract: no arguments.
- Call-safety tier: `SAFE-SCALAR`
- Required valid pointer args: none.
- Static word checks:
  - `0xd100c3ff` stack allocation.
  - `0x528010e1` Samsung SMEM item ID setup.
  - `0x910003e2` stack buffer argument setup.
  - `0x97fe8952` call to `qcom_smem_get`.
  - `0xf94003e8` SMEM size load.
  - `0xaa0003f3` returned pointer save.
  - `0xb9406a60` DDR DSF-version 32-bit field load.
  - `0x2a1f03e0` NULL/error return path.
  - `0xd65f03c0` return.
  - `0x00be7bad` next-entry guard before `get_ddr_revision_id_1`.

The generic classifier exposes only the first 12 words as public signal. This proof gates the later
SMEM call, field load, NULL/error return, RET, and next guard explicitly inside the one-target proof.

## Host Validation

Commands:

```sh
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m py_compile \
  workspace/public/src/scripts/revalidation/a90_repl.py \
  tests/test_a90_repl.py

PYTHONPATH=tests PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m unittest \
  tests.test_a90_repl.CallSafetyClassificationTests.test_proven_live_call_targets_stay_safe \
  tests.test_a90_repl.CallSafetyClassificationTests.test_source_signature_oracle_distinguishes_scalar_and_pointer_args \
  tests.test_a90_repl.CallSafetyClassificationTests.test_seed_inventory_summary_counts_tiers \
  tests.test_a90_repl.SelftestIntegrationTests.test_call_proof_get_ddr_DSF_version_passes_with_stable_uint32_contract

PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 \
  workspace/public/src/scripts/revalidation/a90_repl.py call-safety-classify \
  --map workspace/private/runs/kernel/v2c-c2b-kallsyms-padding-fix/System.map \
  --image workspace/private/inputs/boot_images/boot_linux_tier2_repl_v1_repl.img \
  --no-objdump \
  get_ddr_DSF_version

PYTHONPATH=tests PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m unittest tests.test_a90_repl

git diff --check
```

Result:

- `py_compile`: pass.
- Focused tests: `Ran 4 tests`, `OK`.
- CLI classify: `SAFE-SCALAR`, verified by `disasm-signature+xref+map`, direct-BL xrefs `4`, no
  required pointer args, and first BL resolved to `qcom_smem_get`.
- Full `tests.test_a90_repl`: `Ran 146 tests`, `OK`.
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
- Baseline before flash: `v2321`, `version` OK, `status` OK, `selftest pass=11 warn=1 fail=0`.

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
- Candidate standalone selftest returned `pass=11 warn=1 fail=0`.
- REPL selftest completed and returned `a90-repl-v2a1-selftest-pass`.

## Live Proof

Command:

```sh
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 \
  workspace/public/src/scripts/revalidation/a90_repl.py call-proof get_ddr_DSF_version \
  --map workspace/private/runs/kernel/v2c-c2b-kallsyms-padding-fix/System.map \
  --image workspace/private/inputs/boot_images/boot_linux_tier2_repl_v1_repl.img \
  --source-root workspace/private/inputs/kernel_source/SM-A908N_KOR_12_Opensource/Kernel \
  --evidence-dir workspace/private/runs/kernel/live-call-proof-get-ddr-dsf-version-20260630/proof
```

Public result:

```json
{
  "decision": "a90-repl-live-call-proof-get_ddr_DSF_version-pass",
  "ok": true,
  "proof_status": "trusted-under-smem-uint32-dsf-version-contract",
  "input_contract": "no arguments; Samsung SMEM DDR DSF info is read-only; no returned pointer is dereferenced or freed",
  "return_contract": "uint32_t DDR DSF-version field is nonzero, <= 0xffffffff, and stable across repeated proof calls",
  "all_returns_nonzero_uint32": true,
  "all_returns_stable": true,
  "repeat_count": 2,
  "observed_return_value": "0x650000",
  "raw_runtime_values_redacted": true
}
```

Case table:

| Case | Expected | Observed |
| --- | --- | --- |
| ddr-dsf-version-stable-1 | nonzero uint32 stable | `0x650000` |
| ddr-dsf-version-stable-2 | nonzero uint32 stable | `0x650000` |

Checks:

- `static-c1-identity`: OK, `get_ddr_DSF_version` resolved by `disasm-signature+xref+map`.
- `static-next-symbol-boundary`: OK, next symbol at `+0xb8`.
- `static-source-contract`: OK, no-arg `uint32_t` source signature selected from
  `include/linux/samsung/sec_smem.h`.
- `static-call-safety-contract`: OK, tier `SAFE-SCALAR`.
- Static word checks: OK for stack setup, SMEM ID/buffer setup, `qcom_smem_get`, SMEM size load,
  returned pointer save, DSF-version field load, NULL/error return, RET, and next guard.
- Stable nonzero uint32 repeat table: OK.
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
  --expect-version v2321-usb-clean-identity-rodata \
  --verify-protocol cmdv1 \
  --from-native
```

Result:

- Remote pushed image SHA matched rollback SHA.
- Boot readback SHA matched rollback SHA.
- Post-rollback helper `version/status` verification passed.
- A transient final serial parse fragment was cleared by restarting the serial bridge.
- Final standalone `version` confirmed `v2321-usb-clean-identity-rodata`.
- Final standalone `status` returned OK.
- Final standalone selftest returned `pass=11 warn=1 fail=0`.

## Function Map Update

Add `get_ddr_DSF_version` as `live-proven` only under this contract:

- Static link identity: `0xffffff80086ef774`, `disasm-signature+xref+map`, direct BL xrefs `4`,
  `0xb8`-byte SMEM getter body before `get_ddr_revision_id_1`.
- Trusted input contract: no arguments; Samsung SMEM DDR DSF info is read-only; no returned pointer
  is dereferenced or freed.
- Observed result: two repeated calls returned stable nonzero uint32 value `0x650000`.
- Cleanup: `n/a-scalar-smem-read-only`.

This does not authorize arbitrary SMEM reads, logging-heavy debug getters, changing boot/stat state,
or mass calling.
