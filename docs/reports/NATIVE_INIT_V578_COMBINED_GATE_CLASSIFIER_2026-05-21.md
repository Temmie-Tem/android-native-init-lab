# Native Init V578 Combined Gate Classifier Report

Date: `2026-05-21`

## Goal

Decide the next safe live gate after V575, V576, and V577 without starting any
daemon or touching the device.

## Result

- Decision: `v578-combined-companion-driver-state-needed`
- Pass: `True`
- Reason: existing evidence split the required Android sequence. V513 exercised
  `qcwlanstate` without the V95 companion stack, while V577 exercised the V95
  companion stack without `qcwlanstate` or `/dev/wlan`.
- Evidence: `tmp/wifi/v578-combined-gate-classifier`
- Device mutations: not executed
- Daemon start: not executed
- Wi-Fi bring-up: not executed

## Scope Confirmation

- V578 is host-only.
- It did not start daemons, service-manager, Wi-Fi HAL, `wificond`, supplicant,
  hostapd, or QMI payloads.
- It did not write `boot_wlan`, write `qcwlanstate`, scan, connect, link up,
  use credentials, request DHCP, change routes, ping externally, flash a boot
  image, reboot, or write Android partitions.

## Validation

```text
python3 -m py_compile scripts/revalidation/native_wifi_combined_gate_classifier_v578.py
python3 scripts/revalidation/native_wifi_combined_gate_classifier_v578.py plan
python3 scripts/revalidation/native_wifi_combined_gate_classifier_v578.py run
```

## Evidence Matrix

Android reference from V519 contains the full sequence:

| marker | count |
|---|---:|
| `wlan_driver_load` | `1` |
| `wlan_state_initialized` | `1` |
| `qrtr_modem_readiness_rx` | `1` |
| `qrtr_ns_start` | `1` |
| `sysmon_qmi_ready` | `5` |
| `service_notifier_ready` | `2` |
| `cnss_daemon_wlfw_start` | `1` |
| `qmi_server_connected` | `1` |
| `bdf_regdb` | `1` |
| `bdf_bdwlan` | `1` |
| `wlan_fw_ready` | `1` |
| `wlan0_event` | `17` |

V513 proves the old bounded driver-state path can reach the `qcwlanstate`
write attempt:

```text
decision=v513-dual-hal-driver-state-on-icnss-timeout-captured
driver_state_on=1
write_executed=1
write_rc=1
write_errno=22
private_dev_wlan=1
cnss_observable=1
wlan_count=0
phy_count=0
```

V577 proves the V95 companion/service/HAL window is clean but lacks the driver
state part of the Android sequence:

```text
decision=v577-v95-broader-not-sufficient
identity_contracts_ok=True
iwifi_status=ERROR_UNKNOWN/9
qipcrtr_sockets_window=0
qcwlanstate_write=0
dev_wlan_after_iwifi=0
qmi_server_connected=0
wlan_fw_ready=0
wlan0_event=0
```

## Interpretation

The previous branches each proved only half of the Android ordering:

1. V513: `/dev/wlan` and `qcwlanstate ON` were exercised, but without the V95
   root-start `rmt_storage`/`tftp_server` repair and without the full companion
   + `wificond` + `IWifi.start()` stack.
2. V577: the V95 companion + service-manager + dual-HAL + `wificond` +
   `IWifi.start()` stack was exercised, but `/dev/wlan` was absent and
   `qcwlanstate` was intentionally not written.

Therefore another scan/connect attempt would still be premature. The next
aligned live proof is a combined bounded window that joins these two branches.

## Next Gate

V579 should be a bounded V95 combined proof:

1. first materialize `/dev/wlan` with the existing `boot_wlan` helper only if
   the current boot lacks the node;
2. run the V95 companion + service-manager + dual-HAL + `wificond` +
   `IWifi.start()` window;
3. add exactly one guarded `qcwlanstate ON` write inside that same bounded
   window;
4. keep QMI payload, supplicant, hostapd, scan/connect/link-up, credentials,
   DHCP, routes, and external ping blocked;
5. observe whether any of these appear: QRTR socket count, WLFW start/thread,
   QMI server connected, BDF request, WLAN firmware ready, `wlan0`, or a
   better `IWifi.start()` result.

Wi-Fi objective remains incomplete until native init connects to Wi-Fi and
external ping passes.
