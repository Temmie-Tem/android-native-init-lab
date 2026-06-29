# Kernel Security Tier-2 Runtime Kernel REPL - Live Call Proof: strcpy

- Date: 2026-06-30
- Decision: `a90-repl-live-call-proof-strcpy-pass`
- Scope: separately gated one-target live-call proof after the REPL epic close.
- Device action: yes, boot partition only through `native_init_flash.py`.
- Candidate image: `workspace/private/inputs/boot_images/boot_linux_tier2_repl_v1_repl.img`
- Candidate SHA256: `b846ae9f74d8ceb922bbcd854d78b6795ef833d61e38465d3cc474cb6f0dfb65`
- Rollback image: `workspace/private/inputs/boot_images/boot_linux_v2321_usb_clean_identity_rodata.img`
- Rollback SHA256: `ca978551aabe4b39563abaf529ccf2522054952d8b2ad852e632d26da88168cb`
- Private evidence: `workspace/private/runs/kernel/live-call-proof-strcpy-20260630/proof/a90_repl_evidence.json`

## Static Gate

Target:

- `strcpy`: `0xffffff80099b96d4`
- Resolution method: `export-recovery`
- Direct BL xrefs: `589`
- Shape: JOPP entry, leaf/no-BL helper; RETs observed in scan.
- Source signature: `include/linux/string.h:22`, `extern char * strcpy(char *,const char *)`
- Source pointer contract: x0 is the destination buffer; x1 is the source NUL-terminated string buffer.
- Call-safety tier: `SAFE-WITH-VALID-PTR`
- Required valid pointer args: x0 = `destination-buffer`, x1 = `source-string-buffer`

Owned-input orchestration:

- `__kmalloc`: `0xffffff800826ae34`, `export-recovery`, direct BL xrefs `1765`
- `kfree`: `0xffffff800826b354`, `export-recovery`, direct BL xrefs `10596`
- `__kmalloc` passed the no-pre-call-x0-deref guard.

The target was not called with host-supplied numeric pointers. The tool allocated one owned
destination buffer and one distinct owned source string buffer containing `A90STRCPY-SRC-Q-END`.
The destination was prefilled with `0x44` through the post-NUL tail and followed by an `0xcc` canary.
The source was followed by its own canary. The live contract required `strcpy(dst, src)` to return
the owned destination pointer, copy the source including the NUL byte, preserve the destination
post-NUL tail and canary, and leave the source buffer unchanged.

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
  --timeout 90 \
  --dmesg-tail 80 \
  --safe-op-retries 2 \
  --retry-delay-sec 0.3 \
  --evidence-dir workspace/private/runs/kernel/live-call-proof-strcpy-20260630/proof \
  strcpy
```

Public result:

```json
{
  "decision": "a90-repl-live-call-proof-strcpy-pass",
  "ok": true,
  "proof_string": "A90STRCPY-SRC-Q-END",
  "return_matches_destination_pointer": true,
  "destination_matches_source": true,
  "source_unchanged_after_call": true,
  "proof_status": "trusted-under-owned-input-contract",
  "raw_runtime_values_redacted": true,
  "owned_pointer_redacted": true,
  "observed_bytes_redacted": true
}
```

Checks:

- `static-c1-identity`: OK, `strcpy` resolved by `export-recovery`.
- `static-source-contract`: OK, signature `extern char * strcpy(char *,const char *)`.
- `static-call-safety-contract`: OK, tier `SAFE-WITH-VALID-PTR`, x0/x1 require verified owned buffers.
- `kmalloc-owned-strcpy-buffers`: OK, allocated two distinct owned kernel buffers.
- `owned-strcpy-buffer-poke-peek`: OK, destination prefill, source string, and canaries were written and read back.
- `strcpy-return-contract`: OK, returned the owned destination pointer, redacted publicly.
- `strcpy-destination-contract`: OK, copied `A90STRCPY-SRC-Q-END` including NUL and preserved tail/canary.
- `strcpy-source-immutability`: OK, source buffer stayed unchanged.
- `kfree-owned-strcpy-buffers`: OK, cleanup succeeded.

Raw runtime slide, `strcpy` runtime address, owned allocation pointers, return pointer, and raw
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

## Note

Serial bridge commands must remain sequential during this live proof path. After rollback, an initial
final selftest read returned only the tail of the framed response and the following `version` command
hit serial echo noise before END marker. `--input-mode slow` re-synchronized the bridge; slow-mode
`version` and final selftest then both passed.

## Conclusion

`strcpy` is now live-proven under the owned destination buffer plus owned NUL-terminated source string
contract. The proof confirms the intended helper was reached, returned the destination pointer, copied
the source including the NUL terminator, preserved destination bytes after the terminator and the
canary, left the source unchanged, cleaned up both allocations, and left the device healthy. This does
not authorize arbitrary pointers, user pointers, undersized destinations, unterminated sources, or mass
calling. The device was rolled back to clean v2321 with final `selftest fail=0`.
