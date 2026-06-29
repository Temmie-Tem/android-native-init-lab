# Kernel Security Tier-2 Runtime Kernel REPL - Live Call Proof: ksize

- Date: 2026-06-29
- Decision: `a90-repl-live-call-proof-ksize-pass`
- Scope: separately gated one-target live-call proof after the REPL epic close.
- Device action: yes, boot partition only through `native_init_flash.py`.
- Candidate image: `workspace/private/inputs/boot_images/boot_linux_tier2_repl_v1_repl.img`
- Candidate SHA256: `b846ae9f74d8ceb922bbcd854d78b6795ef833d61e38465d3cc474cb6f0dfb65`
- Rollback image: `workspace/private/inputs/boot_images/boot_linux_v2321_usb_clean_identity_rodata.img`
- Rollback SHA256: `ca978551aabe4b39563abaf529ccf2522054952d8b2ad852e632d26da88168cb`
- Private evidence: `workspace/private/runs/kernel/live-call-proof-ksize-20260629/proof/a90_repl_evidence.json`

## Static Gate

Target:

- `ksize`: `0xffffff800826b27c`
- Resolution method: `export-recovery`
- Direct BL xrefs: `39`
- Source signature: `include/linux/slab.h:153`, `size_t ksize(const void *)`
- Source pointer contract: x0 is the object pointer.
- Call-safety tier: `SAFE-WITH-VALID-PTR`
- Required valid pointer arg: x0 = `kmalloc-object`

Owned-input orchestration:

- `__kmalloc`: `0xffffff800826ae34`, `export-recovery`, direct BL xrefs `1765`
- `kfree`: `0xffffff800826b354`, `export-recovery`, direct BL xrefs `10596`
- `__kmalloc` passed the no-pre-call-x0-deref guard.

The target was not called with a host-supplied numeric pointer. The tool allocated an owned kernel
object first, passed that object to `ksize`, then freed it.

## Flash And Health

Preconditions:

- v1-repl candidate SHA matched `b846ae9f74d8ceb922bbcd854d78b6795ef833d61e38465d3cc474cb6f0dfb65`.
- v2321 rollback SHA matched `ca978551aabe4b39563abaf529ccf2522054952d8b2ad852e632d26da88168cb`.
- v2237 fallback SHA matched `b2ea2d26d160b7702ce7d4438b84367788eea26c6a5bbe4ed93f3d270292ac7f`.
- Final fallback `boot_linux_v48.img` existed with SHA
  `1c87fa59712395027c5c2e489b15c4f6ddefabc3c50f78d3c235c4508a63e042`.
- TWRP recovery image existed with SHA
  `b1ef377a52ec8ab43b49a5fcc7a0b27e8efff91bf2d8cccdc565ecadadcc646c`.
- Bridge was connected to `/dev/ttyACM0`.
- Baseline before flash: `v2321`, `status` OK, `selftest pass=11 warn=1 fail=0`.

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
- Post-flash `selftest verbose`: `pass=11 warn=1 fail=0`.
- `a90_repl.py selftest`: `a90-repl-v2a1-selftest-pass`.

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
  --evidence-dir workspace/private/runs/kernel/live-call-proof-ksize-20260629/proof \
  ksize
```

Public result:

```json
{
  "decision": "a90-repl-live-call-proof-ksize-pass",
  "ok": true,
  "observed_return_value": "0x1000",
  "proof_status": "trusted-under-owned-input-contract",
  "raw_runtime_values_redacted": true,
  "owned_pointer_redacted": true
}
```

Checks:

- `static-c1-identity`: OK, `ksize` resolved by `export-recovery`.
- `static-source-contract`: OK, signature `size_t ksize(const void *)`, pointer arg `[0]`.
- `static-call-safety-contract`: OK, tier `SAFE-WITH-VALID-PTR`, x0 requires `kmalloc-object`.
- `kmalloc-owned-buffer`: OK, allocated `0x1000` bytes and returned sane kernel lowmem.
- `ksize-return-contract`: OK, returned `0x1000`, expected `[0x1000, 0x2000]`.
- `kfree-owned-buffer`: OK, cleanup was attempted and succeeded.

Raw runtime slide, target runtime address, and allocation pointer were written only to private
evidence and are not included in this report.

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
- Final `selftest verbose`: `pass=11 warn=1 fail=0`.

One immediate final selftest attempt hit serial input fragmentation (`selftestvrbose` and missing
`A90P1 END`), then `version` realigned the bridge and a slow-input selftest retry passed. This was a
transport artifact, not a device health regression.

## Conclusion

`ksize` is now live-proven under the owned `__kmalloc` pointer contract. The function map can treat
`ksize` as trusted only for this bounded input pattern: allocate internally, call `ksize(ptr)`, verify
the size return contract, and free the owned object. The device was rolled back to clean v2321 with
final `selftest fail=0`.
