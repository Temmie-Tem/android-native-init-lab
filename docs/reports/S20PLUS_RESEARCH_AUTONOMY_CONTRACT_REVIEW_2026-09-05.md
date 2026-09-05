# Research autonomy contract review

Date: 2026-09-05. Selected target: S20+ `SM-G986N/y2q/G986NKSS8IYC2`.
Scope: policy review and correction; no device commands or runner activation.

## Finding

The intended default is autonomous progress within authorized research scope
when the agent can establish the required facts and safely stop or carry out
permitted recovery. Requiring screen confirmation for machine-observable reboot
facts confused authorization, physical attendance, current runtime binding and
recovery capability. Revision 7 fixed one PMSG transaction but did not express
the broader default or remove redundant requests in existing fixed D0 profiles.

The current contracts already permit H0 without device permission and continued
steps inside a valid finite autonomous grant. Reasking during those steps was
an interpretation error. Common D0 never required blanket attendance, but the
S20 public/root-health/readiness sections separately required renewed requests;
root-health and readiness also required attendance. Those are concrete policy
restrictions, so changing only a general introductory preference was insufficient.

The S20 bounded autonomous campaign remains `H0 POLICY PASS_GO - NOT ACTIVE`;
its render-only model and later dormant components are not a current live
session. Conditional autonomous F1 is also not active for S20+. The reviewed
PMSG runner remains dormant. No prior consumed trial is reset by this review.

## Revision 8 correction

| Work | Default under the updated contract | Limits retained |
|---|---|---|
| H0 research, implementation, tests and review | Continue autonomously within the task | No device contact or implied live activation |
| S20 routine public D0, fixed root-health D0, readiness D0 | Necessary invocations covered by the current foreground S20 research request; no repeated consent or physical attendance | Same active fixed runners, fresh exact identity/health, bounded output and privacy; no generic root, background monitor or retry loop |
| Steps in an already authorized finite lane | Refresh machine binding and continue without renewed step approval | Exact scope, unexpired grant, counters, recovery reservations and no replay |
| Future non-partition D1 research | Reusable common delegation for a reviewed machine-controlled lane | Exact target activation, finite grant and actual safe device failure state or demonstrated authorized recovery |
| F1/R1/F2, fastboot and other physical-return exceptions | Existing specific rules remain | No inherited attendance waiver; unattended F1 still needs failure-specific automatic recovery evidence |

The foreground D0 permission ends with the task, operator stop or target/scope
change. Each read must answer a concrete task question. A failed invocation
closes; another read needs an evidence-based decision after cause/stop assessment,
not another consent merely because it is another read. An unresolved device
session still belongs to its own recovery owner; D0 cannot bypass it or a
foreign guard. Legacy `Attended` root-health identifiers remain unchanged for
execution compatibility, with their foreground-task meaning expressly clarified.

The general D1 delegation is defined, not activated for S20+. It favors the
smallest reusable reviewed runner instead of mandatory completion of unrelated
historical coordinator models. Killing the host process is not proof that the
device can safely remain in its failure state. If the reviewed failure model
needs timely physical recovery, attendance remains a prerequisite. Otherwise,
permitted stable failure may park and request physical help only when needed.
A changed boot ID and healthy return prove observation, not automatic recovery.

## Review and validation

Independent audit confirmed the four-way distinction and the target-level D0
friction. Final independent review returned **PASS_GO — policy amendment**,
with no remaining blocking findings. Foreground D0 authorization is effective;
the general D1 delegation remains unactivated. Existing common permanent
partition/privacy limits, consumed effects, target isolation and recovery-only
continuations remain in force. The new general D1 lane transfers no authority
to other targets or existing F1/R1/F2/fastboot lanes.

This unit changes contracts and their current-state documentation only. Runtime
sources, fixed scripts, activation flags, artifacts and private device journals
are unchanged. Validation covers policy consistency, unchanged runner sources,
report links, goal length and repository boundary/diff checks; unchanged runtime
tests are not repeated for this documentation-only unit.

References: [common contract](../../AGENTS.md),
[risk tiers](../operations/DEVICE_ACTION_RISK_TIERS.md),
[S20 target contract](../operations/targets/S20PLUS_G986N_TARGET_CONTRACT.md),
[PMSG capability and Revision 7 amendment](S20PLUS_G986N_PMSG_WARM_REBOOT_D1_H0_2026-09-05.md).
