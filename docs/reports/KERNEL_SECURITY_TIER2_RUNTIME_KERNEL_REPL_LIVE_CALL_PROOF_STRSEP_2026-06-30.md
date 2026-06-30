# Kernel Security Tier-2 Runtime Kernel REPL - Live Call Proof: strsep

- Date: 2026-06-30
- Decision: `a90-repl-live-call-proof-strsep-pass`
- Scope: separately gated one-target live-call proof after the REPL epic close.
- Device action: yes, boot partition only through `native_init_flash.py`.
- Candidate image: `workspace/private/inputs/boot_images/boot_linux_tier2_repl_v1_repl.img`
- Candidate SHA256: `b846ae9f74d8ceb922bbcd854d78b6795ef833d61e38465d3cc474cb6f0dfb65`
- Rollback image: `workspace/private/inputs/boot_images/boot_linux_v2321_usb_clean_identity_rodata.img`
- Rollback SHA256: `ca978551aabe4b39563abaf529ccf2522054952d8b2ad852e632d26da88168cb`
- Private evidence: `workspace/private/runs/kernel/live-call-proof-strsep-20260630/proof/a90_repl_evidence.json`

## Static Gate

Target:

- `strsep`: `0xffffff80099b9b94`
- Resolution method: `export-recovery`
- Direct BL xrefs: `230`
- Shape: JOPP entry, leaf/no-BL string tokenizer.
- Disasm contract: x0 is an owned `char **` cursor slot, x1 is an owned delimiter string. The code
  dereferences x0 to load the current string pointer, reads string and delimiter bytes, writes NUL at
  the matched delimiter inside the owned mutable string, and writes the next cursor back through the
  owned slot.
- Source signature: `include/linux/string.h:91`, `extern char * strsep(char **,const char *)`
- Source pointer contract: x0 is an owned cursor-slot buffer containing an owned mutable string
  pointer; x1 is an owned NUL-terminated delimiter string.
- Call-safety tier: `SAFE-WITH-VALID-PTR`
- Required valid pointer args: x0 = `string-pointer-slot`, x1 = `delimiter-string`

Owned-input orchestration:

- `__kmalloc`: `0xffffff800826ae34`, `export-recovery`, direct BL xrefs `1765`
- `kfree`: `0xffffff800826b354`, `export-recovery`, direct BL xrefs `10596`
- `__kmalloc` passed the no-pre-call-x0-deref guard.
- `strsep` was allowed to pre-deref x0 only under the owned cursor-slot layout and was called only
  after the tool allocated, initialized, and verified the slot, string, and delimiter buffers.

The target was not called with host-supplied numeric pointers. The proof used one owned cursor slot,
one owned mutable string buffer, and one owned delimiter string.

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
- Post-flash selftest confirmed `pass=11 warn=1 fail=0`.
- REPL selftest: `a90-repl-v2a1-selftest-pass`.

The v1-repl image intentionally keeps the v2321 native-init identity string, so `version` alone does
not distinguish it from the clean rollback image. The REPL selftest is the functional proof that the
candidate kernel REPL path is resident.

## Live Proof

Command:

```sh
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 \
  workspace/public/src/scripts/revalidation/a90_repl.py call-proof strsep \
  --map workspace/private/runs/kernel/v2c-c2b-kallsyms-padding-fix/System.map \
  --image workspace/private/inputs/boot_images/boot_linux_tier2_repl_v1_repl.img \
  --source-root workspace/private/inputs/kernel_source/SM-A908N_KOR_12_Opensource/Kernel \
  --evidence-dir workspace/private/runs/kernel/live-call-proof-strsep-20260630/proof
```

Public result:

```json
{
  "decision": "a90-repl-live-call-proof-strsep-pass",
  "ok": true,
  "input_ascii": "A90STRSEP-HEAD,Q-TAIL",
  "delimiter_ascii": ",",
  "expected_return_offset": 0,
  "observed_return_offset": 0,
  "expected_delimiter_offset": 14,
  "expected_next_offset": 15,
  "slot_updated_to_expected_next_offset": true,
  "delimiter_replaced_with_nul": true,
  "string_after_matches_expected": true,
  "delimiter_unchanged_after_call": true,
  "slot_canary_preserved": true,
  "string_canary_preserved": true,
  "delimiter_canary_preserved": true,
  "proof_status": "trusted-under-owned-input-contract",
  "raw_runtime_values_redacted": true,
  "owned_pointer_redacted": true,
  "observed_bytes_redacted": true
}
```

Checks:

- `static-c1-identity`: OK, `strsep` resolved by `export-recovery`.
- `static-source-contract`: OK, signature `extern char * strsep(char **,const char *)`.
- `static-call-safety-contract`: OK, tier `SAFE-WITH-VALID-PTR`, x0/x1 require verified owned buffers.
- `kmalloc-owned-strsep-buffers`: OK, allocated distinct owned slot, string, and delimiter buffers.
- `owned-strsep-buffer-poke-peek`: OK, slot, string, and delimiter bytes were written and read back.
- `strsep-return-contract`: OK, return matched the original owned string pointer, reported publicly as offset `0`.
- `strsep-slot-update-contract`: OK, cursor slot advanced to offset `15`.
- `strsep-string-mutation-contract`: OK, delimiter offset `14` was replaced with NUL.
- `strsep-delimiter-immutability`: OK, delimiter string stayed unchanged.
- `kfree-owned-strsep-buffers`: OK, all three owned buffers were freed.

Raw runtime slide, target runtime address, owned allocation pointers, and raw observed buffer bytes
were written only to private evidence and are not included in this report.

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
- One standalone final selftest read hit transient serial framing noise before a valid END marker.
- Sequential retry confirmed final selftest `pass=11 warn=1 fail=0`.

## Conclusion

`strsep` is now live-proven under an owned `char **` cursor slot plus owned mutable string plus owned
delimiter string contract. The proof confirms the intended helper was reached, returned the expected
owned string pointer, replaced the expected delimiter with NUL, advanced the cursor slot to the
expected next-token offset, preserved the delimiter and all canaries, cleaned up all allocations, and
left the device healthy. This does not authorize arbitrary cursor slots, arbitrary string pointers,
user pointers, unterminated strings, NULL slot layouts, multi-token loops, delimiter edge cases,
stale buffers, arbitrary parser state, or mass calling. The device was rolled back to clean v2321
with final `selftest fail=0`.
