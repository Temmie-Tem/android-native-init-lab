# Kernel Security Tier-2 Runtime Kernel REPL - Live Call Proof: memchr_inv

- Date: 2026-06-30
- Decision: `a90-repl-live-call-proof-memchr_inv-pass`
- Scope: separately gated one-target live-call proof after the REPL epic close.
- Device action: yes, boot partition only through `native_init_flash.py`.
- Candidate image: `workspace/private/inputs/boot_images/boot_linux_tier2_repl_v1_repl.img`
- Candidate SHA256: `b846ae9f74d8ceb922bbcd854d78b6795ef833d61e38465d3cc474cb6f0dfb65`
- Rollback image: `workspace/private/inputs/boot_images/boot_linux_v2321_usb_clean_identity_rodata.img`
- Rollback SHA256: `ca978551aabe4b39563abaf529ccf2522054952d8b2ad852e632d26da88168cb`
- Private evidence: `workspace/private/runs/kernel/live-call-proof-memchr-inv-20260630/proof/a90_repl_evidence.json`

## Static Gate

Target:

- `memchr_inv`: `0xffffff80099b9fc4`
- Resolution method: `export-recovery`
- Direct BL xrefs: `31`
- Shape: JOPP entry, leaf/no-BL helper; RETs observed in scan.
- Source signature: `include/linux/string.h:165`, `void * memchr_inv(const void *s, int c, size_t n)`
- Source pointer contract: x0 is the buffer pointer, x1 is the scalar fill byte, x2 is scalar size.
- Call-safety tier: `SAFE-WITH-VALID-PTR`
- Required valid pointer args: x0 = `buffer`

Owned-input orchestration:

- `__kmalloc`: `0xffffff800826ae34`, `export-recovery`, direct BL xrefs `1765`
- `kfree`: `0xffffff800826b354`, `export-recovery`, direct BL xrefs `10596`
- `__kmalloc` passed the no-pre-call-x0-deref guard.

The target was not called with a host-supplied numeric pointer. The tool allocated one owned
initialized buffer and fixed `size=32`, which is inside the allocation. The hit case filled the bounded
range with `0x5a` except one `0x33` byte at offset `13` and required `memchr_inv(buf, 0x5a, 32)` to
return the owned buffer pointer at offset `13`. The all-fill case rewrote the bounded range to all
`0x5a`, left a non-fill post-size canary outside the bounded range, required a NULL return, and
required buffer plus canary immutability after both calls.

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
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 \
  workspace/public/src/scripts/revalidation/native_init_flash.py \
  --from-native \
  --expect-sha256 b846ae9f74d8ceb922bbcd854d78b6795ef833d61e38465d3cc474cb6f0dfb65 \
  --expect-readback-sha256 b846ae9f74d8ceb922bbcd854d78b6795ef833d61e38465d3cc474cb6f0dfb65 \
  workspace/private/inputs/boot_images/boot_linux_tier2_repl_v1_repl.img
```

Result:

- Remote pushed image SHA matched candidate SHA.
- Boot readback SHA matched candidate SHA.
- Post-flash `version/status` verification passed.
- Candidate native selftest after re-sync: `pass=11 warn=1 fail=0`.
- `a90_repl.py selftest`: `a90-repl-v2a1-selftest-pass`.

The first standalone candidate `selftest` command hit serial-input echo noise and did not produce an
`A90P1 END` marker. Immediate `version` re-sync succeeded, then `selftest` and the REPL selftest both
passed. This was treated as a transport framing issue, not a device health regression.

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
  --evidence-dir workspace/private/runs/kernel/live-call-proof-memchr-inv-20260630/proof \
  memchr_inv
```

Public result:

```json
{
  "decision": "a90-repl-live-call-proof-memchr_inv-pass",
  "ok": true,
  "size_arg": 32,
  "fill_byte": "0x5a",
  "mismatch_byte": "0x33",
  "expected_hit_offset": 13,
  "hit_expected_return_value": "owned-buffer-pointer-plus-offset-redacted",
  "hit_observed_return_value": "owned-buffer-pointer-plus-offset-redacted",
  "hit_return_matches_expected_offset": true,
  "all_fill_expected_return_value": "0x0",
  "all_fill_observed_return_value": "0x0",
  "all_fill_return_matches_null": true,
  "canary_contains_non_fill_byte": true,
  "buffer_unchanged_after_calls": true,
  "proof_status": "trusted-under-owned-input-contract",
  "raw_runtime_values_redacted": true,
  "owned_pointer_redacted": true,
  "observed_bytes_redacted": true
}
```

Checks:

- `static-c1-identity`: OK, `memchr_inv` resolved by `export-recovery`.
- `static-source-contract`: OK, signature `void * memchr_inv(const void *s, int c, size_t n)`.
- `static-call-safety-contract`: OK, tier `SAFE-WITH-VALID-PTR`, x0 requires a verified buffer,
  bounded size `32`.
- `kmalloc-owned-memchr-inv-buffer`: OK, allocated one owned kernel buffer.
- `owned-memchr-inv-hit-buffer-poke-peek`: OK, hit buffer plus canary was written and read back.
- `memchr-inv-hit-return-contract`: OK, returned owned buffer pointer plus offset `13`.
- `memchr-inv-hit-buffer-immutability`: OK, hit search did not modify the buffer.
- `owned-memchr-inv-equal-buffer-poke-peek`: OK, all-fill buffer plus non-fill canary was written and
  read back.
- `memchr-inv-all-fill-return-contract`: OK, all-fill bounded range returned `0x0` even though the
  post-size canary contained non-fill bytes.
- `memchr-inv-all-fill-buffer-immutability`: OK, all-fill search did not modify the buffer.
- `kfree-owned-memchr-inv-buffer`: OK, cleanup succeeded.

Raw runtime slide, `memchr_inv` runtime address, owned allocation pointer, returned pointer, and raw
observed bytes were written only to private evidence and are not included in this report.

Candidate selftest after proof: `pass=11 warn=1 fail=0`.

## Rollback

Rollback command:

```sh
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 \
  workspace/public/src/scripts/revalidation/native_init_flash.py \
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

`memchr_inv` is now live-proven under the owned initialized buffer plus scalar-fill-byte and
bounded-size contract. The proof confirms the intended helper was reached, returned the first
non-fill owned-buffer pointer offset, returned `NULL` when all bytes inside the bounded range matched
the fill byte, ignored non-fill bytes in the post-size canary, left the buffer unchanged, and left the
device healthy after cleanup. This does not authorize arbitrary pointers, unbounded sizes,
uninitialized buffers, user pointers, or other memory helpers. The device was rolled back to clean
v2321 with final `selftest fail=0`.
