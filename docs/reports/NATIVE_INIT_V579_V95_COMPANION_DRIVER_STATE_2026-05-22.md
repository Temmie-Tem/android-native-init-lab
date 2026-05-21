# Native Init V579 V95 Companion Driver-State Proof

- date: `2026-05-22 KST`
- objective: combine the V95 Android-like companion stack with guarded `/dev/wlan` driver-state `ON` write, without scan/connect/link-up or external ping
- status: `blocked`; Wi-Fi external ping is **not** complete

## Scope

- Keep native init at the recovered stable baseline: `A90 Linux init 0.9.61 (v319)`.
- Use `a90_android_execns_probe v96` with the V95 companion ordering:
  - `servicemanager`
  - `hwservicemanager`
  - `vndservicemanager`
  - `qrtr-ns`
  - `rmt_storage`
  - `tftp_server`
  - `pd-mapper`
  - both Wi-Fi HAL daemons
  - `cnss_diag`
  - `wificond`
  - `cnss-daemon`
- Materialize `/dev/wlan` from the qcwlanstate char-device class before the combined proof.
- During the bounded companion/HAL/IWifi window, write static `ON` to `/dev/wlan`.

## Guardrails

- No SSID/password read.
- No supplicant or hostapd start.
- No scan/connect/link-up/DHCP/route change.
- No external ping.
- No QMI payload injection.
- No Android partition write.
- Helper-owned live processes are expected to be terminated after the bounded window.

## Implementation

- `stage3/linux_init/helpers/a90_android_execns_probe.c`
  - bumped helper marker to `a90_android_execns_probe v96`
  - allows `--allow-wlan-driver-state-on` for `wifi-companion-dual-hal-wificond-lshal-then-iwifi-start`
  - emits `wifi_companion_hal_order.qcwlanstate_write=1` when the guarded write is enabled
  - writes `ON` only after the companion children and service query window have started
- `scripts/revalidation/wifi_execns_helper_v96_deploy_preflight.py`
  - validates and deploys helper v96 with the exact no-bring-up approval boundary
- `scripts/revalidation/native_wifi_v95_companion_driver_state_v579.py`
  - runs the bounded V579 proof
  - records `/dev/wlan` presence, driver-state write result, `IWifi.start()` result, QRTR counters, and postflight safety

## Build and Deploy Evidence

```text
artifact: tmp/wifi/v579-a90_android_execns_probe-v96/a90_android_execns_probe
sha256: 97982aa10d61297691ac87688336fb51183d21a70958660697c7462e009b84f0
marker: a90_android_execns_probe v96
```

Deploy decision:

```text
decision: execns-helper-v96-deploy-pass
```

Evidence:

- `tmp/wifi/v579-execns-helper-v96-deploy-preflight/`

## Devnode Precondition

`a90_wlanbootctl v2` first materialized the qcwlanstate class via `boot-observe`.
V509 then created the fixed `/dev/wlan` node from `/sys/class/wlan/wlan/dev`.

```text
decision: v509-wlan-devnode-ready
pass: True
reason: fixed /dev/wlan node now matches qcwlanstate char device
```

Live node:

```text
crw-rw---- 1 1010 1010 478, 0 /dev/wlan
/sys/class/wlan/wlan/dev = 478:0
```

Evidence:

- `tmp/wifi/v579-wlanboot-v2-boot-observe/`
- `tmp/wifi/v579-v509-wlan-devnode-preflight/`
- `tmp/wifi/v579-v509-wlan-devnode-run/`

## V579 Result

Command result:

```text
decision: v579-driver-state-cleanup-review
pass: False
reason: helper-owned children were not proven cleaned
```

Key proof:

```text
driver_state_on=True
driver_state_write_executed=True
driver_state_write_rc=1
driver_state_write_errno=22
driver_state_write_duration_ms=20205
private_dev_wlan_before=1
private_dev_wlan_after_iwifi=1
iwifi_start_wifi_status=UNDECODED/4294967295
qipcrtr_sockets_window=0
qrtr_readback_qmi_attempted=0
qrtr_readback_service_events=0
wlan_count_window=0
phy_count_window=0
scan_connect_linkup=False
external_ping=False
```

Postflight detail:

```text
wifi_companion_hal_order.all_postflight_safe=0
wifi_companion_hal_order.child.wifi_hal_legacy.postflight_safe=0
wifi_companion_hal_order.child.wifi_hal_legacy.reaped=0
wifi_companion_hal_order.child.wifi_hal_legacy.kill_sent=1
wifi_hal_composite_start.property_service_shim.postflight_safe=1
```

Immediate device health after the run was safe:

```text
selftest: pass=11 warn=1 fail=0
exposure: guard=ok warn=0 fail=0 ncm=absent tcpctl=stopped rshell=stopped boundary=usb-local
```

The later process table no longer contained the transient `android.hardware.wifi@1.0-service` process.
Native PID1 reported it as reaped by the global reaper:

```text
reaper: total=1 last_pid=987 last=signal=15
```

Evidence:

- `tmp/wifi/v579-v95-companion-driver-state/`

## Read-Only Reconfirmation

After V579, the V514 read-only classifier still reports the same blocker:

```text
decision: v514-wlan-module-init-timeout-classified
pass: True
reason: WLAN init starts but does not reach driver-loaded; ICNSS/modules-not-initialized timeout is the current blocker
next: compare Android boot order and build corrected native init sequence
```

Evidence:

- `tmp/wifi/v579-v514-current-readback/`

## Interpretation

- The V578 hypothesis was tested: the V95 companion stack plus `/dev/wlan` driver-state `ON` in the same bounded window still does not produce QRTR/QMI/BDF/WLFW readiness.
- The private runtime has `/dev/wlan`, both HALs can register far enough for `IWifi/default`, and `cnss_diag`/`cnss-daemon` reach `cld80211` netlink.
- The driver-state write reaches the WLAN path but ends with `EINVAL` after about 20 seconds, matching the earlier V513 `Modules not initialized` blocker.
- `IWifi.start()` is not a valid next gate yet because the lower driver/module readiness gate has not advanced.
- The cleanup gate should be tightened in the next helper so a child reaped by native PID1 after helper timeout is classified from a delayed postflight process check instead of masking the primary ICNSS blocker.

## Next Gate

Recommended V580:

1. Add a delayed postflight residual-process classifier for helper-owned Wi-Fi children.
2. Treat `qcwlanstate ON rc=1 errno=22` plus `icnss: Modules not initialized just return` as a first-class ICNSS module-init blocker when the delayed process table is clean.
3. Keep scan/connect/external ping blocked.
4. Compare Android boot order against the native sequence around ICNSS module init, service locator, QRTR, and WLAN-PD readiness.
5. Do not retry `IWifi.start()` or qcwlanstate `ON` unless a new below-qcwlanstate dependency is changed.
