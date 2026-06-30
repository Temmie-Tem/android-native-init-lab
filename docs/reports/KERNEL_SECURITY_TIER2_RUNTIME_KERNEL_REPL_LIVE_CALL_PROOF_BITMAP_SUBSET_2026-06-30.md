# Kernel Security Tier-2 Runtime Kernel REPL - Live Call Proof: __bitmap_subset

- Date: 2026-06-30
- Decision: `a90-repl-live-call-proof-__bitmap_subset-pass`
- Scope: separately gated one-target live-call proof after the REPL epic close.
- Device action: yes, boot partition only through `native_init_flash.py`.
- Candidate image: `workspace/private/inputs/boot_images/boot_linux_tier2_repl_v1_repl.img`
- Candidate SHA256: `b846ae9f74d8ceb922bbcd854d78b6795ef833d61e38465d3cc474cb6f0dfb65`
- Rollback image: `workspace/private/inputs/boot_images/boot_linux_v2321_usb_clean_identity_rodata.img`
- Rollback SHA256: `ca978551aabe4b39563abaf529ccf2522054952d8b2ad852e632d26da88168cb`
- Private evidence: `workspace/private/runs/kernel/live-call-proof-bitmap-subset-20260630/proof/a90_repl_evidence.json`

## Candidate Selection

This unit continued the bitmap helper sweep after `__bitmap_weight`. `bitmap_empty`, `bitmap_full`,
`bitmap_equal`, `bitmap_intersects`, and other non-underscored bitmap names were rejected because
they are absent from the verified System.map in this build. `__bitmap_equal` and
`__bitmap_intersects` were also parked because their direct BL xref count is zero under the current
C1 rules. `__bitmap_subset` was selected because it is export-recovered, has direct callers, has a
clear header ABI, and is a leaf read-only helper over two caller-owned bitmaps.

The selected target is not trusted as a general bitmap facility. The proof creates tool-owned source,
full-mask, partial-mask, and empty-source bitmap buffers, calls a bounded case table with scalar
`nbits` values inside the 128-bit buffers, checks all returns, re-peeks all bitmaps/canaries after the
calls, and frees every allocation.

## Static Gate

Target:

- `__bitmap_subset`: `0xffffff800855cd3c`
- Resolution method: `export-recovery`
- Direct BL xrefs: `3`
- Shape: JOPP entry, leaf/no-BL.
- Static word checks:
  - `0x53067c49` at entry for `nbits >> 6`.
  - `0xf940014c` for the first bitmap1 load.
  - `0xf940016d` for the first bitmap2 load.
  - `0xf869680a` for the tail bitmap1 load.
  - `0xf8696829` for the tail bitmap2 load.
- Source signature: `include/linux/bitmap.h:121`,
  `extern int __bitmap_subset(const unsigned long *bitmap1, const unsigned long *bitmap2, unsigned int nbits)`
- Source pointer contract: x0 and x1 are `const unsigned long *`; x2 is scalar `nbits`.
- Call-safety tier: `SAFE-WITH-VALID-PTR`
- Required valid pointer args: x0 `bitmap-buffer`, x1 `bitmap-buffer`.

The target was not called with arbitrary numeric pointers. The proof requires two owned bitmap
buffers and scalar `nbits` values bounded to the proof bitmaps.

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
  __bitmap_subset

PYTHONPATH=tests PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m unittest \
  tests.test_a90_repl.CallSafetyClassificationTests.test_proven_live_call_targets_stay_safe \
  tests.test_a90_repl.CallSafetyClassificationTests.test_source_signature_oracle_distinguishes_scalar_and_pointer_args \
  tests.test_a90_repl.SelftestIntegrationTests.test_call_proof___bitmap_subset_passes_with_owned_bitmap_contract

PYTHONPATH=tests PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m unittest tests.test_a90_repl
```

Result:

- `py_compile`: pass.
- CLI classify: `SAFE-WITH-VALID-PTR`, verified by `export-recovery`, direct-BL xrefs `3`, leaf/no-BL,
  required x0/x1 `bitmap-buffer`.
- Focused tests: static classification/source tests and the new fake-transport proof passed.
- Full `tests.test_a90_repl`: `Ran 137 tests`, `OK`.

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
  --from-native workspace/private/inputs/boot_images/boot_linux_tier2_repl_v1_repl.img \
  --expect-sha256 b846ae9f74d8ceb922bbcd854d78b6795ef833d61e38465d3cc474cb6f0dfb65 \
  --expect-readback-sha256 b846ae9f74d8ceb922bbcd854d78b6795ef833d61e38465d3cc474cb6f0dfb65
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
  --evidence-dir workspace/private/runs/kernel/live-call-proof-bitmap-subset-20260630/proof \
  __bitmap_subset
```

