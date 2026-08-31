# S20+ G986N autonomous public-health cross-code interlock map

Date: 2026-08-31

Target: Samsung Galaxy S20+ 5G (`SM-G986N` / `y2q` / `y2qksx` /
`G986NKSS8IYC2`)

Status: **H0 READ-ONLY MAP; NO PRODUCTION INTEGRATION OR LIVE AUTHORITY**

## Outcome

The existing start-interlock model was mapped against every S20+ runner that
can begin a new connected transaction. The common production ordering must be:

```text
held leaf-root dirfd
  -> nonblocking exclusive flock on that exact dirfd
  -> exact retained-state scan
  -> admit only EMPTY or fully validated PARKED_COMPLETE
  -> verify the shared guard is absent
  -> let the runner publish and fsync its own exact guard
  -> revalidate that guard through the held parent
  -> unlock
```

This is a serialization boundary, not an effect intent, device approval, or
new-start authorization. It must occur before the first ADB, root, Odin, USB,
or other target observation. A blocked state therefore performs zero host
commands to any device.

Already-owned continuation, recovery, and finalization paths do not acquire a
new-start slot. They validate their existing exact guard and journal and retain
the existing no-replay rules. The one existing exception is native-canary's
terminal-only idempotent re-emission after an exact terminal was already
durably published and its guard was released; that branch validates the exact
terminal result, requires the owned guard to be absent, and still rejects a
present foreign guard.

No source in the mapped runners was changed during this analysis. No ADB,
`su`, Odin, USB, network, device, or partition operation occurred.

## Exact insertion map

| New-start path | Current first target access | Current guard behavior | Required production insertion |
|---|---|---|---|
| Routine public D0 | `s20plus_g986n_routine_d0.py:372-380` enters `collect()`; its first ADB inventory is at `210-218` | No shared guard | After run-directory allocation and before `collect()`. Publish a non-effect observer guard under the held flock; retain it until durable result or failure publication. |
| Attended root-health D0 | `_execute_connected()` at `s20plus_g986n_attended_root_health_d0.py:1077-1102`; first inventory begins in `collect()` at `794-807` | No shared guard | After `EvidenceOwner` allocation and before `collect()`. Retain through durable result or failure publication. |
| Routine D1 actions | `main()` reaches `preflight()`; first inventory is `s20plus_g986n_routine_actions.py:254-263` | `acquire_guard()` is `787-824`; success and effect-free failure release at `920-942` | Execute the existing `acquire_guard()` inside the new-start slot and verify its exact publication before unlock. |
| Payload-free Download exit D1 | `arm()` is `s20plus_g986n_download_exit_d1.py:469-481`; first Odin inventory follows guard acquisition | `acquire_guard()` is `346-357`; `confirm()` and `finalize()` first validate the retained guard | Wrap only `arm()` guard acquisition at line 472. `confirm()` and `finalize()` are owned continuations and bypass the new-start slot. |
| Magisk bootstrap F1 | `prepare()` is `s20plus_g986n_magisk_bootstrap_f1.py:820-847`; target health is reached through `android_health_once()` at `1888` | Guard is published before target access and released only at named terminal/recovery points | After host artifact/closure validation, hold the slot across the existing guard publication and parent durability check. Every non-prepare mode remains an owned continuation. |
| Magisk resident F1 | `prepare()` is `s20plus_g986n_magisk_resident_f1.py:249-274`; it delegates its first target transition to bootstrap | Guard is published before the transition; other modes begin with the retained prepared state and guard | Wrap the prepare-only guard check/publication. All other modes bypass the new-start slot. |
| Native-canary R1 | `prepare()` is `s20plus_g986n_native_canary_r1.py:1438-1498`; first Android health read is line 1449 and root preflight follows | The existing guard is not published until lines 1485-1486, after the complete prepared/event journal | Acquire the slot after host artifact/closure/run-directory validation but before line 1449. Keep it held across read-only preflight, prepared/event publication, and the existing guard publication/fsync. Do not move the guard earlier because that would change the reviewed prepared-before-guard cut behavior. |

