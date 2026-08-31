# S20+ G986N recovery T0 execution-closure H0 record

Date: 2026-08-31
Target: `SM-G986N` / `y2q` / `y2qksx` / `G986NKSS8IYC2`
Tier: H0 only
Result: **HOST_CLOSURE_PASS; LIVE_AUTHORITY_FALSE; INDEPENDENT_REVIEW_PENDING**

## Scope

This unit prepares the next review boundary for the exact-stock-derived
recovery ADB canary T0. It performed host-only file inspection, parser and
state-machine tests, and process design. It issued no ADB, `su`, USB, reboot,
Download, Odin transfer, or device command. It wrote no partition and changed
no device or Android state. S22+, A90, and every other target received zero
commands.

The common and S20+ contracts still forbid recovery block access and recovery
partition transfers. None of the new files activates an exception. Both new
CLIs return a fixed stop verdict for `--connected` before artifact access. The
T0 runner has no device execution backend.

## Fixed stock-recovery digest profile

`workspace/public/src/scripts/revalidation/s20plus_g986n_recovery_digest_profile_h0.py`
freezes one no-input privileged read candidate for later review. Its fixed
script:

- rechecks UID/GID zero, Magisk `30.7:MAGISK:R` / `30700`, the Magisk SELinux
  context, enforcing SELinux, and stock PID 1 identity;
- resolves only `/dev/block/by-name/recovery`;
- requires `/dev/block/by-name/recovery` to resolve exactly to the direct block
  node `/dev/block/sda24`;
- requires exactly 82,694,144 bytes;
- computes SHA-256 with the fixed Android `sha256sum` executable;
- requires the exact stock digest
  `dd797bc0a462d2486ff71c020e89d1137df46299374e48855012e36e86f97e0e`;
- emits only the ten canonical fixed fields and never returns the raw block
path.

The exact-node expectation is derived from the 12,156-byte
`Y2Q_USA_SINGLE.pit` at SHA-256
`06f87a8aba5ac95c4784f034816d2744c246af6067452b0a3acd2b63c5763b99`.
Its `RECOVERY` entry is index 23, identifier 24, block offset 171,027, and
20,189 blocks; 20,189 times 4,096 equals the exact 82,694,144-byte recovery
image size. The `/dev/block/sda24` mapping is an H0 derivation, not a live
observation. A different live resolution stops rather than widening the node
grammar.

There is no caller path, shell fragment, executable, property, or expected
digest. The module imports no subprocess facility. Its parser accepts only the
exact 262-byte canonical stdout with empty stderr and return code zero.

The focused hostile suite passes 16/16. It rejects every changed field,
nonzero return, stderr, oversized output, bad types including bool-as-int,
extra/reordered/CRLF/truncated fields, wrong size/digest, execution imports,
and write/control primitives. Source receipts are:

| File | Size | SHA-256 |
|---|---:|---|
| digest profile | 9,509 | `9377e58d3717e0fa96826210815b09df20bf2ba62a70c85c896f5a6fdf68fded` |
| focused tests | 10,824 | `66f2266083bcb212c04deebd1290845f721723a13bfc5d299d686d49b6ffb9c0` |

This is still a proposed privileged partition read and therefore remains
forbidden live until the common and target contracts explicitly define and
activate it.

## Dormant T0 runner closure

`workspace/public/src/scripts/revalidation/s20plus_g986n_recovery_canary_t0_runner_h0.py`
implements only H0 validation and pure execution modeling. Its host validator
re-read and passed all of these boundaries:

- exact Odin4 regular file, size, and SHA-256;
- candidate and rollback direct single-link, non-group/world-writable APs;
- appended Odin MD5 matching the tar bytes;
- exactly one regular `recovery.img.lz4` member per AP;
- exact member name, type, size, SHA-256, mode, uid/gid, and mtime;
- no VBMeta or other archive member;
- exact builder, fixed recovery-digest profile, and private manifest receipts;
- manifest target, H0/review status, safety flags, component receipts, exact
  rollback identity, and canary marker semantics.

The validator returned
`PASS_S20PLUS_G986N_RECOVERY_CANARY_T0_HOST_CLOSURE` with
`live_authorized=false`.

The candidate command model is fixed to
`odin4 -a CANDIDATE_AP -d BOUND_USBFS` without automatic reboot. A completed
transfer may therefore be followed by one separately journaled attended direct
recovery boot. The rollback model is fixed to
`odin4 --reboot -a ROLLBACK_AP -d BOUND_USBFS`. Neither artifact nor partition
is caller-selectable, and no endpoint is exposed on the CLI.

The fixed recovery observer checks the exact target/build, a new boot ID,
recovery ADB properties, and marker SHA-256
`5aafd7ca6918bf82aef0b7de62346d8de1b17bb0c9ececafa15978cfae2c87b0`.
Its output parser rejects extra, malformed, or mismatched fields.

The modeled durable journal has separate Download intents/arrivals, candidate
intent/result, optional physical recovery-boot intent, candidate observation,
rollback intents/arrival/result, final health, and terminal. Once either
transfer intent exists, that attempt is consumed. A missing result routes to a
result finalizer and never back to transfer. Candidate uncertainty skips the
canary boot and routes only toward exact-stock rollback.

The focused runner suite passes 19/19. It exercises the real private closure,
synthetic valid and hostile recovery-only tar/MD5 cases, symlink/hardlink/
writable-file rejection, strict JSON duplicate rejection, all observer fields,
endpoint grammar, every valid journal prefix, gaps and foreign nodes, both
intent-only cuts, no-replay decisions, dormant connected mode, and the absence
of a device backend. Source receipts are:

| File | Size | SHA-256 |
|---|---:|---|
| dormant T0 runner | 30,909 | `3eb7cd148477c4e28d8bf1102a22f4eeb2f7a92bc99199fdd084af1dde5cd7df` |
| focused tests | 18,477 | `994fbb14f50d3377cda60e3c52cbfdb16cd9585109febd03167a70e0c143f479` |

## Proposed process

The non-binding process review input is
`docs/operations/targets/S20PLUS_G986N_RECOVERY_ONLY_T0_PROCESS_PROPOSED_V1.md`,
13,295 bytes at SHA-256
`1273fdf266f2e0aa9ea0a840f0eead81046a64fb78aa08bf73df3c5a9f9dbbc4`.
It defines the exact effect ceiling, entry gates, durable journal, physical
handoffs, success/NO_PROOF/RECOVERY_PENDING taxonomy, mandatory stock rollback,
final recovery digest, and activation checklist. Its status is
`PROPOSED_NOT_ACTIVE`; it cannot override `AGENTS.md`, the risk tiers, or the
binding S20+ contract.

## Remaining gates

The following remain deliberately incomplete:

1. independently reviewed common-boundary, risk-tier, and S20+ target-contract
   amendments for the exact read and two recovery-only transfers;
2. a concrete connected owner with exact ADB/USB selectors, private durable
   evidence owner, streaming Odin backend, output classifier, physical handoff,
   resume/finalizer paths, and hostile tests;
3. independent exact-byte review of that complete execution closure;
4. mechanical activation plus a fresh attended prepared binding and approval;
5. live demonstration that exact-stock recovery rollback and final healthy
   Android are usable.

The exact rollback bytes are present and host-validated, but the recovery-only
rollback path is still not demonstrated live. T1 remains ineligible for device
transfer. The next bounded unit is the concrete dormant connected owner, not a
device write.
