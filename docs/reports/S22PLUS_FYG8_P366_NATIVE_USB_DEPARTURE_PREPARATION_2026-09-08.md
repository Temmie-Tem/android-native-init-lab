# S22+ P366 native USB departure preparation

## Scope and authority

P366 sequences observation of the exact outgoing native USB node before the
existing strict Download enumeration. It preserves P365's native module,
renderer and CONTROL behavior, including the ARM64 flag corrections. Necessary
D0/D1 preparation was preauthorized. This unit ends at fresh F1 code issuance;
the target contract still requires separately returned exact attended approval.
P365 and earlier candidates remain consumed. No unattended session is activated.

## Evidence and bounded change

P365 retained 46 authenticated preparation records, ten swap submissions and a
CONTROL ACK; the operator reported automatic Download without physical action.
The execute invocation then failed during initial USB inventory. Its inner
exception/path was not retained. Earlier snapshot 9's birth-stat ENOENT belongs
to the successfully observed post-candidate Download departure, not that later
failure. The [P365 report](S22PLUS_FYG8_P365_ARM64_AND_PERSISTENCE_PREPARATION_2026-09-08.md)
corrects the original close narrative without changing consumed run evidence.

P366 addresses the outgoing-node inventory race class; it does not claim to
have recovered P365's missing inner cause. Before CONTROL, existing exact
native tty/lane checks enclose a direct sysfs-to-usbfs binding capture. Original
busnum/devnum bytes are sealed with the existing raw capture writer and reread
from the immutable handle before parsing. Mapping and immutable node identity
must agree across capture; the binding receipt is sealed in the CONTROL intent.

After CONTROL dispatch, the host observes only the bound native usbfs node.
Positive absence permits the unchanged strict Odin enumeration to begin with
the remaining original 30-second budget. Absence alone proves neither Download
nor reboot causality. Download topology/ticket checks, exact rollback and final
health remain mandatory. No inventory error is ignored or resnapshotted by this
new capability; coordinate reuse, identity change and non-ENOENT errors stop.

A sealed terminal departure observation binds its raw evidence, control intent,
source and original deadline. Invalid/partial local records prohibit software
return proof and preserve the preauthorized physical rollback. Live backend
calls occur outside local-record exception handling, so a USB OSError cannot
be relabeled and retried as a local parsing failure.

Initial Odin-inventory failures now retain the same bounded exception taxonomy
with the distinct stage `initial-inventory-before-enumeration`. The original
strict stop behavior remains. Final-evidence diagnostic records retain their
existing stage; neither stage creates an Odin snapshot or transfer ticket.

## H0 validation

- Ten departure-helper tests cover stable-to-absent observation, expired/shared
  deadline, late absence, identity replacement, foreign-node departure,
  non-ENOENT errors, malformed coordinates and records, immutable raw capture,
  publication cuts and the departure/window join.
- Ten P366 lifecycle/ABI tests reuse the existing fixture corpus with actual
  generated P366 C, raw protocol replay and production state/result consumers.
  Four execute generated provider/module functions under real ARM64 syscalls;
  privileged module insertion and physical USB/ADB/Odin remain fixtures.
  Normal, preparation/child/ACK failures, CLOSED publication cuts, barrier I/O
  failure and same-journal recovery are exercised. The native helper differs
  from P365 only in namespace/run identity. A backend OSError is called once
  and propagates; neither CONTROL nor candidate is replayed during recovery.
- Two initial-inventory tests exercise real inventory propagation and sealed
  diagnostic publication before any Odin call, plus invalid-stage rejection.
- Existing Odin core 74 tests and P365 persistence three tests pass. Twenty
  touched/new Python files pass `py_compile`.

Normal lifecycle fixture state/result sizes are 34,898 / 39,323 bytes. These are
fixture sizes, not a prediction of live records. P365/P366 alone retain their
reviewed 64-KiB preparation/state allowance; other variants and journal bounds
remain unchanged. Physical recovery and uncontrolled kernel-call failure modes
remain outside host-only proof.

