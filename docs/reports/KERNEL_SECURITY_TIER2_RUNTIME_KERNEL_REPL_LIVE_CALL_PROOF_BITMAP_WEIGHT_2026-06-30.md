# Kernel Security Tier-2 Runtime Kernel REPL - Live Call Proof: __bitmap_weight

- Date: 2026-06-30
- Decision: `a90-repl-live-call-proof-__bitmap_weight-pass`
- Scope: separately gated one-target live-call proof after the REPL epic close.
- Device action: yes, boot partition only through `native_init_flash.py`.
- Candidate image: `workspace/private/inputs/boot_images/boot_linux_tier2_repl_v1_repl.img`
- Candidate SHA256: `b846ae9f74d8ceb922bbcd854d78b6795ef833d61e38465d3cc474cb6f0dfb65`
- Rollback image: `workspace/private/inputs/boot_images/boot_linux_v2321_usb_clean_identity_rodata.img`
- Rollback SHA256: `ca978551aabe4b39563abaf529ccf2522054952d8b2ad852e632d26da88168cb`
- Private evidence: `workspace/private/runs/kernel/live-call-proof-bitmap-weight-20260630/proof/a90_repl_evidence.json`

## Candidate Selection

This unit continued the bitmap helper sweep after the scalar hweight helpers and the bit-search
helpers. `bitmap_ord_to_pos` was considered first, but was left parked because it had no export and
no direct BL xrefs, so the default C1 resolver could not prove identity strongly enough for a live
call. `__bitmap_weight` was selected instead because it is export-recovered, has direct callers, and
uses the already live-proven `__sw_hweight64` helper internally.

The selected target is not trusted as a general bitmap facility. The proof creates one owned kernel
unsigned-long bitmap buffer, writes a fixed two-word pattern plus canary, calls a bounded case table
with scalar `nbits` values inside that bitmap, checks all returns, re-peeks the bitmap/canary after
the calls, and frees the allocation.

## Static Gate

Target:

- `__bitmap_weight`: `0xffffff800855cdd4`
- Resolution method: `export-recovery`
- Direct BL xrefs: `19`
- Shape: JOPP entry, non-leaf, full-word and tail-word paths call `__sw_hweight64`.
- Wrapper evidence:
  - `0x940042b6` for the pinned full-word hweight64 call.
  - `0x940042aa` for the pinned tail-word hweight64 call.
- Source signature: `include/linux/bitmap.h:123`,
  `extern int __bitmap_weight(const unsigned long *bitmap, unsigned int nbits)`
- Source pointer contract: x0 is `const unsigned long *bitmap`; x1 is scalar `nbits`.
- Call-safety tier: `SAFE-WITH-VALID-PTR`
- Required valid pointer args: x0 `bitmap-buffer`.

The target was not called with an arbitrary numeric pointer. The proof requires one owned bitmap
buffer and scalar `nbits` values bounded to the proof bitmap.

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
  __bitmap_weight

PYTHONPATH=tests PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m unittest \
  tests.test_a90_repl.CallSafetyClassificationTests.test_proven_live_call_targets_stay_safe \
  tests.test_a90_repl.CallSafetyClassificationTests.test_source_signature_oracle_distinguishes_scalar_and_pointer_args \
  tests.test_a90_repl.SelftestIntegrationTests.test_call_proof___bitmap_weight_passes_with_owned_bitmap_contract

PYTHONPATH=tests PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m unittest tests.test_a90_repl
```

Result:

- `py_compile`: pass.
- CLI classify: `SAFE-WITH-VALID-PTR`, verified by `export-recovery`, direct-BL xrefs `19`,
  non-leaf wrapper, required x0 `bitmap-buffer`.
- Focused tests: static classification/source tests and the new fake-transport proof passed.
- Full `tests.test_a90_repl`: `Ran 136 tests`, `OK`.

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
  --evidence-dir workspace/private/runs/kernel/live-call-proof-bitmap-weight-20260630/proof \
  __bitmap_weight
```

Public result:

```json
{
  "decision": "a90-repl-live-call-proof-__bitmap_weight-pass",
  "ok": true,
  "proof_status": "trusted-under-owned-input-contract",
  "input_contract": "owned unsigned-long bitmap buffer + scalar bit count bounded inside that bitmap",
  "return_contract": "int == population count of set bits below nbits",
  "raw_runtime_values_redacted": true,
  "owned_pointer_redacted": true,
  "observed_bytes_redacted": true
}
```

Case table:

| Case | nbits | Expected | Observed |
| --- | ---: | --- | --- |
| zero-size | 0 | `0x0` | `0x0` |
| low-tail | 10 | `0x3` | `0x3` |
| first-word-boundary | 64 | `0x5` | `0x5` |
| second-word-tail | 80 | `0x7` | `0x7` |
| include-third-second-word-bit | 91 | `0x8` | `0x8` |
| exclude-last-bit-boundary | 127 | `0x8` | `0x8` |
| full-size | 128 | `0x9` | `0x9` |

Checks:

- `static-c1-identity`: OK, `__bitmap_weight` resolved by `export-recovery`.
- `static-source-contract`: OK, signature matches the source oracle and pointer arg index is `[0]`.
- `static-call-safety-contract`: OK, tier `SAFE-WITH-VALID-PTR`, x0 `bitmap-buffer`.
- `static-full-word-hweight64-call`: OK, wrapper BL word `0x940042b6` matched.
- `static-tail-word-hweight64-call`: OK, wrapper BL word `0x940042aa` matched.
- `kmalloc-owned-bitmap-weight-bitmap`: OK, owned kernel bitmap allocation returned sane lowmem.
- `owned-bitmap-weight-bitmap-poke-peek`: OK, proof bitmap and canary wrote/read back exactly.
- `bitmap-weight-case-table`: OK, all 7 calls returned expected popcounts.
- `bitmap-weight-bitmap-immutability`: OK, bitmap and canary stayed unchanged after the calls.
- `kfree-owned-bitmap-weight-bitmap`: OK.

Raw per-boot slide, target runtime address, owned allocation pointer, and observed bytes were written
only to private evidence and are not included in this report.

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
- A combined final `version && selftest` read hit serial noise before an END marker; this was
  rechecked read-only with separate commands.
- Final standalone `version` confirmed `v2321-usb-clean-identity-rodata`.
- Final standalone selftest returned `pass=11 warn=1 fail=0`.

## Function Map Update

Add `__bitmap_weight` as `live-proven` only under this contract:

- Static link identity: `0xffffff800855cdd4`, `export-recovery`, direct BL xrefs `19`.
- Trusted input contract: one owned unsigned-long bitmap buffer and scalar bit count bounded inside
  that bitmap.
- Observed result: zero count, low-tail popcount, first-word boundary, second-word tail, third-set-bit
  inclusion, last-bit exclusion boundary, and full-size popcount cases.
- Cleanup: `kfree-owned-bitmap-weight-bitmap-ok`.

This does not authorize arbitrary bitmap pointers, unbounded `nbits`, aliasing assumptions, mutation
paths, or mass calling.
