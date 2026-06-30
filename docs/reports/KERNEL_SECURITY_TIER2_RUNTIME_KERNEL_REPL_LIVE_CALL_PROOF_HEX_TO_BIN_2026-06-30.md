# Kernel Security Tier-2 Runtime Kernel REPL - Live Call Proof: hex_to_bin

- Date: 2026-06-30
- Decision: `a90-repl-live-call-proof-hex_to_bin-pass`
- Scope: separately gated one-target live-call proof after the REPL epic close.
- Device action: yes, boot partition only through `native_init_flash.py`.
- Candidate image: `workspace/private/inputs/boot_images/boot_linux_tier2_repl_v1_repl.img`
- Candidate SHA256: `b846ae9f74d8ceb922bbcd854d78b6795ef833d61e38465d3cc474cb6f0dfb65`
- Rollback image: `workspace/private/inputs/boot_images/boot_linux_v2321_usb_clean_identity_rodata.img`
- Rollback SHA256: `ca978551aabe4b39563abaf529ccf2522054952d8b2ad852e632d26da88168cb`
- Private evidence: `workspace/private/runs/kernel/live-call-proof-hex-to-bin-20260630/proof/a90_repl_evidence.json`

## Static Gate

Target:

- `hex_to_bin`: `0xffffff800856a9dc`
- Resolution method: `export-recovery`
- Direct BL xrefs: `80`
- Shape: JOPP entry, leaf/no-BL, RET observed at offsets `0x18`, `0x50`, and `0x58`.
- Disasm contract: x0 is used as an 8-bit scalar character; no argument memory dereference and no tainted-argument call were observed. Numeric input returns `ch - '0'`; alpha input returns the decoded lower/upper hex nibble; invalid input returns 32-bit `-1`.
- Source signature: `include/linux/kernel.h:585`, `extern int hex_to_bin(char ch)`
- Source pointer contract: none; x0 is a scalar ASCII character.
- Call-safety tier: `SAFE-SCALAR`
- Required valid pointer args: none.

The target was not called with any host-supplied pointer. The proof calls only the verified
`hex_to_bin` entry with fixed scalar characters and checks a complete small case table covering
numeric, lower-case alpha, upper-case alpha, and invalid input.

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

## Live Proof

Command:

```sh
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 \
  workspace/public/src/scripts/revalidation/a90_repl.py call-proof hex_to_bin \
  --map workspace/private/runs/kernel/v2c-c2b-kallsyms-padding-fix/System.map \
  --image workspace/private/inputs/boot_images/boot_linux_tier2_repl_v1_repl.img \
  --source-root workspace/private/inputs/kernel_source/SM-A908N_KOR_12_Opensource/Kernel \
  --evidence-dir workspace/private/runs/kernel/live-call-proof-hex-to-bin-20260630/proof
```

Public result:

```json
{
  "decision": "a90-repl-live-call-proof-hex_to_bin-pass",
  "ok": true,
  "proof_status": "trusted-under-scalar-input-contract",
  "input_contract": "scalar ASCII character",
  "return_contract": "int == decoded hex nibble for 0-9/a-f/A-F; invalid character returns 32-bit -1",
  "raw_runtime_values_redacted": true
}
```

Case table:

| Case | Input | Expected | Observed |
| --- | --- | --- | --- |
| digit-zero | `0` | `0x0` | `0x0` |
| digit-nine | `9` | `0x9` | `0x9` |
| lower-a | `a` | `0xa` | `0xa` |
| upper-a | `A` | `0xa` | `0xa` |
| lower-f | `f` | `0xf` | `0xf` |
| upper-f | `F` | `0xf` | `0xf` |
| invalid-g | `g` | `0xffffffff` | `0xffffffff` |

Checks:

- `static-c1-identity`: OK, `hex_to_bin` resolved by `export-recovery`.
- `static-source-contract`: OK, signature `extern int hex_to_bin(char ch)`, no pointer args.
- `static-call-safety-contract`: OK, tier `SAFE-SCALAR`, no required pointer args.
- `hex-to-bin-scalar-case-table`: OK, all 7 scalar case calls returned the expected values.

Raw per-boot slide and target runtime address were written only to private evidence and are not
included in this report.

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

One final health read hit host-side serial capture noise without an END marker; a separate sequential
`version` retry and final `selftest` both passed.

## Conclusion

`hex_to_bin` is now live-proven under a scalar ASCII character contract. The proof confirms the
intended helper was reached, returned the expected numeric, lower/upper alpha, and invalid-character
values, required no pointer inputs, and left the device healthy. This does not authorize broader
parser state, arbitrary target calls, or mass calling. The device was rolled back to clean v2321 with
final `selftest fail=0`.
