# Kernel Security Tier-2 Runtime Kernel REPL - Live Call Proof: __bitmap_or

- Date: 2026-06-30
- Decision: `a90-repl-live-call-proof-__bitmap_or-pass`
- Scope: separately gated one-target live-call proof after the REPL epic close.
- Device action: yes, boot partition only through `native_init_flash.py`.
- Candidate image: `workspace/private/inputs/boot_images/boot_linux_tier2_repl_v1_repl.img`
- Candidate SHA256: `b846ae9f74d8ceb922bbcd854d78b6795ef833d61e38465d3cc474cb6f0dfb65`
- Rollback image: `workspace/private/inputs/boot_images/boot_linux_v2321_usb_clean_identity_rodata.img`
- Rollback SHA256: `ca978551aabe4b39563abaf529ccf2522054952d8b2ad852e632d26da88168cb`
- Private evidence: `workspace/private/runs/kernel/live-call-proof-bitmap-or-20260630/proof/a90_repl_evidence.json`

## Candidate Selection

This unit continued the bitmap mutation-helper sweep after `__bitmap_andnot`. `__bitmap_or`
was selected because C1 recovered one export candidate, the verified System.map agreed with it,
it has direct callers, and the static shape is leaf/no-BL with x1 source loads, x2 source loads,
x0 destination stores, and scalar `nbits` flow. `__bitmap_xor` and `__bitmap_and` were inspected
but parked for this unit because both had zero direct-BL xrefs under the current C1 gate.

This does not promote arbitrary bitmap mutation. The proof creates tool-owned destination, left,
partial-right, and full-right bitmap buffers, resets the destination before every case, calls only
bounded `nbits` values inside the 128-bit proof bitmap, re-peeks destination/source/canary state,
and frees every allocation.

## Static Gate

Target:

- `__bitmap_or`: `0xffffff800855cbb4`
- Resolution method: `export-recovery`
- Direct BL xrefs: `2`
- Shape: JOPP entry, leaf/no-BL.
- Static word checks:
  - `0x2a0303e8` at entry for the `nbits` move into the word-count path.
  - `0x9100fd08` and `0xd346fd08` for `(nbits + 63) >> 6`.
  - `0xf840842a` for the first left bitmap load.
  - `0xf840844b` for the first right bitmap load.
  - `0xaa0a016a` for the first OR operation.
  - `0xf800840a` for the first destination bitmap store.
- Source signature: `include/linux/bitmap.h:113`,
  `extern void __bitmap_or(unsigned long *dst, const unsigned long *bitmap1, const unsigned long *bitmap2, unsigned int nbits)`
- Source pointer contract: x0 is mutable destination, x1 and x2 are const source bitmaps, x3 is scalar `nbits`.
- Call-safety tier: `SAFE-WITH-VALID-PTR`
- Required valid pointer args: x0 `bitmap-dst-buffer`, x1 `bitmap-left-buffer`, x2 `bitmap-right-buffer`.

The target was not called with arbitrary numeric pointers. The proof requires three owned bitmap
arguments and scalar `nbits` values bounded to the proof bitmaps. The observed implementation writes
covered unsigned-long words via `(nbits + 63) >> 6`; the proof contract is word-coverage based, not
a tail-bit masking contract.

## Host Validation

Commands:

```sh
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m py_compile \
  workspace/public/src/scripts/revalidation/a90_repl.py \
  tests/test_a90_repl.py

PYTHONPATH=tests PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m unittest \
  tests.test_a90_repl.CallSafetyClassificationTests.test_safe_with_valid_pointer_seed_records_required_args \
  tests.test_a90_repl.CallSafetyClassificationTests.test_source_signature_oracle_distinguishes_scalar_and_pointer_args \
  tests.test_a90_repl.SelftestIntegrationTests.test_call_proof___bitmap_or_passes_with_owned_bitmap_contract

PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 \
  workspace/public/src/scripts/revalidation/a90_repl.py call-safety-classify \
  --map workspace/private/runs/kernel/v2c-c2b-kallsyms-padding-fix/System.map \
  --image workspace/private/inputs/boot_images/boot_linux_tier2_repl_v1_repl.img \
  --no-objdump \
  __bitmap_or

PYTHONPATH=tests PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m unittest tests.test_a90_repl
```

