# Kernel Security Tier-2 Runtime Kernel REPL - Live Call Proof: filp_open

- Date: 2026-06-29
- Decision: `a90-repl-live-call-proof-filp_open-pass`
- Scope: separately gated one-target live-call proof after the REPL epic close.
- Device action: yes, boot partition only through `native_init_flash.py`.
- Candidate image: `workspace/private/inputs/boot_images/boot_linux_tier2_repl_v1_repl.img`
- Candidate SHA256: `b846ae9f74d8ceb922bbcd854d78b6795ef833d61e38465d3cc474cb6f0dfb65`
- Rollback image: `workspace/private/inputs/boot_images/boot_linux_v2321_usb_clean_identity_rodata.img`
- Rollback SHA256: `ca978551aabe4b39563abaf529ccf2522054952d8b2ad852e632d26da88168cb`
- Private evidence: `workspace/private/runs/kernel/live-call-proof-filp-open-20260629/proof/a90_repl_evidence.json`

## Static Gate

Target:

- `filp_open`: `0xffffff800828a664`
- Resolution method: `export-recovery`
- Direct BL xrefs: `48`
- Source signature: `include/linux/fs.h:2462`, `extern struct file * filp_open(const char *, int, umode_t)`
- Source pointer contract: x0 is the pathname pointer.
- Call-safety tier: `SAFE-WITH-VALID-PTR`
- Required valid pointer arg: x0 = `pathname`

Paired cleanup:

- `filp_close`: `0xffffff800828ac14`
- Resolution method: `export-recovery`
- Direct BL xrefs: `67`
- Source signature: `include/linux/fs.h:2466`, `extern int filp_close(struct file *, fl_owner_t id)`
- Cleanup input contract: x0 is the `struct file *` returned by this proof's `filp_open`.

Owned-input orchestration:

- `__kmalloc`: `0xffffff800826ae34`, `export-recovery`, direct BL xrefs `1765`
- `kfree`: `0xffffff800826b354`, `export-recovery`, direct BL xrefs `10596`
- `__kmalloc` passed the no-pre-call-x0-deref guard.

The target was not called with a host-supplied numeric pointer. The tool allocated an owned kernel
buffer, wrote `/init\0`, verified the first qword by `peek`, opened it read-only, closed the returned
file pointer, then freed the pathname buffer.

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
- Post-flash selftest: `pass=11 warn=1 fail=0`.
- `a90_repl.py selftest`: `a90-repl-v2a1-selftest-pass`.

One post-flash selftest/version pair hit serial input fragmentation (`cmdv1 vr` / missing END marker).
Slow input realigned the bridge. The REPL selftest and later candidate/final selftests passed.

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
  --evidence-dir workspace/private/runs/kernel/live-call-proof-filp-open-20260629/proof \
  filp_open
```

Public result:

```json
{
  "decision": "a90-repl-live-call-proof-filp_open-pass",
  "ok": true,
  "close_return_value": "0x0",
  "proof_status": "trusted-under-owned-input-contract",
  "raw_runtime_values_redacted": true,
  "owned_pointer_redacted": true
}
```

Checks:

- `static-c1-identity`: OK, `filp_open` resolved by `export-recovery`.
- `static-source-contract`: OK, signature `extern struct file * filp_open(const char *, int, umode_t)`.
- `static-call-safety-contract`: OK, tier `SAFE-WITH-VALID-PTR`, x0 requires `pathname`.
- `static-cleanup-contract`: OK, `filp_close` tier `SAFE-WITH-VALID-PTR`.
- `kmalloc-owned-pathname-buffer`: OK, allocated `0x1000` bytes and returned sane kernel lowmem.
- `owned-pathname-poke-peek`: OK, `/init` pathname was written and read back.
- `filp-open-return-contract`: OK, returned non-null, non-ERR_PTR, kernel-lowmem `struct file *`.
- `filp-close-opened-file`: OK, `filp_close(file, NULL)` returned `0`.
- `kfree-owned-pathname-buffer`: OK, cleanup was attempted and succeeded.

Raw runtime slide, `filp_open`/`filp_close` runtime addresses, pathname buffer pointer, and file
pointer were written only to private evidence and are not included in this report.

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

One immediate final selftest attempt hit serial input fragmentation and missed the `A90P1 END`
marker. `version` realigned the bridge and a slow-input selftest retry passed. This was a transport
artifact, not a device health regression.

## Conclusion

`filp_open` is now live-proven under the owned pathname contract: allocate a kernel pathname buffer,
write `/init\0`, call `filp_open(path, O_RDONLY, 0)`, require a sane `struct file *`, close it with
`filp_close(file, NULL) == 0`, and free the pathname buffer. `filp_close` receives cleanup-only
function-map evidence for the file pointer returned by this proof. The device was rolled back to
clean v2321 with final `selftest fail=0`.
