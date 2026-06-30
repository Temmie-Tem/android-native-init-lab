# Kernel Security Tier-2 Runtime Kernel REPL - Live Call Proof: __bitmap_andnot

- Date: 2026-06-30
- Decision: `a90-repl-live-call-proof-__bitmap_andnot-pass`
- Scope: separately gated one-target live-call proof after the REPL epic close.
- Device action: yes, boot partition only through `native_init_flash.py`.
- Candidate image: `workspace/private/inputs/boot_images/boot_linux_tier2_repl_v1_repl.img`
- Candidate SHA256: `b846ae9f74d8ceb922bbcd854d78b6795ef833d61e38465d3cc474cb6f0dfb65`
- Rollback image: `workspace/private/inputs/boot_images/boot_linux_v2321_usb_clean_identity_rodata.img`
- Rollback SHA256: `ca978551aabe4b39563abaf529ccf2522054952d8b2ad852e632d26da88168cb`
- Private evidence: `workspace/private/runs/kernel/live-call-proof-bitmap-andnot-20260630/proof/a90_repl_evidence.json`

## Candidate Selection

This unit continued the bitmap mutation-helper sweep after `__bitmap_complement`. `__bitmap_andnot`
was selected because C1 recovered one export candidate, the verified System.map agreed with it, it
has a direct BL xref, and the static shape is leaf/no-BL with x1 source loads, x2 mask loads, x0
destination stores, and scalar `nbits` flow. The helper also returns a bool, so this proof checks
both mutation and return semantics.

This does not promote arbitrary bitmap mutation. The proof creates tool-owned destination, source,
partial-mask, and full-mask bitmap buffers, resets the destination before every case, calls only
bounded `nbits` values inside the 128-bit proof bitmap, re-peeks destination/source/masks/canaries,
and frees every allocation.

## Static Gate

Target:

- `__bitmap_andnot`: `0xffffff800855cc24`
- Resolution method: `export-recovery`
- Direct BL xrefs: `1`
- Shape: JOPP entry, leaf/no-BL.
- Static word checks:
  - `0x53067c69` at entry for `nbits >> 6`.
  - `0xf840856e` for the first source bitmap load.
  - `0xf840858f` for the first mask bitmap load.
  - `0x8a2f01ce` for the first `source & ~mask` operation.
  - `0xf80085ae` for the first destination bitmap store.
  - `0xf869682a` for the tail source bitmap load.
  - `0xf869684b` for the tail mask bitmap load.
  - `0xf829680a` for the tail destination bitmap store.
  - `0x1a9f07e0` for the boolean return materialization.
- Source signature: `include/linux/bitmap.h:117`,
  `extern int __bitmap_andnot(unsigned long *dst, const unsigned long *bitmap1, const unsigned long *bitmap2, unsigned int nbits)`
- Source pointer contract: x0 is mutable destination, x1 is const source, x2 is const mask, x3 is scalar `nbits`.
- Call-safety tier: `SAFE-WITH-VALID-PTR`
- Required valid pointer args: x0 `bitmap-dst-buffer`, x1 `bitmap-src-buffer`, x2 `bitmap-mask-buffer`.

The target was not called with arbitrary numeric pointers. The proof requires three owned bitmap
arguments and scalar `nbits` values bounded to the proof bitmaps.

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
  __bitmap_andnot

PYTHONPATH=tests PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m unittest \
  tests.test_a90_repl.CallSafetyClassificationTests.test_safe_with_valid_pointer_seed_records_required_args \
  tests.test_a90_repl.CallSafetyClassificationTests.test_source_signature_oracle_distinguishes_scalar_and_pointer_args \
  tests.test_a90_repl.SelftestIntegrationTests.test_call_proof___bitmap_andnot_passes_with_owned_bitmap_contract

PYTHONPATH=tests PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m unittest tests.test_a90_repl
```

Result:

- `py_compile`: pass.
- CLI classify: `SAFE-WITH-VALID-PTR`, verified by `export-recovery`, direct-BL xrefs `1`,
  leaf/no-BL, required x0 `bitmap-dst-buffer`, x1 `bitmap-src-buffer`, x2 `bitmap-mask-buffer`.
- Focused tests: static classification/source tests and the new fake-transport mutation/return proof
  passed.
- Full `tests.test_a90_repl`: `Ran 139 tests`, `OK`.

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
  --from-native \
  --expect-sha256 b846ae9f74d8ceb922bbcd854d78b6795ef833d61e38465d3cc474cb6f0dfb65 \
  workspace/private/inputs/boot_images/boot_linux_tier2_repl_v1_repl.img
```

Result:

