# S20+ P1 PID1 witness: H0 acquisition and F1 integration

Tier: H0 only

Status: `HISTORICAL_H0_QUALIFICATION_P1_RUN_CLOSED_NO_PROOF`

## Outcome

The later run is closed with healthy resident rollback and NO_PROOF; see the
[run and recovery report](S20PLUS_G986N_P1_RUN_RECOVERY_2026-09-08.md).

The P1 witness now has a concrete same-boot acquisition path and a
profile of the complete P0 runtime. It reuses that runtime's isolated dependency
graph, session lock, append-only consumed-candidate registry, cage journals,
exact target/transfer checks and mandatory resident rollback. The private
profile is installed. Activation status is recorded above and enforced by the
P1 records and flags. No candidate transfer was performed for this H0 work.
Native PID1 execution, real candidate handoff and sufficient log retention remain
unproved. The existing second-build candidate artifacts are unchanged.

The previous bare-B0 connection omitted the P0 protections and returned a closure
incompatible with the engine's prepared-binding consumer. A fixed P1-only hook
now specializes the P0 module before it builds final maps and entrypoint wrappers;
ordinary P0 imports retain their behavior. The P1 closure preserves actual engine
artifact audits, physical-recovery evidence and the host cage-capability check.

## Corrections and evidence

- The retained publication helper completes short writes, retries interruption,
  rejects zero progress, preserves incomplete staging and verifies the published
  bytes. A 16-byte input reduced to 3-byte writes now publishes all 16 bytes;
  failure after the first 3 bytes produces no success receipt.
- Acquisition uses the existing raw owner. Both original bounded streams and the
  acquisition result are durable before framing or attestation. A partial tail
  or malformed record remains in the original file. Consumer schema v4 verifies
  the raw size/digest and derives its prefix directly, eliminating the separate
  unbound-prefix path.
- The only new read is fixed stock toybox `timeout -s KILL 5 head -n 65536
  /dev/kmsg`, under the inherited exact-serial ADB lease and private raw capture.
  Host bounds are 15 seconds, 8 MiB stdout and 4096 bytes stderr. The target's
  extracted toybox accepts these applets; an offline QEMU timeout fixture returns
  137. A remote timeout is a bounded prefix, never drain proof.
- Qualified serial/topology/target properties and the candidate boot ID must
  agree before and after capture. Reader handles must name the fixed raw files.
  Another device appearing is not part of this S20 capture identity.
- Positive observations are rederived from the stored candidate transfer,
  artifact closure, acquisition receipt, boot binding, attestation and raw file.
  Reader and consumer function identities are fenced after exact source load.
- A qualified Android observation retains its serial for mandatory rollback.
  Failed acquisition, publication, unexpected recovery-adb and reporting cuts
  remain recovery-only; neither capture nor candidate is replayed. Recovery CLI
  dispatch does not consult the observation-activation gate.

The first-log predicate is conditional controlled-experiment evidence. Kmsg
sequence/facility checks constrain ordering; they do not authenticate the text's
PID/namespace values or prove the nonexistence of a silent process. The reviewed
producer/artifact path and stated threat model supply the remaining attribution
conditions. A matching record with a missing prefix or sequence gap is rejected.
FIFO eviction can remove sequence zero while retaining the witness; retention
is not inferred from the witness alone.

## Validation

- P1 witness/parser/fault-harness suite: 88 tests passed.
- P1 acquisition/profile/integration suite: 28 tests passed.
- Existing P0 owner and USB suites: 95 tests passed.
- Touched Python `py_compile`, scoped whitespace checks and repository boundary
  check passed. The goal remains below its 900-line limit.
- Real P1 `--validate-host`: `PASS_P1_HOST_CLOSURE_ONLY`, including inherited
  archive and host cage-capability checks.
- The P1 suite cross-compiles the existing producer, checks its AArch64 entry and
  syscall surface, runs the QEMU self-test and executes fault-injected production
  control flow. Source-comment corrections reproduce identical compiled candidate bytes.

Integration fixtures run the installed engine's prepared-closure reader,
execute and resume paths with a real temporary session flock and real bounded
raw subprocess capture. Device health, Odin and cgroup qualification are explicit
fixture boundaries. Successful acquisition joins rollback; acquisition failure,
publication failure and an observation reporting cut keep raw evidence and never
retry the candidate or capture. These tests do not prove physical device behavior.

## Review and activation scope

Independent review covers the P1 owner, reader, consumer, P0 fixed hook/read
extension, producer/builder and tests, plus the target contract and common F1
requirements. The H0 review does not activate a device capability. The next
execution still requires P1-specific reviewed mechanical activation and records,
fresh attended preparation, its exact approval, and the unchanged rollback/final
health conditions. Other targets and their dirty work remain outside this unit.

The changed H0 integration received independent `PASS_GO_H0` with no remaining
actionable finding, reviewer device contacts/writes 0/0. The reviewer inspected
the actual code and integration fixtures and used the executed parent test
results; it did not rerun unchanged tests or repeat a full producer/builder
capability review. This result is not the P1 activation record or live PID1 proof.
The private H0 review receipt binds the exact reviewed source identities.
