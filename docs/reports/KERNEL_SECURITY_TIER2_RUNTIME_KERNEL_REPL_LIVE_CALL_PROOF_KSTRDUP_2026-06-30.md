# Kernel Security Tier-2 Runtime Kernel REPL - Live Call Proof: kstrdup

- Date: 2026-06-30
- Decision: `a90-repl-live-call-proof-kstrdup-pass`
- Scope: separately gated one-target live-call proof after the REPL epic close.
- Device action: yes, boot partition only through `native_init_flash.py`.
- Candidate image: `workspace/private/inputs/boot_images/boot_linux_tier2_repl_v1_repl.img`
- Candidate SHA256: `b846ae9f74d8ceb922bbcd854d78b6795ef833d61e38465d3cc474cb6f0dfb65`
- Rollback image: `workspace/private/inputs/boot_images/boot_linux_v2321_usb_clean_identity_rodata.img`
- Rollback SHA256: `ca978551aabe4b39563abaf529ccf2522054952d8b2ad852e632d26da88168cb`
- Private evidence: `workspace/private/runs/kernel/live-call-proof-kstrdup-20260630/proof/a90_repl_evidence.json`

## Static Gate

Target:

- `kstrdup`: `0xffffff800822a664`
- Resolution method: `export-recovery`
- Direct BL xrefs: `160`
- Shape: JOPP entry, non-leaf helper, RET observed at offset `0x70`.
- Disasm contract: the helper calls `__pi_strlen`, `__kmalloc_track_caller`, and `__memcpy`; x0 is the source string pointer and x1 is scalar GFP.
- Source signature: `include/linux/string.h:170`, `extern char * kstrdup(const char *s, gfp_t gfp) __malloc`
- Source pointer contract: x0 is an owned NUL-terminated kernel string buffer; x1 is scalar `GFP_KERNEL`.
- Call-safety tier: `SAFE-WITH-VALID-PTR`
- Required valid pointer args: x0 = `source-string-buffer`

Owned-input orchestration:

- `__kmalloc`: `0xffffff800826ae34`, `export-recovery`, direct BL xrefs `1765`
- `kfree`: `0xffffff800826b354`, `export-recovery`, direct BL xrefs `10596`
- `__kmalloc` passed the no-pre-call-x0-deref guard.
- `kstrdup` was called only after the tool allocated and verified an owned source string buffer.

The target was not called with a host-supplied numeric pointer. The tool allocated one owned kernel
source string buffer, wrote a bounded NUL-terminated test string plus canary, required the duplicate
to be a distinct owned kernel allocation, and verified both allocations were cleaned up.

## Flash And Health

Preconditions:

- v1-repl candidate SHA matched `b846ae9f74d8ceb922bbcd854d78b6795ef833d61e38465d3cc474cb6f0dfb65`.
- v2321 rollback SHA matched `ca978551aabe4b39563abaf529ccf2522054952d8b2ad852e632d26da88168cb`.
- v2237 fallback SHA matched `b2ea2d26d160b7702ce7d4438b84367788eea26c6a5bbe4ed93f3d270292ac7f`.
- Final fallback `boot_linux_v48.img` existed with SHA
  `1c87fa59712395027c5c2e489b15c4f6ddefabc3c50f78d3c235c4508a63e042`.
- TWRP recovery image existed with SHA
  `b1ef377a52ec8ab43b49a5fcc7a0b27e8efff91bf2d8cccdc565ecadadcc646c`.
- TWRP recovery tar existed with SHA
  `6d9e929462ea4c85f257b080431d387d5bfb787ff800bd4178c823c3874d862a`.
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

One host-side retry was required before the REPL selftest because two serial consumers were started
in parallel and collided on the bridge. The bridge remained reachable; the sequential `version`,
native `selftest`, and REPL `selftest` immediately passed.

## Live Proof

Command:

```sh
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 \
  workspace/public/src/scripts/revalidation/a90_repl.py call-proof kstrdup \
  --map workspace/private/runs/kernel/v2c-c2b-kallsyms-padding-fix/System.map \
  --image workspace/private/inputs/boot_images/boot_linux_tier2_repl_v1_repl.img \
  --source-root workspace/private/inputs/kernel_source/SM-A908N_KOR_12_Opensource/Kernel \
  --evidence-dir workspace/private/runs/kernel/live-call-proof-kstrdup-20260630/proof
```

Public result:

```json
{
  "decision": "a90-repl-live-call-proof-kstrdup-pass",
  "ok": true,
  "source_string": "A90KSTRDUP-SOURCE-Q-END",
  "duplicate_matches_source": true,
  "returned_owned_duplicate_pointer": true,
  "duplicate_distinct_from_source": true,
  "source_unchanged_after_call": true,
  "proof_status": "trusted-under-owned-input-contract",
  "raw_runtime_values_redacted": true,
  "owned_pointer_redacted": true,
  "observed_bytes_redacted": true
}
```

Checks:

- `static-c1-identity`: OK, `kstrdup` resolved by `export-recovery`.
- `static-source-contract`: OK, signature `extern char * kstrdup(const char *s, gfp_t gfp) __malloc`.
- `static-call-safety-contract`: OK, tier `SAFE-WITH-VALID-PTR`, x0 requires a verified owned source string buffer.
- `kmalloc-owned-kstrdup-source`: OK, allocated one owned kernel source string buffer.
- `owned-kstrdup-source-poke-peek`: OK, source string plus canary was written and read back.
- `kstrdup-return-owned-duplicate`: OK, returned a distinct owned kernel duplicate pointer.
- `kstrdup-duplicate-byte-contract`: OK, duplicate bytes matched source including NUL.
- `kstrdup-source-immutability`: OK, source string and canary stayed unchanged.
- `kfree-owned-kstrdup-source-and-duplicate`: OK, duplicate and source cleanup succeeded.

Raw runtime slide, `kstrdup` runtime address, owned source/duplicate pointers, and raw observed bytes
were written only to private evidence and are not included in this report.

Candidate selftest after proof: `pass=11 warn=1 fail=0`.

## Rollback

Rollback command:

```sh
python3 workspace/public/src/scripts/revalidation/native_init_flash.py \
  --from-native \
  --expect-version v2321-usb-clean-identity-rodata \
  --expect-sha256 ca978551aabe4b39563abaf529ccf2522054952d8b2ad852e632d26da88168cb \
  --expect-readback-sha256 ca978551aabe4b39563abaf529ccf2522054952d8b2ad852e632d26da88168cb \
  workspace/private/inputs/boot_images/boot_linux_v2321_usb_clean_identity_rodata.img
```

Result:

- Remote pushed image SHA matched v2321 SHA.
- Boot readback SHA matched v2321 SHA.
- Post-rollback `version/status` verification passed.
- Final resident: `v2321-usb-clean-identity-rodata`.
- Final `selftest`: `pass=11 warn=1 fail=0`.

## Conclusion

`kstrdup` is now live-proven under an owned source string plus `GFP_KERNEL` contract. The proof
confirms the intended helper was reached, returned a distinct owned kernel duplicate string whose
bytes matched the source including NUL, left the source buffer unchanged, cleaned up both allocations,
and left the device healthy. This does not authorize arbitrary pointers, user pointers, unterminated
strings, arbitrary GFP flags, stale buffers, or mass calling. The device was rolled back to clean v2321
with final `selftest fail=0`.
