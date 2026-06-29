# Kernel Security Tier-2 Runtime Kernel REPL - Live Call Proof: strreplace

- Date: 2026-06-30
- Decision: `a90-repl-live-call-proof-strreplace-pass`
- Scope: separately gated one-target live-call proof after the REPL epic close.
- Device action: yes, boot partition only through `native_init_flash.py`.
- Candidate image: `workspace/private/inputs/boot_images/boot_linux_tier2_repl_v1_repl.img`
- Candidate SHA256: `b846ae9f74d8ceb922bbcd854d78b6795ef833d61e38465d3cc474cb6f0dfb65`
- Rollback image: `workspace/private/inputs/boot_images/boot_linux_v2321_usb_clean_identity_rodata.img`
- Rollback SHA256: `ca978551aabe4b39563abaf529ccf2522054952d8b2ad852e632d26da88168cb`
- Private evidence: `workspace/private/runs/kernel/live-call-proof-strreplace-20260630/proof/a90_repl_evidence.json`

## Static Gate

Target:

- `strreplace`: `0xffffff80099ba12c`
- Resolution method: `export-recovery`
- Direct BL xrefs: `15`
- Shape: JOPP entry, leaf/no-BL helper; first RET observed at offset `0x8` with a scan of `64`
  bytes.
- Source signature: `include/linux/string.h:166`, `char * strreplace(char *s, char old, char new)`
- Source pointer contract: x0 is the mutable NUL-terminated string buffer; x1/x2 are scalar bytes.
- Call-safety tier: `SAFE-WITH-VALID-PTR`
- Required valid pointer args: x0 = `mutable-string-buffer`

Owned-input orchestration:

- `__kmalloc`: `0xffffff800826ae34`, `export-recovery`, direct BL xrefs `1765`
- `kfree`: `0xffffff800826b354`, `export-recovery`, direct BL xrefs `10596`
- `__kmalloc` passed the no-pre-call-x0-deref guard.

The target was not called with host-supplied numeric pointers. The tool allocated one owned mutable
kernel string buffer, wrote `A90STRREPLACE-Q-Q-END`, required `strreplace(buf, 'Q', 'Z')` to return
the owned NUL terminator pointer at offset `21`, and required both `Q` bytes to become `Z`. It then
rewrote the same buffer, called the missing-byte case with `@ -> !`, required the same NUL pointer
return, and required the string to remain unchanged.

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
- One candidate selftest read hit serial input noise before any proof call; normal mode re-sync
  succeeded immediately.
- Candidate native selftest after re-sync: `pass=11 warn=1 fail=0`.
- `a90_repl.py selftest`: `a90-repl-v2a1-selftest-pass`.

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
  --timeout 90 \
  --dmesg-tail 80 \
  --safe-op-retries 2 \
  --retry-delay-sec 0.3 \
  --evidence-dir workspace/private/runs/kernel/live-call-proof-strreplace-20260630/proof \
  strreplace
```

Public result:

```json
{
  "decision": "a90-repl-live-call-proof-strreplace-pass",
  "ok": true,
  "proof_string": "A90STRREPLACE-Q-Q-END",
  "expected_replaced_string": "A90STRREPLACE-Z-Z-END",
  "old_byte": "0x51",
  "new_byte": "0x5a",
  "missing_byte": "0x40",
  "expected_nul_offset": 21,
  "hit_expected_return_value": "owned-string-nul-terminator-pointer-redacted",
  "hit_observed_return_value": "owned-string-nul-terminator-pointer-redacted",
  "hit_return_matches_nul_offset": true,
  "replacement_bytes_match_expected": true,
  "missing_expected_return_value": "owned-string-nul-terminator-pointer-redacted",
  "missing_observed_return_value": "owned-string-nul-terminator-pointer-redacted",
  "missing_return_matches_nul_offset": true,
  "missing_string_unchanged_after_call": true,
  "proof_status": "trusted-under-owned-input-contract",
  "raw_runtime_values_redacted": true,
  "owned_pointer_redacted": true,
  "observed_bytes_redacted": true
}
```

Checks:

- `static-c1-identity`: OK, `strreplace` resolved by `export-recovery`.
- `static-source-contract`: OK, signature `char * strreplace(char *s, char old, char new)`.
- `static-call-safety-contract`: OK, tier `SAFE-WITH-VALID-PTR`, x0 requires a verified mutable string.
- `kmalloc-owned-strreplace-string-buffer`: OK, allocated one owned mutable kernel string buffer.
- `owned-strreplace-hit-string-poke-peek`: OK, hit string plus canary was written and read back.
- `strreplace-hit-return-contract`: OK, returned the owned NUL terminator pointer at offset `21`.
- `strreplace-hit-mutation-contract`: OK, both `Q` bytes were replaced with `Z`; canary was preserved.
- `owned-strreplace-missing-string-poke-peek`: OK, missing-case string plus canary was written and read back.
- `strreplace-missing-return-contract`: OK, returned the owned NUL terminator pointer at offset `21`.
- `strreplace-missing-string-immutability`: OK, missing-byte case left the string unchanged.
- `kfree-owned-strreplace-string-buffer`: OK, cleanup succeeded.

Raw runtime slide, `strreplace` runtime address, owned allocation pointer, return pointers, and raw
observed bytes were written only to private evidence and are not included in this report.

Candidate selftest after proof: `pass=11 warn=1 fail=0`.

## Rollback

Rollback command:

```sh
python3 workspace/public/src/scripts/revalidation/native_init_flash.py \
  --from-native \
  --expect-sha256 ca978551aabe4b39563abaf529ccf2522054952d8b2ad852e632d26da88168cb \
  --expect-readback-sha256 ca978551aabe4b39563abaf529ccf2522054952d8b2ad852e632d26da88168cb \
  workspace/private/inputs/boot_images/boot_linux_v2321_usb_clean_identity_rodata.img
```

Result:

- Remote pushed image SHA matched v2321 SHA.
- Boot readback SHA matched v2321 SHA.
- Post-rollback `version/status` verification passed.
- Final resident: `A90 Linux init 0.9.285 (v2321-usb-clean-identity-rodata)`.
- Final `selftest`: `pass=11 warn=1 fail=0`.

## Conclusion

`strreplace` is now live-proven under the owned mutable NUL-terminated kernel string plus scalar
old/new byte contract. The proof confirms the intended helper was reached, returned the expected NUL
terminator pointer, performed the expected bounded in-place replacement, left a missing-byte case
unchanged, cleaned up its allocation, and left the device healthy. This does not authorize arbitrary
pointers, user pointers, unterminated strings, read-only strings, or mass calling. The device was
rolled back to clean v2321 with final `selftest fail=0`.
