# Kernel Security Tier-2 Runtime Kernel REPL - Live Call Proof: hex2bin

- Date: 2026-06-30
- Decision: `a90-repl-live-call-proof-hex2bin-pass`
- Scope: separately gated one-target live-call proof after the REPL epic close.
- Device action: yes, boot partition only through `native_init_flash.py`.
- Candidate image: `workspace/private/inputs/boot_images/boot_linux_tier2_repl_v1_repl.img`
- Candidate SHA256: `b846ae9f74d8ceb922bbcd854d78b6795ef833d61e38465d3cc474cb6f0dfb65`
- Rollback image: `workspace/private/inputs/boot_images/boot_linux_v2321_usb_clean_identity_rodata.img`
- Rollback SHA256: `ca978551aabe4b39563abaf529ccf2522054952d8b2ad852e632d26da88168cb`
- Private evidence: `workspace/private/runs/kernel/live-call-proof-hex2bin-20260630/proof/a90_repl_evidence.json`

## Static Gate

Target:

- `hex2bin`: `0xffffff800856aa3c`
- Resolution method: `export-recovery`
- Direct BL xrefs: `15`
- Shape: JOPP entry, leaf/no-BL, RET observed at offset `0xb0`.
- Disasm contract: x0 is the destination byte buffer, x1 is the ASCII hex source buffer, and x2 is the byte count. The function reads two source bytes per output byte, stores one decoded byte per iteration, returns `0` on success, and returns 32-bit `-EINVAL` on invalid hex input.
- Source signature: `include/linux/kernel.h:586`, `extern int __must_check hex2bin(u8 *dst, const char *src, size_t count)`
- Source pointer contract: x0 is an owned destination byte buffer; x1 is an owned ASCII hex source buffer; x2 is a scalar byte count staying inside both buffers.
- Call-safety tier: `SAFE-WITH-VALID-PTR`
- Required valid pointer args: x0 = `destination-buffer`, x1 = `source-hex-buffer`

Owned-input orchestration:

- `__kmalloc`: `0xffffff800826ae34`, `export-recovery`, direct BL xrefs `1765`
- `kfree`: `0xffffff800826b354`, `export-recovery`, direct BL xrefs `10596`
- `__kmalloc` passed the no-pre-call-x0-deref guard.
- `hex2bin` was called only after the tool allocated, initialized, and verified both owned buffers.

The target was not called with a host-supplied numeric pointer. The proof used one owned destination
buffer and one owned source buffer, wrote a fixed even-length ASCII hex string, decoded exactly seven
output bytes, and verified the destination canary plus source buffer stayed unchanged.

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
- Candidate native selftest: `pass=11 warn=1 fail=0`.
- `a90_repl.py selftest`: `a90-repl-v2a1-selftest-pass`.

The v1-repl image intentionally keeps the v2321 native-init identity string, so `version` alone does
not distinguish it from the clean rollback image. The REPL selftest is the functional proof that the
candidate kernel REPL path is resident.

## Live Proof

Command:

```sh
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 \
  workspace/public/src/scripts/revalidation/a90_repl.py call-proof hex2bin \
  --map workspace/private/runs/kernel/v2c-c2b-kallsyms-padding-fix/System.map \
  --image workspace/private/inputs/boot_images/boot_linux_tier2_repl_v1_repl.img \
  --source-root workspace/private/inputs/kernel_source/SM-A908N_KOR_12_Opensource/Kernel \
  --evidence-dir workspace/private/runs/kernel/live-call-proof-hex2bin-20260630/proof
```

Public result:

```json
{
  "decision": "a90-repl-live-call-proof-hex2bin-pass",
  "ok": true,
  "source_ascii": "A90f00dC0ffEe1",
  "count": 7,
  "expected_output_hex": "a90f00dc0ffee1",
  "observed_output_hex": "a90f00dc0ffee1",
  "observed_return_value": "0x0",
  "destination_canary_preserved": true,
  "source_unchanged_after_call": true,
  "proof_status": "trusted-under-owned-input-contract",
  "raw_runtime_values_redacted": true,
  "owned_pointer_redacted": true,
  "observed_bytes_redacted": true
}
```

Checks:

- `static-c1-identity`: OK, `hex2bin` resolved by `export-recovery`.
- `static-source-contract`: OK, signature `extern int __must_check hex2bin(u8 *dst, const char *src, size_t count)`.
- `static-call-safety-contract`: OK, tier `SAFE-WITH-VALID-PTR`, x0/x1 require verified owned buffers.
- `kmalloc-owned-hex2bin-buffers`: OK, allocated distinct owned destination and source buffers.
- `owned-hex2bin-buffer-poke-peek`: OK, destination initial bytes/canary and source bytes/canary were written and read back.
- `hex2bin-return-contract`: OK, returned `0x0` for the valid source.
- `hex2bin-destination-decode-contract`: OK, destination bytes matched `a90f00dc0ffee1` and the destination canary stayed intact.
- `hex2bin-source-immutability`: OK, source bytes and source canary stayed unchanged.
- `kfree-owned-hex2bin-buffers`: OK, both owned buffers were freed.

Raw runtime slide, `hex2bin` runtime address, owned destination/source pointers, and raw observed
buffer bytes were written only to private evidence and are not included in this report.

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
- Final `selftest`: `pass=11 warn=1 fail=0`.

One final health read hit host-side serial capture noise without an END marker; a separate sequential
`version` retry and final `selftest` both passed.

## Conclusion

`hex2bin` is now live-proven under an owned destination byte buffer plus owned ASCII hex source buffer
plus scalar byte count contract. The proof confirms the intended helper was reached, returned success,
decoded the expected bytes, preserved the destination canary, left the source buffer unchanged, cleaned
up both allocations, and left the device healthy. This does not authorize arbitrary pointers, user
pointers, odd-length or invalid hex input, unbounded counts, stale buffers, arbitrary output aliases,
or mass calling. The device was rolled back to clean v2321 with final `selftest fail=0`.
