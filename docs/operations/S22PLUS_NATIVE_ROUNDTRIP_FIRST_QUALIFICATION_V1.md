# S22+ native roundtrip first qualification V1

Status: **REVIEW_GATED_CAPABILITY; no current device grant.**

This is a separate common-boundary specialization for one future attended qualification
on `SM-S906N/g0q/S906NKSS7FYG8`, incorporated by the common contract after
independent review. It does not change the existing consumed registry or any old
approval or journal. Its definition and H0 implementation are within the
operator-requested same-N roundtrip scope; they are not a device-run grant.

## Why a common exception is necessary

[Common F1 Invariants](DEVICE_ACTION_CONTRACT_DETAILS.md#common-f1-invariants)
require one candidate and forbid candidate replay.
[Process v2](DEVICE_ACTION_PROCESS_V2.md) defines the permanent
cross-run consumed-candidate boundary using the physical target and AP/member
content identity. Giving the second copy of N a different role name does not
change that identity. The current runner must reject it.

The prior design omitted this higher-precedence conflict. Its earlier
design-only review is not qualification of this exception. This separately
reviewed incorporation specializes the common rule; successful v0.1.2/P382
evidence and a target-only amendment cannot substitute for that incorporation.

## Exact specialization

The following exact scope is incorporated under Common F1 Invariants, with this
file's digest declared there and the common details pinned by AGENTS.md:

> S22PLUS_NATIVE_ROUNDTRIP_FIRST_QUALIFICATION_V1 is a closed exception to the
> same-candidate repeat prohibition for one separately prepared, independently
> reviewed and explicitly granted attended S22+ FYG8 qualification transaction.
> Its sealed binding identifies exactly one previously unconsumed native
> boot-only AP N and one exact existing Magisk Android recovery AP A, by stable
> artifact paths, AP and boot.img.lz4 member sizes and SHA256, physical target,
> execution closure, run identity, deadlines, and three ordered effect roles:
> N installation, one N restoration, and one A cleanup/fallback. No artifact
> from an already consumed historical candidate/run is eligible as N. A and N
> must be distinct and present/readable/hash-verified before any effect.
>
> The N installation uses the existing permanent consumed-candidate claim. It
> remains consumed permanently. The exception permits the same exact N bytes
> once more only in this transaction's predeclared restoration role, after
> completed N installation, raw-authenticated first native health, a one-shot
> CONTROL intent, and exact timely Download arrival under the bound observer.
> The restoration has its own durable intent before first backend delivery and
> never releases, replaces, clears or renames the installation's consumed claim.
> It cannot be reached through ordinary candidate dispatch or another run.
>
> A failed, missing or uncertain installation/restoration result, failed native
> health, unexplained session failure, expired native observation window or
> unresolved identity stops further research. At most one CONTROL is permitted
> per declared native arrival, and none after a research stop. No N restoration
> after that stop, reconnect within an arrival, or repetition of any role's
> intent/effect is permitted. Only the one predeclared same-N restoration above
> is excepted from the content repeat prohibition. An intent-only cut is treated
> conservatively as possibly delivered;
> recovery never synthesizes completion or native health from that intent.
>
> The sole later partition effect after a research stop is the one predeclared
> A fallback, still requiring physical attendance, demonstrated available
> physical Download recovery, current exact target/Download binding, unchanged
> exact A identity, and durable evidence sufficient to exclude any previous A
> attempt. Missing/uncertain target identity or physical recovery parks. A
> failed, missing or uncertain A result parks without replay. Permitted fresh
> observation and local finalization may resume from durable evidence; neither
> authorizes another transfer. This specializes boundary 7 only for that one
> preauthorized recovery route, never for continued research after a failure.
>
> Success requires both separately authenticated native arrivals, the same
> verified N transfer bytes, different authenticated kernel boot identities and
> challenges, complete native-health command/STATUS proof, observed Download
> departures, one completed A cleanup, and final rooted FYG8/original-partition
> Android health. CONTROL ACK proves acceptance only. Native roundtrip and
> Android recovery/final health are reported independently. Recovery cannot
> promote a failed or uncertain roundtrip to PASS.
>
> This exception has no standing or cross-run native baseline authority. It
> closes on the selected transaction's terminal outcome; an intent/effect
> uncertainty does not renew its budget or allow replacement by another run.
> Its finite grant expires under the sealed attendance/time bounds, retaining
> only expressly preauthorized recovery. Source, artifact, target, health,
> observer or recovery-path changes require a new reviewed binding before any
> unconsumed effect, and may never repin a consumed transaction. Any subsequent
> adoption or additional qualification is a separate policy decision.

This leaves boot-only membership, forbidden partitions and transports, exact
rollback availability, attended execution, private evidence, and target
isolation unchanged. It changes the permanent no-replay boundary in precisely
the second-N role above; it must not be described as a semantics-only refactor.

## Implementation and activation conditions

Internal **P383 / v0.2.0-rc.1** implements this first qualification in the existing
Process-v2 owner. Its approval binding includes the ordered roles, exact N/A
AP/member receipts, fixed health command identity, one effect per role, two
native arrivals, one CONTROL per arrival, and the original 1,800-second research
window. Each native observer retains its 600-second bound. The source closure
includes this policy, the fixed health observer and the role owner.

The ordinary journal and permanent registry own the N installation and A cleanup.
A linked `native-restoration` directory owns the exceptional N delivery and the
second observer's raw evidence, guard, CONTROL and Download window. Its immutable
intent binds independently reopened first health/window and a fresh exact
Download receipt. Its exclusive delivery record precedes the unchanged bounded
Odin boot-only adapter. The installation claim remains consumed permanently;
a separate immutable first-qualification claim prevents renewing this exception.
No ordinary candidate dispatch or recovery path can invoke the N restoration.

The fixed health profile checks numeric root, PID1 parentage, real proc/sys/dev
mounts, complete bounded binary stdout/stderr, terminal status and a subsequent
idle STATUS. Before second CONTROL, the authenticated kernel identity and
challenge must both differ from the first arrival. Neither challenge freshness
nor CONTROL acceptance alone proves a new boot or Download arrival.

Recovery uses fresh exact Download observation and at most one A attempt.
A missing, failed or uncertain A result cannot start a second A delivery.
Raw-complete native qualification survives a later local publication cut; a
cut before its complete proof or any research failure remains NO_PROOF. Final
result validation reopens both native raw streams/windows, the restoration
intent/delivery/result and original consumed claim. Its linked role timeline
reports N installation, N restoration and A cleanup alongside the ordinary
transaction timeline, before final F1 ownership retirement.

The [H0 report](../reports/S22PLUS_FYG8_NATIVE_BASELINE_ROUNDTRIP_H0_2026-09-10.md)
records the exact reviewed execution closure, joined normal/cut/failure tests
and fresh A/B/static qualification. Those checks, current exact preparation,
demonstrated physical recovery, physical attendance and a fresh finite
Process-v2 approval are required before the first device effect. A past run or
PASS_GO is not that grant. No standing native baseline is adopted by this lane.

The tests use generated C authentication/supervision and real fork/pipes, with
explicit fixture UUID, root/mount, USB, Odin and Android facts. They qualify host
protocol/ownership behavior; they are not live native health or physical
recovery proof. The candidate preserves the prior native runtime's behavior
apart from its new identity and version label; no numeric target syscall flag
or native ABI behavior is changed by this qualification owner.
