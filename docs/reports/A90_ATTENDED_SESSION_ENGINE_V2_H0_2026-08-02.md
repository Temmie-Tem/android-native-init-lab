# A90 attended-session engine v2 H0 closure

Date: 2026-08-02

Status: `A90_ATTENDED_SESSION_ENGINE_V2_H0_REVIEWED_LIVE_BLOCKED`

Device action: none

## Decision

The pure A90 transition-v2 contract and state engine now model the target
workflow:

```text
one A90_F1_RESIDENT_INSTALL_V1
-> PASS_A90_RESIDENT_INSTALLED
-> one A90_D1_ATTENDED_SESSION_V1 approval
-> bounded SWITCHROOT_EXPERIMENT actions without payload transfer
```

This is tested H0 machinery, not a live runner. It does not prepare an
approval, contact a target, transfer a boot image, or replace the existing v1
live owner.

## Resident-install model

The F1 model now ends after exact candidate health with:

- terminal `PASS_A90_RESIDENT_INSTALLED`;
- device safety `RESIDENT_HEALTHY`;
- one candidate effect and no candidate replay; and
- exact rollback after any failed or ambiguous started candidate effect.

Rollback success restores `BASELINE_HEALTHY`; rollback failure is
`RECOVERY_REQUIRED`. The adapter blueprint retains an explicit
`F1_RESIDENT_TERMINAL_ADAPTER_UNIMPLEMENTED` blocker, so this terminal cannot
be produced by the existing v1 live runner.

## Attended-session model

The session binding pins the exact target profile, manifest, resident boot,
rollback boot, recovery profile, device-effect runner, observer, return-health
profile, action allowlist, fixed validity window, and action budget.

The first schema permits only `SWITCHROOT_EXPERIMENT`. It rejects validity
longer than eight hours and budgets above 32. Opening requires an active time
window and exact attended target/resident/rollback/recovery preflight before
the one approval consumption.

Every action then follows:

```text
preflight -> durable intent -> one effect -> compact result -> postflight
```

No session result contains a candidate, rollback, or payload transfer. An
effect exception, malformed result, control ambiguity, unsafe postflight, or
lost identity/control ends in `RECOVERY_REQUIRED`. Expiry, operator absence,
budget exhaustion, and an unallowlisted action stop before another effect.

Device safety and experiment proof stay separate. `PROVED` and `REFUTED` may
retain `RESIDENT_HEALTHY` only with an exact safe postflight. Two identical
confirmed refutations stop across session boundaries because the next session
must ingest durable prior refutation history before consuming approval.

`NO_PROOF_OBSERVER` additionally requires an independent bounded safety check.
It consumes the uncertain action once, pauses the session, and rejects another
action. Resume requires a different exact observer SHA256, host-only focused
test PASS, unchanged safe preflight, an unexpired session, remaining budget,
and a recorded repair. The next intent and effect receive the repaired
observer identity; the uncertain action is never resent.

## Live blockers

The blueprint remains `host_only=true`, `live_ready=false`, and
`device_authority=false`. It explicitly lacks:

- a connected immutable manifest and fresh F1 approval;
- the F1 resident-terminal adapter;
- immutable activation source binding and exact live target;
- durable D1 session journal and prior-refutation history owners;
- observer-repair record and atomic session-approval consumers;
- a real D1 effects backend; and
- a replacement for the legacy cleanup approval/baseline contract.

Therefore no current manifest or approval can activate this code.

## Validation

- transition and adapter focused tests: `49/49` PASS;
- related A90 observation, resident v1, manifest, session, and policy tests:
  `133/133` PASS;
- touched Python `py_compile`: PASS;
- read-only disposable import test with no private tree: PASS;
- simulation CLI and blueprint audit: H0-only/live-blocked PASS;
- scoped `git diff --check`: PASS; and
- independent safety review: PASS/GO, no remaining finding.

Reviewed source SHA256 values:

```text
903e50cfbdd1255716cdcd482dd70ad67e4e141df9e0b1938ad06bfb745f8f4e  contract
631b669ec67d84dcb6ed5e90606ccb2818d7edb92c4be624fd57bb31dd1269d8  manifest
23aaab8a3a08df7a9aee2124f103ee48cb5a488708d1bb5eea069c6d7bea53e1  engine
8fc1fc5029d50a493b382c5869c6876a5adb681aa9fd8f4d258d45025d73f507  H0 CLI
```

No A90 or S22+ command was issued. Existing v1 live code, boot artifacts,
Debian images, rollback artifacts, and private evidence were not changed.

## Next gate

The next bounded unit is still H0: implement the immutable activation manifest,
durable session journal, atomic approval/refutation/observer-repair consumers,
and the exact live effects adapter. That new live closure requires focused
tests and another independent review. Only then may connected preflight and a
fresh exact F1 approval be prepared.
