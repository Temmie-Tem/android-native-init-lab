# S22+ FYG8 P2.61 E3 ACM observer implementation (H0)

Date: 2026-07-25 KST
Tier: H0
Status: `PASS_P261_E3_ACM_OBSERVER_IMPLEMENTATION_HOST_ONLY`;
`INDEPENDENT_REVIEW_GO`
Live authority: none

## Result

P2.61 implements the P2.60 E3 contract without building an image or contacting
a device:

- the committed P2.60 candidate contract preserves the exact P2.58A 60-module
  prefix, adds E3 stages `0x88..0x8f`, and moves terminal success to `0x90`;
- the run ID derives one 37-byte USB serial and one exact 49-byte banner;
- Process v2 accepts an optional typed `exact_cdc_acm_banner_v1` observer and
  re-derives it from the selected source contract;
- the live adapter arms device-scoped ModemManager inhibition before Download,
  selects only the exact topology/VID/PID/serial/driver/interface endpoint,
  opens it raw without a flush, requires `TIOCEXCL`, and reads exact bytes plus
  a 250 ms no-extra-byte settle;
- raw bytes are fsynced before the bound JSON receipt;
- resume reopens the raw, baseline, Download-departure, guard, topology, and
  approval/candidate bindings without repeating candidate observation; and
- E3 PASS requires candidate completion, Download departure, exact ACM bytes,
  retained terminal success, rollback, and final health.

Retained-only and ACM-only outcomes are named diagnostics. A missing or
malformed receipt becomes `interrupted-before-receipt` and proceeds to the
already authorized rollback. Manifests without a candidate observer retain
their previous verdict semantics.

Host core and live adapter versions advance to
`device-action-f1-v2-host-core-3` and `device-action-f1-live-v2-2`.
Historical closed runs remain evidence under their original versions.

## Candidate Contract Evidence

The source contract reports:

- 89 descriptor steps and terminal stage `0x90`;
- byte-identical P2.58A module plan;
- raw gadget TTY with no flush and one-shot UDC bind;
- two byte-identical static AArch64 links;
- linked userspace size `71816`;
- linked userspace SHA256
  `68f65212623b27fa378172e177afb5714eca4cf062809b68a0c8de4992edb9bd`;
- generated runtime SHA256
  `592cd4836f4595031b09c7509910013794d7514737d1111609fd13b59d289c69`;
- generated checkpoint SHA256
  `fe78924942a53161611d6c03441a35ccd3221c3319a1f6228400feb55f036fb7`;
  and
- `PASS_P260_E3_ACM_IMPLEMENTATION_HOST_ONLY`.

No fresh candidate intent, final patch, kernel, AP archive, Process v2
manifest, target binding, or approval was created in P2.61.

## Recurrence Guards

The host fixtures execute the boundaries that previously escaped string-only
checks:

- a real pty proves a prequeued banner survives `TCSANOW` raw setup;
- split/delayed bytes are reassembled, while an extra byte is rejected;
- `TIOCEXCL` failure, wrong serial, UID mismatch, malformed peers, and
  unrelated ACM endpoints cannot accept;
- active, inactive, refused, and handshake-fault ModemManager paths are
  bounded, and guard-receipt failure releases the inhibition child;
- baseline, departure, guard, topology, raw, receipt, approval, bundle,
  manifest, and candidate AP identities are revalidated;
- self-consistent but semantically false supporting evidence is rejected;
- malformed non-string classifications cannot escape as parser exceptions;
- observer faults after transfer close as no-proof only after verified
  rollback;
- E3 observer-arm, Download-request, and Odin local-parse aborts remain
  reportable; and
- accepted, retained-only, ACM-only, neither, impossible continuity, and
  receipt-resume paths are covered while legacy retained-only tests pass.

Focused integration validation passed 112 tests. The final observer/live/core
subset passed 78 tests. `py_compile` and `git diff --check` passed.

## Independent Review

A GPT-5.6-sol xhigh read-only review first returned `NO-GO` for:

1. supporting receipt contents not being semantically revalidated;
2. ModemManager being rechecked after the TTY open;
3. inhibition cleanup beginning after guard-receipt persistence;
4. unrelated ACM entries aborting selection;
5. malformed classification escaping as `TypeError`; and
6. a post-`Popen` inhibition-handshake cleanup gap.

All were repaired and mutation-tested. The same reviewer returned `GO` with no
remaining HIGH/MEDIUM finding.

The persistent Claude Opus session was reused without
`--no-session-persistence`. Its first post-implementation pass found two state
integration bugs: receipt-less observer faults stored Odin departure instead
of durable departure, and pre-candidate E3 aborts incorrectly required
observer state. Both were repaired with end-to-end execute/rollback/close and
E3 abort tests. The follow-up returned `GO`.

Claude usage moved from current-session `0%` / weekly `57%` to
current-session `40%` / weekly `60%`. The substantive and follow-up reviews
used the latest `opus` alias at `xhigh`; FAST mode was not used.

## Proof Boundary

P2.61 proves source-contract and host-observer semantics only. It does not
prove:

- that a future E3 kernel, ramdisk, or AP is reproducible;
- candidate USB enumeration or the host seeing an ACM endpoint;
- ModemManager UID stability across actual re-enumeration;
- exclusive absence of every possible privileged competing opener;
- exact wire bytes on hardware;
- retained E3 terminal success; or
- rollback/final health for a future E3 candidate.

The remaining review warnings are false-negative risks: a ModemManager restart,
an already-open privileged client, advisory `udevadm` stderr, and partial-byte
classification. None can create PASS without exact candidate-bound bytes and
retained terminal acceptance.

## Next Bounded Unit

P2.62 is the final candidate qualification unit:

1. derive one fresh P2.60 intent and final patch;
2. pass the cheap exact two-link userspace/entrypoint closure;
3. run two clean Full-LTO builds and require all six artifacts byte-identical;
4. run linked audits and deterministic boot-only packaging twice;
5. generate the private E3 Process v2 manifest with the source-derived
   candidate observer;
6. pass offline promotion and one final independent closure review; and
7. run connected D0, then stop at a fresh exact F1 approval token.

P2.62 grants no live authority by itself.
