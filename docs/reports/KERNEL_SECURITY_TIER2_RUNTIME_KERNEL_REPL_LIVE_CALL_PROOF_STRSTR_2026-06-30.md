# Kernel Security Tier-2 Runtime Kernel REPL - Live Call Proof: strstr

- Date: 2026-06-30
- Decision: `a90-repl-live-call-proof-strstr-pass`
- Scope: separately gated one-target live-call proof after the REPL epic close.
- Device action: yes, boot partition only through `native_init_flash.py`.
- Candidate image: `workspace/private/inputs/boot_images/boot_linux_tier2_repl_v1_repl.img`
- Candidate SHA256: `b846ae9f74d8ceb922bbcd854d78b6795ef833d61e38465d3cc474cb6f0dfb65`
- Rollback image: `workspace/private/inputs/boot_images/boot_linux_v2321_usb_clean_identity_rodata.img`
- Rollback SHA256: `ca978551aabe4b39563abaf529ccf2522054952d8b2ad852e632d26da88168cb`
- Private evidence: `workspace/private/runs/kernel/live-call-proof-strstr-20260630/proof/a90_repl_evidence.json`

## Static Gate

Target:

- `strstr`: `0xffffff80099b9ebc`
- Resolution method: `export-recovery`
- Direct BL xrefs: `50`
- Shape: JOPP entry, non-leaf helper; calls `__pi_strlen` and `__pi_memcmp`; RET observed at
  offset `0x7c` with a scan of `136` bytes.
- Source signature: `include/linux/string.h:76`, `extern char * strstr(const char *, const char *)`
- Source pointer contract: x0 is the haystack string buffer, x1 is the needle string buffer.
- Call-safety tier: `SAFE-WITH-VALID-PTR`
- Required valid pointer args: x0 = `haystack-string-buffer`, x1 = `needle-string-buffer`

Owned-input orchestration:

- `__kmalloc`: `0xffffff800826ae34`, `export-recovery`, direct BL xrefs `1765`
- `kfree`: `0xffffff800826b354`, `export-recovery`, direct BL xrefs `10596`
- `__kmalloc` passed the no-pre-call-x0-deref guard.

The target was not called with host-supplied numeric pointers. The tool allocated two owned kernel
buffers, wrote haystack `A90STRSTR-HEAD-NEEDLE-TAIL` and needle `NEEDLE`, then required
`strstr(haystack, needle)` to return the owned haystack pointer at offset `15`. It then rewrote the
needle buffer to `ABSENT` and required the missing case to return `0`.

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
  --evidence-dir workspace/private/runs/kernel/live-call-proof-strstr-20260630/proof \
  strstr
```

Public result:

```json
{
  "decision": "a90-repl-live-call-proof-strstr-pass",
  "ok": true,
  "haystack": "A90STRSTR-HEAD-NEEDLE-TAIL",
  "needle": "NEEDLE",
  "missing_needle": "ABSENT",
  "expected_hit_offset": 15,
  "hit_expected_return_value": "owned-haystack-pointer-plus-offset-redacted",
  "hit_observed_return_value": "owned-haystack-pointer-plus-offset-redacted",
  "hit_return_matches_expected_offset": true,
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

- `static-c1-identity`: OK, `strstr` resolved by `export-recovery`.
- `static-source-contract`: OK, signature `extern char * strstr(const char *, const char *)`.
- `static-call-safety-contract`: OK, tier `SAFE-WITH-VALID-PTR`, x0/x1 require verified strings.
- `kmalloc-owned-strstr-strings`: OK, allocated two distinct owned buffers.
- `owned-strstr-string-poke-peek`: OK, haystack and present needle plus canaries were written and
  read back.
- `strstr-hit-return-contract`: OK, returned the owned haystack pointer at offset `15`.
- `strstr-hit-string-immutability`: OK, both strings stayed unchanged.
- `owned-strstr-missing-needle-poke-peek`: OK, missing needle `ABSENT` was written and read back.
- `strstr-missing-return-contract`: OK, returned `0`.
- `strstr-missing-string-immutability`: OK, both strings stayed unchanged.
- `kfree-owned-strstr-strings`: OK, cleanup succeeded.

Raw runtime slide, `strstr` runtime address, owned allocation pointers, and raw observed bytes were
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

One candidate selftest read and one final status read hit transient serial framing/echo capture issues
with no END marker. The bridge remained reachable. Retrying the candidate selftest separately and
using slow input mode for final `version`/`selftest` succeeded and confirmed candidate health plus final
v2321 `selftest fail=0`.

## Conclusion

`strstr` is now live-proven under the owned haystack/needle NUL-string contract. The proof confirms
the intended helper was reached, returned the expected present-substring offset, returned `0` for a
missing needle, left both owned strings unchanged, cleaned up both allocations, and left the device
healthy. This does not authorize arbitrary pointers, user pointers, unterminated strings, or broader
substring cases. The device was rolled back to clean v2321 with final `selftest fail=0`.
