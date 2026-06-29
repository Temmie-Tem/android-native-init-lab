# Kernel Security Tier-2 Runtime Kernel REPL - Live Call Proof: strspn

- Date: 2026-06-30
- Decision: `a90-repl-live-call-proof-strspn-pass`
- Scope: separately gated one-target live-call proof after the REPL epic close.
- Device action: yes, boot partition only through `native_init_flash.py`.
- Candidate image: `workspace/private/inputs/boot_images/boot_linux_tier2_repl_v1_repl.img`
- Candidate SHA256: `b846ae9f74d8ceb922bbcd854d78b6795ef833d61e38465d3cc474cb6f0dfb65`
- Rollback image: `workspace/private/inputs/boot_images/boot_linux_v2321_usb_clean_identity_rodata.img`
- Rollback SHA256: `ca978551aabe4b39563abaf529ccf2522054952d8b2ad852e632d26da88168cb`
- Private evidence: `workspace/private/runs/kernel/live-call-proof-strspn-20260630/proof/a90_repl_evidence.json`

## Static Gate

Target:

- `strspn`: `0xffffff80099b9a6c`
- Resolution method: `export-recovery`
- Direct BL xrefs: `2`
- Shape: JOPP entry, leaf/no-BL helper; RETs observed in scan.
- Source signature: `include/linux/string.h:94`, `extern __kernel_size_t strspn(const char *,const char *)`
- Source pointer contract: x0 is the haystack NUL-terminated string buffer; x1 is the accept-set
  NUL-terminated string buffer.
- Call-safety tier: `SAFE-WITH-VALID-PTR`
- Required valid pointer args: x0 = `haystack-string-buffer`, x1 = `accept-string-buffer`

Owned-input orchestration:

- `__kmalloc`: `0xffffff800826ae34`, `export-recovery`, direct BL xrefs `1765`
- `kfree`: `0xffffff800826b354`, `export-recovery`, direct BL xrefs `10596`
- `__kmalloc` passed the no-pre-call-x0-deref guard.

The target was not called with host-supplied numeric pointers. The tool allocated one owned
haystack string buffer containing `A90STRSPN-HEAD-Q-TAIL` and one owned accept-set string buffer.
The prefix accept set `A90STRSPNHED-` intentionally excluded the first `Q` byte and required
`strspn(haystack, accept)` to return scalar length `15`. The tool then rewrote the accept-set buffer
to `A90STRSPNHEDQIL-`, required haystack length `21`, and required both strings plus canaries to
remain unchanged.

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
  --evidence-dir workspace/private/runs/kernel/live-call-proof-strspn-20260630/proof \
  strspn
```

Public result:

```json
{
  "decision": "a90-repl-live-call-proof-strspn-pass",
  "ok": true,
  "haystack": "A90STRSPN-HEAD-Q-TAIL",
  "prefix_accept_set": "A90STRSPNHED-",
  "full_accept_set": "A90STRSPNHEDQIL-",
  "expected_prefix_return_value": 15,
  "prefix_observed_return_value": 15,
  "prefix_return_matches_expected_length": true,
  "full_expected_return_value": 21,
  "full_observed_return_value": 21,
  "full_return_matches_haystack_length": true,
  "strings_unchanged_after_calls": true,
  "proof_status": "trusted-under-owned-input-contract",
  "raw_runtime_values_redacted": true,
  "owned_pointer_redacted": true,
  "observed_bytes_redacted": true
}
```

Checks:

- `static-c1-identity`: OK, `strspn` resolved by `export-recovery`.
- `static-source-contract`: OK, signature `extern __kernel_size_t strspn(const char *,const char *)`.
- `static-call-safety-contract`: OK, tier `SAFE-WITH-VALID-PTR`, x0/x1 require verified owned strings.
- `kmalloc-owned-strspn-strings`: OK, allocated two distinct owned kernel string buffers.
- `owned-strspn-string-poke-peek`: OK, haystack plus prefix accept-set plus canaries were written and read back.
- `strspn-prefix-return-contract`: OK, prefix accept-set returned scalar length `15`.
- `strspn-prefix-string-immutability`: OK, prefix case left both strings unchanged.
- `owned-strspn-full-accept-poke-peek`: OK, full accept-set plus canary was written and read back.
- `strspn-full-return-contract`: OK, full accept-set returned haystack length `21`.
- `strspn-full-string-immutability`: OK, full case left both strings unchanged.
- `kfree-owned-strspn-strings`: OK, cleanup succeeded.

Raw runtime slide, `strspn` runtime address, owned allocation pointers, and raw observed bytes were
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

## Note

Serial bridge commands must remain sequential during this live proof path. An initial parallel
candidate native selftest plus REPL selftest attempt encountered serial echo noise before END marker;
`version` re-synchronized the bridge, and sequential candidate native selftest plus REPL selftest
passed before the live proof ran. The first final selftest command after rollback also hit echo noise;
`version` re-synchronized the bridge and final selftest then passed.

## Conclusion

`strspn` is now live-proven under the owned NUL-terminated haystack plus owned NUL-terminated
accept-set contract. The proof confirms the intended helper was reached, returned the expected initial
accepted span length, returned the haystack length when the accept set covered every haystack byte, did
not mutate either owned string, cleaned up both allocations, and left the device healthy. This does not
authorize arbitrary pointers, user pointers, unterminated strings, writable side effects, or mass
calling. The device was rolled back to clean v2321 with final `selftest fail=0`.
