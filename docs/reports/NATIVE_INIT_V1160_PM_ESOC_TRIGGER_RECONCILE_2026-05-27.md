# Native Init V1160 PM eSoC Trigger Reconcile Report

Date: `2026-05-27`

## Result

- Decision: `v1160-late-per-proxy-esoc-trigger-route-classified`
- Pass: `true`
- Classifier: `scripts/revalidation/native_wifi_pm_esoc_trigger_reconcile_v1160.py`
- Evidence: `tmp/wifi/v1160-pm-esoc-trigger-reconcile/manifest.json`
- Summary: `tmp/wifi/v1160-pm-esoc-trigger-reconcile/summary.md`

## Summary

V1160 reconciles the Android-good V1159 evidence with the latest native PM
path.  The important delta is no longer `mdm_helper` hold time:

```text
Android:
  vendor.per_proxy starts
    -> pm-service Binder thread enters __subsystem_get(esoc0)
      -> icnss_qmi connected
        -> BDF downloads
          -> FW-ready
            -> wlan0

Native V1139:
  provider + cnss-daemon + mdm_helper /dev/esoc-0 positive
    -> per_proxy intentionally skipped
      -> no /dev/subsys_esoc0, MHI, ks, service69, mdm3 ONLINE, or wlan0
```

The next native gate should therefore reproduce the missing PM-service Binder
request by starting `pm-proxy` late, after the upper PM/CNSS path and
`mdm_helper` `/dev/esoc-0` readiness are already positive.

## Classification

| evidence | ok | detail |
| --- | --- | --- |
| Android lower chain | `true` | FW-ready + `wlan0` observed |
| Android PM-service owner | `true` | `pm-service` Binder samples in `mdm_subsys_powerup` |
| Android `per_proxy` before eSoC | `true` | `per_proxy=8.824458`, `esoc0=9.491382` |
| PM proxy actionable codes | `true` | V1099 saw `connect=1`, `ack=1`, transaction `0x3/0x5` |
| pre-CNSS `per_proxy` blocker | `true` | V1107 proved the pre-CNSS route holds the modem mutex |
| V1139 `per_proxy` skipped | `true` | `per_proxy_start_executed=0`, `child.per_proxy.start_skipped=1` |
| V1139 upper path positive | `true` | `pm_proxy_helper`, `pm-service`, and `mdm_helper /dev/esoc-0` present |
| V1139 lower missing | `true` | `/dev/subsys_esoc0=0`, MHI `0`, `ks=0`, service69 `0` |

## Android Timing

| event | dmesg seconds |
| --- | --- |
| `vendor.per_proxy_helper` start | `6.665643` |
| `pm_proxy_helper` modem get | `6.673646` |
| `vendor.per_proxy` start | `8.824458` |
| `pm-service` modem get | `8.854707` |
| `vendor.mdm_helper` start | `9.259917` |
| `cnss-daemon` start | `9.265216` |
| `pm-service` esoc0 get | `9.491382` |
| `icnss_qmi` connected | `10.263706` |
| BDF downloads | `10.333750` / `10.347832` |
| FW-ready | `15.344607` |
| `wlan0` event | `15.784281` |

## Next Gate

V1161 should add a bounded late-`per_proxy` gate:

1. Start service managers, `pm_proxy_helper`, `pm-service`, and `cnss-daemon`.
2. Confirm upper PM/CNSS and `mdm_helper` `/dev/esoc-0` readiness.
3. Start `pm-proxy` as the eSoC trigger.
4. Capture `pm-service` Binder wchan/syscall/stack, `/dev/subsys_esoc0`, MHI
   pipe, `ks`, service69, `mdm3`, and WLFW markers.
5. Keep Wi-Fi HAL, scan/connect, credentials, DHCP/routes, external ping, and
   boot-image writes disabled.

## Validation

Executed:

```bash
python3 -m py_compile scripts/revalidation/native_wifi_pm_esoc_trigger_reconcile_v1160.py
python3 scripts/revalidation/native_wifi_pm_esoc_trigger_reconcile_v1160.py
```

Result:

```text
decision: v1160-late-per-proxy-esoc-trigger-route-classified
pass: True
```

## Safety

- Host-only classifier; no device command executed.
- No PM actor, `mdm_helper`, Wi-Fi HAL, scan/connect, credential use, DHCP,
  route, or external ping executed.
- No eSoC open/ioctl, GPIO write, partition write, flash, or reboot executed.
