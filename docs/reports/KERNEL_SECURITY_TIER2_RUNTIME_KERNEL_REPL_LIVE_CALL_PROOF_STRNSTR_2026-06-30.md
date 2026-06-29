# Kernel Security Tier-2 Runtime Kernel REPL - Live Call Proof: strnstr

- Date: 2026-06-30
- Decision: `a90-repl-live-call-proof-strnstr-pass`
- Scope: separately gated one-target live-call proof after the REPL epic close.
- Device action: yes, boot partition only through `native_init_flash.py`.
- Candidate image: `workspace/private/inputs/boot_images/boot_linux_tier2_repl_v1_repl.img`
- Candidate SHA256: `b846ae9f74d8ceb922bbcd854d78b6795ef833d61e38465d3cc474cb6f0dfb65`
- Rollback image: `workspace/private/inputs/boot_images/boot_linux_v2321_usb_clean_identity_rodata.img`
- Rollback SHA256: `ca978551aabe4b39563abaf529ccf2522054952d8b2ad852e632d26da88168cb`
- Private evidence: `workspace/private/runs/kernel/live-call-proof-strnstr-20260630/proof/a90_repl_evidence.json`

## Static Gate

Target:

- `strnstr`: `0xffffff80099b9f44`
- Resolution method: `export-recovery`
- Direct BL xrefs: `268`
- Shape: JOPP entry, non-leaf helper; calls `__pi_strlen` and `__pi_memcmp`; RET observed at
  offset `0x74` with a scan of `128` bytes.
- Source signature: `include/linux/string.h:79`, `extern char * strnstr(const char *, const char *, size_t)`
- Source pointer contract: x0 is the haystack string buffer, x1 is the needle string buffer, and x2 is the scalar bounded length.
- Call-safety tier: `SAFE-WITH-VALID-PTR`
- Required valid pointer args: x0 = `haystack-string-buffer`, x1 = `needle-string-buffer`

Owned-input orchestration:

- `__kmalloc`: `0xffffff800826ae34`, `export-recovery`, direct BL xrefs `1765`
- `kfree`: `0xffffff800826b354`, `export-recovery`, direct BL xrefs `10596`
- `__kmalloc` passed the no-pre-call-x0-deref guard.

The target was not called with host-supplied numeric pointers. The tool allocated two owned kernel
buffers, wrote haystack `A90STRNSTR-HEAD-NEEDLE-TAIL` and needle `NEEDLE`, then required
`strnstr(haystack, needle, 27)` to return the owned haystack pointer at offset `16`. It also required
length `21` to return `0` because that bound excludes one needle byte. It then rewrote the needle
buffer to `ABSENT` and required the missing case to return `0`. Both buffers had private canary bytes.

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
  --evidence-dir workspace/private/runs/kernel/live-call-proof-strnstr-20260630/proof \
  strnstr
```

Public result:

```json
{
  "decision": "a90-repl-live-call-proof-strnstr-pass",
  "ok": true,
  "haystack": "A90STRNSTR-HEAD-NEEDLE-TAIL",
  "needle": "NEEDLE",
  "missing_needle": "ABSENT",
  "hit_len": 27,
  "bound_miss_len": 21,
  "expected_hit_offset": 16,
  "hit_return_matches_expected_offset": true,
  "bound_miss_expected_return_value": "0x0",
  "bound_miss_observed_return_value": "0x0",
  "missing_expected_return_value": "0x0",
  "missing_observed_return_value": "0x0",
  "strings_unchanged_after_calls": true,
  "proof_status": "trusted-under-owned-input-contract",
  "raw_runtime_values_redacted": true,
  "owned_pointer_redacted": true,
  "observed_bytes_redacted": true
}
```

Checks:

- `static-c1-identity`: OK, `strnstr` resolved by `export-recovery`.
- `static-source-contract`: OK, signature `extern char * strnstr(const char *, const char *, size_t)`.
- `static-call-safety-contract`: OK, tier `SAFE-WITH-VALID-PTR`, x0/x1 require verified strings, and x2 length is bounded inside the haystack.
- `kmalloc-owned-strnstr-strings`: OK, allocated two distinct owned buffers.
- `owned-strnstr-string-poke-peek`: OK, haystack and present needle plus canaries were written and read back.
- `strnstr-hit-return-contract`: OK, returned the owned haystack pointer at offset `16`.
- `strnstr-hit-string-immutability`: OK, both strings stayed unchanged.
- `strnstr-boundary-miss-return-contract`: OK, bounded length `21` returned `0`.
- `strnstr-boundary-miss-string-immutability`: OK, both strings stayed unchanged.
- `owned-strnstr-missing-needle-poke-peek`: OK, missing needle `ABSENT` was written and read back.
- `strnstr-missing-return-contract`: OK, returned `0`.
- `strnstr-missing-string-immutability`: OK, both strings stayed unchanged.
- `kfree-owned-strnstr-strings`: OK, cleanup succeeded.

Raw runtime slide, `strnstr` runtime address, owned allocation pointers, and raw observed bytes were
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

One candidate selftest read after candidate boot returned no END marker and only shell `AT` echo text.
The bridge remained reachable; repeated `version` and `selftest` immediately succeeded, and the proof
plus post-proof health checks were clean. A final rollback `version` capture also had minor stale echo
before the command text but retained a valid END marker and rc/status `ok`.

## Conclusion

`strnstr` is now live-proven under the owned haystack/needle NUL-string plus bounded-length contract.
The proof confirms the intended helper was reached, returned the expected present-substring offset
when the bounded length covered the whole needle, returned `0` when the bounded length excluded one
needle byte, returned `0` for a missing needle, left both owned strings unchanged, cleaned up both
allocations, and left the device healthy. This does not authorize arbitrary pointers, user pointers,
unterminated strings, out-of-range lengths, broader substring cases, or mass calling. The device was
rolled back to clean v2321 with final `selftest fail=0`.
