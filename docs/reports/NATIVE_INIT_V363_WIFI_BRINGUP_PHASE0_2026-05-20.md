# v363 Report: Wi-Fi Bring-Up Phase 0 Baseline Gate

- date: `2026-05-20`
- scope: no-scan/no-connect Wi-Fi bring-up baseline gate
- boot image change: none
- native baseline: `A90 Linux init 0.9.61 (v319)`
- plan: `docs/plans/NATIVE_INIT_V363_WIFI_BRINGUP_PHASE0_PLAN_2026-05-20.md`
- result: `PASS`

## Summary

The operator requested Wi-Fi bring-up. V363 marks that direction change, but it
does not jump directly to AP scan/connect. It first captures the current native
Wi-Fi/CNSS surface after V362.

The current result is clear: CNSS daemon start-only is proven, but active Wi-Fi
link surface is still absent. The next bring-up blocker is the Android
HAL/service-manager boundary, not another blind CNSS start-only run.

## Evidence

| item | path | decision |
| --- | --- | --- |
| live baseline | `tmp/wifi/v363-bringup-preflight-20260520-001255/` | `wifi-bringup-phase0-live-baseline-ready` |
| legacy gate refresh | `tmp/wifi/v363-bringup-gate-v2-refresh-20260520/` | `no-go` |

The legacy v220 gate still reports old blocker labels:

```text
icnss_recovery
shim_policy
security_exposure
```

Those labels are too coarse for the current V317/V320/V362 state, but the
important operational conclusion remains valid: do not skip directly to
scan/connect.

## Live Observations

```text
native: A90 Linux init 0.9.61 (v319)
wlan module: present
wlan fwpath: empty
wlan con_mode: 0
wlan country_code: (null)
ICNSS node: present
ICNSS core driver: bound to platform driver icnss
QCA6390 node: present
QCA6390 driver link: absent
wlan netdev: absent
Wi-Fi rfkill: absent
cnss-daemon/cnss_diag process: absent
```

`wifiinv full` also reports:

```text
wlan_like=0
rfkill_wifi=0
module_matches=0
```

## Interpretation

- V362 proved bounded `cnss-daemon -n -l` start-only can execute and clean up.
- V363 confirms the native post-V362 baseline still has no `wlan*`, no Wi-Fi
  rfkill, and no QCA6390 driver bind.
- Therefore `cnss-daemon` alone is not enough to create the Wi-Fi link surface.
- Android bring-up evidence points to a broader service chain: Wi-Fi HAL,
  `wificond`, supplicant, and related Binder/property/service-manager runtime.

## Guardrails

- No Wi-Fi scan/connect/link-up was executed.
- No credential, DHCP, routing, supplicant, `wificond`, hostapd, or Wi-Fi HAL
  was started.
- No `cnss_diag` was started.
- No rfkill unblock, ICNSS bind/unbind, firmware mutation, Android property
  write, or partition write was performed.

## Decision

- decision: `wifi-bringup-phase0-live-baseline-ready`
- current status: active Wi-Fi bring-up direction accepted, but link surface is
  still absent
- next step: plan a no-scan/no-connect HAL/service-manager readiness gate before
  any bounded Wi-Fi HAL start-only probe or AP scan/connect action.
