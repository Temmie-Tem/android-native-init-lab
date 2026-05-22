# Native Init V610 QMI Publication Precondition Report

- date: `2026-05-23 KST`
- status: `classified`; Wi-Fi external ping is **not** complete
- classifier: `scripts/revalidation/native_wifi_qmi_publication_precondition_v610.py`
- evidence: `tmp/wifi/v610-qmi-publication-precondition/`
- Android dmesg input: `tmp/wifi/v515-android-native-sequence-delta/inputs/android-dmesg-wifi-cnss-tail.txt`
- Android subsystem input:
  `tmp/wifi/v591-android-subsys-state-sample-handoff/v590-android-subsys-state-sample-run/android-subsys-state.txt`
- native input: `tmp/wifi/v609-post-sysmon-20260523-004918/v609-observer-live/`

## Scope

V610 is host-only. It compared existing Android reference evidence against the
V609 native no-CNSS observer evidence.

It did not contact the device, start daemons, start service-manager, start Wi-Fi
HAL, write `qcwlanstate`, send QMI payloads, scan/connect/link-up, use
credentials, run DHCP, change routes, ping externally, flash boot images, or
write partitions.

## Result

```text
decision: v610-companion-surface-gap
pass: True
reason: Android reaches service-notifier with mss/mdm3 ONLINE and sibling sysmon services, while native V609 reaches QRTR TX/sysmon with mss ONLINE but mdm3 remains OFFLINING
wifi_bringup_executed: False
```

## Key Comparison

Android lower publication path:

```text
mss_state=ONLINE
mdm3_state=ONLINE
sysmon_slpi=present
sysmon_cdsp=present
sysmon_adsp=present
sysmon_esoc0=present
service_notifier_180=present
service_notifier_74=present
```

Native V609 lower publication path:

```text
mss_after_holder=ONLINE
mss_after_companion=ONLINE
mdm3_after_companion=OFFLINING
sysmon_slpi=missing
sysmon_cdsp=missing
sysmon_adsp=missing
sysmon_esoc0=missing
service_notifier=missing
WLFW service 69 readback=clean end-of-list
QIPCRTR sockets=0
```

## Timing

Android:

```text
qrtr_rx_to_qrtr_tx: 645.083ms
qrtr_tx_to_sysmon_modem: 4.874ms
sysmon_modem_to_sysmon_slpi: 2.387ms
sysmon_modem_to_sysmon_cdsp: 4.599ms
sysmon_modem_to_sysmon_adsp: 5.077ms
sysmon_modem_to_service_notifier_180: 22.262ms
service_notifier_180_to_service_notifier_74: 0.947ms
```

Native V609:

```text
qrtr_rx_to_qrtr_tx: 2488.47ms
qrtr_tx_to_sysmon_modem: 0.597ms
sysmon_modem_to_service_notifier_180: None
sysmon_modem_to_service_locator: 723.916ms
sysmon_modem_to_cma_alloc_fail: 0.021ms
```

## Diagnostics

```text
android_has_service_notifier_pair=True
native_base_ready=True
native_has_service_notifier=False
android_sibling_sysmon_count=4
native_sibling_sysmon_count=0
android_mss_online=True
android_mdm3_online=True
native_mss_online=True
native_mdm3_offlining=True
native_wlfw_readback_empty=True
native_memshare_or_cma_fail=True
```

## Evidence Limit

The Android dmesg input is useful for the Wi-Fi/CNSS timeline, but it was
captured through a filtered grep. That means it cannot prove the absence or
presence of some lower surfaces:

```text
memshare
servloc/service_locator
rmt_storage
QIPCRTR socket counts
rpmsg surface
```

V610 therefore does not justify opening `esoc0` or retrying CNSS/HAL. It
identifies the next evidence gap more precisely: Android has mdm3/esoc0 and
sibling sysmon readiness where native V609 still has `mdm3=OFFLINING` and no
service-notifier publication.

## Interpretation

The current blocker is below Wi-Fi HAL and below CNSS retry ordering. Native now
reliably reaches modem PIL, QRTR RX/TX, and modem `sysmon-qmi`, but the Android
reference shows additional lower publication prerequisites before the Wi-Fi
chain proceeds:

1. `mdm3`/`esoc0` reaches `ONLINE`;
2. sibling sysmon services appear for `slpi`, `cdsp`, `adsp`, and `esoc0`;
3. service-notifier services `180` and `74` publish shortly after modem sysmon;
4. WLAN-PD, WLFW/BDF, firmware-ready, and `wlan0` follow later.

The native V609 evidence instead shows `mdm3=OFFLINING`, no sibling sysmon, no
service-notifier, empty WLFW QRTR readback, and zero QIPCRTR sockets in the
bounded window.

## Next Gate

Recommended V611:

1. Perform an Android read-only lower-surface recapture with unfiltered dmesg
   slices and direct reads of subsystem, rpmsg, QRTR/QIPCRTR, memshare, and
   service-locator surfaces.
2. Compare that recapture with V609 before any native `esoc0` open attempt.
3. Keep CNSS, service-manager, Wi-Fi HAL, scan/connect, credentials, DHCP,
   routing, and external ping blocked until the lower mdm3/esoc0 publication
   precondition is understood.
