# A90 V3403 F1 Closed No-Proof

Date: 2026-07-31 KST

Status: `NO_PROOF_F1_V2_CANDIDATE_ROLLED_BACK`

## Scope

This report records one approved A90 V3403 boot-only candidate transfer, the
bounded Debian PID1 observation, one mandatory exact V2321 rollback, and the
read-only recovery of final-health reporting.

Raw device and host evidence remains under `workspace/private/`. This report
contains no device serial, USB identity, filesystem UUID, network address,
credential, or raw console log.

## Exact transaction

- Run ID: `a90-v3403-debian-f1-20260730-03`
- Prepared-manifest SHA256:
  `38f1b16a90d1c48c2b9ba3b6ea372772c644027a0a4030850148eff75d813177`
- Approval binding SHA256:
  `066fa5330f77a648c47e60db79f83b6112e685920eeb5fc63b09d85e254fbf50`
- V3403 candidate SHA256:
  `2b2b458b4f021825e0567c239ef86996d482a7b55baccc4e4a8cd9e670a2e2b9`
- Exact V2321 rollback SHA256:
  `ca978551aabe4b39563abaf529ccf2522054952d8b2ad852e632d26da88168cb`
- Rootfs SHA256:
  `36d49b9daf29166650482810a5c228075b9704692a593a1b6250d9610604ddde`

The approval is consumed and cannot authorize another candidate attempt.

## Rootfs staging

The topology-bound host NCM gate selected the NCM function under the same USB
parent as the manifest-bound A90 ACM bridge. The absent-only adapter then:

1. reserved the exact run-owned staging directory;
2. transferred the exact 2 GiB rootfs;
3. verified device-side size and SHA256;
4. published it with hard-link no-clobber semantics;
5. removed the staging directory; and
6. closed its ten-record journal.

Immediately before candidate intent, the orchestrator reverified that the
published source was a regular file with the exact size and SHA256 and that
the handoff work path was absent.

## Candidate and observation

The checked helper transferred V3403 to `boot` exactly once. Local validation,
recovery endpoint selection, payload transfer, boot write, and boot readback
all completed. V3403 returned exact version `0.11.159`, build
`v3403-d3-immutable-handoff`, and a zero-failure selftest.

The Debian observation did not reach the handoff. Console/menu input
interleaved with the first candidate-side remote source-preflight request and
corrupted that framed command. The observation result contains no accepted
source-preflight, handoff, or SSH phase, so the switch-root handoff command was
never sent. There is therefore no Debian PID1 proof, no accepted substitute
evidence, and no candidate replay. The bounded return check subsequently
reconfirmed exact V3403 version/build and zero-failure selftest.

## Rollback and recovery closure

The mandatory exact V2321 rollback ran once. Its helper completed local image
validation, recovery endpoint selection, payload transfer, boot write, boot
readback, and returned success. The durable journal recorded
`rollback-flashed` with rollback transfer count `1`.

The first final-health sequence then lost the framed `selftest` end marker
after a successful V2321 status response. The initial runner stopped at the
durable `rollback-flashed` state. It did not repeat the candidate or rollback.

The manifest-bound `--recover-approved-rollback` path reopened the consumed
approval binding. Because the journal already contained `rollback-flashed`,
this path did not invoke the rollback helper. It performed only read-only
health checks and proved:

- exact V2321 version and build;
- selftest failure count zero;
- pstore entry count zero; and
- continuity of the exact A90 bridge.

It appended `rollback-boot-ready`, `health-verified`, and `closed`, then wrote
the structured result.

## Evidence closure

Private evidence is under:

`workspace/private/runs/server-distro/a90-v3403-debian-f1-20260730-03/`

The F1 append-only journal has 14 records, sequence `0..13`, and ends in
`CLOSED`. Its structured result records:

- candidate transfer count: `1`;
- rollback transfer count: `1`;
- candidate replay: `false`;
- candidate transfer uncertainty: `false`;
- Debian PID1 proven: `false`; and
- final health restored: `true`.

The structured result SHA256 is:

`f872141bbc337b650ca77b6fb17439b8e600e69d7e33ec5419b1ed207702dec8`

The canonical timeline SHA256 is:

`06c762fd3e40e7604c2a0d665e4b91317daba53ae3baa0411bfc344c24ee6fbf`

The timeline contains the canonical eight events in order. Raw transfer,
bridge, and observation logs remain private.

## Disposition

The transaction is closed healthy/no-proof. Internal userdata was not
mounted, written, formatted, or flashed. The only partition payloads were the
approved candidate and mandatory rollback writes to `boot`.

Do not replay this run, reuse its approval, or invoke its rollback again. The
host-only diagnosis and command/menu serialization remediation is recorded in
`A90_V3403_F1_OBSERVATION_CHANNEL_H0_2026-07-31.md`. Any later candidate
experiment requires a fresh run, fresh connected preflight, immutable
manifest, and fresh exact approval.
