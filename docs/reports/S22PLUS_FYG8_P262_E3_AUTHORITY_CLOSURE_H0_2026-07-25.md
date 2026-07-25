# S22+ FYG8 P2.62 E3 authority closure correction (H0)

Date: 2026-07-25 KST
Tier: H0
Status: `PASS_P262_E3_AUTHORITY_CLOSURE_HOST_ONLY`;
`INDEPENDENT_REVIEW_GO`
Live authority: none

## Stop

The first P2.62 qualification attempt produced two clean Full-LTO builds with
six byte-identical linked artifacts and two byte-identical deterministic AP
archives. Promotion stopped before D0 because the independent candidate static
checker reported:

`E2 candidate /init contains forbidden authority`

No device was contacted and no F1 authority was created or consumed.

## Root Cause

P2.60 intentionally adds a bounded E3 ACM runtime that uses the exact
`/config/usb_gadget/g1` tree and `/dev/ttyGS0`. Its versioned source contract
pins the complete `/init` bytes, but its stock-rootfs adapter still delegated
authority classification to the P2.42 generic E2 rule. That historical rule
unconditionally rejects every configfs gadget and `ttyGS` string.

The candidate did not acquire an unexpected authority. The selected P2.60
host contract could not represent the authority that P2.60 itself requires.
Because the P2.60 stock-closure adapter is part of the candidate identity
preimage, changing it invalidates the first intent and both otherwise
reproducible builds for promotion.

## Correction

The correction is versioned at P2.60:

- one exact source-contract tuple enumerates every expected E3 configfs,
  `ttyGS0`, UDC-state, speed, and SSUSB-role string;
- all 67 slash-prefixed printable strings in the compiled init, including
  three pinned ELF byte artifacts, must equal one exact versioned set;
- sensitive hex, function-target, speed, role, and UDC-name string sets must
  match exactly, and the E3 runtime include has a fixed source SHA256;
- block-device, shell, and `sec_log_buf.ko` authority remain forbidden;
- the P2.60 override is installed only around its P2.57/P2.53/P2.42 closure
  call and restored in `finally`; and
- P2.42 and P2.58A semantics remain unchanged.

The exact init and child file identities, modes, ownership, link counts, ELF
entrypoints, run-ID cardinality, module closure, child token, and absence of an
`rdinit=` override retain their prior checks.

## Recurrence Guard

Focused tests execute these semantic cases:

1. the complete exact E3 authority set passes;
2. removing each required E3 authority string fails closed;
3. adding gadget `g2`, mass-storage, RNDIS, `ttyGS1`, or another sysfs path
   fails closed;
4. short `/x` and `/ab` paths fail closed;
5. lower/upper-case hex, alternate speed/role/UDC, and function-target
   mutations fail closed; and
6. adding `/dev/block` fails closed.

They also prove that the temporary selector/auditor override is active only
inside the P2.60 call, restores after exceptions and nested calls, and leaves
the P2.58A isolated closure unchanged.
Historical P2.42 and P2.58A tests run in the same validation set.

The first independent review returned `NO-GO`: the initial correction required
the expected strings but allowed unrelated new authority. The first repair
added exact path and sensitive-control sets; a follow-up found short-path and
uppercase-hex bypasses. Collecting printable runs from one byte, explicitly
pinning current slash artifacts, and recognizing both `0x` and `0X` candidates
closed those findings. Final read-only re-review returned `GO` with no
remaining finding in scope.

The build runbook now also records the unrelated malformed SSH-inline
completion-hook incident from the first A/B attempt. Future detached builds
must use the reviewed Python `shlex.join()` launcher and verify the live
launcher command line before allowing a long build to continue.

## Consequence

The first P2.62 intent, linked bundles, and AP archives are diagnostic evidence
only. They must not be promoted under the corrected source contract. After
this correction passes focused and independent review, P2.62 must derive a
fresh intent and repeat clean Full-LTO A/B qualification from that identity.
