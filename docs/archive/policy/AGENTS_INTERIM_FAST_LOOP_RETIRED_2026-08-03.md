## Interim Fast-Loop Rules (operational trial)

Status: **RETIRED**. The trial was activated by operator declaration on 2026-08-03
and retired at 2026-08-03T20:46:02Z, when the first `CAMPAIGN_CLOSED` rows for the two distinct campaign IDs
`s22plus-fyg8-p296` and `s22plus-fyg8-p298` had both been recorded. The terms below are retained as the historical trial contract only.
They no longer grant standing D0, procedural autonomy, or an override of the ordinary target contracts and process documents.
Permanent device, repository, and evidence boundaries remained absolute throughout.

Retirement: end after the first `CAMPAIGN_CLOSED` row for each of two distinct campaign IDs across both ledgers, or on 2026-09-03, whichever comes first.
Duplicate closes and parked campaigns do not count. Contract Revision 2 and permanent boundaries remain; adopt this autonomy or lapse only it. Never extend silently.

The retirement condition above is satisfied. The following trial-only procedural authority, autonomy, health, and evidence terms
are non-operative and remain here only to preserve the contract record for the interval in which the trial was active.

### Procedural authority gates - closed list

For a new device effect that already satisfies every permanent boundary, only
these procedural authority gates may refuse it:

1. exact target identity matches its bound profile (D0/D1/F1);
2. an exact hash-bound rollback is ready when required (D1/F1);
3. the target-contract recovery path is demonstrated and available (D1/F1); and
4. the target-contract presence predicate is true (D1/F1; unattended only where both contracts expressly allow it).

These are not the exhaustive safety checks. Permanent boundaries, artifact and
journal integrity, no-replay, and the inter-effect `HEALTHY` barrier still stop
or park work. Other host-only schema, shape, and evidence failures are H0 bugs
to fix and rerun, not new device-authority gates.

### Autonomy

| Tier | Rule |
|---|---|
| H0 | Unlimited. Rule 7 suspended. Fix and continue. |
| D0 | Autonomous for a resolved exact target. No approval. |
| D1 | Autonomous under the target presence mode. Only the qualified A90 resident lane may be unattended; all other D1 stays attended. |
| F1 | Autonomous while attended. No per-candidate approval. Rollback and health verification between attempts. At most one target may be F1-armed at a time. |

The agent owns goal selection, experiment design, and iteration. Do not require
a campaign-level planner or runner. Target runners are transaction primitives
for one device effect, durable intent, observation, recovery, and health.
Legacy v1 approval/time/action limits remain implementation constraints until
their runners change; they do not define the trial policy.

An F1 run parked while awaiting a required physical operator step remains
F1-armed. Host-only work continues during a park; no second candidate may be
armed, and a park is not an abort. Resume from durable journal state.

F1 exclusivity belongs to target-identity gate 1, not a fifth gate. H0/D0
preparation may coexist. A target becomes F1-armed when its journal durably
records candidate intent, before the first candidate effect, and remains armed
through observation, park, rollback, and recovery. Disarm only after exact
`HEALTHY` is durable; an uncontrolled or recovery-required close stays armed.

Each target contract defines its presence predicate. Only its qualified A90
resident D1 lane may be unattended; every F1 and all other D1 stay attended.

### Health, observation, and recovery

A missing, late, timed-out, or malformed observation is not by itself a device-health or recovery failure.
Endpoint absence is not target ambiguity; ambiguity requires multiple plausible targets or
conflicting bound identity. Unresolved observation freezes new effects as
`HEALTH_PENDING`, `HOST_OBSERVER_FAILURE`, or `RECOVERY_PENDING_PARKED`.

Until exact health and recovery establish `HEALTHY`, permit only passive bounded
observation, re-enumeration stabilization, H0 observer repair/replay, and exact
recovery. Never replay the uncertain action. A timeout parks rather than closes;
confirmed negative health enters recovery. Permanent stops and operator stop
still close. Attendance loss stops F1 and all D1 except the qualified A90 lane.

### Evidence

Routine narrative evidence is the commit body: attempt, result including no-proof, judgment, work, and a `Validation:` line.

Append the structured row to the per-target campaign ledger:
`docs/operations/CAMPAIGN_LEDGER_S22PLUS.md` or
`docs/operations/CAMPAIGN_LEDGER_A90.md`. Write a separate report only for a
new capability, a new hazard class, an incident, or a genuinely ambiguous
device-safety result. No per-run prose, no review ladder, and no per-candidate
policy document.

A superseded report moves to `docs/archive/reports/`; location is the authority signal.
