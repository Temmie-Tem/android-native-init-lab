# V3437 S22+ Ramoops Positive-Control Live-Gate Implementation

## Verdict

`HOST_SOURCE_READY_POLICY_INERT_NO_LIVE`.

V3437 implements the resumable host orchestrator specified by V3436 and stages
two inert policy drafts. It does not modify `AGENTS.md`; therefore every
device-facing mode remains blocked before ADB/Odin access.

Helper:

```text
workspace/public/src/scripts/revalidation/s22plus_v3437_ramoops_positive_control_live_gate.py
```

## Current Modes

Usable now without device contact:

```text
--offline-check
--print-plan
```

Present but policy-gated:

```text
--dry-run
--live-session
--resume-after-manual-recovery
--restore-from-android
--restore-from-download
```

`--dry-run`, `--live-session`, and resume require both independent policy
clauses. `--live-session`, resume, and restore-only modes also require the
independent restore acknowledgement because each can reach a stock-DTBO write.

## Policy Split

Inert drafts:

```text
docs/operations/S22PLUS_V3437_RAMOOPS_DTBO_MAINTENANCE_AGENTS_EXCEPTION_DRAFT_2026-07-11.md
docs/operations/S22PLUS_V3437_RAMOOPS_INTENTIONAL_PANIC_AGENTS_EXCEPTION_DRAFT_2026-07-11.md
```

The DTBO policy covers exactly one candidate DTBO flash and one stock rollback.
It explicitly forbids panic. The panic policy covers exactly one `S22RPC1`
marker sequence and one `sysrq-trigger-c`; it authorizes no partition write.

The helper requires separate tokens:

```text
S22PLUS-V3437-RAMOOPS-DTBO-MAINTENANCE
S22PLUS-V3437-RAMOOPS-INTENTIONAL-PANIC
S22PLUS-V3437-RAMOOPS-STOCK-DTBO-RESTORE
```

Token knowledge alone is insufficient. Exact active policy markers and artifact
hashes must also be present in `AGENTS.md`. Each policy additionally requires
an `=ACTIVE` sentinel that must be removed or changed when the exception is
consumed, preventing a retained consumed/retired block from being reused.

## Durable Session Model

Each future run has:

```text
session.json   contract-bound state and run ID
timeline.json  only {"events":[{"name","timestamp_utc"}]}
baseline/      pre-marker negative-control files
evidence/      duplicate pstore reads and hashes
classification.json
```

Session and timeline updates use temp-file write, file `fsync`, atomic rename,
and directory `fsync`. The session is bound to the V3436 contract and candidate
DTBO identities. Resume rejects an unknown schema, state, run ID, contract, or
candidate hash.

## Live Sequence

```text
stock Android preflight
  -> candidate DTBO transfer
  -> patched Android/root return
  -> exact live DT + ramoops parameter + backend proof
  -> fresh-run negative control
  -> PREPANIC_KMSG + PREPANIC_PMSG
  -> exactly one TRIGGER_KMSG + sysrq panic
  -> require ADB loss
  -> patched Android early-root return or attended manual recovery
  -> duplicate pstore reads, compare, hash, fsync
  -> classify
  -> stock DTBO rollback
  -> stock Android/root/hash/status/stability proof
```

Any failure before a successful panic transition attempts immediate stock DTBO
rollback through one pinned Android or Odin transport. After panic, the helper
does not auto-rollback over unread evidence. If automatic patched-Android return
fails, it persists `RECOVERY_WAIT` and exits for
`--resume-after-manual-recovery`.

An explicit recovery override may abandon evidence and restore stock DTBO. That
path is permanently classified
`NO_PROOF_EVIDENCE_ABANDONED_FOR_RECOVERY`; it cannot become PASS.

## Evidence Handling

- pstore filenames are allowlisted before reads;
- each file is read twice without deletion;
- filename sets and bytes must match;
- every payload is stored and SHA256 summarized;
- collection retries at most twice;
- only V3436's run-bound classifier decides PASS/PARTIAL/NO_PROOF/FAIL;
- pmsg-only remains PARTIAL.

## Current Gate

```text
offline-check: PASS
dtbo_active: false
panic_active: false
device_action: 0
```

V3437 is source-ready but not live-ready until both inert drafts are reviewed,
explicitly approved, and promoted to active `AGENTS.md` exceptions. After
promotion, run offline-check again and then the read-only `--dry-run` before any
flash.