Preliminary independent review found raw-coordinate provenance, malformed local
record normalization and possible nested backend retry defects. All three were
corrected before final qualification. The coordinate parser now consumes its
sealed capture handle; focused tests cover the failure paths. An initial
`--audit-only` build invocation only found the not-yet-built result absent; it
created no build proof or device action. Source existence/hash checks then
froze the 122 build inputs before the actual A/B build.

Private evidence remains under `workspace/private/outputs/s22plus_fyg8_p366/`.
The current source freeze has SHA-256
`34a2c750db5eeae1d740b3a43facd62114115907f3359a56ab50ba864007595a`.
Native Image identity is 41,490,944 bytes, SHA-256
`1272863798d595ae9653a500429c64d929165b4f53610e3e3ef1af5154de45f5`;
it is derived by the exact same-length raw/IKCONFIG identity transform and
validated against the original P344 Image. No module/kernel behavior is changed.

## Scoped past-failure checks

Using the [existing checklist](../operations/S22PLUS_FYG8_PAST_FAILURE_CHECKLIST.md):

| Item | Current evidence |
| --- | --- |
| ABI | P366 real ARM64 provider/module tests and identity-only native helper comparison pass. |
| IO / SEMANTIC | Existing operation semantics retained; exact departures, errors and late deadlines remain distinct. |
| WIRE | Actual generated C, fixed CONTROL/ACK and immutable raw replay exercised. |
| PERSIST | Production normal/error/CLOSED writers and source-bound departure records exercised. |
| ROUTE | P366-only declaration; existing P365 path and unrelated record bounds retain regression coverage. |
| ARTIFACT | Source freeze and strict Image transform complete; final A/B/static joins recorded below when complete. |
| AUDIT | Historical P365 error attribution corrected; no consumed journal/state/raw content changed. |
| DISPLAY | P365/P361 renderer behavior retained; no new live visibility claim. |
| RETURN | Exact native absence and Download arrival remain separate; host tests do not prove autonomous failure recovery. |

A90 and S20+ received no command from this unit.

## Qualified artifacts and independent review

The A/B build is byte-identical. Each boot-only AP is 31,006,761 bytes, SHA-256
`9660c89ca67470040e67eef30a40f5ddce871d0e797c9a90d289c9e4e49ffa7c`.
The static ARM64 `/init` is 150,632 bytes, SHA-256
`45976a5f99e7ee712249ab7c0ef6ebc5a54df28c193ae05a8415e5ac566d87d0`.
The renderer is unchanged at 710,040 bytes, SHA-256
`5e66fea1f312aa81853aa499336a35bc397886b7fbdafb7421b8db8d69d68919`.
Build result SHA-256:
`24fca121e2e140289b03a8560e5f08740aba5220511ad0daa53e49ed6dfa07e6`.

Static qualification returned `PASS_P366_PROCESS_V2_CANDIDATE_STATIC_HOST_ONLY`;
its 63,765-byte record has SHA-256
`94e5efcf8ec88b70fbbb2d202c60d657f1633be005cd499e1694dc7b0d179bf0`.
All 122 frozen build inputs remained unchanged after the build.

Independent frozen boundary review and its separate artifact/static addendum
both returned PASS_GO with no blockers. They bind the new departure helper,
P366 registration/intent reader, generic runner/evidence/USB diagnostic changes,
current target/common contract and relevant tests, plus the actual artifact
joins. Private review SHA-256 values:

- Boundary review: `7a2da76daf06c5ed707a90a96888c79fb0bb8929ca616b4279d191efe2c3e7a9`.
- Artifact addendum: `85d562f474a13d709f988175c1bf6c8173a574199a6e8bc4d77219668ed36995`.

These reviews qualify the capability, not a live run or an unattended session.

