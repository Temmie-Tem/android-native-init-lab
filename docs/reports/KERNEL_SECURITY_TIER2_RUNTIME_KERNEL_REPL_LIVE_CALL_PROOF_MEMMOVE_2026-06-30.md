# Kernel Security Tier-2 Runtime Kernel REPL - Live Call Proof: memmove

- Date: 2026-06-30
- Decision: `a90-repl-live-call-proof-memmove-pass`
- Scope: separately gated one-target live-call proof after the REPL epic close.
- Device action: yes, boot partition only through `native_init_flash.py`.
- Candidate image: `workspace/private/inputs/boot_images/boot_linux_tier2_repl_v1_repl.img`
- Candidate SHA256: `b846ae9f74d8ceb922bbcd854d78b6795ef833d61e38465d3cc474cb6f0dfb65`
- Rollback image: `workspace/private/inputs/boot_images/boot_linux_v2321_usb_clean_identity_rodata.img`
- Rollback SHA256: `ca978551aabe4b39563abaf529ccf2522054952d8b2ad852e632d26da88168cb`
- Private evidence: `workspace/private/runs/kernel/live-call-proof-memmove-20260630/proof/a90_repl_evidence.json`

## Static Gate

Target:

- `memmove`: `0xffffff80099a8800`
- Resolution method: `leaf-map-disasm+xref`
- Direct BL xrefs: `165`
- Shape: non-JOPP arm64 leaf helper; no BL in scan; RET observed at offset `0xc4` with a function-size scan of `384` bytes.
- Source signature: `include/linux/string.h:137`, `extern void * memmove(void *,const void *,__kernel_size_t)`
- Source pointer contract: x0 is destination buffer, x1 is source buffer, x2 is scalar bounded size.
- Call-safety tier: `SAFE-WITH-VALID-PTR`
- Required valid pointer args: x0 = `destination-buffer`, x1 = `source-buffer`

`memmove` is an arm64 leaf routine without the JOPP marker used by most C functions in this image.
The C1 exception is intentionally narrow: it accepts only the `memmove` System.map label when the body
is leaf/no-BL, has a RET in a bounded function-size scan, has no zero-return-before-ret pattern, and
has at least 100 direct BL xrefs. The observed xref count was `165`.

The disassembly front branch falls back to the `memcpy` implementation only when `dst < src` or
`dst >= src + size`. This proof deliberately uses `dst = src + 5` and `size = 29`, so the selected
inputs land inside the overlap path instead of the memcpy fallback. This proof owns the allocation and
requires both ranges to remain inside that allocation. It does not authorize arbitrary pointers,
unbounded sizes, user pointers, or other overlap shapes.

Owned-input orchestration:

- `__kmalloc`: `0xffffff800826ae34`, `export-recovery`, direct BL xrefs `1765`
- `kfree`: `0xffffff800826b354`, `export-recovery`, direct BL xrefs `10596`
- `__kmalloc` passed the no-pre-call-x0-deref guard.

The target was not called with host-supplied numeric pointers. The tool allocated one owned buffer,
wrote `A90MEMMOVE-OVERLAP-0123456789`, set `src=base`, `dst=base+5`, fixed `size=29`, and placed a
post-move canary after the destination range. The proof required `memmove(dst, src, 29)` to return the
owned destination pointer and the final buffer to match snapshot-copy semantics for the overlapping
move.

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
  --evidence-dir workspace/private/runs/kernel/live-call-proof-memmove-20260630/proof \
  memmove
```

Public result:

```json
{
  "decision": "a90-repl-live-call-proof-memmove-pass",
  "ok": true,
  "proof_bytes_label": "A90MEMMOVE-OVERLAP-0123456789",
  "size_arg": 29,
  "source_offset": 0,
  "destination_offset": 5,
  "overlap_direction": "dst-after-src",
  "expected_path": "overlap-backward-copy",
  "expected_return_value": "owned-destination-pointer-redacted",
  "observed_return_value": "owned-destination-pointer-redacted",
  "return_matches_destination": true,
  "final_buffer_matches_overlap_safe_snapshot": true,
  "post_move_canary_preserved": true,
  "proof_status": "trusted-under-owned-input-contract",
  "raw_runtime_values_redacted": true,
  "owned_pointer_redacted": true,
  "observed_bytes_redacted": true
}
```

Checks:

- `static-c1-identity`: OK, `memmove` resolved by `leaf-map-disasm+xref`.
- `static-source-contract`: OK, signature `extern void * memmove(void *,const void *,__kernel_size_t)`.
- `static-call-safety-contract`: OK, tier `SAFE-WITH-VALID-PTR`, x0/x1 require verified buffers,
  bounded size `29`, overlap contract `dst=src+offset, 0<offset<size`.
- `kmalloc-owned-memmove-overlap-buffer`: OK, allocated one owned buffer.
- `memmove-overlap-range-contract`: OK, `src=base`, `dst=base+5`, `size=29`, ranges inside the
  allocation and overlapping.
- `owned-memmove-buffer-poke-peek`: OK, input bytes plus canary were written and read back.
- `memmove-return-contract`: OK, returned the owned destination pointer.
- `memmove-overlap-final-buffer-contract`: OK, final buffer matched overlap-safe snapshot-copy
  semantics and the post-move canary was preserved.
- `kfree-owned-memmove-overlap-buffer`: OK, cleanup succeeded.

Raw runtime slide, `memmove` runtime address, owned allocation pointer, and raw observed bytes were
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

One candidate selftest read and the first final `version && selftest` read hit transient serial
framing/echo capture issues with no END marker. The bridge remained reachable. Retrying the commands
separately succeeded and confirmed candidate health before proof plus final v2321 `selftest fail=0`.

## Conclusion

`memmove` is now live-proven under the same-owned-buffer overlap plus scalar bounded-size contract.
The proof confirms the intended helper was reached, used an overlapping `dst=src+5` range, returned
the destination pointer, produced the overlap-safe snapshot-copy final buffer, preserved the post-move
canary, cleaned up the owned allocation, and left the device healthy. This does not authorize
arbitrary pointers, unbounded sizes, user pointers, or other overlap shapes. The device was rolled back
to clean v2321 with final `selftest fail=0`.