- Remote pushed image SHA matched candidate SHA.
- Boot readback SHA matched candidate SHA.
- Post-flash helper `version/status` verification passed.
- The first standalone candidate selftest attempt hit a transient bridge prompt desync; a host-side
  bridge restart cleared it and standalone selftest returned `pass=11 warn=1 fail=0`.
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
  --evidence-dir workspace/private/runs/kernel/live-call-proof-bitmap-andnot-20260630/proof \
  __bitmap_andnot
```

Public result:

```json
{
  "decision": "a90-repl-live-call-proof-__bitmap_andnot-pass",
  "ok": true,
  "proof_status": "trusted-under-owned-input-contract",
  "input_contract": "owned destination unsigned-long bitmap buffer + owned source unsigned-long bitmap buffer + owned mask unsigned-long bitmap buffer + scalar bit count bounded inside all three bitmaps",
  "return_contract": "int bool == 1 when (source & ~mask) below nbits is nonzero, else 0; destination receives the bounded and-not result",
  "raw_runtime_values_redacted": true,
  "owned_pointer_redacted": true,
  "observed_bytes_redacted": true
}
```

Case table:

| Case | Mask | nbits | Expected | Observed | Destination | Source/Mask | Canaries |
| --- | --- | ---: | --- | --- | --- | --- | --- |
| zero-size-partial | partial | 0 | `0x0` | `0x0` | unchanged expected initial pattern | unchanged | preserved |
| low-tail-positive | partial | 10 | `0x1` | `0x1` | matched expected `source & ~mask` | unchanged | preserved |
| first-word-boundary-positive | partial | 64 | `0x1` | `0x1` | matched expected `source & ~mask` | unchanged | preserved |
| second-word-before-missing-positive | partial | 80 | `0x1` | `0x1` | matched expected `source & ~mask` | unchanged | preserved |
| include-missing-bit90-positive | partial | 91 | `0x1` | `0x1` | matched expected `source & ~mask` | unchanged | preserved |
| full-size-positive-partial | partial | 128 | `0x1` | `0x1` | matched expected `source & ~mask` | unchanged | preserved |
| full-size-negative-full | full | 128 | `0x0` | `0x0` | matched expected zero result | unchanged | preserved |

Checks:

- `static-c1-identity`: OK, `__bitmap_andnot` resolved by `export-recovery`.
- `static-source-contract`: OK, signature matches the source oracle and pointer arg indices are `[0,1,2]`.
- `static-call-safety-contract`: OK, tier `SAFE-WITH-VALID-PTR`, x0 `bitmap-dst-buffer`,
  x1 `bitmap-src-buffer`, x2 `bitmap-mask-buffer`.
- Static word checks: OK for entry `nbits` shift, source/mask loads, `bic`, destination stores, and
  boolean return materialization.
- Owned source, partial-mask, full-mask, and destination allocations: OK.
- All poke/peek setup checks: OK.
- Seven-case mutation/return table: OK.
- Immutability: OK, source and mask bitmaps and all canaries stayed unchanged; destination changed
  only as expected for each case.
- Cleanup: OK, all four buffers freed with `kfree`.

Raw per-boot slide, target runtime address, owned allocation pointers, and observed bytes were
written only to private evidence and are not included in this report.

Candidate selftest after proof: `pass=11 warn=1 fail=0`.

## Rollback

Rollback command:

```sh
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 \
  workspace/public/src/scripts/revalidation/native_init_flash.py \
  --from-native \
  --expect-sha256 ca978551aabe4b39563abaf529ccf2522054952d8b2ad852e632d26da88168cb \
  workspace/private/inputs/boot_images/boot_linux_v2321_usb_clean_identity_rodata.img
```

Result:

- Remote pushed image SHA matched rollback SHA.
- Boot readback SHA matched rollback SHA.
- Post-rollback helper `version/status` verification passed.
- Bridge was restarted host-side once to clear a residual probe byte before the final standalone
  checks.
- Final standalone `version` confirmed `v2321-usb-clean-identity-rodata`.
- Final standalone selftest returned `pass=11 warn=1 fail=0`.

## Function Map Update

Add `__bitmap_andnot` as `live-proven` only under this contract:

- Static link identity: `0xffffff800855cc24`, `export-recovery`, direct BL xrefs `1`.
- Trusted input contract: owned destination unsigned-long bitmap buffer, owned source unsigned-long
  bitmap buffer, owned mask unsigned-long bitmap buffer, and scalar bit count bounded inside all
  three bitmaps.
- Observed result: zero-size false, partial-mask positive results for low-tail, first-word boundary,
  second-word tail, bit-90 inclusion, and full-size cases, plus full-mask full-size negative; destination
  matched `source & ~mask`, source/mask/canaries preserved.
- Cleanup: `kfree-owned-bitmap-andnot-buffers-ok`.

This does not authorize arbitrary bitmap pointers, unbounded `nbits`, aliasing assumptions, other
bitmap mutation helpers, or mass calling.
