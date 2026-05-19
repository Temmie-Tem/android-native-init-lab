# V380 Execns Helper V13 Deploy + Start-Only Live Report

## Result

- deploy decision: `execns-helper-v12-deploy-pass` (inherited label from V375 mechanics)
- live decision: `service-manager-start-only-live-runtime-gap`
- classifier decision: `service-manager-runtime-gap-property-runtime-required`
- overall pass: `true` for bounded smoke and clean postflight
- device build: `A90 Linux init 0.9.61 (v319)`
- helper: `a90_android_execns_probe v13`
- daemon_start_executed: `true`
- wifi_bringup_executed: `false`

## Evidence

| phase | path | result |
| --- | --- | --- |
| pre/deploy/live root | `tmp/wifi/v380-v13-deploy-and-live-20260520-024112` | collected |
| deploy | `tmp/wifi/v380-v13-deploy-and-live-20260520-024112/v380-deploy` | v13 installed by serial fallback |
| live start-only | `tmp/wifi/v380-v13-deploy-and-live-20260520-024112/v380-live` | runtime gap, clean postflight |
| post-live classify | `tmp/wifi/v380-v13-deploy-and-live-20260520-024112/v378-classify-after-v13` | property runtime required |

## Deploy

- NCM device side was ready, but host IP setup needed sudo TTY; deploy used serial fallback.
- Transfer method: serial `appendfile + uudecode`.
- Serial chunks: `910`.
- Remote SHA verified:
  - `9866c8f1e7c346906f4a400ee431ea35ed3880c157e5ee4e8b1757377dcfffa8  /cache/bin/a90_android_execns_probe`
- Remote usage verified:
  - `a90_android_execns_probe v13`
  - `service-manager-start-only`
  - `--allow-service-manager-start-only`

## Live Observations

| target | result | reason | postflight |
| --- | --- | --- | --- |
| `system-servicemanager` | `start-only-runtime-gap` | `child-exited-before-observe-window` | clean |
| `system-hwservicemanager` | `start-only-pass` | `observed-until-timeout-clean-stop` | clean |

## Binder Result

Private Binder device provisioning worked inside the helper namespace:

- `context.dev_binder.exists=1 mode=666 rdev=10:81`
- `context.dev_hwbinder.exists=1 mode=666 rdev=10:80`
- `context.dev_vndbinder.exists=1 mode=666 rdev=10:79`

This means the V376/V378 missing Binder devnode blocker is resolved for the start-only namespace.

## Remaining Gap

The classifier now reports `service-manager-runtime-gap-property-runtime-required`.
Evidence from both target runs includes:

- `context.dev_properties.exists=0`
- `context.data.exists=0`
- `servicemanager` aborts with `SIGABRT`
- `hwservicemanager` can stay observable until timeout, but still logs old/missing property runtime state

## Interpretation

V380 moved the stack forward: Binder is no longer the first blocker. The next actionable blocker is private property/runtime materialization for service-manager start-only, especially `/dev/__properties__` and minimal `/data` expectations inside the helper namespace.

## Next

- V381: plan private property area + minimal `/data` namespace materialization for service-manager start-only.
- Continue blocking Wi-Fi HAL/start/bring-up until service-manager start-only is stable and classified clean.
