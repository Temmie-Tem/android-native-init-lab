# S22+ FYG8 pre-F1 normal-reboot live integration H0 report

Date: 2026-08-29

Status: **IMPLEMENTED / REVIEW PENDING / NOT ACTIVE**

## Result

The first pre-F1 live-integration slice now exists for exactly one catalog
action: `normal_android_reboot_health` with `new_boot_health`. It reuses the
reviewed D1 V3 target selector, raw-first observer, canonical arm, normal reboot
and bounded final-health implementation. It reuses the reviewed pre-F1
coordinator and append-only journal rather than introducing a second state
model.

The tracked binding remains `review-pending`. Every connected entry checks that
state before creating a session namespace or loading a device transport. The
default `--self-test` is host-only and reports `live_authority: false`. No
activation proposal, session approval, device command, reboot, D0, D1, F1,
recovery or live authority was created by this unit.

## Deliberately small surface

The fixed CLI contains five operations:

1. `--self-test` validates the dormant binding without device access.
2. `--prepare-activation` performs one bounded read-only exact-target
   observation and publishes a ten-minute proposal plus its exact attended
   approval string.
3. `--activate APPROVAL` rechecks the same serial hash, topology, boot and
   healthy Android, then opens one twelve-hour session with no effect.
4. `--run-normal-reboot` performs a fresh pre-intent recheck, publishes one
   durable outer intent and invokes only the fixed reviewed D1 V3 executor.
5. `--reconcile` reads an already-published V3 result after a host reporting
   cut; it has no execution path and never repeats the reboot.

There is no caller-selected target, path, command, action class, proof mode,
ordinal or executor. This version supports at most one normal reboot. It does
not implement Download entry, sysfs/configfs mutation, Recovery entry, F1,
partition transfer, a renewable campaign or a background daemon.

## Binding and evidence

The final pending binding is 2,511 bytes / `fab1fdaa`. It binds:

- live wrapper: 46,505 bytes / `e93ec6df`;
- reviewed policy: 9,587 bytes / `b0868105`;
- reviewed coordinator: 23,764 bytes / `c0d56417`;
- reviewed journal: 32,123 bytes / `0d13c621`;
- reviewed D1 V3 source: 73,125 bytes / `cb13236e`;
- reviewed D1 V3 binding: 6,705 bytes / `dcb869ae`; and
- fixed descriptor: `fe16838a`.

The activation proposal binds the complete runner-binding receipt, descriptor,
exact target, selected-serial hash, topology hash, current boot hash, health,
creation time and expiry. The activation envelope retains the selected-serial
hash explicitly; every pre-intent observation and the V3 result must match it.
The coordinator journal separately retains the target, topology, boot,
descriptor state and one monotonic D1 debit. Thus the integration binding and
effect descriptor remain distinct, visible authorities rather than one being
silently relabelled as the other.

All production observation flows through V3's bound
`device_action_raw_capture_v1.py` provider. Failed pre-intent observations are
not deleted or parsed as successes; they remain in a bounded numbered slot and
the next no-effect retry gets a fresh slot. The permanent raw-first auditor now
byte-freezes this live source and checks observation and effect ordering. Its
new private receipt is 14,553 bytes / `b076020e`, mode 0400, link count one.

## Cut and replay behavior

Hostile review found seven meaningful omissions in the first draft. The final
pending implementation repairs all seven:

- a cut between healthy-return and close cannot dispatch a second reboot;
  `d1_effects_used == 1` permits only idempotent close finalization;
- a partial pre-intent observation no longer poisons the sole fixed path;
- a published activation with a missing or empty journal resumes without a
  second target observation or device effect;
- session expiry blocks a new effect but not passive result reconciliation;
- time is read again after long activation and pre-intent observations;
- V3 success must retain complete before/after health, raw evidence, target
  selection, changed boot and every false safety field; and
- selected-serial identity is retained and compared at activation, pre-intent
  and result acceptance.

The first re-review then found two residual envelope gaps. A result could carry
`raw_evidence={"complete":true,"forged":...}` because the wrapper checked only
one Boolean, and a rewritten activation could change its boot/topology while
remaining internally well-typed. The repair compares activation boot and
topology directly with the approved proposal observation. It also requires the
complete result to be canonical-equal to V3's fresh `_post_validate()` result,
which reopens the fixed arm, start, result, raw inventory, manifest and
namespace. Both forged fixtures now stop before a healthy close or any new
device effect.

A second hostile probe recomputed the raw aggregate around `children=[{}]` and
`handles=[{}]`; the first local grammar still accepted it. Rather than copying
V3's grammar into this wrapper, the final repair delegates to the exact bound
V3 post-validator and compares the whole result. Immediately before outer
intent it also runs V3's host-only fixed-namespace preflight, so a pre-existing
arm/result cannot be reconciled as this campaign's result. Activation rechecks
the selected serial before publication as well as at pre-intent and result.

The outer intent is durable before the reviewed V3 invocation. Any exception
while the V3 result is absent or invalid records
`UNCERTAIN_CONSUMED_NO_REPLAY`. A later invocation sees that terminal park and
does not call the executor or result loader. If the healthy-return record is
already durable but close publication was interrupted, the only permitted
transition is close; the D1 debit itself is the replay guard.

## Host-only validation

The final live-wrapper suite passes 25/25. It covers pending-review blocking,
short-lived proposal binding, wrong/expired approval, activation recheck and
resume, session expiry, exact serial, pre-intent no-consumption, retained
partial observation, fixed V3 namespace absence, happy return, malformed
health or raw inventory, activation serial/envelope mutation, post-intent park,
reporting-cut reconciliation and the healthy-return/close cut that previously
allowed a second invocation.

The permanent raw-first audit passes over 1,744 `revalidation/` Python files
with this wrapper as an active byte-frozen source. The auditor is 75,044 bytes
with normalized self-hash `6cb6dae5`; its output preserves the existing
128-member pre-boundary and 126-member closed-observer inventories.

Independent changed-closure review is still required. Until the pending
binding is promoted to the exact named `PASS_GO`, `--prepare-activation` fails
before observation and no live-session approval can be derived. F1 remains
separately attended under Process-v2.
