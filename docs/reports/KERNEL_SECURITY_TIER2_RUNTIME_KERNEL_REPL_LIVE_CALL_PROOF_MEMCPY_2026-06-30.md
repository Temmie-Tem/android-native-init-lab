# Kernel Security Tier-2 Runtime Kernel REPL - Live Call Proof: memcpy

- Date: 2026-06-30
- Decision: `a90-repl-live-call-proof-memcpy-pass`
- Scope: separately gated one-target live-call proof after the REPL epic close.
- Device action: yes, boot partition only through `native_init_flash.py`.
- Candidate image: `workspace/private/inputs/boot_images/boot_linux_tier2_repl_v1_repl.img`
- Candidate SHA256: `b846ae9f74d8ceb922bbcd854d78b6795ef833d61e38465d3cc474cb6f0dfb65`
- Rollback image: `workspace/private/inputs/boot_images/boot_linux_v2321_usb_clean_identity_rodata.img`
- Rollback SHA256: `ca978551aabe4b39563abaf529ccf2522054952d8b2ad852e632d26da88168cb`
- Private evidence: `workspace/private/runs/kernel/live-call-proof-memcpy-20260630/proof/a90_repl_evidence.json`

## Static Gate

Target:

- `memcpy`: `0xffffff80099a8680`
- Resolution method: `leaf-map-disasm+xref`
- Direct BL xrefs: `6227`
- Shape: non-JOPP arm64 leaf helper; no BL in scan; RET observed at offset `0x150` with a function-size scan of `384` bytes.
- Source signature: `include/linux/string.h:134`, `extern void * memcpy(void *,const void *,__kernel_size_t)`
- Source pointer contract: x0 is destination buffer, x1 is source buffer, x2 is scalar bounded size.
- Call-safety tier: `SAFE-WITH-VALID-PTR`
- Required valid pointer args: x0 = `destination-buffer`, x1 = `source-buffer`

`memcpy` is an arm64 leaf routine without the JOPP marker used by most C functions in this image.
The C1 exception is intentionally narrow: it accepts only the `memcpy` System.map label when the body
is leaf/no-BL, has a RET in a bounded function-size scan, has no zero-return-before-ret pattern, and
has at least 5000 direct BL xrefs. The observed xref count was `6227`.

This proof owns both the destination and source buffers, requires distinct non-overlapping allocation
ranges, and fixes `size=30`, which is inside both buffers. It does not authorize arbitrary pointers,
overlapping ranges, unbounded sizes, user pointers, or `memmove`.

Owned-input orchestration:

- `__kmalloc`: `0xffffff800826ae34`, `export-recovery`, direct BL xrefs `1765`
- `kfree`: `0xffffff800826b354`, `export-recovery`, direct BL xrefs `10596`
- `__kmalloc` passed the no-pre-call-x0-deref guard.

The target was not called with host-supplied numeric pointers. The tool allocated distinct owned
destination and source buffers. The source contained `A90MEMCPY-SRC-0123456789ABCDEF` followed by a
source canary. The destination was initialized with `0x11` bytes followed by a destination canary. The
proof required `memcpy(dst, src, 30)` to return the owned destination pointer, copy exactly the first
30 source bytes into the destination, preserve the destination post-size canary, leave the source
buffer unchanged, then free both buffers.

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
  --evidence-dir workspace/private/runs/kernel/live-call-proof-memcpy-20260630/proof \
  memcpy
```

Public result:

```json
{
  "decision": "a90-repl-live-call-proof-memcpy-pass",
  "ok": true,
  "proof_bytes_label": "A90MEMCPY-SRC-0123456789ABCDEF",
  "size_arg": 30,
  "initial_destination_byte": "0x11",
  "expected_return_value": "owned-destination-pointer-redacted",
  "observed_return_value": "owned-destination-pointer-redacted",
  "return_matches_destination": true,
  "destination_prefix_matches_source": true,
  "destination_post_size_canary_preserved": true,
  "source_buffer_unchanged": true,
  "proof_status": "trusted-under-owned-input-contract",
  "raw_runtime_values_redacted": true,
  "owned_pointer_redacted": true,
  "observed_bytes_redacted": true
}
```

Checks:

- `static-c1-identity`: OK, `memcpy` resolved by `leaf-map-disasm+xref`.
- `static-source-contract`: OK, signature `extern void * memcpy(void *,const void *,__kernel_size_t)`.
- `static-call-safety-contract`: OK, tier `SAFE-WITH-VALID-PTR`, x0/x1 require verified buffers,
  bounded size `30`.
- `kmalloc-owned-memcpy-buffers`: OK, allocated distinct owned destination and source buffers with
  non-overlapping allocation ranges.
- `owned-memcpy-buffer-poke-peek`: OK, destination/source plus canaries were written and read back.
- `memcpy-return-contract`: OK, returned the owned destination pointer.
- `memcpy-copy-canary-and-source-immutability`: OK, destination first `30` bytes matched source,
  destination post-size canary was preserved, and the source buffer stayed unchanged.
- `kfree-owned-memcpy-buffers`: OK, destination and source cleanup both succeeded.

Raw runtime slide, `memcpy` runtime address, owned allocation pointers, and raw observed bytes were
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

A final independent `version && selftest` attempt first hit a transient serial framing/echo capture
issue with no END marker; the bridge remained reachable. Retrying the commands separately succeeded
and confirmed v2321 plus `selftest fail=0`.

## Conclusion

`memcpy` is now live-proven under the distinct-owned-destination/source-buffer plus scalar bounded-size
contract. The proof confirms the intended helper was reached, copied exactly the bounded source bytes
into the owned destination, returned the destination pointer, preserved the destination post-size
canary, left the source buffer unchanged, and left the device healthy after cleanup. This does not
authorize arbitrary pointers, overlapping ranges, unbounded sizes, user pointers, or `memmove`. The
device was rolled back to clean v2321 with final `selftest fail=0`.
