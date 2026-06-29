# Kernel Security Tier-2 Runtime Kernel REPL - Live Call Proof: sysfs_streq

- Date: 2026-06-30
- Decision: `a90-repl-live-call-proof-sysfs_streq-pass`
- Scope: separately gated one-target live-call proof after the REPL epic close.
- Device action: yes, boot partition only through `native_init_flash.py`.
- Candidate image: `workspace/private/inputs/boot_images/boot_linux_tier2_repl_v1_repl.img`
- Candidate SHA256: `b846ae9f74d8ceb922bbcd854d78b6795ef833d61e38465d3cc474cb6f0dfb65`
- Rollback image: `workspace/private/inputs/boot_images/boot_linux_v2321_usb_clean_identity_rodata.img`
- Rollback SHA256: `ca978551aabe4b39563abaf529ccf2522054952d8b2ad852e632d26da88168cb`
- Private evidence: `workspace/private/runs/kernel/live-call-proof-sysfs-streq-20260630/proof/a90_repl_evidence.json`

## Static Gate

Target:

- `sysfs_streq`: `0xffffff80099b9c14`
- Resolution method: `export-recovery`
- Direct BL xrefs: `68`
- Shape: JOPP entry, leaf/no-BL helper, RET observed at offsets `0x44` and `0x80`.
- Disasm contract: the helper reads bytes from x0 and x1 only, loops over the two strings, and handles the sysfs trailing-newline equality case without calling another helper.
- Source signature: `include/linux/string.h:179`, `extern bool sysfs_streq(const char *s1, const char *s2)`
- Source pointer contract: x0 and x1 are owned NUL-terminated kernel string buffers.
- Call-safety tier: `SAFE-WITH-VALID-PTR`
- Required valid pointer args: x0 = `left-string-buffer`, x1 = `right-string-buffer`

Owned-input orchestration:

- `__kmalloc`: `0xffffff800826ae34`, `export-recovery`, direct BL xrefs `1765`
- `kfree`: `0xffffff800826b354`, `export-recovery`, direct BL xrefs `10596`
- `__kmalloc` passed the no-pre-call-x0-deref guard.
- `sysfs_streq` uses the expected string-helper pre-call x0/x1 dereferences, so the proof requires owned pointers before allowing the call.

The target was not called with host-supplied numeric pointers. The tool allocated two distinct owned
kernel string buffers, wrote bounded NUL-terminated test strings plus canaries, and verified the
buffers stayed unchanged after all calls.

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
  workspace/public/src/scripts/revalidation/a90_repl.py call-proof sysfs_streq \
  --map workspace/private/runs/kernel/v2c-c2b-kallsyms-padding-fix/System.map \
  --image workspace/private/inputs/boot_images/boot_linux_tier2_repl_v1_repl.img \
  --source-root workspace/private/inputs/kernel_source/SM-A908N_KOR_12_Opensource/Kernel \
  --evidence-dir workspace/private/runs/kernel/live-call-proof-sysfs-streq-20260630/proof
```

Public result:

```json
{
  "decision": "a90-repl-live-call-proof-sysfs_streq-pass",
  "ok": true,
  "newline_left": "A90SYSFS-VALUE\\n",
  "equal_left": "A90SYSFS-VALUE",
  "equal_right": "A90SYSFS-VALUE",
  "mismatch_right": "A90SYSFS-OTHER",
  "newline_expected_return_value": "0x1",
  "newline_observed_return_value": "0x1",
  "strict_equal_expected_return_value": "0x1",
  "strict_equal_observed_return_value": "0x1",
  "mismatch_expected_return_value": "0x0",
  "mismatch_observed_return_value": "0x0",
  "strings_unchanged_after_calls": true,
  "proof_status": "trusted-under-owned-input-contract",
  "raw_runtime_values_redacted": true,
  "owned_pointer_redacted": true,
  "observed_bytes_redacted": true
}
```

Checks:

- `static-c1-identity`: OK, `sysfs_streq` resolved by `export-recovery`.
- `static-source-contract`: OK, signature `extern bool sysfs_streq(const char *s1, const char *s2)`.
- `static-call-safety-contract`: OK, tier `SAFE-WITH-VALID-PTR`, x0/x1 require verified owned string buffers.
- `kmalloc-owned-sysfs-streq-strings`: OK, allocated two distinct owned kernel string buffers.
- `owned-sysfs-streq-newline-string-poke-peek`: OK, newline-left and equal-right strings plus canaries were written and read back.
- `sysfs-streq-newline-return-contract`: OK, returned `0x1`.
- `sysfs-streq-newline-string-immutability`: OK, both strings stayed unchanged.
- `owned-sysfs-streq-strict-equal-poke-peek`: OK, exact-equal strings were written and read back.
- `sysfs-streq-strict-equal-return-contract`: OK, returned `0x1`.
- `owned-sysfs-streq-mismatch-poke-peek`: OK, mismatch string was written and read back.
- `sysfs-streq-mismatch-return-contract`: OK, returned `0x0`.
- `sysfs-streq-final-string-immutability`: OK, both strings and canaries stayed unchanged.
- `kfree-owned-sysfs-streq-strings`: OK, cleanup succeeded.

Raw runtime slide, `sysfs_streq` runtime address, owned string pointers, and raw observed bytes were
written only to private evidence and are not included in this report.

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

One final selftest read after rollback returned no END marker and only stale serial echo text. The
bridge remained reachable; a repeated `selftest` immediately succeeded with `fail=0`.

## Conclusion

`sysfs_streq` is now live-proven under a two-owned-string contract. The proof confirms the intended
helper was reached, returned true for exact equality and the sysfs one-trailing-newline equality case,
returned false for a mismatch, left the owned strings unchanged, cleaned up both allocations, and left
the device healthy. This does not authorize arbitrary pointers, user pointers, unterminated strings,
stale buffers, or mass calling. The device was rolled back to clean v2321 with final `selftest fail=0`.
