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