The native-canary ordering is the only mapped path whose current guard appears
after its first target read. Holding the leaf flock for the longer interval
closes that race without reordering the existing durable R1 journal and guard.

## Owned-path bypass closure

- Routine-actions `--resolve-control` is a host-only resolution of an existing
  guard, not a new start.
- Download `--confirm` and `--finalize` first validate the owned guard and must
  not reacquire a new-start slot.
- Bootstrap and resident F1 non-prepare modes resume only through their
  existing prepared journal and guard.
- Native-canary execute, resume, recovery, finalization, and stock-recovery
  paths are owned branches. A second `--prepare` invocation with an existing
  guard reaches only `resume_prepared_cli_output()` at lines 1656-1673 and
  cannot create another start.
- Native-canary terminal-only re-emission is an exact post-terminal exception:
  `read_prepared(..., allow_released_terminal=True)` admits an absent guard only
  after the terminal is already present, while first terminal publication still
  requires the owned guard. This branch may re-emit the exact retained terminal
  result only; it cannot reacquire a guard, start a command, publish a first
  terminal, or tolerate a present foreign guard.

No bypass grants a new target selection, command replay, effect replay,
capacity, approval, or recovery deviation.

## Integration blockers

The current fixture helper
`s20plus_g986n_autonomous_public_health_start_interlock_v1_h0.py::_fixture_new_start_slot()`
requires the shared guard to remain absent when the context exits. It therefore
cannot be copied into production unchanged: the production lease must instead
require the runner's exact guard to be present, complete, owned, durable, and
bound to the internal run directory before unlock.

The current recovery scanner
`s20plus_g986n_autonomous_public_health_recovery_v1.py::_scan_fixed_state_impl()`
acquires the separate `coordinator.lock`. That lock is recovery-only. A
production new-start adapter must accept already-held base/evidence/leaf
directory descriptors, perform an exact scan without touching
`coordinator.lock`, and derive its result only from retained content. It may
return only exact `EMPTY` or fully validated `PARKED_COMPLETE`; every partial,
expired, malformed, unknown, foreign, or ambiguous state stops.

Routine D0 currently promises that it creates no active intent. Its future
observer guard must therefore be reviewed and documented as a pure
serialization guard, never as an effect intent or device authority.

## Required hostile tests before integration

The shared adapter must cover:

- exact `EMPTY` and fully validated `PARKED_COMPLETE` admission only;
- every incomplete, expired, malformed, unknown, symlink, FIFO, hardlink, and
  foreign-guard state;
- multiprocess flock contention and a guard-appearance race;
- guard publication and parent-directory fsync before unlock;
- proof that `coordinator.lock` is never opened by a new-start scan; and
- process death, exception, and reporting-cut behavior.

Each runner must additionally prove:

- a blocked state executes zero commands;
- the interlock is held before its first target transport or read;
- its exact guard is published and revalidated while the flock remains held;
- terminal publication precedes observer-guard release; and
- every enumerated continuation/recovery path bypasses new-start acquisition
  and still requires its existing guard and journal, except the exact
  native-canary post-terminal re-emission branch described above.

The native-canary suite must retain direct tests that guard-released terminal
re-emission performs no device command, reproduces only the exact existing
terminal result, rejects first publication without an owned guard, and rejects
any present foreign guard.

Native-canary tests must directly observe the leaf flock held during
`android_health_once()`, then retained through the prepared/event journal and
released only after the existing guard publication is durable.

## Claim boundary

This map proves insertion points and exposes the native-canary first-read race
in the current composition. It does not implement a production scanner,
serialization guard, runner integration, device command, or activation.
Independent review of the future shared adapter and every touched runner is
required before any target-contract or mechanical activation change.
