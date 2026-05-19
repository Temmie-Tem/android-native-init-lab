# v364 Report: Wi-Fi HAL/Service-Manager Readiness Gate

- date: `2026-05-20`
- scope: no-scan/no-connect Wi-Fi HAL/service-manager readiness gate
- boot image change: none
- native baseline: `A90 Linux init 0.9.61 (v319)`
- plan: `docs/plans/NATIVE_INIT_V364_HAL_SERVICE_READINESS_GATE_PLAN_2026-05-20.md`
- result: `PASS`, decision `hal-service-readiness-blocked`

## Summary

V364 converts the post-V363 Wi-Fi bring-up question into a concrete readiness
gate. It reused V292/V320/V362/V363 evidence and ran current live read-only
checks through the serial bridge.

The result is intentionally conservative: Wi-Fi HAL/service-manager start-only
is still blocked. The current native environment is clean, but the service
runtime prerequisites are not currently present.

## Evidence

| item | path | decision |
| --- | --- | --- |
| plan mode | `tmp/wifi/v364-hal-service-readiness-gate-plan-20260520/` | `hal-service-readiness-gate-plan-ready` |
| live mode | `tmp/wifi/v364-hal-service-readiness-gate-live-20260520/` | `hal-service-readiness-blocked` |

Live summary:

```text
decision: hal-service-readiness-blocked
pass: True
start_only_candidate: False
reason: blocked by current-binder-devnodes, current-service-manager-processes, current-property-runtime, linkerconfig-visibility
```

Source evidence accepted:

```text
v292: binder-open-only-smoke-pass
v320: private-property-lookup-getprop-pass
v362: start-only-pass
v363: wifi-bringup-phase0-live-baseline-ready
```

## Live Observations

| check | result |
| --- | --- |
| native version | `A90 Linux init 0.9.61 (v319)` |
| wlan/wiphy surface | absent |
| Wi-Fi rfkill | absent |
| `cnss-daemon` / `cnss_diag` process | clean, `0` lines |
| Binder devnodes | absent |
| service-manager processes | absent |
| property runtime | absent |
| service binary visibility | partial, `3/6` visible |
| linkerconfig visibility | missing |
| Wi-Fi VINTF metadata | present, `61` matching lines |

Visible service binaries:

```text
stat-system-servicemanager
stat-system-hwservicemanager
stat-wificond
```

Missing/blocked runtime prerequisites:

```text
current-binder-devnodes: binder/hwbinder/vndbinder are not currently present
current-service-manager-processes: manager_process_lines=0
current-property-runtime: no property socket or global property area currently visible
linkerconfig-visibility: linkerconfig not visible
```

## Interpretation

- V362 proved bounded CNSS daemon start-only, but V363/V364 confirm that CNSS
  alone does not create the active Wi-Fi link surface.
- V292/V320 are useful primitives, but they are not a persistent service runtime.
- The next blocker is the Android service chain: Binder devnodes,
  service-manager processes, property runtime, and private linker namespace.
- Wi-Fi VINTF metadata exists, so service identity mapping is discoverable after
  the runtime prerequisites are solved.

## Guardrails

- No service-manager, Wi-Fi HAL, `wificond`, supplicant, hostapd,
  `cnss-daemon`, or `cnss_diag` was started.
- No Wi-Fi scan/connect/link-up was executed.
- No credential, DHCP, routing, rfkill unblock, ICNSS bind/unbind, firmware
  mutation, Android property write, or partition write was performed.

## Decision

- decision: `hal-service-readiness-blocked`
- start-only candidate: `false`
- next step: plan the smallest service-runtime primitive before any HAL start-only
  attempt. The likely next package is a bounded Binder/property/linker namespace
  readiness repair, not AP scan/connect.
