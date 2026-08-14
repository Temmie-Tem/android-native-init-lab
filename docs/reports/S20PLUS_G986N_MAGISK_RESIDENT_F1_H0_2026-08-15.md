# S20+ G986N Magisk resident F1 H0 design

Date: 2026-08-15

State: **PASS_S20PLUS_G986N_MAGISK_RESIDENT_ROOT_HEALTHY; CAPABILITY BINDING - ACTIVE**

## Objective

Keep the already-proved Magisk-patched boot installed on the exact S20+ after
healthy Android and `uid=0(root)` are proved. This is a new resident terminal
policy; it does not replay the completed bootstrap run.

## Fixed scope

- target: `SM-G986N` / `y2q` / `y2qksx` / `G986NKSS8IYC2`;
- candidate: boot-only TAR+MD5, SHA-256
  `1b33d098ea34b0396330cedf2e40c508704f1ba035b1f81e80a8526a637f1be2`;
- rollback: fixed stock boot-only TAR+MD5, SHA-256
  `48a11265a6730a6ab842b07f63cffe9cbdf1582a919b02abdaf1d2b9a2e0bd6b`;
- one candidate attempt, at most one stock rollback attempt, no replay;
- no recovery, vbmeta, vendor_boot, DTBO, BL, CP, CSC, userdata, or other
  partition payload.

## State machine

Prepare starts only from exact healthy root-absent Android, records an empty
Download baseline, performs the reviewed one-shot Android-to-Download
transition, and binds the exact endpoint, artifacts, tools, and shared guard.
The fresh approval prefix is
`S20PLUS-G986N-MAGISK-RESIDENT-F1-DATA-RESET-ACCEPTED:`; approval therefore
records acceptance that the first boot may require another recovery factory
reset and complete data loss.

Execute permits one fixed candidate transfer. Immediate exact Android/root
proof is terminal resident success with zero rollback. Otherwise the run
parks with the guard held and candidate replay forbidden. After an
operator-performed factory reset, `--finalize-resident` performs bounded health
and root reads only and succeeds only for the same serial/topology, a changed
boot ID, and Magisk root.
The terminal receipt calls this `late_boot_finalization`; it does not claim a
factory reset was machine-observed.

Failure recovery is not automatic. A two-step attended physical Download
handoff first records an empty endpoint baseline, then accepts one explicit
confirmation and permits only the fixed stock boot. If stock also requires a
factory reset, `--finalize-stock` performs exact health and root-absence reads
before releasing the guard. Pre-candidate abandonment performs no partition
transfer and requires healthy root-absent Android.

## Evidence and boundaries

Raw device identifiers and execution output remain under `workspace/private/`.
Public receipts use hashes. The S20 shared guard excludes routine and bootstrap
actions while resident state is unresolved. Success records S22+ and A90
command counts as zero. TWRP, native init, arbitrary Odin, arbitrary artifacts,
non-boot partitions, candidate replay, and unattended execution remain out of
scope.

## Dormant closure

- runner:
  `workspace/public/src/scripts/revalidation/s20plus_g986n_magisk_resident_f1.py`;
- reviewed dormant size: `41,140` bytes;
- reviewed dormant SHA-256:
  `3141fe6eea3fae7844715df3a6b3304e176cd608de446f382d570da643cb19e7`;
- reviewed dormant normalized SHA-256:
  `73388d9ba786ae9d73fe577ed5e5e202a1879de99ee5a947b051a0f76a0ebe88`;
- active size: `41,139` bytes;
- active SHA-256:
  `226842be1c5a32dd72e4af3f5d4e9936a2d389489ce09f1d904b56e955b99a22`;
- active normalized SHA-256:
  `d9a47bbc6627fbfc2f57ee18952c5d9524527c23978873ea541e04c7617c8fdc`;
- pinned bootstrap runner SHA-256:
  `11ca8aaef183e76c6eeec1a43e75b00bbc14e4b51650e3122c8f4bbdfdc8799f`.

Focused host-only tests pass 20/20 and the seven-module S20+ aggregate passes
155/155. Independent review returned `PASS_GO` with no unresolved finding.
`RESIDENT_F1_ACTIVE` is true. Activation created no run or approval; a fresh
connected prepare and the exact emitted approval remain required before any
candidate transfer.

A failure after the initial Download intent but before `prepared.json` is a
stranded conservative state. The runner retains the shared guard, sends no
candidate or rollback, and grants no retry or raw guard deletion. A separate
reviewed host repair would be required after manual normal-boot return.

## First resident execution

The fresh approval bound complete-data-loss acceptance and the exact prepared
manifest. Odin transferred the fixed patched boot candidate exactly once and
reported completion. Android did not return within the initial bounded window,
so the runner durably parked for late boot/factory-reset handling without
candidate replay or stock rollback.

After the operator returned the device to Android, the read-only resident
finalizer proved exact serial/topology continuity, a changed boot ID, and
`uid=0(root)` after five bounded attempts. It wrote terminal verdict
`PASS_S20PLUS_G986N_MAGISK_RESIDENT_ROOT_HEALTHY`, retained the patched boot,
recorded one candidate transfer and zero rollback transfers, and released the
shared guard. S22+, A90, and other-target command counts are zero. The private
terminal result SHA-256 is
`14dfeb9bae3567dc20da9719104bceb06bf64d1a14e7880775eeb8826602fdd2`;
the private candidate-result SHA-256 is
`0e3612192ba4f71c2a00603088a5dad1ad1784582621782aa01d2db5ebe456a1`.
