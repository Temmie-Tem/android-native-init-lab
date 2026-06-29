# Kernel Security Tier-2 Runtime Kernel REPL - Live Call Proof: memcmp

- Date: 2026-06-30
- Decision: `a90-repl-live-call-proof-memcmp-pass`
- Scope: separately gated one-target live-call proof after the REPL epic close.
- Device action: yes, boot partition only through `native_init_flash.py`.
- Candidate image: `workspace/private/inputs/boot_images/boot_linux_tier2_repl_v1_repl.img`
- Candidate SHA256: `b846ae9f74d8ceb922bbcd854d78b6795ef833d61e38465d3cc474cb6f0dfb65`
- Rollback image: `workspace/private/inputs/boot_images/boot_linux_v2321_usb_clean_identity_rodata.img`
- Rollback SHA256: `ca978551aabe4b39563abaf529ccf2522054952d8b2ad852e632d26da88168cb`
- Private evidence: `workspace/private/runs/kernel/live-call-proof-memcmp-20260630/proof/a90_repl_evidence.json`

## Static Gate

Target:

- `memcmp`: `0xffffff80099a84b0`
- Resolution method: `leaf-map-disasm+xref`
- Direct BL xrefs: `921`
- Shape: non-JOPP arm64 leaf helper; no BL in scan; RET observed at offset `0xf4`.
- Source signature: `include/linux/string.h:143`, `extern int memcmp(const void *,const void *,__kernel_size_t)`
- Source pointer contract: x0 is left buffer, x1 is right buffer, x2 is scalar size.
- Call-safety tier: `SAFE-WITH-VALID-PTR`
- Required valid pointer args: x0 = `left-buffer`, x1 = `right-buffer`

`memcmp` is an arm64 leaf routine without the JOPP marker used by most C functions in this image.
The C1 exception is intentionally narrow: it accepts only the `memcmp` System.map label when the body
is leaf/no-BL, has a RET in scan, has no zero-return-before-ret pattern, and has at least 500 direct
BL xrefs. The observed xref count was `921`.

This proof owns both buffers and fixes `size=32`, which is inside both allocated buffers. It does not
authorize arbitrary pointers, unbounded sizes, user pointers, or other memory helpers.

Owned-input orchestration:

- `__kmalloc`: `0xffffff800826ae34`, `export-recovery`, direct BL xrefs `1765`
- `kfree`: `0xffffff800826b354`, `export-recovery`, direct BL xrefs `10596`
- `__kmalloc` passed the no-pre-call-x0-deref guard.

The target was not called with host-supplied numeric pointers. The tool allocated distinct owned left
and right buffers, filled each scan window with initialized bytes plus canary, verified by peek, called
`memcmp(left, right, 32)` for equal bytes, changed one right-buffer byte at offset `10`, called
`memcmp(left, right, 32)` again, verified return contracts and buffer immutability, then freed both
buffers.

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
  --evidence-dir workspace/private/runs/kernel/live-call-proof-memcmp-20260630/proof \
  memcmp
```

Public result:

```json
{
  "decision": "a90-repl-live-call-proof-memcmp-pass",
  "ok": true,
  "proof_bytes_label": "A90MEMCMP-PROOF-0123456789ABCDEF",
  "size_arg": 32,
  "equal_observed_return_value": "0x0",
  "mismatch_expected_return_sign": "positive",
  "mismatch_observed_return_value": "0x80",
  "mismatch_offset": 10,
  "buffers_unchanged_after_calls": true,
  "proof_status": "trusted-under-owned-input-contract",
  "raw_runtime_values_redacted": true,
  "owned_pointer_redacted": true,
  "observed_bytes_redacted": true
}
```

Checks:

- `static-c1-identity`: OK, `memcmp` resolved by `leaf-map-disasm+xref`.
- `static-source-contract`: OK, signature `extern int memcmp(const void *,const void *,__kernel_size_t)`.
- `static-call-safety-contract`: OK, tier `SAFE-WITH-VALID-PTR`, x0/x1 require verified buffers,
  bounded size `32`.
- `kmalloc-owned-memcmp-buffers`: OK, allocated distinct owned left and right buffers.
- `owned-memcmp-buffer-poke-peek`: OK, equal buffer contents were written and read back.
- `memcmp-equal-return-contract`: OK, equal compare returned `0x0`.
- `memcmp-equal-buffer-immutability`: OK, equal compare did not modify either buffer.
- `owned-memcmp-mismatch-poke-peek`: OK, right byte at offset `10` was changed from left `0x50` to
  right `0x40`.
- `memcmp-mismatch-return-contract`: OK, mismatch compare returned positive; observed `0x80`.
- `memcmp-mismatch-buffer-immutability`: OK, mismatch compare did not modify either buffer.
- `kfree-owned-memcmp-buffers`: OK, left and right cleanup both succeeded.

Raw runtime slide, `memcmp` runtime address, owned allocation pointers, and raw observed bytes were
written only to private evidence and are not included in this report.

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

`memcmp` is now live-proven under the two-owned-initialized-buffer plus bounded-size contract. The
proof confirms the intended helper was reached, returned `0` for equal bytes, returned a positive
value for a controlled first-difference case, left both buffers unchanged, and left the device healthy
after cleanup. This does not authorize arbitrary pointers, unbounded sizes, user pointers, or other
memory helpers. The device was rolled back to clean v2321 with final `selftest fail=0`.
