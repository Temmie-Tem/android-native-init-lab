# A90 F1 Operator-Attended Observation v1

Status: `H0_IMPLEMENTED_STATIC_GO_NO_LIVE_MANIFEST`

This contract defines a future A90-only extension to Process v2. It is not
live authority and cannot be applied to a candidate after candidate intent.
The reusable runner, manifest schema, approval binding, journal validation,
and focused tests now implement this contract and passed independent safety
review. No final manifest or approval currently selects it.

## Purpose

The unattended path remains fail-fast. The attended path exists so a present
operator can correct a transient native-init menu/channel condition before the
one destructive runtime handoff without repeating the candidate boot transfer.

It does not relax partition, candidate, handoff, rollback, target, or recovery
limits.

## Predeclared Mode

A future immutable manifest must select exactly:

```json
{
  "observation": {
    "mode": "operator-attended-v1",
    "attended_window_sec": 900,
    "pre_handoff_attempt_limit": 3,
    "handoff_attempt_limit": 1
  }
}
```

The F1 approval binding must include all four values. Version 1 accepts no
window above 900 seconds, no pre-handoff budget above three, and no handoff
limit other than one. The mode cannot be added or changed after approval or
candidate intent.

The attended window is valid only while:

- the operator is physically present and confirms recovery remains available;
- the exact candidate completed one transfer with no replay;
- no rollback intent or completion exists;
- no handoff intent exists;
- the manifest-bound deadline has not expired; and
- the exact target remains unambiguous.

## Window Open

After durable `candidate-flashed`, the runner records
`attended-window-open` before attempting candidate health. It publishes one
private mode-0600 continuation receipt binding:

- run ID and manifest SHA256;
- consumed F1 approval-binding SHA256;
- candidate and rollback SHA256;
- exact journal sequence and window-open timestamp;
- exact deadline and attempt limits; and
- SHA256 of the exact immutable handoff argv.

The receipt creates no new partition authority. The runner may print its exact
operator-continuation token. A continuation requires the operator to
acknowledge that token while still attending the device.

## Allowed Pre-Handoff Attempts

At most three attempts are allowed and each is append-only journaled before
device contact. One attempt may perform only:

1. exact framed native-init `hide`;
2. a three-second settle;
3. the harmless exact framed BusyBox `true` canary;
4. exact version and selftest reads;
5. the manifest-bound source/work read-only preflight;
6. a second hide, settle, and canary sequence.

No arbitrary shell, file mutation, mount, reboot, boot-mode transition,
payload, or partition action belongs to this window.

A positively classified pre-handoff channel failure may leave the window open
for another bounded attempt only when the journal proves:

- no handoff intent was recorded;
- the handoff command was not sent;
- candidate transfer count remains one; and
- rollback remains required and available.

Expiry, attempt exhaustion, target ambiguity, health mismatch, lost recovery,
or an unclassified error closes continuation authority. Only rollback recovery
may follow.

## One Handoff

After one pre-handoff attempt passes, the runner durably commits
`attended-handoff-started` and fsyncs its journal record before dispatching the
first byte of the exact manifest-bound handoff.

The handoff attempt limit is one. A returned error, timeout, missing output,
ambiguous dispatch, SSH failure, or candidate-return failure never authorizes
another handoff. The runner records the observation result and proceeds to the
already-authorized rollback path.

After that durable intent, observation and rollback form a one-way path; no
health, channel, or handoff command may be retried.

Success still requires all existing V3403 evidence:

- exact source and work-copy SHA markers;
- `exec_switch_root_now`;
- USB-local Debian marker;
- `/proc/1` proving distro init as PID 1;
- bounded candidate return;
- one exact V2321 rollback; and
- restored final health.

## Low-Risk Operator Controls

While the operator is actively attending, exact UI-only native-init `hide` is
a routine low-risk D1 control. The active operator direction covers it without
a per-invocation ceremony when the agent announces the action, selects the
exact target, sends it once, and verifies its framed return.

This standing treatment does not cover reboot, Download/recovery entry,
service start or stop, mount, network reconfiguration, file mutation, payload
transfer, or any action that can remove the recovery path. Those retain their
normal tier and approval requirements.

## Recovery and Non-Retroactivity

The original F1 approval continues to authorize mandatory exact rollback.
Rollback must not wait for an attended-continuation acknowledgement and must
never repeat the candidate.

This contract cannot reactivate, extend, or reinterpret a consumed or failed
run. In particular, it does not apply to
`a90-v3403-debian-f1-20260731-01`, which is closed with final V2321 health
restored.

## Implementation Closure

Host-only implementation proves:

- strict manifest and approval-binding validation;
- canonical private continuation-receipt generation and reopening;
- deadline and exact integer attempt-limit enforcement;
- pre-handoff failure classification with no self-declared success;
- journal source-order gates for window, attempt, health, and handoff intent;
- one-way transition to rollback after any handoff intent;
- recovery compatibility without candidate retransmission;
- mutation tests for every attempt/deadline/handoff limit; and
- one independent review of the execution-critical closure.

The runner also reopens the exact successful candidate-transfer closure before
continuation. It requires the original approval, one exact candidate intent
and completion, transfer count one, no replay, the bound candidate SHA256,
the exact successful private flash log, and all checked transfer/readback
milestones. Stored retry booleans are never self-authenticating: continuation
re-derives the exact error identity and verifies the attempt/failure
timestamps are inside the window.

The focused suite passes `71/71`. Independent review passed its related
`154/154` closure, `py_compile`, and `git diff --check`, and returned `GO`
with no remaining Critical, High, or Medium finding. The reviewed source and
test SHA256 values are respectively
`695c4f8c19a8016bee095156b21573353668181370d34266b3aadb1460ef8330`
and
`5740fce0062dc9e06b8d3b7700fdc2ba295caf7265f7bb626bbf45e92f944e59`.

This status does not create a run, final manifest, continuation receipt,
approval, or device authority. A future experiment still requires a new
immutable run closure, fresh connected D0, and one exact F1 approval.
