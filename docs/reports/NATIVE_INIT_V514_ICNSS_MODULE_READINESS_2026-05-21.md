# Native Init V514 ICNSS/WLAN Module-Readiness Classifier

- date: `2026-05-21`
- objective: classify why native-init Wi-Fi still cannot reach scan/connect/external-ping after V513 proved the private `/dev/wlan` ON path
- status: `in-progress`; Wi-Fi external ping is **not** complete

## Scope

- Run a read-only classifier against current native-init state.
- Reuse V513 evidence as the authoritative proof that private `/dev/wlan` ON was actually attempted.
- Capture current dmesg/sysfs/WLAN status without starting daemons or writing any Wi-Fi control node.
- Compare the native blocker shape against prior Android boot-complete evidence.

## Guardrails

- No SSID/password read.
- No qcwlanstate write.
- No `boot_wlan` write.
- No scan/connect/link-up/DHCP/external ping.
- No daemon start.
- No firmware mutation.
- No ICNSS bind/unbind.

## Implementation

- `scripts/revalidation/native_wifi_icnss_module_readiness_v514.py`
  - collects current native health, `a90_wlanbootctl status`, ICNSS sysfs, WLAN module parameters, and dmesg
  - parses dmesg for canonical WLAN readiness markers
  - imports V513 manifest and verifies that the private ON write proof exists
  - classifies the blocker without mutating device state

## V514 Result

Command result:

```text
decision: v514-wlan-module-init-timeout-classified
pass: True
reason: WLAN init starts but does not reach driver-loaded; ICNSS/modules-not-initialized timeout is the current blocker
next: compare Android boot order and build corrected native init sequence
device_mutations: False
wifi_bringup_executed: False
```

Evidence:

- `tmp/wifi/v514-icnss-module-readiness/`

## Current Native State

WLAN surface:

```text
qcwlanstate=OFF
dev_wlan=478:0
wlan0_exists=0
ieee80211_count=0
proc_net_dev_wlan=0
```

Dmesg pattern counts:

```text
loading_driver=1
state_initialized=1
driver_loaded=0
driver_load_failure=0
wifi_turning_on=2
timed_out=2
modules_not_initialized=85
cnss_daemon_netlink=55
```

Latest key native markers:

```text
wlan: Loading driver v5.2.022.3Q-HL210630A ...
wlan_hdd_state wlan major(478) initialized
a90_android_exe: Wifi Turning On from UI
cnss-daemon: netlink_create ...
Timed-out!!
icnss: Modules not initialized just return
```

V513 link:

```text
decision=v513-dual-hal-driver-state-on-icnss-timeout-captured
write_executed=True
write_rc=1
write_errno=22
wlan_count=0
phy_count=0
micro_result=service-query-timeout
```

## Android Reference Delta

Existing Android boot-complete evidence:

- `tmp/wifi/v206-android-icnss-cnss-map/android/commands/dmesg-wifi-cnss-tail.txt`
- `tmp/wifi/v204-android-baseline/root-dmesg-wifi-tail.txt`

Android reaches a richer sequence:

```text
init: [libfs_mgr]__mount(source=apnhlos,target=/vendor/firmware_mnt,type=vfat)=0
wlan: Loading driver v5.2.022.3Q-HL210630A ...
wlan_hdd_state wlan major(478) initialized
qrtr: Modem QMI Readiness ...
icnss: Assigning MAC from Macloader ...
init: starting service 'cnss_diag'...
init: starting service 'cnss-daemon'...
cnss-daemon wlfw_start: Starting
icnss_qmi: QMI Server Connected: state: 0x980
cnss-daemon wlfw_send_bdf_download_req: BDF file : regdb.bin
cnss-daemon wlfw_send_bdf_download_req: BDF file : bdwlan.bin
Wifi Turning On from UI
icnss: WLAN FW is ready: 0xd87
ueventd: firmware: loading 'wlan/qca_cld/WCNSS_qcom_cfg.ini'
wlan: [I:WMA] wma_rx_service_ready_event: Firmware build version ...
dev : wlan0 : event : 16
dev : swlan0 : event : 16
```

Native V513 reaches only:

```text
Wifi Turning On from UI
cnss-daemon netlink activity
Timed-out!!
icnss: Modules not initialized just return
```

Missing native readiness markers:

- `cnss_diag` sidecar start before `cnss-daemon`
- `cnss-daemon wlfw_start`
- `icnss_qmi: QMI Server Connected`
- BDF downloads for `regdb.bin` and `bdwlan.bin`
- `icnss: WLAN FW is ready`
- `WCNSS_qcom_cfg.ini` firmware request
- `wma_rx_service_ready_event`
- `wlan0`/`swlan0` netdev events

## Interpretation

V514 narrows the blocker from “Wi-Fi HAL/native namespace gap” to “ICNSS/WLFW firmware readiness sequence gap”.

The private ON write is reaching the WLAN driver, but native does not reproduce the Android ordering that brings WLFW/QMI/BDF readiness online before the useful Wi-Fi surface appears. Starting Wi-Fi HAL and `cnss-daemon` alone is insufficient.

The most important Android/native delta is that Android starts `cnss_diag`, runs `cnss-daemon` long enough to reach WLFW/QMI/BDF activity, then receives `WLAN FW is ready` before `wlan0` appears. Native V513 attempts ON inside a bounded window but never reaches those readiness markers.

## Source References

- QCACLD qcwlanstate and WLAN module readiness path:
  - https://android.googlesource.com/kernel/msm/+/android-msm-wahoo-4.4-oreo-m4/drivers/staging/qcacld-3.0/core/hdd/src/wlan_hdd_main.c

## Follow-Up

V515 completed the host-only Android/native sequence comparator and classified the gap as `v515-android-native-sequence-gap-classified`.

Recommended V516:

1. Keep ICNSS bind/unbind and firmware mutation blocked.
2. Prepare a bounded native CNSS userspace-sequence proof:
   - include `cnss_diag` before `cnss-daemon`
   - wait for WLFW/QMI/BDF readiness markers before any qcwlanstate retry
   - keep scan/connect/external ping disabled
   - keep cleanup/postflight checks mandatory
3. Only if V516 observes WLFW/QMI/BDF or `WLAN FW is ready`, proceed to a new bounded qcwlanstate/HAL retry.
