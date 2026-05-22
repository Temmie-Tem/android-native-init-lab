# Native Init V599 Service-Notifier Instance Gap Report

- date: `2026-05-22 KST`
- status: `classified`; Wi-Fi external ping is **not** complete
- runner: `scripts/revalidation/native_wifi_service_notifier_instance_gap_v599.py`
- evidence: `tmp/wifi/v599-service-notifier-instance-gap/`

## Scope

V599 is host-only. It compared Android reference dmesg, V597 timing output, and
V598 native WLFW readback evidence. It did not contact the device, send QRTR/QMI
packets, start daemons, start Wi-Fi HAL, write `qcwlanstate`, scan, connect, use
credentials, run DHCP, change routes, or ping externally.

## Result

```text
decision: v599-service-notifier-instance-gap-classified
pass: True
reason: Android reaches sysmon modem/slpi/cdsp/adsp plus service-notifier 180/74; native V598 reaches modem sysmon and service-notifier 180 only, while WLFW service 69 readback is clean end-of-list
next: bounded service-registry/sysmon instance matrix; still no qcwlanstate, HAL, scan/connect, or external ping
```

## Android Reference

Android shows this sequence:

```text
sysmon_modem=7.006162
sysmon_slpi=7.008549
sysmon_cdsp=7.010761
sysmon_adsp=7.011239
service_notifier_180=7.028424
service_notifier_74=7.029371
wlan_pd=9.421183
qmi_server_connected=9.423450
bdf_regdb=9.496028
bdf_bdwlan=9.511402
wlan_fw_ready=14.571374
wlan0=14.724770
```

Key deltas:

```text
sysmon_modem_to_service_notifier_180=22.262ms
service_notifier_180_to_service_notifier_74=0.947ms
wlfw_thread_to_wlan_pd=1097.136ms
wlan_pd_to_qmi_server_connected=2.267ms
wlan_pd_to_bdf_regdb=74.845ms
```

The important ordering point is that the service-notifier pair appears before
CNSS daemon's WLFW work reaches WLAN-PD. That makes it a kernel QMI service
registration callback path, not an ordinary userspace daemon trigger.

## Native V598 Coverage

V598 native evidence reached:

```text
qrtr_rx=188.551873
qrtr_tx=191.045271
sysmon_modem=191.047720
service_notifier_180=191.769090
```

Still missing:

```text
sysmon_slpi
sysmon_cdsp
sysmon_adsp
service_notifier_74
wlan_pd
qmi_server_connected
bdf_regdb
bdf_bdwlan
wlan_fw_ready
wlan0
```

V598 WLFW QRTR readback stayed clean but empty:

```text
service=69 instance=0 service_events=0 end_of_list=1 timeout=0 qmi_attempted=0
service=69 instance=1 service_events=0 end_of_list=1 timeout=0 qmi_attempted=0
```

## Interpretation

- V596/V598 no longer stop at modem PIL or QRTR RX; the lower modem-readiness
  path can reach QRTR TX, `sysmon-qmi`, and service-notifier instance `180`.
- Native V598 is still not equivalent to Android because the sibling
  `sysmon-qmi` services and service-notifier instance `74` do not appear.
- WLFW service `69` remains unpublished even though QRTR nameservice readback
  itself is working.
- Retrying `qcwlanstate`, HAL, scan/connect, or credential work is still
  premature because WLAN-PD, `icnss_qmi`, BDF, FW-ready, and `wlan0` are absent.

## Next Gate

Recommended V600:

1. Build a bounded service-registry/sysmon instance matrix from current
   Android and native evidence.
2. Confirm which service-notifier instance and subsystem SSCTL registrations
   are absent in native.
3. Only after the missing registration path is identified, run a live bounded
   probe that preserves the V598 guardrails.
4. Keep Wi-Fi HAL, scan/connect, credentials, DHCP, routing, and external ping
   blocked until WLFW/BDF/`wlan0` readiness appears.
