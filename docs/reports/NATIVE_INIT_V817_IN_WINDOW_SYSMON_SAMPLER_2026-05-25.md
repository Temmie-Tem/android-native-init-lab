# Native Init V817 In-Window Sysmon Sampler Report

## Result

- decision: `v817-in-window-mdm3-service-gap-confirmed`
- pass: `true`
- runner: `scripts/revalidation/native_wifi_in_window_sysmon_sampler_v817.py`
- evidence: `tmp/wifi/v817-in-window-sysmon-sampler/`

## What Ran

```bash
python3 -m py_compile scripts/revalidation/native_wifi_in_window_sysmon_sampler_v817.py

python3 scripts/revalidation/native_wifi_in_window_sysmon_sampler_v817.py \
  --out-dir tmp/wifi/v817-in-window-sysmon-sampler-plan-check \
  plan

python3 scripts/revalidation/native_wifi_in_window_sysmon_sampler_v817.py run

timeout 25 python3 scripts/revalidation/a90ctl.py --json version
timeout 30 python3 scripts/revalidation/a90ctl.py --json selftest
```

## Evidence Summary

| Signal | before holder | after holder | after companion |
| --- | --- | --- | --- |
| mss/modem | `OFFLINING` | `ONLINE` | `ONLINE` |
| mdm3/esoc0 | `OFFLINING` | `OFFLINING` | `OFFLINING` |
| QRTR modem readiness | `0` | `1` | `2` |
| `sysmon_qmi` runtime marker | `0` | `0` | `1` |
| service-notifier/service74 | `0` | `0` | `0` |
| WLAN-PD/WLFW/BDF/`wlan0` | absent | absent | absent |

The lower window is therefore strong enough to move mss/QRTR/sysmon, but it
does not move mdm3 or publish the WLAN-PD/WLFW services needed for ICNSS/QCACLD
startup.

## Safety

- Stock v724 remained the runtime kernel and native init build.
- No custom kernel flash, boot image write, or bootloader handoff executed.
- No `esoc0` open, bind/unbind, driver override, or module load/unload
  executed.
- No service-manager, Wi-Fi HAL, wificond, scan/connect/link-up, credential use,
  DHCP, route change, or external ping executed.
- Cleanup reboot returned to stock v724; postflight `version` and `selftest`
  passed with `selftest: pass=11 warn=1 fail=0`.
- No Wi-Fi secret material was written to tracked output.

## Classification

V817 confirms the V816 route with live in-window evidence:

```text
before holder:
  mss OFFLINING
  mdm3 OFFLINING
  no runtime service-publication

after holder:
  mss ONLINE
  QRTR readiness begins
  mdm3 still OFFLINING
  service74/WLAN-PD/WLFW still absent

after companion:
  mss ONLINE
  sysmon-qmi appears
  mdm3 still OFFLINING
  service74/WLAN-PD/WLFW/BDF/wlan0 still absent
```

The immediate blocker is not Wi-Fi HAL, credentials, DHCP, or external network
reachability. The blocker is still below those layers: mdm3/esoc0
service-locator/sysmon registration does not advance far enough to publish
WLAN-PD/WLFW.

## Next

V818 should isolate the mdm3/esoc0 service-locator/sysmon registration state
without opening `esoc0` and without starting service-manager, Wi-Fi HAL,
scan/connect, DHCP, or external ping.
