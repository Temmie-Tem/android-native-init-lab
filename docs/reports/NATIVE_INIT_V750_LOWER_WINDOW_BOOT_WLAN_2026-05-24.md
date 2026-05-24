# Native Init V750 Lower-window Boot WLAN Report

- date: `2026-05-24 KST`
- runner: `scripts/revalidation/native_wifi_lower_window_boot_wlan_v750.py`
- plan evidence: `tmp/wifi/v750-lower-window-boot-wlan-plan/`
- initial preflight evidence: `tmp/wifi/v750-lower-window-boot-wlan-preflight/`
- prerequisite evidence:
  - `tmp/wifi/v750-v401-current-run/`
  - `tmp/wifi/v750-v490-current-run/`
- final preflight evidence: `tmp/wifi/v750-lower-window-boot-wlan-preflight-retry/`
- live evidence: `tmp/wifi/v750-lower-window-boot-wlan/`
- decision: `v750-lower-window-boot-wlan-control-surface-only`
- status: `pass`

## Summary

V750 executed the bounded `boot_wlan` proof inside the lower-ready window:

```text
firmware ro mounts -> pass
subsys_modem holder -> pass
QRTR RX/TX -> pass
sysmon-qmi -> pass
lower companion contract -> pass
boot_wlan write -> pass
WLFW/service69/BDF/wiphy/wlan0 -> absent
reboot cleanup -> pass
```

The run did not start service-manager, `cnss-daemon`, Wi-Fi HAL, scan/connect,
credentials, DHCP/routes, or external ping.

## Result

| item | result |
| --- | --- |
| decision | `v750-lower-window-boot-wlan-control-surface-only` |
| `subsys_modem` holder | opened |
| lower companion | executed; four lower children observable and postflight-safe |
| `boot_wlan` write | executed successfully |
| `qcwlanstate` | remained `OFF` |
| `/dev/wlan` | absent |
| wiphy / `ieee80211` | absent |
| `wlan0` | absent |
| QRTR service `69` | absent |
| WLFW/BDF | absent |
| kernel warning marker | absent |
| postflight | rebooted; native `0.9.68 (v724)` healthy |

## Evidence Highlights

- `tmp/wifi/v750-lower-window-boot-wlan/manifest.json`
- `tmp/wifi/v750-lower-window-boot-wlan/summary.md`
- `tmp/wifi/v750-lower-window-boot-wlan/native/boot-wlan-observe.txt`
- `tmp/wifi/v750-lower-window-boot-wlan/native/dmesg-delta.txt`
- `tmp/wifi/v750-lower-window-boot-wlan/native/post-boot-cat-proc-net-dev.txt`
- `tmp/wifi/v750-lower-window-boot-wlan/native/post-reboot-status.txt`

Observed marker counts:

| marker | count |
| --- | ---: |
| QRTR RX | 1 |
| QRTR TX | 1 |
| `sysmon-qmi` | 1 |
| WLFW | 0 |
| BDF | 0 |
| `wlan0` | 0 |
| wiphy | 0 |
| kernel warning | 0 |

The `boot_wlan` helper showed the control write happened, but the surface stayed
below link readiness:

```text
wlanboot.result=boot-write-executed
wlanboot.after.qcwlanstate.value=OFF
wlanboot.after.dev_wlan.exists=0
wlanboot.after.sys_class_net_wlan0.exists=0
wlanboot.after.sys_class_ieee80211.count=0
```

The dmesg delta shows the reason this is not a connection-ready state:

```text
qrtr: Modem QMI Readiness RX
qrtr: Modem QMI Readiness TX
sysmon-qmi: ... Connection established ...
icnss: Modules not initialized just return
wlan: Loading driver ...
wlan_hdd_state wlan major(478) initialized
```

## Interpretation

V750 eliminates lower-window `boot_wlan` as the missing single trigger. Even
when firmware mounts, modem holder, QRTR RX/TX, `sysmon-qmi`, and the lower
companion stack are present, `boot_wlan` only reaches the WLAN control surface.
It does not publish WLFW/service `69`, download BDF, create wiphy, or create
`wlan0`.

Therefore, repeating standalone `boot_wlan`, standalone `qcwlanstate`, or the
same lower-window `boot_wlan` proof is not useful. The next blocker is the
ICNSS/QCA "modules initialized" path before WLFW, not a credential or
connection-level blocker.

## Next Gate

V751 should classify the `icnss: Modules not initialized just return` path:

1. compare Android/native ICNSS module state and platform-driver state around
   the successful Android Wi-Fi path;
2. identify which ICNSS initialization flag or callback is absent in native;
3. keep bind/unbind, `driver_override`, module load/unload, service-manager,
   Wi-Fi HAL, scan/connect, credentials, DHCP/routes, and external ping blocked.
