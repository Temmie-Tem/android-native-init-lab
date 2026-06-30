# Kernel Security Tier-2 Runtime Kernel REPL - Live Call Proof: kstrtouint

- Date: 2026-06-30
- Decision: `a90-repl-live-call-proof-kstrtouint-pass`
- Scope: separately gated one-target live-call proof after the REPL epic close.
- Device action: yes, boot partition only through `native_init_flash.py`.
- Candidate image: `workspace/private/inputs/boot_images/boot_linux_tier2_repl_v1_repl.img`
- Candidate SHA256: `b846ae9f74d8ceb922bbcd854d78b6795ef833d61e38465d3cc474cb6f0dfb65`
- Rollback image: `workspace/private/inputs/boot_images/boot_linux_v2321_usb_clean_identity_rodata.img`
- Rollback SHA256: `ca978551aabe4b39563abaf529ccf2522054952d8b2ad852e632d26da88168cb`
- Private evidence: `workspace/private/runs/kernel/live-call-proof-kstrtouint-20260630/proof/a90_repl_evidence.json`

## Static Gate

Target:

- `kstrtouint`: `0xffffff800856b7a4`
- Resolution method: `export-recovery`
- Direct BL xrefs: `217`
- Shape: JOPP entry, non-leaf helper calling `kstrtoull` plus the stack-check fail path.
- Disasm contract: x0 is the numeric string, x1 is scalar base, and x2 is the writable `unsigned int *` result slot. On the success path, the helper writes a 32-bit value through x2.
- Source signature: `include/linux/kernel.h:375`, `int __must_check kstrtouint(const char *s, unsigned int base, unsigned int *res)`
- Source pointer contract: x0 is an owned NUL-terminated numeric string; x2 is an owned writable `unsigned int *` output slot; x1 is scalar base.
- Call-safety tier: `SAFE-WITH-VALID-PTR`
- Required valid pointer args: x0 = `numeric-string-buffer`, x2 = `uint-result-output-slot`

Owned-input orchestration:

- `__kmalloc`: `0xffffff800826ae34`, `export-recovery`, direct BL xrefs `1765`
- `kfree`: `0xffffff800826b354`, `export-recovery`, direct BL xrefs `10596`
- `__kmalloc` passed the no-pre-call-x0-deref guard.
- `kstrtouint` was called only after the tool allocated, initialized, and verified both owned buffers.

The target was not called with a host-supplied numeric pointer. The proof used one owned numeric
string buffer and one owned writable unsigned-int result slot.

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
- Post-flash native selftest: `pass=11 warn=1 fail=0`.
- REPL selftest: `a90-repl-v2a1-selftest-pass`.

The v1-repl image intentionally keeps the v2321 native-init identity string, so `version` alone does
not distinguish it from the clean rollback image. The REPL selftest is the functional proof that the
candidate kernel REPL path is resident.

## Live Proof

Command:

```sh
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 \
  workspace/public/src/scripts/revalidation/a90_repl.py call-proof kstrtouint \
  --map workspace/private/runs/kernel/v2c-c2b-kallsyms-padding-fix/System.map \
  --image workspace/private/inputs/boot_images/boot_linux_tier2_repl_v1_repl.img \
  --source-root workspace/private/inputs/kernel_source/SM-A908N_KOR_12_Opensource/Kernel \
  --evidence-dir workspace/private/runs/kernel/live-call-proof-kstrtouint-20260630/proof
```

Public result:

```json
{
  "decision": "a90-repl-live-call-proof-kstrtouint-pass",
  "ok": true,
  "input_ascii": "123456789",
  "base": 10,
  "expected_return": 0,
  "observed_return": 0,
  "expected_result": 123456789,
  "observed_result": 123456789,
  "expected_result_hex": "0x75bcd15",
  "observed_result_hex": "0x75bcd15",
  "input_unchanged_after_call": true,
  "result_slot_canary_preserved": true,
  "proof_status": "trusted-under-owned-input-contract",
  "raw_runtime_values_redacted": true,
  "owned_pointer_redacted": true,
  "observed_bytes_redacted": true
}
```

Checks:

- `static-c1-identity`: OK, `kstrtouint` resolved by `export-recovery`.
- `static-source-contract`: OK, signature `int __must_check kstrtouint(const char *s, unsigned int base, unsigned int *res)`.
- `static-call-safety-contract`: OK, tier `SAFE-WITH-VALID-PTR`, x0/x2 require verified owned buffers.
- `kmalloc-owned-kstrtouint-buffers`: OK, allocated distinct owned input and result-slot buffers.
- `owned-kstrtouint-buffer-poke-peek`: OK, input bytes and result-slot bytes were written and read back.
- `kstrtouint-return-contract`: OK, `kstrtouint("123456789", 10, &res) == 0`.
- `kstrtouint-result-contract`: OK, result slot stored `123456789`.
- `kstrtouint-input-immutability`: OK, input stayed unchanged.
- `kstrtouint-result-slot-canary`: OK, the bytes after the 32-bit result stayed unchanged.
- `kfree-owned-kstrtouint-buffers`: OK, both owned buffers were freed.

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
- Sequential final `version` confirmed resident `v2321-usb-clean-identity-rodata`.
- One final standalone selftest read hit transient serial framing noise after END status `ok`; sequential retry confirmed `pass=11 warn=1 fail=0`.

## Conclusion

`kstrtouint` is now live-proven under an owned NUL-terminated numeric string plus scalar base plus
owned writable `unsigned int *` result output slot contract. The proof confirms the intended helper
was reached, returned the expected success code, wrote the expected parsed value into the owned result
slot, preserved the input and result-slot canary, cleaned up both allocations, and left the device
healthy. This does not authorize arbitrary pointers, user pointers, unterminated strings, invalid
bases, overflow cases, NULL result slots, failure paths, stale buffers, arbitrary parser state, or
mass calling. The device was rolled back to clean v2321 with final `selftest fail=0`.
