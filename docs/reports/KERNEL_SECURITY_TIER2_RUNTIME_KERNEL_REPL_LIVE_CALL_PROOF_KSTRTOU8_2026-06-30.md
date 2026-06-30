# Kernel Security Tier-2 Runtime Kernel REPL - Live Call Proof: kstrtou8

- Date: 2026-06-30
- Decision: `a90-repl-live-call-proof-kstrtou8-pass`
- Scope: separately gated one-target live-call proof after the REPL epic close.
- Device action: yes, boot partition only through `native_init_flash.py`.
- Candidate image: `workspace/private/inputs/boot_images/boot_linux_tier2_repl_v1_repl.img`
- Candidate SHA256: `b846ae9f74d8ceb922bbcd854d78b6795ef833d61e38465d3cc474cb6f0dfb65`
- Rollback image: `workspace/private/inputs/boot_images/boot_linux_v2321_usb_clean_identity_rodata.img`
- Rollback SHA256: `ca978551aabe4b39563abaf529ccf2522054952d8b2ad852e632d26da88168cb`
- Private evidence: `workspace/private/runs/kernel/live-call-proof-kstrtou8-20260630/proof/a90_repl_evidence.json`

## Static Gate

Target:

- `kstrtou8`: `0xffffff800856b9a4`
- Resolution method: `export-recovery`
- Direct BL xrefs: `59`
- Shape: JOPP entry, non-leaf helper calling `kstrtoull` plus the stack-check fail path.
- Disasm contract: x0 is the unsigned numeric string, x1 is scalar base, and x2 is the writable
  `u8 *` result slot. The success path validates unsigned 8-bit range with `cmp x8, #0xff`/`b.ls`
  and writes exactly 1 byte through x2 using `strb`.
- Source signature: `include/linux/kernel.h:400`, `int __must_check kstrtou8(const char *s, unsigned int base, u8 *res)`
- Source pointer contract: x0 is an owned NUL-terminated unsigned numeric string; x2 is an owned
  writable `u8 *` output slot; x1 is scalar base.
- Call-safety tier: `SAFE-WITH-VALID-PTR`
- Required valid pointer args: x0 = `numeric-string-buffer`, x2 = `u8-result-output-slot`

Owned-input orchestration:

- `__kmalloc`: `0xffffff800826ae34`, `export-recovery`, direct BL xrefs `1765`
- `kfree`: `0xffffff800826b354`, `export-recovery`, direct BL xrefs `10596`
- `__kmalloc` passed the no-pre-call-x0-deref guard.
- `kstrtou8` was called only after the tool allocated, initialized, and verified both owned buffers.

The target was not called with a host-supplied numeric pointer. The proof used one owned unsigned
numeric string buffer and one owned writable unsigned-8 result slot.

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
- One standalone post-flash selftest command hit transient serial framing noise before an END marker;
  sequential retry confirmed `pass=11 warn=1 fail=0`.
- REPL selftest: `a90-repl-v2a1-selftest-pass`.

The v1-repl image intentionally keeps the v2321 native-init identity string, so `version` alone does
not distinguish it from the clean rollback image. The REPL selftest is the functional proof that the
candidate kernel REPL path is resident.

## Live Proof

Command:

```sh
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 \
  workspace/public/src/scripts/revalidation/a90_repl.py call-proof kstrtou8 \
  --map workspace/private/runs/kernel/v2c-c2b-kallsyms-padding-fix/System.map \
  --image workspace/private/inputs/boot_images/boot_linux_tier2_repl_v1_repl.img \
  --source-root workspace/private/inputs/kernel_source/SM-A908N_KOR_12_Opensource/Kernel \
  --evidence-dir workspace/private/runs/kernel/live-call-proof-kstrtou8-20260630/proof
```

Public result:

```json
{
  "decision": "a90-repl-live-call-proof-kstrtou8-pass",
  "ok": true,
  "input_ascii": "213",
  "base": 10,
  "expected_return": 0,
  "observed_return": 0,
  "expected_result": 213,
  "observed_result": 213,
  "expected_result_raw_hex": "0xd5",
  "observed_result_raw_hex": "0xd5",
  "input_unchanged_after_call": true,
  "result_slot_canary_preserved": true,
  "proof_status": "trusted-under-owned-input-contract",
  "raw_runtime_values_redacted": true,
  "owned_pointer_redacted": true,
  "observed_bytes_redacted": true
}
```

Checks:

- `static-c1-identity`: OK, `kstrtou8` resolved by `export-recovery`.
- `static-source-contract`: OK, signature `int __must_check kstrtou8(const char *s, unsigned int base, u8 *res)`.
- `static-call-safety-contract`: OK, tier `SAFE-WITH-VALID-PTR`, x0/x2 require verified owned buffers.
- `kmalloc-owned-kstrtou8-buffers`: OK, allocated distinct owned input and result-slot buffers.
- `owned-kstrtou8-buffer-poke-peek`: OK, input bytes and result-slot bytes were written and read back.
- `kstrtou8-return-contract`: OK, `kstrtou8("213", 10, &res) == 0`.
- `kstrtou8-result-contract`: OK, result slot stored unsigned `213` with raw `0xd5`.
- `kstrtou8-input-immutability`: OK, input stayed unchanged.
- `kstrtou8-result-slot-canary`: OK, the bytes after the 8-bit result stayed unchanged.
- `kfree-owned-kstrtou8-buffers`: OK, both owned buffers were freed.

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
- One standalone final combined health read hit transient serial framing noise before a valid END
  marker; sequential retry confirmed resident `v2321-usb-clean-identity-rodata`.
- Final selftest confirmed `pass=11 warn=1 fail=0`.

## Conclusion

`kstrtou8` is now live-proven under an owned NUL-terminated unsigned numeric string plus scalar base
plus owned writable `u8 *` result output slot contract. The proof confirms the intended helper was
reached, returned the expected success code, wrote the expected unsigned 8-bit parsed value and raw
representation into the owned result slot, preserved the input and 1-byte result-slot canary, cleaned
up both allocations, and left the device healthy. This does not authorize arbitrary pointers, user
pointers, unterminated strings, invalid bases, overflow cases, NULL result slots, failure paths, stale
buffers, arbitrary parser state, or mass calling. The device was rolled back to clean v2321 with final
`selftest fail=0`.
