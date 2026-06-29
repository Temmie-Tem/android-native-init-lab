# Kernel Security Tier-2 Runtime Kernel REPL - Live Call Proof: strchr

- Date: 2026-06-30
- Decision: `a90-repl-live-call-proof-strchr-pass`
- Scope: separately gated one-target live-call proof after the REPL epic close.
- Device action: yes, boot partition only through `native_init_flash.py`.
- Candidate image: `workspace/private/inputs/boot_images/boot_linux_tier2_repl_v1_repl.img`
- Candidate SHA256: `b846ae9f74d8ceb922bbcd854d78b6795ef833d61e38465d3cc474cb6f0dfb65`
- Rollback image: `workspace/private/inputs/boot_images/boot_linux_v2321_usb_clean_identity_rodata.img`
- Rollback SHA256: `ca978551aabe4b39563abaf529ccf2522054952d8b2ad852e632d26da88168cb`
- Private evidence: `workspace/private/runs/kernel/live-call-proof-strchr-20260630/proof/a90_repl_evidence.json`

## Static Gate

Target:

- `strchr`: `0xffffff80099a8b48`
- Resolution method: `leaf-map-disasm+xref`
- Direct BL xrefs: `127`
- Shape: non-JOPP arm64 leaf helper; no BL in scan; RET observed at offset `0x20`.
- Source signature: `include/linux/string.h:55`, `extern char * strchr(const char *,int)`
- Source pointer contract: x0 is the string pointer, x1 is the scalar search byte.
- Call-safety tier: `SAFE-WITH-VALID-PTR`
- Required valid pointer args: x0 = `string-buffer`

`strchr` is an arm64 leaf routine without the JOPP marker used by most C functions in this image.
The C1 exception is intentionally narrow: it accepts only the `strchr` System.map label when the body
is leaf/no-BL, has a RET in scan, has no zero-return-before-ret pattern, and has at least 100 direct
BL xrefs. The observed xref count was `127`.

This proof owns the string buffer and fixes the calls to:

- hit case: `strchr("A90STRCHR-Q-B-Q-Z", 'Q')`, expecting the first occurrence at offset `10`
- missing case: `strchr("A90STRCHR-Q-B-Q-Z", '@')`, expecting `NULL`

It does not authorize arbitrary pointers, unterminated strings, user pointers, or other string helpers.

Owned-input orchestration:

- `__kmalloc`: `0xffffff800826ae34`, `export-recovery`, direct BL xrefs `1765`
- `kfree`: `0xffffff800826b354`, `export-recovery`, direct BL xrefs `10596`
- `__kmalloc` passed the no-pre-call-x0-deref guard.

The target was not called with a host-supplied numeric pointer. The tool allocated one owned string
buffer, wrote the proof string plus post-NUL canary, verified it by peek, called `strchr` for the hit
case, verified the string stayed unchanged, called `strchr` again for the missing case, verified the
string stayed unchanged again, then freed the buffer.

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
  --evidence-dir workspace/private/runs/kernel/live-call-proof-strchr-20260630/proof \
  strchr
```

Public result:

```json
{
  "decision": "a90-repl-live-call-proof-strchr-pass",
  "ok": true,
  "proof_string": "A90STRCHR-Q-B-Q-Z",
  "search_byte": "0x51",
  "expected_hit_offset": 10,
  "return_matches_expected_offset": true,
  "missing_byte": "0x40",
  "missing_observed_return_value": "0x0",
  "string_unchanged_after_calls": true,
  "proof_status": "trusted-under-owned-input-contract",
  "raw_runtime_values_redacted": true,
  "owned_pointer_redacted": true,
  "observed_bytes_redacted": true
}
```

Checks:

- `static-c1-identity`: OK, `strchr` resolved by `leaf-map-disasm+xref`.
- `static-source-contract`: OK, signature `extern char * strchr(const char *,int)`.
- `static-call-safety-contract`: OK, tier `SAFE-WITH-VALID-PTR`, x0 requires a verified owned
  string buffer.
- `kmalloc-owned-strchr-string-buffer`: OK, allocated one owned kernel string buffer.
- `owned-strchr-string-poke-peek`: OK, proof string plus canary was written and read back.
- `strchr-hit-return-contract`: OK, hit returned owned string pointer plus offset `10`.
- `strchr-hit-string-immutability`: OK, string stayed unchanged.
- `strchr-missing-return-contract`: OK, missing byte returned `0x0`.
- `strchr-missing-string-immutability`: OK, string stayed unchanged.
- `kfree-owned-strchr-string-buffer`: OK, cleanup succeeded.

Raw runtime slide, `strchr` runtime address, owned allocation pointer, returned pointer, and raw
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

## Note On Serial Noise

During candidate and final health checks, two direct `a90ctl selftest` attempts hit serial-input echo
noise and failed to parse an `A90P1 END` marker. The commands were retried after a successful `version`
probe using slow input mode, and both bounded retries returned clean `selftest fail=0`. This was a
transport capture/input issue, not a device health regression.

## Conclusion

`strchr` is now live-proven under the owned NUL-terminated string plus scalar-search-byte contract.
The proof confirms the intended helper was reached, returned the first matching owned-string pointer
offset, returned `NULL` for a missing byte, left the string unchanged, and left the device healthy
after cleanup. This does not authorize arbitrary pointers, unterminated strings, user pointers, or
other string helpers. The device was rolled back to clean v2321 with final `selftest fail=0`.
