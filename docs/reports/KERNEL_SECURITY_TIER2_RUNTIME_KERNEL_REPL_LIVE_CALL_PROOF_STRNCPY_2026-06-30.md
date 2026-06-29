# Kernel Security Tier-2 Runtime Kernel REPL - Live Call Proof: strncpy

- Date: 2026-06-30
- Decision: `a90-repl-live-call-proof-strncpy-pass`
- Scope: separately gated one-target live-call proof after the REPL epic close.
- Device action: yes, boot partition only through `native_init_flash.py`.
- Candidate image: `workspace/private/inputs/boot_images/boot_linux_tier2_repl_v1_repl.img`
- Candidate SHA256: `b846ae9f74d8ceb922bbcd854d78b6795ef833d61e38465d3cc474cb6f0dfb65`
- Rollback image: `workspace/private/inputs/boot_images/boot_linux_v2321_usb_clean_identity_rodata.img`
- Rollback SHA256: `ca978551aabe4b39563abaf529ccf2522054952d8b2ad852e632d26da88168cb`
- Private evidence: `workspace/private/runs/kernel/live-call-proof-strncpy-20260630/proof/a90_repl_evidence.json`

## Static Gate

Target:

- `strncpy`: `0xffffff80099b96f4`
- Resolution method: `export-recovery`
- Direct BL xrefs: `187`
- Shape: JOPP entry true; leaf/no-BL; RET observed at offset `0x24`.
- Source signature: `include/linux/string.h:25`, `extern char * strncpy(char *,const char *, __kernel_size_t)`
- Source pointer contract: x0 is destination buffer, x1 is source string buffer, x2 is scalar count.
- Call-safety tier: `SAFE-WITH-VALID-PTR`
- Required valid pointer args: x0 = `destination-buffer`, x1 = `source-string-buffer`

This proof owns both buffers and fixes `count=32`, which is inside the allocated destination. It does
not authorize arbitrary destination/source pointers, arbitrary counts, or other string/memory helpers.

Owned-input orchestration:

- `__kmalloc`: `0xffffff800826ae34`, `export-recovery`, direct BL xrefs `1765`
- `kfree`: `0xffffff800826b354`, `export-recovery`, direct BL xrefs `10596`
- `__kmalloc` passed the no-pre-call-x0-deref guard.

The target was not called with host-supplied numeric pointers. The tool allocated distinct owned
destination and source buffers, filled the destination scan window with a canary, zero-filled the
source window, wrote `A90STRNCPY\0`, verified the source by peek, called
`strncpy(dst, src, 32)`, verified the return pointer matched the owned destination pointer, verified
the destination prefix, verified NUL padding through the bounded count, verified the post-count canary,
then freed both buffers.

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
  --evidence-dir workspace/private/runs/kernel/live-call-proof-strncpy-20260630/proof \
  strncpy
```

Public result:

```json
{
  "decision": "a90-repl-live-call-proof-strncpy-pass",
  "ok": true,
  "proof_string": "A90STRNCPY",
  "count_arg": 32,
  "expected_return_value": "owned-destination-pointer-redacted",
  "observed_return_value": "owned-destination-pointer-redacted",
  "return_matches_destination": true,
  "proof_status": "trusted-under-owned-input-contract",
  "raw_runtime_values_redacted": true,
  "owned_pointer_redacted": true
}
```

Checks:

- `static-c1-identity`: OK, `strncpy` resolved by `export-recovery`.
- `static-source-contract`: OK, signature `extern char * strncpy(char *,const char *, __kernel_size_t)`.
- `static-call-safety-contract`: OK, tier `SAFE-WITH-VALID-PTR`, x0/x1 require verified buffers,
  bounded count `32`.
- `kmalloc-owned-strncpy-buffers`: OK, allocated distinct owned destination and source buffers.
- `owned-strncpy-source-poke-peek`: OK, `A90STRNCPY\0` was written and read back.
- `strncpy-return-contract`: OK, returned the owned destination pointer. The pointer value is redacted
  from public output.
- `strncpy-destination-contract`: OK, destination prefix matched the source string, bytes through count
  were NUL padded, and the canary after the count boundary remained intact.
- `kfree-owned-strncpy-buffers`: OK, destination and source cleanup both succeeded.

Raw runtime slide, `strncpy` runtime address, owned allocation pointers, return pointer, and raw
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

`strncpy` is now live-proven under the owned destination buffer plus owned NUL-terminated source
buffer plus bounded-count contract. The proof confirms the intended helper was reached, returned the
expected owned destination pointer, copied `A90STRNCPY`, NUL padded up to count `32`, preserved the
post-count canary, and left the device healthy after cleanup. This does not authorize arbitrary
string pointers, arbitrary counts, or other string/memory copy helpers. The device was rolled back to
clean v2321 with final `selftest fail=0`.
