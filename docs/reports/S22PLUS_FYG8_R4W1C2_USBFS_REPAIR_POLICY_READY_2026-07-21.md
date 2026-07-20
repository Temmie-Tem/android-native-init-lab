# S22+ FYG8 R4W1-C2 USBFS Repair Policy Ready

Date: 2026-07-21 KST

## Verdict

`POST_REACTIVATION_HOST_GO_WAITING_FOR_FRESH_EXACT_LIVE_ACK`

The independently reviewed R4W1-C2 USBFS stabilization repair is committed,
exactly rebound, reactivated, and qualified. No device contact occurred during
review, policy replacement, or post-activation validation.

## Checkpoints

- Repair and incident record: `10d4412093c737f3dc443bf032296b42deb141c7`.
- Independent review record: `8142e9ca`.
- Policy-only reactivation: `1099b410382b182f0e7b47d5472b4412b7dc0b1f`.
- Corrected helper: size `111396`, SHA256
  `22cba55a924e9c56e5d245114357921ebefc73460a673e40e22c7ecf2e145172`.
- Corrected focused test: size `92470`, SHA256
  `9ba6da5d1e72e030e3648297491dc8c745b33607b0ea08a37478eb2787c9cbdb`.
- Exact installed clause: size `13442`, SHA256
  `cae20071b1f23b0e8e7944dd3632955c334cb438f54a5a7a73559ceafdb1fe3b`.
- Current `AGENTS.md` SHA256:
  `632b78b7a33cec047ec13d14e08877a27ba29127d278a828fab37ff4baacd539`.

The installed clause is byte-identical to the private reviewed clause. Its only
differences from the previous block are the corrected helper and test hashes.
All boot-only, rollback, one-shot, physical-continuity, taint, and fresh-
acknowledgement semantics remain unchanged.

## Post-Activation Qualification

The related standard-library suite passed `162/162`, covering the repaired live
helper, deterministic binding packet, shared Odin transition core, measured
USBFS identity, and frozen connected gate.

The exact helper then rehashed the complete artifact and source contract and
returned:

`PASS_R4W1C2_LIVE_GATE_OFFLINE_CHECK`

It reported the corrected helper/test identities, `policy.active=true`,
`candidate_consumed=false`, and `device_contact=false`, `device_writes=false`,
`reboot=false`, `download_transition=false`, `odin_transfer=false`, and
`flash=false`. The unique consumed-state file remains absent.

## Device State

The earlier authorized invocation ended before candidate consumption or
transfer. The exact Download endpoint was returned with Odin `--reboot` and no
AP argument. Read-only checks then proved exact FYG8 Android, completed boot,
stopped boot animation, orange state, and Magisk root. No candidate or rollback
image was transferred in that failed entry.

## Live Boundary

The previous acknowledgement does not carry across the failed invocation and
source/policy replacement. A new live entry requires the exact token:

`S22PLUS-FYG8-R4W1C2-MEASURED-USBFS-PHYSICAL-CONTINUITY-DIRECT-PID1-LIVE`

Supplying it starts a new Android preflight and renews the physical-continuity
attestation under the corrected clause. Later rollback and cleanup transfers
retain their separate immediate acknowledgement gates.
