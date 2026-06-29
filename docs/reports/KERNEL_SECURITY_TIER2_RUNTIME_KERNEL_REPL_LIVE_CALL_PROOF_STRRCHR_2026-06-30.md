# Kernel Security Tier-2 Runtime Kernel REPL - Live Call Proof: strrchr

- Date: 2026-06-30
- Decision: `a90-repl-live-call-proof-strrchr-pass`
- Scope: separately gated one-target live-call proof after the REPL epic close.
- Device action: yes, boot partition only through `native_init_flash.py`.
- Candidate image: `workspace/private/inputs/boot_images/boot_linux_tier2_repl_v1_repl.img`
- Candidate SHA256: `b846ae9f74d8ceb922bbcd854d78b6795ef833d61e38465d3cc474cb6f0dfb65`
- Rollback image: `workspace/private/inputs/boot_images/boot_linux_v2321_usb_clean_identity_rodata.img`
- Rollback SHA256: `ca978551aabe4b39563abaf529ccf2522054952d8b2ad852e632d26da88168cb`
- Private evidence: `workspace/private/runs/kernel/live-call-proof-strrchr-20260630/proof/a90_repl_evidence.json`

## Static Gate

Target:

- `strrchr`: `0xffffff80099a900c`
- Resolution method: `leaf-map-disasm+xref`
- Direct BL xrefs: `1405`
- Shape: non-JOPP arm64 leaf helper; no BL in scan; RET observed at offset `0x24`.
- Source signature: `include/linux/string.h:64`, `extern char * strrchr(const char *,int)`
- Source pointer contract: x0 is the string buffer, x1 is the scalar search byte.
- Call-safety tier: `SAFE-WITH-VALID-PTR`
- Required valid pointer args: x0 = `string-buffer`

`strrchr` is an arm64 leaf routine without the JOPP marker used by most C functions in this image.
The C1 exception is intentionally narrow: it accepts only the `strrchr` System.map label when the body
is leaf/no-BL, has a RET in scan, has no zero-return-before-ret pattern, and has at least 1000 direct
BL xrefs. The observed xref count was `1405`.

This proof owns the string buffer and fixes the probe to a NUL-terminated string
`A90STRRCHR-A-B-A-Z`, search byte `0x41` (`A`), and missing byte `0x40` (`@`). It does not authorize
arbitrary pointers, unterminated strings, user pointers, or other string helpers.

Owned-input orchestration:

- `__kmalloc`: `0xffffff800826ae34`, `export-recovery`, direct BL xrefs `1765`
- `kfree`: `0xffffff800826b354`, `export-recovery`, direct BL xrefs `10596`
- `__kmalloc` passed the no-pre-call-x0-deref guard.

The target was not called with host-supplied numeric pointers. The tool allocated one owned string
buffer, filled the scan window with a NUL-terminated proof string plus canary, verified it by peek,
called `strrchr(buf, 'A')`, checked the returned pointer matched the expected last-occurrence offset
`15`, called `strrchr(buf, '@')`, checked that it returned `0`, verified string immutability after both
calls, then freed the buffer.

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
- Baseline before flash: `v2321`, `version` OK, `selftest pass=11 warn=1 fail=0`.

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
- Candidate native selftest: `pass=11 warn=1 fail=0`.
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
  --timeout 60 \
  --dmesg-tail 80 \
  --safe-op-retries 1 \
  --retry-delay-sec 0.2 \
  --evidence-dir workspace/private/runs/kernel/live-call-proof-strrchr-20260630/proof \
  strrchr
```

Public result:

```json
{
  "decision": "a90-repl-live-call-proof-strrchr-pass",
  "ok": true,
  "proof_string": "A90STRRCHR-A-B-A-Z",
  "search_byte": "0x41",
  "expected_hit_offset": 15,
  "return_matches_expected_offset": true,
  "missing_byte": "0x40",
  "missing_observed_return_value": "0x0",
  "string_unchanged_after_calls": true,
  "proof_status": "trusted-under-owned-input-contract",
  "raw_runtime_values_redacted": true,
  "owned_pointer_redacted": true,
  "observed_bytes_redacted": true
}
```

Checks:

- `static-c1-identity`: OK, `strrchr` resolved by `leaf-map-disasm+xref`.
- `static-source-contract`: OK, signature `extern char * strrchr(const char *,int)`.
- `static-call-safety-contract`: OK, tier `SAFE-WITH-VALID-PTR`, x0 requires verified string buffer.
- `kmalloc-owned-strrchr-string-buffer`: OK, allocated owned kernel string buffer.
- `owned-strrchr-string-poke-peek`: OK, proof string plus canary were written and read back.
- `strrchr-hit-return-contract`: OK, search byte `0x41` returned the expected owned-pointer offset
  `15`.
- `strrchr-hit-string-immutability`: OK, hit case did not modify the string buffer.
- `strrchr-miss-return-contract`: OK, missing byte `0x40` returned `0x0`.
- `strrchr-miss-string-immutability`: OK, miss case did not modify the string buffer.
- `kfree-owned-strrchr-string-buffer`: OK, cleanup succeeded.

Raw runtime slide, `strrchr` runtime address, owned allocation pointer, hit return pointer, and raw
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

`strrchr` is now live-proven under the owned NUL-terminated string plus scalar-search-byte contract.
The proof confirms the intended helper was reached, returned the expected owned-pointer offset for a
present byte, returned `0` for a missing byte, left the string buffer unchanged, and left the device
healthy after cleanup. This does not authorize arbitrary pointers, unterminated strings, user pointers,
or other string helpers. The device was rolled back to clean v2321 with final `selftest fail=0`.
