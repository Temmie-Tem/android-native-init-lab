# Kernel Security Tier-2 Runtime Kernel REPL - Live Call Proof: match_int

- Date: 2026-06-30
- Decision: `a90-repl-live-call-proof-match_int-pass`
- Scope: separately gated one-target live-call proof after the REPL epic close.
- Device action: yes, boot partition only through `native_init_flash.py`.
- Candidate image: `workspace/private/inputs/boot_images/boot_linux_tier2_repl_v1_repl.img`
- Candidate SHA256: `b846ae9f74d8ceb922bbcd854d78b6795ef833d61e38465d3cc474cb6f0dfb65`
- Rollback image: `workspace/private/inputs/boot_images/boot_linux_v2321_usb_clean_identity_rodata.img`
- Rollback SHA256: `ca978551aabe4b39563abaf529ccf2522054952d8b2ad852e632d26da88168cb`
- Private evidence: `workspace/private/runs/kernel/live-call-proof-match-int-20260630/proof/a90_repl_evidence.json`

## Static Gate

Target:

- `match_int`: `0xffffff800855b65c`
- Resolution method: `export-recovery`
- Direct BL xrefs: `54`
- Shape: JOPP entry, non-leaf wrapper calling `match_number`.
- Disasm contract: x0 is the `substring_t *`, x1 is the `int *result`, the wrapper sets
  `w2 = 0`, then calls `match_number`.
- Source signature: `include/linux/parser.h:31`, `int match_int(substring_t *, int *result)`
- Source pointer contract: x0 is an owned `substring_t` slot; x1 is an owned 4-byte result slot.
- Call-safety tier: `SAFE-WITH-VALID-PTR`
- Required valid pointer args: x0 = `substring-slot`, x1 = `int-result-output-slot`

Owned-input orchestration:

- `__kmalloc`: `0xffffff800826ae34`, `export-recovery`, direct BL xrefs `1765`
- `kfree`: `0xffffff800826b354`, `export-recovery`, direct BL xrefs `10596`
- `__kmalloc` passed the no-pre-call-x0-deref guard.
- The target was not called with host-supplied numeric pointers. The proof used one tool-owned
  layout containing `substring_t {from,to}`, bounded decimal text `12345`, an owned 4-byte result
  slot, and canaries around the controlled regions.

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
  --expect-version v2321-usb-clean-identity-rodata \
  workspace/private/inputs/boot_images/boot_linux_tier2_repl_v1_repl.img
```

Result:

- Remote pushed image SHA matched candidate SHA.
- Boot readback SHA matched candidate SHA.
- Post-flash `version/status` verification passed.
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
  --evidence-dir workspace/private/runs/kernel/live-call-proof-match-int-20260630/proof \
  match_int
```

Public result:

```json
{
  "decision": "a90-repl-live-call-proof-match_int-pass",
  "ok": true,
  "input_ascii": "12345",
  "expected_return": 0,
  "observed_return": 0,
  "expected_result": 12345,
  "observed_result": 12345,
  "expected_result_raw_hex": "0x00003039",
  "observed_result_raw_hex": "0x00003039",
  "substring_unchanged_after_call": true,
  "input_unchanged_after_call": true,
  "result_slot_canary_preserved": true,
  "proof_status": "trusted-under-owned-input-contract",
  "raw_runtime_values_redacted": true,
  "owned_pointer_redacted": true,
  "observed_bytes_redacted": true
}
```

Checks:

- `static-c1-identity`: OK, `match_int` resolved by `export-recovery`.
- `static-source-contract`: OK, signature `int match_int(substring_t *, int *result)`.
- `static-call-safety-contract`: OK, tier `SAFE-WITH-VALID-PTR`, x0/x1 require verified owned pointers.
- `kmalloc-owned-match-int-layout`: OK, allocated one owned kernel layout.
- `owned-match-int-layout-poke-peek`: OK, substring slot, decimal input, result slot, and canaries were written and read back.
- `match-int-return-contract`: OK, returned `0`.
- `match-int-result-layout-contract`: OK, stored signed `12345`, preserved the substring slot, preserved the input text, and preserved the result-slot canary.
- `kfree-owned-match-int-layout`: OK, cleanup succeeded.

Raw runtime slide, `match_int` runtime address, owned layout pointer, substring pointer, input pointer,
result pointer, and raw observed bytes were written only to private evidence and are not included in
this report.

Candidate selftest after proof: `pass=11 warn=1 fail=0`.

## Rollback

Rollback command:

```sh
python3 workspace/public/src/scripts/revalidation/native_init_flash.py \
  --from-native \
  --expect-sha256 ca978551aabe4b39563abaf529ccf2522054952d8b2ad852e632d26da88168cb \
  --expect-readback-sha256 ca978551aabe4b39563abaf529ccf2522054952d8b2ad852e632d26da88168cb \
  --expect-version v2321-usb-clean-identity-rodata \
  workspace/private/inputs/boot_images/boot_linux_v2321_usb_clean_identity_rodata.img
```

Result:

- Remote pushed image SHA matched v2321 SHA.
- Boot readback SHA matched v2321 SHA.
- Post-rollback `version/status` verification passed.
- Final standalone selftest confirmed `pass=11 warn=1 fail=0` with rc=0/status=ok.

## Conclusion

`match_int` is now live-proven under an owned `substring_t` plus owned `int *result` contract. The
proof confirms the intended wrapper was reached, parsed bounded decimal input `12345`, returned `0`,
stored signed `12345` in the owned result slot, preserved the input layout and canaries, and cleaned
up the owned allocation. It does not authorize arbitrary substring pointers, user pointers,
unterminated or unbounded parser state, failure paths, overflow cases, or mass calling.
