# Kernel Security Tier-2 Runtime Kernel REPL - Live Call Proof: __sysfs_match_string

- Date: 2026-06-30
- Decision: `a90-repl-live-call-proof-__sysfs_match_string-pass`
- Scope: separately gated one-target live-call proof after the REPL epic close.
- Device action: yes, boot partition only through `native_init_flash.py`.
- Candidate image: `workspace/private/inputs/boot_images/boot_linux_tier2_repl_v1_repl.img`
- Candidate SHA256: `b846ae9f74d8ceb922bbcd854d78b6795ef833d61e38465d3cc474cb6f0dfb65`
- Rollback image: `workspace/private/inputs/boot_images/boot_linux_v2321_usb_clean_identity_rodata.img`
- Rollback SHA256: `ca978551aabe4b39563abaf529ccf2522054952d8b2ad852e632d26da88168cb`
- Private evidence: `workspace/private/runs/kernel/live-call-proof-sysfs-match-string-20260630/proof/a90_repl_evidence.json`

## Static Gate

Target:

- `__sysfs_match_string`: `0xffffff80099b9d1c`
- Resolution method: `export-recovery`
- Direct BL xrefs: `11`
- Shape: JOPP entry, leaf/no-BL sysfs array matcher.
- Disasm contract: the helper walks a bounded `const char *` array, compares each entry with the search string using sysfs trailing-newline equality semantics, returns the matching index, and returns 32-bit `-EINVAL` for no match or zero count.
- Source signature: `include/linux/string.h:187`, `int __sysfs_match_string(const char * const *array, size_t n, const char *s)`
- Source pointer contract: x0 is an owned `const char *` array, x2 is an owned NUL-terminated kernel search string, and x1 is a scalar count bounded inside that array.
- Call-safety tier: `SAFE-WITH-VALID-PTR`
- Required valid pointer args: x0 = `string-pointer-array`, x2 = `search-string-buffer`

Owned-input orchestration:

- `__kmalloc`: `0xffffff800826ae34`, `export-recovery`, direct BL xrefs `1765`
- `kfree`: `0xffffff800826b354`, `export-recovery`, direct BL xrefs `10596`
- `__kmalloc` passed the no-pre-call-x0-deref guard.
- `__sysfs_match_string` reads through x0 and x2 by design, so the proof requires tool-owned pointers before allowing the call.

The target was not called with host-supplied numeric pointers. The tool allocated one owned kernel
layout, wrote the pointer table, three owned NUL-terminated item strings, an owned search string, and
canaries, then verified the layout stayed unchanged after all calls.

## Host Validation

Commands:

```sh
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m py_compile \
  workspace/public/src/scripts/revalidation/a90_repl.py \
  tests/test_a90_repl.py

PYTHONPATH=tests PYTHONPYCACHEPREFIX=/tmp/a90_pycache \
  python3 -m unittest tests.test_a90_repl
```

Result:

- `py_compile`: pass.
- `tests.test_a90_repl`: `Ran 124 tests`, `OK`.

## Flash And Health

Preconditions:

- v1-repl candidate SHA matched `b846ae9f74d8ceb922bbcd854d78b6795ef833d61e38465d3cc474cb6f0dfb65`.
- v2321 rollback SHA matched `ca978551aabe4b39563abaf529ccf2522054952d8b2ad852e632d26da88168cb`.
- v2237 fallback SHA matched `b2ea2d26d160b7702ce7d4438b84367788eea26c6a5bbe4ed93f3d270292ac7f`.
- Final fallback `boot_linux_v48.img` existed with SHA
  `1c87fa59712395027c5c2e489b15c4f6ddefabc3c50f78d3c235c4508a63e042`.
- TWRP recovery image existed with SHA
  `b1ef377a52ec8ab43b49a5fcc7a0b27e8efff91bf2d8cccdc565ecadadcc646c`.
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
- The first REPL selftest attempt hit a transient serial END-marker timeout while setting `panic_on_oops`.
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
  --evidence-dir workspace/private/runs/kernel/live-call-proof-sysfs-match-string-20260630/proof \
  __sysfs_match_string
```

Public result:

```json
{
  "decision": "a90-repl-live-call-proof-__sysfs_match_string-pass",
  "ok": true,
  "array_count": 3,
  "array_items": [
    "A90SYSFSMATCH-ALPHA",
    "A90SYSFSMATCH-BRAVO",
    "A90SYSFSMATCH-CHARLIE"
  ],
  "search": "A90SYSFSMATCH-BRAVO\\n",
  "missing_search": "A90SYSFSMATCH-MISSING",
  "expected_hit_index": 1,
  "hit_observed_return_value": "0x1",
  "missing_observed_return_value": "0xffffffea",
  "zero_count_observed_return_value": "0xffffffea",
  "layout_unchanged_after_calls": true,
  "proof_status": "trusted-under-owned-input-contract",
  "raw_runtime_values_redacted": true,
  "owned_pointer_redacted": true,
  "observed_bytes_redacted": true
}
```

Checks:

- `static-c1-identity`: OK, `__sysfs_match_string` resolved by `export-recovery`.
- `static-source-contract`: OK, signature `int __sysfs_match_string(const char * const *array, size_t n, const char *s)`.
- `static-call-safety-contract`: OK, tier `SAFE-WITH-VALID-PTR`, x0/x2 require verified owned buffers and x1 is bounded count.
- `kmalloc-owned-sysfs-match-string-layout`: OK, allocated one owned layout for the pointer table, item strings, search string, and canaries.
- `owned-sysfs-match-string-layout-poke-peek`: OK, pointer table, item strings, search string, and canaries were written and read back.
- `sysfs-match-string-newline-hit-return-contract`: OK, newline-tolerant search returned index `1`.
- `sysfs-match-string-hit-layout-immutability`: OK, table, items, search string, and canaries stayed unchanged.
- `owned-sysfs-match-string-missing-search-poke-peek`: OK, missing search string and canary were written and read back.
- `sysfs-match-string-missing-return-contract`: OK, missing search returned `0xffffffea`.
- `sysfs-match-string-zero-count-return-contract`: OK, zero count returned `0xffffffea`.
- `sysfs-match-string-final-layout-immutability`: OK, table, items, missing search string, and canaries stayed unchanged.
- `kfree-owned-sysfs-match-string-layout`: OK, cleanup succeeded.

Raw runtime slide, `__sysfs_match_string` runtime address, owned layout pointer, item pointers,
search pointer, and raw observed bytes were written only to private evidence and are not included in
this report.

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
- Final standalone `selftest`: `pass=11 warn=1 fail=0`.

## Conclusion

`__sysfs_match_string` is now live-proven under an owned array plus owned search string contract. The
proof confirms the intended helper was reached, returned index `1` for the sysfs newline-tolerant
match, returned 32-bit `-EINVAL` for missing and zero-count cases, left the owned layout unchanged,
cleaned up the allocation, and left the device healthy. This does not authorize arbitrary arrays, user
pointers, unterminated strings, stale buffers, unbounded counts, output aliases, or mass calling. The
device was rolled back to clean v2321 with final `selftest fail=0`.
