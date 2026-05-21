# Native Init V515 Android/Native ICNSS Sequence Delta

## Purpose

V515 converts the V514 conclusion into a reproducible host-only comparator.

It compares:

- Android boot-complete Wi-Fi/ICNSS evidence from `tmp/wifi/v206-android-icnss-cnss-map/android/commands/dmesg-wifi-cnss-tail.txt`
- Native-init V514 readiness evidence from `tmp/wifi/v514-icnss-module-readiness/native/dmesg.txt`
- V514 machine decision from `tmp/wifi/v514-icnss-module-readiness/manifest.json`

No live device command is executed.

## Guardrails

- No daemon start.
- No qcwlanstate write.
- No boot_wlan write.
- No scan/connect.
- No DHCP/route mutation.
- No external ping.
- No partition or firmware mutation.

## Added Artifact

- `scripts/revalidation/native_wifi_android_native_sequence_delta_v515.py`
  - host-only log comparator
  - extracts first occurrence of Android/native ICNSS/WLAN readiness markers
  - verifies V514 classified the native timeout
  - identifies required Android firmware-readiness markers missing from native init

## V515 Result

Command:

```bash
python3 scripts/revalidation/native_wifi_android_native_sequence_delta_v515.py run
```

Result:

```text
decision: v515-android-native-sequence-gap-classified
pass: True
reason: Android reaches CNSS/WLFW/QMI/BDF/FW-ready before wlan0, while native reaches qcwlanstate ON then times out without those markers
next: implement V516 bounded cnss_diag + cnss-daemon WLFW readiness proof before any scan/connect
device_commands_executed: False
device_mutations: False
wifi_bringup_executed: False
evidence: /home/temmie/dev/A90_5G_rooting/tmp/wifi/v515-android-native-sequence-delta
```

## Key Android Sequence

The Android baseline reaches these ordered markers:

```text
4.833786  firmware_mounts        apnhlos -> /vendor/firmware_mnt mounted
5.854769  wlan_loading_driver    QCACLD driver load starts
5.862068  wlan_state_initialized /dev/wlan/qcwlanstate layer initialized
6.356205  qrtr_modem_readiness   modem QMI readiness observed
6.957467  qrtr_ns_start          vendor.qrtr-ns starts
7.807753  cnss_diag_start        cnss_diag starts
7.884353  cnss_diag_netlink      cnss_diag opens netlink
8.111985  cnss_daemon_start      cnss-daemon starts
8.294932  cnss_daemon_wlfw_start WLFW start begins
9.423450  qmi_server_connected   ICNSS QMI server connects
9.496028  bdf_regdb              regdb.bin BDF requested
9.511402  bdf_bdwlan             bdwlan.bin BDF requested
12.572290 wifi_turning_on        qcwlanstate ON path
14.571374 wlan_fw_ready          WLAN firmware is ready
14.578320 wcnss_cfg_request      WCNSS_qcom_cfg.ini requested
14.641400 wma_service_ready      WMA service-ready event
14.724770 wlan0_event            wlan0 netdev appears
```

## Key Native Sequence

The native-init V514/V513 evidence reaches only:

```text
40018.876612 modules_not_initialized ICNSS reports modules not initialized
40114.829297 wlan_loading_driver     QCACLD driver load starts
40114.830952 wlan_state_initialized  /dev/wlan/qcwlanstate layer initialized
40240.593107 cnss_daemon_netlink     cnss-daemon opens netlink
41482.593451 wifi_turning_on         qcwlanstate ON path
41503.200250 timed_out               qcwlanstate/ICNSS wait times out
```

It does not reach:

- `cnss_diag_start`
- `cnss_daemon_wlfw_start`
- `qmi_server_connected`
- `bdf_regdb`
- `bdf_bdwlan`
- `wlan_fw_ready`
- `wcnss_cfg_request`
- `wma_service_ready`
- `wlan0_event`

## Interpretation

V515 confirms the next blocker is not raw `/dev/wlan` presence and not merely Binder/private namespace. Native init can reach the qcwlanstate ON attempt, but it does so before the Android-style CNSS/WLFW/QMI/BDF readiness sequence is reproduced.

The next implementation should therefore avoid scan/connect work and avoid another direct qcwlanstate retry until a bounded userspace readiness proof observes at least one of:

- `cnss-daemon wlfw_start`
- `icnss_qmi: QMI Server Connected`
- BDF download request for `regdb.bin` or `bdwlan.bin`
- `icnss: WLAN FW is ready`

## Source References

- Android init reference shows `cnss_diag` as a oneshot late_start service and `cnss-daemon` as a late_start system service:
  - https://android.googlesource.com/device/google/marlin/+/e8ea1d15b6e35e4ba0c1eeeba47fe712af0fba92/init.common.rc
- QCACLD source shows `boot_wlan` starts WLAN initialization, `hdd_wlan_startup()` starts modules, and “Modules not initialized just return” is emitted when the driver status is still uninitialized:
  - https://android.googlesource.com/kernel/msm/+/android-msm-wahoo-4.4-oreo-m2/drivers/staging/qcacld-3.0/core/hdd/src/wlan_hdd_main.c

## Validation

```bash
python3 -m py_compile scripts/revalidation/native_wifi_android_native_sequence_delta_v515.py
git diff --check -- scripts/revalidation/native_wifi_android_native_sequence_delta_v515.py docs/reports/NATIVE_INIT_V515_ANDROID_NATIVE_SEQUENCE_DELTA_2026-05-21.md
```

Both passed.

## Next Gate

Recommended V516:

1. Build a bounded CNSS userspace readiness proof.
2. Start with `cnss_diag` before `cnss-daemon`, mirroring the Android sequence.
3. Wait for WLFW/QMI/BDF/firmware-ready markers.
4. Do not scan/connect or ping externally in V516.
5. Only if V516 observes readiness markers, proceed to a separate bounded qcwlanstate/HAL retry gate.
