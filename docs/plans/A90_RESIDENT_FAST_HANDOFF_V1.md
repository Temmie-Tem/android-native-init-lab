# A90 resident fast-handoff v1

## Decision

Keep the existing F1 orchestrator frozen for rare boot installation and exact
recovery. Do not refactor its 6,000-line execution closure into the ordinary
experiment path.

The intended ordinary path is a small resident D1 transaction. Once one exact
native-init boot has been separately promoted as the resident experimental
baseline, a normal display or Debian experiment performs no candidate or
rollback flash. It verifies the resident baseline, performs one handoff,
observes Debian, verifies the changed USB generation and returned native
health, and removes the exact handoff work copy before closing.

This document is an H0 design. It grants no resident promotion, D1 action,
flash, cleanup, or device authority.

## Why this is smaller

There are two deliberately separate paths:

| Path | Frequency | Scope |
| --- | --- | --- |
| Installation/recovery | Rare | Frozen F1 machinery, boot only, exact V2321 recovery available |
| Ordinary experiment | Repeated | Resident D1, no flash, one handoff, one bounded return, one exact cleanup |

The daily path does not regenerate an AP, start Odin, enter Download mode,
transfer an unchanged rollback, or run the F1 journal/recovery state machine.
The large path remains available without becoming a dependency of each Debian
iteration.

## Current boundary

The ordinary F1 Process v2 requires mandatory rollback and defines PASS to
include that rollback. The A90-only F1-RP policy is now adopted in
`docs/operations/A90_RESIDENT_BOOT_PROMOTION_V1.md`; it adds a distinct
two-boot resident-health terminal without changing ordinary F1 or S22+.

The policy has no live runner or manifest and grants no device authority.
Until those are implemented, reviewed, and freshly approved, exact V2321
remains the resident baseline and the daily D1 runner remains inactive.

## One-time resident promotion

The promotion unit must bind one exact A90 target, candidate boot, V2321
recovery boot, corrected Debian image, transport closure, and physical Download
recovery path. It may transfer only `boot`. After installation it must prove:

- exact native version and build;
- `selftest fail=0` and clean pstore;
- bridge and NCM identity on the named A90;
- the fixed Debian source is present and the work path is absent; and
- exact V2321 rollback remains locally readable and hash-correct.

Any failed promotion health check invokes the already-authorized exact
rollback. A successful promotion closes as a new known-healthy resident
baseline instead of immediately rolling back. That different terminal state
is the policy change that must be reviewed once.

## Ordinary D1 transaction

The reduced transaction is:

```text
PREFLIGHT
-> APPROVED
-> GUARD_ARMED
-> HANDOFF_STARTED
-> DEBIAN_OBSERVED
-> NATIVE_RETURNED
-> WORK_CLEANED
-> HEALTH_VERIFIED
-> CLOSED
```

Preflight requires the exact resident version/build, exact A90 endpoint, clean
selftest and pstore, the exact immutable Debian source, and an absent
`d3-handoff-work.img`. It also binds the exact USB-local NCM profile and the
transient A90-only ModemManager guard.

One fresh D1 approval authorizes one `switch-root-to-distro` dispatch and the
same-run exact work-copy cleanup after healthy native return. It never
authorizes a flash, a second handoff, a candidate replay, or cleanup of an
unexpected path or hash.

Debian observation must prove PID 1, Dropbear, and the display result through
the framed observation pipeline. Return requires a changed USB epoch, exact
guard identity, exact resident version/build, and `selftest fail=0`. The NCM
profile is rebound to the interface sharing the returned ACM USB parent rather
than to an interface name.

If return is not proved inside the bound, the D1 transaction stops. It does not
turn itself into an F1 recovery operation. Recovery uses a separately selected
and authorized path with the exact rollback already available.

## Work-copy rule

The native contract creates a fixed absent-only work image. Leaving it behind
both blocks the next experiment and risks reusing mutable Debian runtime
state. Therefore successful return is not closure: exact cleanup and a second
absence check are mandatory in the same D1 transaction.

Cleanup is fail-closed. A missing source, changed path, changed expected work
identity, ambiguous target, or failed health check stops the next handoff. It
does not trigger generic deletion or automatic repair.

## Host-qualified Debian input

`a90_resident_fast_handoff_v1.py` validates only the corrected Phase 2 display
A/B build. It verifies both private 2 GiB images byte-for-byte, read-only
filesystem checks, source preservation, and the exact static presenter. Its
output explicitly remains `live_ready=false` and lists the promotion and D1
activation blockers.

The qualified image SHA256 is
`88152ef1150fc98765eed7c3f196ab9ef8a325d4cc5f74222e45949b089950c2`.
The corrected static presenter SHA256 is
`35e6a18d50c73ef14b2309124d4dbe7f1cd0607f525afd992e6a6334c55dd583`.

## Deferred work

- Do not flatten or delete the legacy native-init builder chain in this unit.
- Do not minimize native-init C until Debian owns the corresponding function.
- Do not generalize NCM handling beyond the exact A90 USB parent.
- Do not add another review ladder for an unchanged ordinary D1 profile.
- Do not activate the live runner before the resident promotion policy and
  exact baseline exist.
