# Kernel Security Tier-2 Runtime Kernel REPL - Live Call Proof Attempt: get_ddr_revision_id_1

- Date: 2026-06-30
- Decision: `a90-repl-live-call-proof-get_ddr_revision_id_1-fail-contract-mismatch`
- Scope: one-target live-call proof attempt after the `get_ddr_total_density` pass.
- Device action: yes, boot partition only through `native_init_flash.py`.
- Candidate image: `workspace/private/inputs/boot_images/boot_linux_tier2_repl_v1_repl.img`
- Candidate SHA256: `b846ae9f74d8ceb922bbcd854d78b6795ef833d61e38465d3cc474cb6f0dfb65`
- Rollback image: `workspace/private/inputs/boot_images/boot_linux_v2321_usb_clean_identity_rodata.img`
- Rollback SHA256: `ca978551aabe4b39563abaf529ccf2522054952d8b2ad852e632d26da88168cb`
- Promotion: none. `get_ddr_revision_id_1` remains DENY/not seeded in the current tree.

## Candidate Selection

This unit tested whether another Samsung SMEM DDR getter could follow the already-proven
`get_ddr_total_density` pattern. `get_ddr_revision_id_1` looked attractive because static C1 identity
was verified and the public header declares a no-argument `uint8_t` getter:

- Symbol: `get_ddr_revision_id_1`
- Static link address: `0xffffff80086ef82c`
- Resolution method: `disasm-signature+xref+map`
- Direct BL xrefs: `1`
- Source signature: `include/linux/samsung/sec_smem.h:196`,
  `extern uint8_t get_ddr_revision_id_1(void)`
- Next symbol boundary: `get_ddr_revision_id_2` at `+0xc0`

The intended proof contract was: no arguments, read-only Samsung SMEM access, no returned pointer,
and repeated calls return a stable raw `uint8_t` value.

## Static Gate

The temporary proof harness gated the following words before the live call:

- `0xd100c3ff` stack allocation.
- `0x528010c1` Samsung SMEM item ID setup.
- `0x910003e2` stack buffer argument setup.
- `0x97fe8924` call to `qcom_smem_get`.
- `0xf94003e8` SMEM size load.
- `0xaa0003f3` returned pointer save.
- `0xb9401268` revision source word load.
- `0x53087d00` revision return transform.
- `0x2a1f03e0` NULL/error return path.
- `0xd65f03c0` return.
- `0xd503201f` padding NOP.
- `0x00be7bad` next-entry guard before `get_ddr_revision_id_2`.

The disassembly decoded the return path as:

```text
ldr w8, [x19, #16]
lsr w0, w8, #8
```

That is not a byte mask. It shifts the SMEM word right by 8 and returns the resulting raw word in
`w0`.

## Host Validation

Before the live attempt, the temporary uncommitted harness passed:

- `py_compile` for `a90_repl.py` and `tests/test_a90_repl.py`.
- Focused classification/source/fake-transport tests.
- Full `tests.test_a90_repl`: `Ran 146 tests`, `OK`.
- CLI classify with the temporary seed: `SAFE-SCALAR`, C1 verified by
  `disasm-signature+xref+map`.

After the live mismatch, the temporary seed/proof target was removed. In the committed/current tree,
`call-safety-classify get_ddr_revision_id_1` returns `DENY` because the symbol is not in the vetted
seed whitelist.

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

Candidate flash result:

- Remote pushed image SHA matched candidate SHA.
- Boot readback SHA matched candidate SHA.
- Post-flash helper `version/status` verification passed.
- A transient serial parse fragment was cleared by restarting the serial bridge.
- Candidate standalone selftest returned `pass=11 warn=1 fail=0`.
- REPL selftest completed and returned `a90-repl-v2a1-selftest-pass`.

## Live Attempt Result

The bounded live call reached the intended function and returned through the REPL, but the raw return
violated the pre-declared raw `uint8_t` contract:

```text
ReplError: get_ddr_revision_id_1() did not return a uint8_t DDR revision-id field in proof call 1: 0x60106
```

Interpretation:

- C1 identity and no-argument call routing were correct.
- The live call did not oops or hang.
- The raw return contract was wrong. The binary returns the shifted word `w8 >> 8`, not a byte-masked
  `uint8_t` value.
- Because the return semantics do not match the intended source-level contract, the target was not
  promoted and no function map row was added.

Candidate selftest after the failed attempt returned `pass=11 warn=1 fail=0`.

## Rollback

Rollback result:

- v2321 rollback image remote SHA matched.
- Boot readback SHA matched rollback SHA.
- Post-rollback helper `version/status` verification passed.
- A transient final serial parse fragment was cleared by restarting the serial bridge.
- Final standalone `version` confirmed `v2321-usb-clean-identity-rodata`.
- Final standalone selftest returned `pass=11 warn=1 fail=0`.

## Parked Follow-Up

Do not promote `get_ddr_revision_id_1` under the original raw `uint8_t` contract. A future unit can
revisit the DDR revision getters only after defining a source-to-binary semantic contract that
accounts for the `lsr w0, w8, #8` return transform, for example by proving an explicitly shifted
SMEM revision-register value rather than a byte-sized C return. Until then it stays DENY/not seeded.
