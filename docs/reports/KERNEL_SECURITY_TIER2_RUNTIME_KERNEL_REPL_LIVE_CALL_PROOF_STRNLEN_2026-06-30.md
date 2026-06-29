# Kernel Security Tier-2 Runtime Kernel REPL - Live Call Proof: strnlen

- Date: 2026-06-30
- Decision: `a90-repl-live-call-proof-strnlen-pass`
- Scope: separately gated one-target live-call proof after the REPL epic close.
- Device action: yes, boot partition only through `native_init_flash.py`.
- Candidate image: `workspace/private/inputs/boot_images/boot_linux_tier2_repl_v1_repl.img`
- Candidate SHA256: `b846ae9f74d8ceb922bbcd854d78b6795ef833d61e38465d3cc474cb6f0dfb65`
- Rollback image: `workspace/private/inputs/boot_images/boot_linux_v2321_usb_clean_identity_rodata.img`
- Rollback SHA256: `ca978551aabe4b39563abaf529ccf2522054952d8b2ad852e632d26da88168cb`
- Private evidence: `workspace/private/runs/kernel/live-call-proof-strnlen-20260630/proof/a90_repl_evidence.json`

## Static Gate

Target:

- `strnlen`: `0xffffff80099a8f4c`
- Resolution method: `leaf-map-disasm+xref`
- Direct BL xrefs: `473`
- Leaf shape: no BL in the scanned body, RET at offset `0x74`, no zero-return-before-ret pattern.
- Source signature: `include/linux/string.h:85`, `extern __kernel_size_t strnlen(const char *,__kernel_size_t)`
- Source pointer contract: x0 is the string buffer pointer; x1 is scalar maxlen.
- Call-safety tier: `SAFE-WITH-VALID-PTR`
- Required valid pointer args: x0 = `string-buffer`

`strnlen` is a non-JOPP arm64 leaf helper, so it does not use the export/JOPP C1 path. The verifier
accepts only the explicit `strnlen` leaf-map ground-truth row when the map address has a high xref
count, leaf/no-BL shape, a real RET, and no zero-return shape. This is not a general relaxation for
all non-JOPP functions.

Owned-input orchestration:

- `__kmalloc`: `0xffffff800826ae34`, `export-recovery`, direct BL xrefs `1765`
- `kfree`: `0xffffff800826b354`, `export-recovery`, direct BL xrefs `10596`
- `__kmalloc` passed the no-pre-call-x0-deref guard.

The target was not called with a host-supplied numeric pointer. The tool allocated an owned kernel
buffer, wrote `A90STRNLEN\0`, verified it by peek, called `strnlen(ptr, 64)`, then freed the buffer.

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
- Post-flash selftest retry: `pass=11 warn=1 fail=0`.
- `a90_repl.py selftest`: `a90-repl-v2a1-selftest-pass`.

The first post-flash selftest attempt hit serial input/capture fragmentation and missed the
`A90P1 END` marker. `version` realigned the bridge and the slow-input selftest retry passed. This was
a transport artifact, not a device health regression.

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
  --evidence-dir workspace/private/runs/kernel/live-call-proof-strnlen-20260630/proof \
  strnlen
```

Public result:

```json
{
  "decision": "a90-repl-live-call-proof-strnlen-pass",
  "ok": true,
  "proof_string": "A90STRNLEN",
  "maxlen": 64,
  "expected_return_value": "0xa",
  "observed_return_value": "0xa",
  "proof_status": "trusted-under-owned-input-contract",
  "raw_runtime_values_redacted": true,
  "owned_pointer_redacted": true
}
```

Checks:

- `static-c1-identity`: OK, `strnlen` resolved by `leaf-map-disasm+xref`.
- `static-source-contract`: OK, signature `extern __kernel_size_t strnlen(const char *,__kernel_size_t)`.
- `static-call-safety-contract`: OK, tier `SAFE-WITH-VALID-PTR`, x0 requires verified string buffer.
- `kmalloc-owned-string-buffer`: OK, allocated `0x1000` bytes and returned sane kernel lowmem.
- `owned-string-poke-peek`: OK, `A90STRNLEN\0` was written and read back.
- `strnlen-return-contract`: OK, returned `0xa`, expected `0xa`, maxlen `0x40`.
- `kfree-owned-string-buffer`: OK, cleanup was attempted and succeeded.

Raw runtime slide, `strnlen` runtime address, owned allocation pointer, and raw observed bytes were
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
- Final `selftest verbose`: `pass=11 warn=1 fail=0`.

One immediate final health command hit serial input fragmentation and missed the `A90P1 END` marker.
`version` realigned the bridge and the slow-input selftest retry passed. This was a transport artifact,
not a device health regression.

## Conclusion

`strnlen` is now live-proven under the owned NUL-terminated kernel string plus scalar maxlen contract.
The proof confirms the intended helper was reached, returned the exact expected length for
`A90STRNLEN`, and left the device healthy after cleanup. This does not authorize arbitrary string
pointers, unbounded string helpers, or other string/memory functions. The device was rolled back to
clean v2321 with final `selftest fail=0`.
