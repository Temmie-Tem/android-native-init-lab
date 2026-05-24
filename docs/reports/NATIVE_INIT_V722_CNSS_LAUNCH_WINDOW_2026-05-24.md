# Native Init V722 CNSS Launch-window Report

- date: `2026-05-24 KST`
- runner: `scripts/revalidation/native_wifi_cnss_launch_window_v722.py`
- evidence: `tmp/wifi/v722-cnss-launch-window-final/`
- latest pointer: `tmp/wifi/latest-v722-cnss-launch-window.txt`
- decision: `v722-cnss-launch-window-tradeoff-classified`
- status: `pass`

## Scope Result

V722 was host-only:

- `device_commands_executed=False`
- `daemon_start_executed=False`
- `wifi_hal_start_executed=False`
- `scan_connect_executed=False`
- `wifi_bringup_executed=False`
- `external_ping_executed=False`

No Wi-Fi credential, scan/connect, DHCP, route change, external ping,
sysfs/debugfs write, `esoc0` hold, boot image write, or partition write was
used.

## Input Evidence

| source | evidence |
| --- | --- |
| Android V622 | `tmp/wifi/v622-android-mdm-helper-timing-handoff-live-20260523-032506/v622-android-mdm-helper-timing-recapture-run/manifest.json` |
| V659 early CNSS readiness | `tmp/wifi/v659-vndservicemanager-readiness-only-live/manifest.json` |
| V660 ready CNSS retry | `tmp/wifi/v660-ready-cnss-retry-live/manifest.json` |
| V720 provider-first CNSS | `tmp/wifi/v720-same-window-cnss2-observer-final-20260524-112922/service-positive-v712/arm-v700-v119-provider-first-cnss/live/native/dmesg-delta.txt` |

## Timing Contrast

| event delta from service `180` | Android V622 | Native V720 provider-first |
| --- | ---: | ---: |
| service `74` | `6.561 ms` | `0.291 ms` |
| `cnss_diag` netlink | `1043.4 ms` | `225.623 ms` |
| `cnss-daemon` netlink | `1260.699 ms` | `3749.805 ms` |
| WLFW start | `1415.75 ms` | missing |
| WLAN-PD | `2427.362 ms` | missing |

Provider-first native also shows:

| delta | value |
| --- | ---: |
| `cnss_diag` -> `cnss-daemon` | `3524.182 ms` |

## Key Findings

| check | result |
| --- | --- |
| Android CNSS launch window | service `180/74`, `cnss_diag`, `cnss-daemon`, WLFW, WLAN-PD, QMI, BDF, fw-ready, and `wlan0` are present |
| early native CNSS paths | V659 and V660 both hit `cnss_binder_transaction_failed=1` and do not reach WLFW |
| provider-first native path | binder transaction failure is gone, but `cnss-daemon` starts after Android would already have started WLFW |
| service `74` and `cnss_diag` | both present in provider-first native evidence; not the current blockers |

## Interpretation

V722 classifies a concrete tradeoff:

```text
pre-provider / early CNSS
  -> cnss-daemon starts early enough
  -> native-only binder transaction failure
  -> no WLFW

provider-first CNSS
  -> provider/runtime issue avoided
  -> binder transaction failure removed
  -> cnss-daemon starts too late relative to Android WLFW timing
  -> no WLFW/WLAN-PD/QMI/BDF/wlan0
```

That means the next useful live unit is not another raw early CNSS retry and
not another delayed provider-first replay. The next unit should preserve the
runtime/provider fixes, but move the fresh `cnss-daemon` retry earlier in the
same service `180/74` window.

Wi-Fi HAL, scan/connect, credentials, DHCP, route changes, and external ping
remain blocked until WLFW/QMI/BDF/fw-ready/`wlan0` advances.

## Validation

Executed:

```bash
python3 -m py_compile scripts/revalidation/native_wifi_cnss_launch_window_v722.py

python3 scripts/revalidation/native_wifi_cnss_launch_window_v722.py \
  --out-dir tmp/wifi/v722-cnss-launch-window-plan-check plan

python3 scripts/revalidation/native_wifi_cnss_launch_window_v722.py \
  --out-dir tmp/wifi/v722-cnss-launch-window-final run
```

## Next Gate

V723 should be a bounded live gate below Wi-Fi HAL/connect:

1. reproduce service `180/74`;
2. preserve vndservicemanager/property/provider readiness fixes;
3. start the fresh `cnss-daemon` retry earlier than the V700/V720
   provider-first tail;
4. capture WLFW/QMI/WLAN-PD/BDF/fw-ready/`wlan0`, binder failures, cleanup, and
   post-run health.
