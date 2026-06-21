# Native Init V3044 DOOM Host Input Latency Source

Date: 2026-06-22

## Scope

Host-only DOOM input tooling update for the already-flashed V3042 resident.
No boot image was built or flashed in this iteration.

## Problem

Two independent host-side input failures were confirmed:

- The keyboard-only helper started a single `video demo doom loop-start 300`.
  On V3042 the visible helper loop becomes inactive after the requested frame
  budget, while later `doompad key` commands still return success. This makes
  gameplay appear to ignore input over time.
- The dashboard refreshed four status commands as one synchronous block every
  second. The heavy `status` command and prompt/drain waits could hold the
  serial bridge lock while a synthetic key-up was due, causing visible release
  lag.

## Changes

- Added `DoomLoopKeeper` to `host_doompad_keyboard_v3033.py`.
  It tracks the expected visible-loop lifetime, checks `loop-status` after the
  frame budget plus grace period, and restarts the visible DOOM loop when it is
  inactive.
- Added `--loop-frame-ms`, `--loop-restart-grace-ms`, and `--no-auto-restart`
  to the keyboard host tool.
- Updated the dashboard loop frame default to the V3042 observed helper cadence
  of 33 ms.
- Added fast read-only dashboard status handling for:
  - `status`
  - `video demo doom status`
  - `video demo doom loop-status`
  - `doompad status`
- Split dashboard refresh into lightweight DOOM/input refresh and heavy system
  refresh. The default heavy system refresh interval is now 10 seconds.
- Deferred dashboard refresh and auto-restart checks while a synthetic key-up is
  pending, so status polling does not block host-side key release.

## Static Validation

Commands:

```console
python3 -m py_compile \
  workspace/public/src/scripts/revalidation/host_doompad_keyboard_v3033.py \
  workspace/public/src/scripts/revalidation/host_doompad_dashboard_v3035.py

PYTHONPATH=tests python3 -m unittest \
  tests.test_host_doompad_fast_path_v3042 \
  tests.test_host_doompad_dashboard_v3035 \
  tests.test_native_doomgeneric_visible_loop_source_v3033
```

Result:

```console
Ran 18 tests in 0.002s
OK
```

## Live Host Validation

Resident:

```console
A90 Linux init 0.10.80 (v3042-doomgeneric-latency-color)
```

Short-loop restart validation used a 30-frame loop with the updated host
keeper:

```console
keeper.start.rc 0 next_check_delta_ms 1190.0
keeper.activity.t_ms 1231.0 new_commands [['video', 'demo', 'doom', 'loop-status']]
keeper.activity.t_ms 1752.7 new_commands [['video', 'demo', 'doom', 'loop-status'], ['video', 'demo', 'doom', 'loop-start', '30', '--wad', 'runtime-private', '--sha256', '<redacted-doom1-wad-sha256>']]
final.loop.active 1 pid <redacted> rc 0
```

Dashboard release gating validation:

```console
release.refresh_skipped_while_active 1
release.lag_ms_after_deadline 24.2 release_cmd_ms 14.1
dashboard.light_refresh_ms 22.2
dashboard.system_refresh_ms 648.7
dashboard.commands 6 failures 0
```

## Decision

The confirmed host-side causes are addressed without a new boot flash:

- Input no longer permanently drops after the visible helper loop exits; the
  host restarts the loop.
- Dashboard refresh no longer performs the full heavy status block every second
  and does not run while host key-up emulation is pending.

Residual latency remains possible when a user presses a key during the
infrequent heavy `status` call. The next structural improvement would be a
persistent input channel or a native batch state command, but this iteration
removes the confirmed 0.5s-class dashboard polling and finite-loop failures.
