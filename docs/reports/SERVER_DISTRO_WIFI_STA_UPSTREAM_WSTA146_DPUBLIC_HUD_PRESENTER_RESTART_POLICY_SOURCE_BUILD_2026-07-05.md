# WSTA146 D-public HUD Presenter Restart Policy Source Build Pass

Date: 2026-07-05 10:33 KST

## Verdict

WSTA146 adds the long-running appliance cleanup/restart policy for the durable
native D-public HUD presenter.  This was a source/build-only unit: no device
action, flash, reboot, Wi-Fi association, DHCP, public tunnel, packet-filter
mutation, switch-root, userdata write, or live display action ran.

Result: PASS.  V3402 built successfully from the V3401 shared-run-bind
baseline.

## Build

- Candidate: `A90 Linux init 0.11.158 (v3402-dpublic-hud-presenter-restart-policy)`
- Boot image:
  `workspace/private/inputs/boot_images/boot_linux_v3402_dpublic_hud_presenter_restart_policy.img`
- Boot SHA256:
  `57821e94857cb58b397c737a73d5f85381329f5e9ec8a6b55dc7d5dbb6a7d3f1`
- Helper SHA256:
  `fa395d3ecb6944a57487f3966948a634596157e4de3fdc39575a2fc502d1ceef`
- Source-build report:
  `docs/reports/NATIVE_INIT_V3402_DPUBLIC_HUD_PRESENTER_RESTART_POLICY_SOURCE_BUILD_2026-07-05.md`

## Source Change

The service control surface now includes:

- `dpublic-hud-presenter-service restart`
- live-visible marker `A90WSTA146 restart-stop-start-stale-pid-cleanup`
- `restart.policy`, `restart.stop_rc`, `restart.start_rc`, and `restart.done`
  telemetry
- stop-then-start restart sequencing
- fail-closed restart if the stop phase cannot release the old DRM owner
- explicit stale pidfile cleanup before a new start
- `stale-cleaned` status when a dead pidfile is removed
- `status.restart_policy` in service status output

This keeps the V3401 shared `/run/a90-dpublic` bind contract and V3400 stale
intent dedupe behavior intact.

## Validation

- `py_compile`:
  - `build_native_init_boot_v3402_dpublic_hud_presenter_restart_policy.py`
  - `test_build_native_init_boot_v3402_dpublic_hud_presenter_restart_policy.py`
- Focused V3400/V3401/V3402 tests: `15 tests OK`.
- `git diff --check`: pass.
- V3402 source build:
  - AArch64 helper/native-init compile
  - required-string audit
  - preserved ramdisk overlay
  - boot image pack
  - SHA256 capture

## Safety

The generated boot image is private and uncommitted.  V3402 has not been
flashed.  The live device remains on the previously proven V3401 resident image
from WSTA144 unless a later live-gate changes it.

## Next

WSTA147 should live-gate V3402 through `native_init_flash.py` under the normal
rollback gates, then prove `start/status/restart/status/stop`, stale pidfile
cleanup if safely synthesizable, and final health.
