# Native Init V576 QRTR Namespace Surface Report

Date: `2026-05-21`

## Goal

After the V575 helper v95 init-root repair, re-check the native QRTR/modem
readiness surface without starting any daemon or Wi-Fi component.

## Result

- Decision: `v576-qrtr-namespace-surface-absent`
- Pass: `True`
- Reason: V95 companion baseline is clean, but native still has `QIPCRTR`
  sockets `0`, no `/proc/net/qrtr`, and no QMI/BDF/FW markers.
- Evidence: `tmp/wifi/v576-qrtr-namespace-surface`
- Device mutations: not executed
- Daemon start: not executed
- Wi-Fi bring-up: not executed

## Scope Confirmation

- V576 only ran read-only native commands.
- It did not start companion daemons, service-manager, Wi-Fi HAL, `wificond`,
  supplicant, hostapd, or QMI payloads.
- It did not scan, connect, link up, use credentials, request DHCP, change
  routes, ping externally, flash a boot image, reboot, or write Android
  partitions.

## Validation

```text
python3 -m py_compile scripts/revalidation/native_wifi_qrtr_namespace_surface_v576.py
python3 scripts/revalidation/native_wifi_qrtr_namespace_surface_v576.py plan
python3 scripts/revalidation/native_wifi_qrtr_namespace_surface_v576.py run
```

## V575 Baseline

The V575 helper v95 companion proof is now a valid clean baseline:

```text
decision=v534-companion-start-only-no-fw-marker
helper_result=companion-window-pass
all_observable=True
all_postflight_safe=True
child_started=6
qrtr_before_ok=False
qrtr_after_ok=False
```

It still had no readiness markers:

```text
qmi_server_connected=0
qrtr_modem_readiness=0
bdf_regdb=0
bdf_bdwlan=0
wlan_fw_ready=0
wlan0_event=0
```

## Current Native Surface

| surface | value |
|---|---:|
| `QIPCRTR` protocol present | `true` |
| `QIPCRTR` sockets | `0` |
| `/proc/net/qrtr` present | `false` |
| `/dev/qrtr` present | `false` |
| service-notifier debugfs surface | `false` |
| `/sys/class/remoteproc` present | `false` |
| `/sys/bus/msm_subsys/devices` present | `true` |
| `/sys/bus/rpmsg/devices` present | `true` |
| active target process hits | `0` |
| Wi-Fi netdev/wiphy hits | `0` |

Current dmesg readiness markers:

```text
qrtr_modem_readiness_rx=0
qrtr_modem_readiness_tx=0
sysmon_qmi_ready=0
service_notifier_ready=0
wlan_pd_indication=0
qmi_server_connected=0
cnss_daemon_wlfw_start=0
wlfw_thread=0
bdf_regdb=0
bdf_bdwlan=0
wlan_fw_ready=0
wlan0_event=0
```

## Interpretation

V576 confirms the V575 repair did not leave residual processes and did not
advance native QRTR/modem readiness by itself.

The remaining blocker is not rmt/tftp start identity anymore. It is now one of
these earlier surfaces:

1. QRTR namespace/procfs surface is not available in native init despite
   `AF_QIPCRTR` being registered.
2. Modem/service-notifier/sysmon readiness does not enter the Android-like
   sequence in the current native state.
3. The late interactive companion-only window is still missing another Android
   boot/runtime dependency.

The V576 dmesg focus also shows `cnss-daemon` reaches netlink and later binder
error paths during the prior V575 window. That makes a V95 broader replay with
service-manager/HAL ordering a better next proof than a scan/connect attempt.

## Next Gate

V577 should reuse the V95 init-root contracts in the broader bounded
service-manager + companion + dual-HAL + `wificond` + `IWifi.start()` window:

1. keep scan/connect/link-up, credentials, DHCP, routes, and external ping
   blocked;
2. start only the bounded service/HAL window already used in earlier proofs;
3. verify whether the V95 root-start repair changes `IWifi.start()` result,
   QRTR socket count, QMI/BDF/WLFW markers, or `wlan0`;
4. if QRTR/QMI/BDF or `wlan0` appears, then move to scan-only; otherwise stay
   in readiness dependency analysis.

Wi-Fi objective remains incomplete until native init connects to Wi-Fi and
external ping passes.