Result:

- `py_compile`: pass.
- Focused tests: static classification, source signature, and the fake-transport OR mutation proof
  passed (`Ran 3 tests`, `OK`).
- CLI classify: `SAFE-WITH-VALID-PTR`, verified by `export-recovery`, direct-BL xrefs `2`,
  leaf/no-BL, required x0 `bitmap-dst-buffer`, x1 `bitmap-left-buffer`, x2 `bitmap-right-buffer`.
- Full `tests.test_a90_repl`: `Ran 140 tests`, `OK`.

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
- A first standalone selftest read was accidentally overlapped with the REPL selftest and produced
  serial framing noise; this was not treated as health evidence. After a bridge restart, standalone
  candidate selftest returned `pass=11 warn=1 fail=0`.
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
  --evidence-dir workspace/private/runs/kernel/live-call-proof-bitmap-or-20260630/proof \
  __bitmap_or
```

Public result:

```json
{
  "decision": "a90-repl-live-call-proof-__bitmap_or-pass",
  "ok": true,
  "proof_status": "trusted-under-owned-input-contract",
  "input_contract": "owned destination unsigned-long bitmap buffer + two owned source unsigned-long bitmap buffers + scalar bit count bounded inside all three bitmaps",
  "return_contract": "void; destination receives source1 | source2 for the covered unsigned-long words, source bitmaps and canaries stay unchanged",
  "raw_runtime_values_redacted": true,
  "owned_pointer_redacted": true,
  "observed_bytes_redacted": true
}
```

Case table:

| Case | Right bitmap | nbits | Destination | Left/Right | Canaries |
| --- | --- | ---: | --- | --- | --- |
| zero-size-partial | partial | 0 | unchanged expected initial pattern | unchanged | preserved |
| low-tail-partial | partial | 10 | matched expected word-coverage OR result | unchanged | preserved |
| first-word-boundary-partial | partial | 64 | matched expected first-word OR result | unchanged | preserved |
| second-word-tail-partial | partial | 80 | matched expected two-word OR result | unchanged | preserved |
| full-size-partial | partial | 128 | matched expected two-word OR result | unchanged | preserved |
| full-size-full | full | 128 | matched expected two-word OR result | unchanged | preserved |

Checks:

- `static-c1-identity`: OK, `__bitmap_or` resolved by `export-recovery`.
- `static-source-contract`: OK, signature matches the source oracle and pointer arg indices are `[0,1,2]`.
- `static-call-safety-contract`: OK, tier `SAFE-WITH-VALID-PTR`, x0 `bitmap-dst-buffer`,
  x1 `bitmap-left-buffer`, x2 `bitmap-right-buffer`.
- Static word checks: OK for word-count setup, left/right loads, OR operation, and destination store.
- Owned left, partial-right, full-right, and destination allocations: OK.
- All poke/peek setup checks: OK.
- Six-case mutation table: OK.
- Immutability: OK, left and right bitmaps and all canaries stayed unchanged; destination changed
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
- A bridge restart immediately after helper verification hit one transient socket reset; bridge status
  was still healthy, and the following standalone checks succeeded.
- Final standalone `version` confirmed `v2321-usb-clean-identity-rodata`.
- Final standalone selftest returned `pass=11 warn=1 fail=0`.

## Function Map Update

Add `__bitmap_or` as `live-proven` only under this contract:

- Static link identity: `0xffffff800855cbb4`, `export-recovery`, direct BL xrefs `2`.
- Trusted input contract: owned destination unsigned-long bitmap buffer, two owned source unsigned-long
  bitmap buffers, and scalar bit count bounded inside all three bitmaps.
- Observed result: zero-size no-op, first-word and two-word OR destination mutation for partial/full
  right bitmaps; left/right/canaries preserved.
- Cleanup: `kfree-owned-bitmap-or-buffers-ok`.

This does not authorize arbitrary bitmap pointers, unbounded `nbits`, aliasing assumptions, other
bitmap mutation helpers, or mass calling.
