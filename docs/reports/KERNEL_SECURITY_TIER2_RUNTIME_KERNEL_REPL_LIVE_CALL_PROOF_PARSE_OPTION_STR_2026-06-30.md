# Kernel Security Tier-2 Runtime Kernel REPL - Live Call Proof: parse_option_str

- Date: 2026-06-30
- Decision: `a90-repl-live-call-proof-parse_option_str-pass`
- Scope: separately gated one-target live-call proof after the REPL epic close.
- Device action: yes, boot partition only through `native_init_flash.py`.
- Candidate image: `workspace/private/inputs/boot_images/boot_linux_tier2_repl_v1_repl.img`
- Candidate SHA256: `b846ae9f74d8ceb922bbcd854d78b6795ef833d61e38465d3cc474cb6f0dfb65`
- Rollback image: `workspace/private/inputs/boot_images/boot_linux_v2321_usb_clean_identity_rodata.img`
- Rollback SHA256: `ca978551aabe4b39563abaf529ccf2522054952d8b2ad852e632d26da88168cb`
- Private evidence: `workspace/private/runs/kernel/live-call-proof-parse-option-str-20260630/proof/a90_repl_evidence.json`

## Static Gate

Target:

- `parse_option_str`: `0xffffff80099a9c44`
- Resolution method: `disasm-signature+xref+map`
- Direct BL xrefs: `3`
- Shape: JOPP entry, non-leaf helper calling `__pi_strlen` and `__pi_strncmp`.
- Disasm contract: x0 is the comma-separated option string and x1 is the option string. The helper reads x0 before its first BL, calls strlen/strncmp on the owned strings, returns bool `1` only for an exact comma-delimited token match, and returns bool `0` otherwise.
- Source signature: `include/linux/kernel.h:472`, `extern bool parse_option_str(const char *str, const char *option)`
- Source pointer contract: x0 is an owned NUL-terminated comma-separated option string; x1 is an owned NUL-terminated option string.
- Call-safety tier: `SAFE-WITH-VALID-PTR`
- Required valid pointer args: x0 = `comma-separated-option-string`, x1 = `option-string`

Owned-input orchestration:

- `__kmalloc`: `0xffffff800826ae34`, `export-recovery`, direct BL xrefs `1765`
- `kfree`: `0xffffff800826b354`, `export-recovery`, direct BL xrefs `10596`
- `__kmalloc` passed the no-pre-call-x0-deref guard.
- `parse_option_str` was called only after the tool allocated, initialized, and verified both owned buffers.

The target was not called with a host-supplied numeric pointer. The proof used one owned list string
buffer and one owned option string buffer. The early x0 byte read is trusted only under that owned
NUL-terminated list string contract.

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
- A first REPL selftest attempt hit transient host-side serial `AT` capture noise and did not produce an END marker.
- Retry `a90_repl.py selftest`: `a90-repl-v2a1-selftest-pass`.

The v1-repl image intentionally keeps the v2321 native-init identity string, so `version` alone does
not distinguish it from the clean rollback image. The REPL selftest is the functional proof that the
candidate kernel REPL path is resident.

## Live Proof

Command:

```sh
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 \
  workspace/public/src/scripts/revalidation/a90_repl.py call-proof parse_option_str \
  --map workspace/private/runs/kernel/v2c-c2b-kallsyms-padding-fix/System.map \
  --image workspace/private/inputs/boot_images/boot_linux_tier2_repl_v1_repl.img \
  --source-root workspace/private/inputs/kernel_source/SM-A908N_KOR_12_Opensource/Kernel \
  --evidence-dir workspace/private/runs/kernel/live-call-proof-parse-option-str-20260630/proof
```

Public result:

```json
{
  "decision": "a90-repl-live-call-proof-parse_option_str-pass",
  "ok": true,
  "option": "A90PARSE-OPTION",
  "cases": {
    "exact-token-hit": {
      "input_ascii": "alpha,A90PARSE-OPTION,beta",
      "expected_return": 1,
      "observed_return": 1,
      "list_unchanged": true,
      "option_unchanged": true
    },
    "prefix-token-miss": {
      "input_ascii": "alpha,A90PARSE-OPTION-SUFFIX,beta",
      "expected_return": 0,
      "observed_return": 0,
      "list_unchanged": true,
      "option_unchanged": true
    },
    "missing-token": {
      "input_ascii": "alpha,beta,gamma",
      "expected_return": 0,
      "observed_return": 0,
      "list_unchanged": true,
      "option_unchanged": true
    }
  },
  "proof_status": "trusted-under-owned-input-contract",
  "raw_runtime_values_redacted": true,
  "owned_pointer_redacted": true,
  "observed_bytes_redacted": true
}
```

Checks:

- `static-c1-identity`: OK, `parse_option_str` resolved by `disasm-signature+xref+map`.
- `static-source-contract`: OK, signature `extern bool parse_option_str(const char *str, const char *option)`.
- `static-call-safety-contract`: OK, tier `SAFE-WITH-VALID-PTR`, x0/x1 require verified owned strings.
- `kmalloc-owned-parse-option-str-buffers`: OK, allocated distinct owned list and option buffers.
- `owned-parse-option-str-option-poke-peek`: OK, option bytes/canary were written and read back.
- `parse-option-str-case-exact-token-hit`: OK, exact comma-delimited token returned `1`.
- `parse-option-str-case-prefix-token-miss`: OK, prefix-only token returned `0`.
- `parse-option-str-case-missing-token`: OK, missing token returned `0`.
- `kfree-owned-parse-option-str-buffers`: OK, both owned buffers were freed.

Raw runtime slide, `parse_option_str` runtime address, owned list/option pointers, and raw observed
buffer bytes were written only to private evidence and are not included in this report.

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
- A first final health read hit transient host-side serial `AT` capture noise and did not produce an END marker.
- Sequential retry confirmed final resident `v2321-usb-clean-identity-rodata`.
- Final `selftest`: `pass=11 warn=1 fail=0`.

## Conclusion

`parse_option_str` is now live-proven under an owned NUL-terminated comma-separated option string plus
owned NUL-terminated option string contract. The proof confirms the intended helper was reached,
returned true for an exact comma-delimited token, returned false for prefix-only and missing-token
cases, left both input strings unchanged, cleaned up both allocations, and left the device healthy.
This does not authorize arbitrary pointers, user pointers, unterminated strings, unbounded scans,
stale buffers, arbitrary parser state, or mass calling. The device was rolled back to clean v2321
with final `selftest fail=0`.