Public result:

```json
{
  "decision": "a90-repl-live-call-proof-__bitmap_subset-pass",
  "ok": true,
  "proof_status": "trusted-under-owned-input-contract",
  "input_contract": "two owned unsigned-long bitmap buffers + scalar bit count bounded inside both bitmaps",
  "return_contract": "int bool == 1 when every set bit in bitmap1 below nbits is also set in bitmap2, else 0",
  "raw_runtime_values_redacted": true,
  "owned_pointer_redacted": true,
  "observed_bytes_redacted": true
}
```

Case table:

| Case | Source | Mask | nbits | Expected | Observed |
| --- | --- | --- | ---: | --- | --- |
| zero-size-nonempty-src-partial | src | partial | 0 | `0x1` | `0x1` |
| empty-src-full-size | empty | partial | 128 | `0x1` | `0x1` |
| low-tail-positive | src | partial | 10 | `0x1` | `0x1` |
| first-word-boundary-positive | src | partial | 64 | `0x1` | `0x1` |
| second-word-before-missing-positive | src | partial | 80 | `0x1` | `0x1` |
| include-missing-bit90-negative | src | partial | 91 | `0x0` | `0x0` |
| full-size-negative-partial | src | partial | 128 | `0x0` | `0x0` |
| full-size-positive-full | src | full | 128 | `0x1` | `0x1` |

Checks:

- `static-c1-identity`: OK, `__bitmap_subset` resolved by `export-recovery`.
- `static-source-contract`: OK, signature matches the source oracle and pointer arg indices are `[0,1]`.
- `static-call-safety-contract`: OK, tier `SAFE-WITH-VALID-PTR`, x0/x1 `bitmap-buffer`.
- Static word checks: OK for entry `nbits` shift, first-word bitmap1/bitmap2 loads, and tail
  bitmap1/bitmap2 loads.
- Four owned bitmap allocations: OK.
- Four bitmap poke/peek setup checks: OK.
- Eight-case return table: OK.
- Immutability: OK, source/full/partial/empty bitmaps and canaries stayed unchanged.
- Cleanup: OK, all four buffers freed with `kfree`.

Raw per-boot slide, target runtime address, owned allocation pointers, and observed bytes were
written only to private evidence and are not included in this report.

Candidate selftest after proof: `pass=11 warn=1 fail=0`.

## Rollback

Rollback command:

```sh
python3 workspace/public/src/scripts/revalidation/native_init_flash.py \
  --from-native workspace/private/inputs/boot_images/boot_linux_v2321_usb_clean_identity_rodata.img \
  --expect-sha256 ca978551aabe4b39563abaf529ccf2522054952d8b2ad852e632d26da88168cb \
  --expect-readback-sha256 ca978551aabe4b39563abaf529ccf2522054952d8b2ad852e632d26da88168cb
```

Result:

- Remote pushed image SHA matched rollback SHA.
- Boot readback SHA matched rollback SHA.
- Post-rollback helper `version/status` verification passed.
- Final standalone `version` confirmed `v2321-usb-clean-identity-rodata`.
- Final standalone selftest returned `pass=11 warn=1 fail=0`.

## Function Map Update

Add `__bitmap_subset` as `live-proven` only under this contract:

- Static link identity: `0xffffff800855cd3c`, `export-recovery`, direct BL xrefs `3`.
- Trusted input contract: two owned unsigned-long bitmap buffers and scalar bit count bounded inside
  both bitmaps.
- Observed result: zero-size true, empty-source true, low-tail/first-word/second-word positive
  subset cases, bit-90 missing negative, full-size partial-mask negative, and full-size full-mask
  positive cases.
- Cleanup: `kfree-owned-bitmap-subset-buffers-ok`.

This does not authorize arbitrary bitmap pointers, unbounded `nbits`, aliasing assumptions, mutation
paths, `__bitmap_equal`/`__bitmap_intersects`, or mass calling.
