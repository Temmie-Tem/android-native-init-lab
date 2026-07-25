# S22+ FYG8 P2.65 E3 pre-candidate ModemManager guard abort

> Follow-up correction: the root authorization fix in this report was
> necessary but insufficient. A fresh run reached ModemManager and proved that
> `InhibitDevice` cannot arm against this not-yet-exported future ACM device.
> The transient candidate-exact udev guard and second abort are recorded in the
> P2.66 report.

Date: 2026-07-26 KST

Verdict: `FAIL_F1_V2_PRE_CANDIDATE_DOWNLOAD_EXPLAINED_HOST_GUARD`

Device result: unchanged healthy FYG8 Android with root.

## Live boundary

One exact P2.60 E3 F1 approval was submitted to the prepared P2.63 run. The
approval matched the private binding and the execution-time Android D0 recheck
passed.

The runner then stopped while arming the CDC-ACM host-interference guard:

```text
PREFLIGHT -> APPROVED -> ABORTED
```

The durable result records:

- `candidate_attempted=false`;
- candidate classification `not-attempted`;
- outcome `candidate_observer_arm_failed_before_candidate`;
- no Download request;
- no Odin endpoint or session;
- no candidate or rollback transfer; and
- `recovery_required=false`.

Only `live_session_start` exists in the timeline because no candidate phase
started. Rollback was correctly not invoked: the device never left Android and
no partition changed.

Post-abort read-only checks proved Android online, boot complete, and Magisk
root returning uid 0.

## Root cause

The host runs ModemManager. E3 intentionally inhibits only the prepared
physical USB device while waiting for the candidate CDC-ACM endpoint.

The observer launched:

```text
setpriv --pdeathsig SIGKILL mmcli --inhibit-device=<uid>
```

as the ordinary desktop user. The installed system D-Bus policy denies
unlisted ModemManager manager methods to ordinary users and grants all manager
methods to root. `InhibitDevice` is not in the default-user allowlist.

The system journal at the exact abort timestamp records the ordinary user's
`InhibitDevice` method call being rejected before it reached ModemManager.
The child exited, the observer failed closed, and the runner aborted before
requesting Download.

This is a host privilege-path omission. It is not:

- a candidate kernel or userspace failure;
- an ACM enumeration result;
- an Odin failure;
- a target health failure; or
- evidence for or against the E3 banner.

## Why static tests missed it

The guard tests mocked a successful `mmcli` child and asserted only that
`setpriv --pdeathsig SIGKILL` prefixed the command. They did not model the
installed D-Bus policy or require a root broker.

The failure path also discarded the captured child output. The journal could
name `ObserverError` but not the D-Bus rejection. Host `journalctl` supplied the
missing discriminator.

## Bounded correction

The observer now launches:

```text
/usr/bin/pkexec /usr/bin/setpriv --pdeathsig SIGKILL \
    /bin/bash <fixed-supervisor> --inhibit-device=<uid>
        -> /usr/bin/setpriv --pdeathsig SIGKILL \
           /usr/bin/mmcli --inhibit-device=<uid>
```

The ordering is intentional:

1. `pkexec` obtains attended host-root authorization;
2. outer root `setpriv` protects the fixed supervisor after the credential
   change;
3. inner root `setpriv` makes the inhibiting `mmcli` die if the supervisor
   disappears;
4. an unprivileged control pipe asks the root supervisor to signal and reap
   `mmcli` on normal release; and
5. parent death remains the fallback if the control pipe or runner fails.

No global ModemManager stop, service edit, udev rule, or persistent host policy
change is introduced.

If launch or inhibition fails, the private run directory now receives:

- `candidate-observer-guard-arm.raw`; and
- `candidate-observer-guard-arm-failure.json`.

These make the next failure attributable without weakening the pre-candidate
abort. Raw output is capped at 16 KiB and records whether truncation occurred;
an evidence-write failure cannot replace the original arm error.

## Validation

Host validation passed:

- Python compilation;
- 24 focused CDC-ACM observer tests;
- root-broker command order and exact absolute paths;
- outer and inner parent-death ordering;
- normal control-pipe release and release failure;
- refused-inhibition durable evidence;
- launch-failure, collision, and bounded/truncated durable evidence; and
- 61 Process v2 core/live integration tests, including E3 all-of verdicts,
  rollback-only recovery, interrupted runs, and historical retained-only
  behavior.

One host-only harmless probe used the production `pkexec` and two-level
`setpriv` ordering with `/bin/sleep` in place of `mmcli`. Attended KDE
authorization completed, the control pipe released the root child with return
code 0, and no process remained. The probe did not access the S22+,
ModemManager, Odin, or any partition.

No kernel, userspace, candidate AP, rollback AP, manifest schema, Odin wrapper,
or device payload changed.

## Independent review

One persistent-session Claude Opus 5 maximum-effort, read-only review returned
`GO` on the privilege direction but found two evidence-correctness MUST-FIX
items:

1. an ordinary runner cannot signal the already-root `mmcli` process group;
2. argv-only tests did not exercise the normal release path.

The fixed supervisor/control-pipe design, added release tests, bounded failure
evidence, and harmless host probe close those findings without widening device
authority. The first delta review returned `GO` with no blocker. Its remaining
bounded-release warning was then closed with a 5-second TERM-to-KILL
escalation, dedicated control FD, detached child stdin, and an execution test
of the exact supervisor body. The final exact-delta review also returned `GO`
with no blocker. Its two evidence-accuracy warnings were closed by proving the
supervisor remains alive before release and allowing 10 seconds for the
supervisor's 5-second escalation and reap. The other residual warnings do not
weaken pre-candidate abort, rollback, or parent-death cleanup.

## Authority and next action

The aborted transaction is terminal and the submitted token must not be
reused. Although the candidate attempt was not consumed, any later attempt
requires:

1. independent review of this execution-critical observer change;
2. regenerated execution closure and offline validation;
3. a new connected read-only D0 preparation in a new run directory;
4. one fresh exact approval binding; and
5. one candidate attempt plus its preapproved mandatory rollback.

No F1 is currently authorized.
