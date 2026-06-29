# Kernel Security Tier-2 Runtime Kernel REPL - Live Call Proof: memset

- Date: 2026-06-30
- Decision: `a90-repl-live-call-proof-memset-pass`
- Scope: separately gated one-target live-call proof after the REPL epic close.
- Device action: yes, boot partition only through `native_init_flash.py`.
- Candidate image: `workspace/private/inputs/boot_images/boot_linux_tier2_repl_v1_repl.img`
- Candidate SHA256: `b846ae9f74d8ceb922bbcd854d78b6795ef833d61e38465d3cc474cb6f0dfb65`
- Rollback image: `workspace/private/inputs/boot_images/boot_linux_v2321_usb_clean_identity_rodata.img`
- Rollback SHA256: `ca978551aabe4b39563abaf529ccf2522054952d8b2ad852e632d26da88168cb`
- Private evidence: `workspace/private/runs/kernel/live-call-proof-memset-20260630/proof/a90_repl_evidence.json`

## Static Gate

Target:

- `memset`: `0xffffff80099a8980`
- Resolution method: `leaf-map-disasm+xref`
- Direct BL xrefs: `6517`
- Shape: non-JOPP arm64 leaf helper; no BL in scan; RET observed at offset `0x3c`.
- Source signature: `include/linux/string.h:101`, `extern void * memset(void *,int,__kernel_size_t)`
- Source pointer contract: x0 is the destination buffer, x1 is the scalar fill byte, x2 is the scalar
  size.
- Call-safety tier: `SAFE-WITH-VALID-PTR`
- Required valid pointer args: x0 = `destination-buffer`

`memset` is an arm64 leaf routine without the JOPP marker used by most C functions in this image.
The C1 exception is intentionally narrow: it accepts only the `memset` System.map label when the body
is leaf/no-BL, has a RET in scan, has no zero-return-before-ret pattern, and has at least 5000 direct
BL xrefs. The observed xref count was `6517`.

This proof owns the destination buffer and fixes the call to `memset(dst, 0x5a, 32)`, with the size
inside the allocated object and a canary immediately after the bounded write region. It does not
authorize arbitrary pointers, unbounded sizes, user pointers, or other memory write helpers.

Owned-input orchestration:

- `__kmalloc`: `0xffffff800826ae34`, `export-recovery`, direct BL xrefs `1765`
- `kfree`: `0xffffff800826b354`, `export-recovery`, direct BL xrefs `10596`
- `__kmalloc` passed the no-pre-call-x0-deref guard.

The target was not called with a host-supplied numeric pointer. The tool allocated one owned
destination buffer, filled the scan window with `0x11` bytes plus canary, verified by peek, called
`memset(dst, 0x5a, 32)`, checked that the return pointer matched the destination, verified the first
32 bytes changed to `0x5a`, verified the canary was unchanged, then freed the buffer.

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
  --evidence-dir workspace/private/runs/kernel/live-call-proof-memset-20260630/proof \
  memset
```

Public result:

```json
{
  "decision": "a90-repl-live-call-proof-memset-pass",
  "ok": true,
  "size_arg": 32,
  "fill_byte": "0x5a",
  "initial_byte": "0x11",
  "return_matches_destination": true,
  "filled_size": 32,
  "post_size_canary_preserved": true,
  "proof_status": "trusted-under-owned-input-contract",
  "raw_runtime_values_redacted": true,
  "owned_pointer_redacted": true,
  "observed_bytes_redacted": true
}
```

Checks:

- `static-c1-identity`: OK, `memset` resolved by `leaf-map-disasm+xref`.
- `static-source-contract`: OK, signature `extern void * memset(void *,int,__kernel_size_t)`.
- `static-call-safety-contract`: OK, tier `SAFE-WITH-VALID-PTR`, x0 requires verified destination
  buffer, bounded size `32`.
- `kmalloc-owned-memset-destination-buffer`: OK, allocated owned kernel destination buffer.
- `owned-memset-destination-poke-peek`: OK, initial bytes plus canary were written and read back.
- `memset-return-contract`: OK, return pointer matched the owned destination pointer.
- `memset-fill-and-canary-contract`: OK, first 32 bytes became `0x5a` and post-size canary was
  preserved.
- `kfree-owned-memset-destination-buffer`: OK, cleanup succeeded.

Raw runtime slide, `memset` runtime address, owned allocation pointer, return pointer, and raw observed
bytes were written only to private evidence and are not included in this report.

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

## Note On Serial Noise

During candidate and final health checks, two direct `a90ctl selftest` attempts hit serial-input echo
noise and failed to parse an `A90P1 END` marker. The commands were retried after a successful `version`
probe using slow input mode, and both bounded retries returned clean `selftest fail=0`. This was a
transport capture/input issue, not a device health regression.

## Conclusion

`memset` is now live-proven under the owned destination plus scalar-fill-byte and bounded-size
contract. The proof confirms the intended helper was reached, returned the owned destination pointer,
wrote the expected bytes inside the bounded region, preserved the post-size canary, and left the device
healthy after cleanup. This does not authorize arbitrary pointers, unbounded sizes, user pointers, or
other memory write helpers. The device was rolled back to clean v2321 with final `selftest fail=0`.
