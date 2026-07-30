# A90 V3403 Switch-Root F1 Frame Abort and Rollback

Date: 2026-07-31 KST

Status: `ABORTED_F1_V2_CANDIDATE_UNCERTAIN_ROLLED_BACK`

## Scope

This report records the exact approved run
`a90-v3403-debian-f1-20260731-01`. The run was intended to prove the first
real Debian PID-1 handoff through `switch_root`.

The approval and run are consumed and non-reusable.

## Staging and candidate

The absent-only staging transaction passed:

- the fresh run-derived final path was absent;
- the fixed work path and exclusive staging directory were absent;
- the 2 GiB payload transferred and matched the exact SHA256;
- hard-link no-clobber publication passed;
- the staging directory was removed; and
- exact V2321 health passed before candidate intent.

The candidate boot transfer then ran once. The durable journal contains one
`candidate-transfer-started` record followed by one `candidate-flashed`
record. There was no candidate replay.

The device returned the exact expected banner:

```text
A90 Linux init 0.11.159 (v3403-d3-immutable-handoff)
```

Candidate boot itself therefore occurred. The strict runner nevertheless
could not record `candidate-boot-ready`: automatic menu and prompt output
interleaved after the version body and the required `A90P1 END` frame was not
received. Candidate selftest was not reached.

The source preflight, handoff command, `switch_root`, and Debian SSH observer
were never invoked. This is not a switch-root failure; switch-root was not
attempted.

## Rollback

The operator paused the first rollback-recovery process before any rollback
journal intent or helper log existed. No transfer occurred in that paused
process.

Rollback-only recovery was then resumed from the durable candidate state. One
exact V2321 rollback transfer completed and the journal reached
`ROLLBACK_FLASHED`.

The first final-health read met the same framing failure after returning the
exact V2321 version and build. It did not repeat the rollback transfer. After
one explicitly operator-approved low-risk framed `hide`, the complete hide
BEGIN/END response returned `rc=0` and `status=ok`. Health-only recovery then
resumed from `ROLLBACK_FLASHED` without another transfer.

Final checks proved:

- exact version `0.9.285`;
- exact build `v2321-usb-clean-identity-rodata`;
- selftest failure count zero; and
- pstore entry count zero.

The journal reached `HEALTH_VERIFIED` and `CLOSED`. Candidate and rollback
transfer intents and completions each occur once. The structured result keeps
the conservative `candidate_transfer_uncertain: true` classification because
the strict candidate boot-health gate never completed, while the durable
`candidate-flashed` record remains the exact transfer evidence.

## Result

The final structured status is
`ABORTED_F1_V2_CANDIDATE_UNCERTAIN_ROLLED_BACK`.

- Debian PID1 proof: false
- candidate replay: false
- rollback transfer count: one
- final health restored: true
- internal userdata touched: false

Private journal, raw logs, timeline, and structured result remain under
`workspace/private/runs/server-distro/a90-v3403-debian-f1-20260731-01/`.

## Successor direction

The failure was caused by a brittle single-shot serial health gate, not by the
candidate boot or switch-root code. Future work will define a separately
reviewed operator-attended observation mode. It will preserve one candidate,
one handoff, and mandatory rollback limits while allowing bounded pre-handoff
health/channel retries during an explicitly attended window. This new mode
must be declared and approved before a future candidate; it is not applied
retroactively to this closed run.