The publishing entry rehearsed the real offline bundle, then published and
reopened ready1 manifest 5,054 bytes, SHA-256
`9cbb3a1483efce11e387a330109bfec10c6ec71ee6fe9ac2380e2300124bb5c9`.
Bundle SHA-256:
`f23b08424a959afacd54b69ca196f098aeee2e51bf2c6e6be97ae360c180d72f`.
This registration created no connected run and granted no F1 authority.

## Connected preparation

Fresh exact-target D0 returned `PASS_DEVICE_ACTION_D0_V2_CONNECTED_READ_ONLY`.
No D1 reboot was needed. Production `load_prepared` then reopened the real
bundle and 32,823-byte prepared record successfully; the scoped 64-KiB allowance
also covers this actual preparation above 32 KiB. No reboot, Odin invocation or
partition transfer occurred; F1 remains unauthorized until the fresh attended
approval code is returned.

Private run: `workspace/private/runs/device-action-f1-live-v2/p366-ready1-prepared-20260908-1/`.
Prepared SHA-256:
`0b1fc225d09cb11c2a29902e9db3b46128ede6e59b9bc111cc68c8daa510be85`.
D0 result: 3,261 bytes, SHA-256
`f49516060fa59ca37a3bb8deca49ed18008b35036c7647de41292bbf662579d2`.
The private output `connected-prepared-reopen.json` retains the reopen summary.
Implementation/qualification commit is `1fe09c04a5`. A90 and S20+ received no
command from this unit. No candidate or CONTROL was replayed.

## Consumed execution and recovery incident

The operator returned the fresh attended approval. One candidate transfer,
46 authenticated preparation records, ten swap submissions and one accepted
CONTROL were retained. Exact outgoing native USB absence and strict Download
enumeration were observed. The operator reported Download mode without physical
intervention; no P366 display appearance is inferred from that statement.

Publication then failed because the native-return consumer required a legacy
P318 topology record that the actual Samsung backend does not emit on this
path. The H0 fake backend had supplied that record and masked the producer /
consumer mismatch. No missing record was synthesized into the consumed run,
and the bounded native-return result remains unproved.

The first recovery observation stopped on two live Download endpoints, before
rollback intent. The bound S22+ paths subsequently disappeared. After the
operator reported reconnection and removal of the other device, a separately
reviewed private binding captured the exact, unique S22+ endpoint for recovery
only. Physical continuity remained lost; this did not upgrade candidate proof.
The first helper encountered the preserved old ambiguous endpoint history
before a transfer. A reviewed V2 helper used one fixed new recovery observation
context, preserving the original index, raw receipts and journal prefix. Fresh
ambiguity in that context remained fatal. The exact Magisk rollback transferred
once; its completion event is `2026-09-07T21:08:50.552132Z`.

Android returned, as also reported by the operator. ADB initially remained
offline. One bound host-side ADB reconnect restored the selected transport.
The next health-only resume captured fresh properties, root health and two
identical EOF outputs, but collided with an existing raw capture filename:
a new client started its capture sequence at zero. A reviewed private health
finalizer resumes above every existing capture ordinal, requires the fresh
Android boot identity to match the retained EOF evidence, and revalidates those
sealed captures. Its transfer and Download-wait methods always fail closed.
It sends no replacement observer capture command and preserves prior raw files.

Private recovery helpers, bindings, reviews and bounded test evidence are under
`workspace/private/outputs/s22plus_fyg8_p366/`. The V2 binding SHA-256 is
`96288164d93794d6928ed0282b48d4584fb8febacb6c772c6714ee147ed78a3a`;
its helper SHA-256 is
`8415ebc26c2e59622cb746a30e785b2a20bb672b8aa7206750af495c3ce9a8af`.
The final health helper SHA-256 is
`6230065ca84e4ef4d4fe7c142f55018fa345d8873d8885d5c1a35f99e1e7b4a7`.
Independent reviews cover the exact recovery-only binding and final-health-only
helper. Four V1 binding tests, three V2 history/context tests and two final
health tests passed; the health helper also passed `py_compile`. These are
incident-specific private recovery repairs, not a reusable production fix.
Original execution-critical source pins and consumed evidence remain intact.

