# Native Init V1136 Post-PM eSoC Gate Planner Report

Date: `2026-05-27`

## Result

- Decision: `v1136-post-pm-mdm-helper-composite-support-required`
- Pass: `true`
- Planner: `scripts/revalidation/native_wifi_post_pm_esoc_gate_planner_v1136.py`
- Evidence: `tmp/wifi/v1136-post-pm-esoc-gate-planner/manifest.json`
- Plan: `docs/plans/NATIVE_INIT_V1136_POST_PM_ESOC_MDM2AP_GATE_PLAN_2026-05-27.md`

## Summary

V1136 is host-only. It checks whether the current helper can directly execute
the V1135-selected next gate:

```text
V1134 upper PM/CNSS path
  + post-PM mdm_helper/eSoC/MDM2AP observer
```

It cannot. Helper `v213` contains the two separate building blocks:

- `wifi-companion-pm-service-trigger-observer`
- `wifi-companion-mdm-helper-runtime-contract-capture`

but the PM observer path explicitly records:

```text
pm_service_trigger_observer.mdm_helper_start_executed=0
```

There is no current composite mode that preserves the V1134 PM/CNSS success
while also starting or observing `mdm_helper` and the eSoC/MDM2AP lower path.

## Evidence

| Evidence | Result |
| --- | --- |
| V1135 ready | `true` |
| V1134 upper reference | `true` |
| Android mdm_helper/eSoC contract | `true` |
| helper has separate building blocks | `true` |
| current helper lacks post-PM mdm_helper composite | `true` |

Android V1024 remains the reference contract:

```text
pm-service      -> /dev/subsys_modem
pm_proxy_helper -> /dev/subsys_modem
mdm_helper      -> /dev/esoc-0
```

V1134 now reproduces the PM/CNSS side, so the next implementation must add the
`mdm_helper`/eSoC observation side without broadening into Wi-Fi connect work.

## Next

V1137 should be source/build-only. Add a guarded helper mode that:

1. reuses the V1134 PM/CNSS prerequisite ordering;
2. starts or observes `mdm_helper` through the repaired runtime-contract path;
3. captures `/dev/esoc-0`, `ESOC_WAIT_FOR_REQ`, MDM2AP/GPIO142, `mdm3`, QRTR
   services `69/74/180`, WLFW/BDF/MHI, and `wlan0`;
4. forbids Wi-Fi HAL, scan/connect, credentials, DHCP/route, external ping,
   boot image writes, partition writes, and flash.

No live V1137 run should happen until the helper mode, allow flags, timeout,
and cleanup contract are built and statically verified.

## Validation

Executed:

```bash
python3 -m py_compile scripts/revalidation/native_wifi_post_pm_esoc_gate_planner_v1136.py
python3 scripts/revalidation/native_wifi_post_pm_esoc_gate_planner_v1136.py
```

Result:

```text
decision: v1136-post-pm-mdm-helper-composite-support-required
pass: True
```