The remaining H0 repair must exercise the actual Samsung backend producer with
the native-return consumer and cover resumed raw-capture allocation. No new
candidate, CONTROL, rollback transfer or reusable lane is authorized by this
report. A90 and S20+ received no command from this unit.

The first health finalizer stopped before fresh ADB reads because a Download
endpoint was again present on a separate host path. Host-only census retained
the original S22+ path in Android mode and the separate Download path. The
unchanged global absence condition was not weakened. This attempt issued no
partition transfer and did not close the journal.


## Earlier reporting disposition (before subsequent H0 closure)

Reporting is complete at the operator's direction, without another device
action or requiring another device to be disconnected. Candidate transfer and
exact Magisk rollback each occurred once. Rollback is complete and Android
return is observed; the subsequent host verification failure does not reverse
that device transition. The experiment is NO_PROOF, independently of recovery.

The original append-only journal has 15 records and remains
`ROLLBACK_FLASHED`. There is no canonical `CLOSED/19` transition and no terminal
`live-result.json`. Earlier properties/root-health captures and identical EOF
outputs remain evidence, but are not promoted to a completed final-health PASS.
No journal entry or structured success result is fabricated to make the report
appear closed. The ledger records this as a host observer failure after
completed rollback, with automated final health incomplete. Any future H0
repair is separate from this completed reporting unit.


## Subsequent H0 closure from fresh P367 D0

The operator subsequently authorized fresh connected preparation for P367.
Its existing read-only D0 profile passed, verifying the same Android boot as
P366's retained post-rollback properties, exact rooted FYG8, original boot and
supporting hashes, and global Download absence. Fresh observer bytes equal
both retained P366 EOF captures. No historical health failure is relabeled;
this new evidence satisfies the original final-health conditions.

A fixed private H0 finalizer reconstructs that evidence through the original
parsers and terminal validators. Four changed historical source files are
escrowed by their original exact hashes; all other source bindings remain
checked. Independent review verified the original 3,001 files, 38 fresh input
files, and the consumed recovery binding/approval/artifact/endpoint provenance.
The copy rehearsal preserved all 15 original journal records and produced
CLOSED/19 with NO_PROOF. The reviewed application then appended only the four
terminal records, updated final state/head and published the terminal result.
Original records, prepared/source pins and raw captures remain unchanged.

Canonical close publication: `2026-09-07T23:27:57.832691Z`.
Verdict: `NO_PROOF_F1_V2_CANDIDATE_ROLLED_BACK`, recovery_required=false.
The 45,265-byte live result has SHA-256
`0c639520c2156c8a28c2a45bf6deb810445e50fe8917d15aa3ed7c210a6e9e9f`.
Current timestamps describe final publication, not the earlier device return.
Candidate/CONTROL/rollback counts remain one each; native arrival proof and
lost physical continuity are not upgraded by healthy rollback.

Private closure evidence resides under
`workspace/private/outputs/s22plus_fyg8_p366/h0-close-from-p367-d0-v1/`.
Finalizer SHA-256: `7ab877005823a0c67bfd13202c211cfed3eac55d78db512eac6d5b7d159a4ffc`;
evidence binding SHA-256: `8cee4722f0d14ca2911d7f964dbd15f12fedb945e777b9c7ebf32282d900179d`.
Both independent review and supplemental recovery-origin review returned
PASS_GO. `py_compile`, copy rehearsal, original-input preservation checks and
the exact apply passed. H0 closure issued no device command or transfer;
P367 F1 approval remains separate. A90/S20+ received no command from this unit.

Documentation links, goal length, diff checks and append-only ledger preservation
pass. The new close row passes the existing parser with its fixed legacy prefix.
The full historical ledger audit still fails on pre-existing log row 547's
unknown evidence outcome; the unchanged HEAD baseline fails identically. That
unrelated historical taxonomy issue was not repaired or counted as a PASS.
