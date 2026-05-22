# Native Init V597 Post-Sysmon Gap Report

- date: `2026-05-22 KST`
- status: `classified`; Wi-Fi external ping is **not** complete
- runner: `scripts/revalidation/native_wifi_post_sysmon_gap_v597.py`
- evidence: `tmp/wifi/v597-post-sysmon-gap/`

## Scope

V597 is host-only. It compares captured Android dmesg with V596 native evidence
to avoid another blind live retry after V596 reached QRTR TX and `sysmon-qmi`.

No device command, QRTR/QMI packet, daemon start, Wi-Fi HAL, `qcwlanstate`,
scan/connect/link-up, credential, DHCP, route change, or external ping was
executed.

## Result

```text
decision: v597-post-sysmon-service-notifier-gap-classified
pass: True
reason: Android service-notifier appears 22.262ms after sysmon and before CNSS daemon WLFW; native reaches QRTR TX/sysmon but has no service-notifier
next: bounded service-notifier/WLFW visibility probe or WLFW QRTR readback; still no scan/connect
```

## Android Ordering

The Android reference shows this post-sysmon sequence:

```text
7.001288  qrtr: Modem QMI Readiness TX
7.006162  sysmon-qmi modem SSCTL service
7.008549  sysmon-qmi slpi SSCTL service
7.010761  sysmon-qmi cdsp SSCTL service
7.011239  sysmon-qmi adsp SSCTL service
7.028424  service-notifier 180 service
7.029371  service-notifier 74 service
7.807753  cnss_diag start
8.111985  cnss-daemon start
8.294932  cnss-daemon wlfw_start
8.324047  cnss-daemon wlfw_service_request thread
9.421183  service-notifier msm/modem/wlan_pd indication
9.423450  icnss_qmi QMI Server Connected
9.496028  BDF regdb.bin
9.511402  BDF bdwlan.bin
14.571374 WLAN FW ready
14.724770 wlan0 event
```

Key deltas:

```text
sysmon_modem_to_service_notifier_180 = 22.262 ms
service_notifier_180_to_cnss_diag_start = 779.329 ms
service_notifier_180_to_cnss_daemon_start = 1083.561 ms
cnss_daemon_start_to_wlfw_start = 182.947 ms
wlfw_thread_to_wlan_pd = 1097.136 ms
wlan_pd_to_qmi_server_connected = 2.267 ms
```

## Native V596 Comparison

V596 reached:

```text
qrtr_rx=1
qrtr_tx=1
sysmon_qmi=1
kernel_warning=0
```

V596 did not reach:

```text
service_notifier=0
wlan_pd=0
wlfw=0
qmi_server_connected=0
bdf=0
wlan_fw_ready=0
wlan0=0
```

## Interpretation

- Android service-notifier `180` and `74` appear about 22 ms after
  `sysmon-qmi`, and about 0.78-1.08 seconds before `cnss_diag` /
  `cnss-daemon` are started.
- Therefore the first missing native marker after V596 is not caused by
  `cnss-daemon` WLFW start. It is earlier: native reaches modem QRTR TX and
  modem `sysmon-qmi`, but does not receive service-notifier service publication.
- WLAN-PD appears later, after `cnss-daemon` starts the WLFW request thread,
  and is followed by ICNSS QMI Server Connected about 2 ms later.
- A direct qcwlanstate/HAL/scan retry remains premature until the
  service-notifier/WLAN-PD/WLFW boundary moves.

## Next Gate

Recommended V598:

1. Reuse the V596 lower precondition:
   global firmware mounts + `subsys_modem` holder + QRTR RX gate.
2. Add bounded observation/readback for the post-sysmon gap:
   - WLFW QRTR nameservice readback without QMI payload, or
   - service-notifier/WLAN-PD focused dmesg/sysfs probe.
3. Keep `esoc0` unopened.
4. Keep service-manager, Wi-Fi HAL, `qcwlanstate`, scan/connect, credentials,
   DHCP, routing, and external ping blocked until service-notifier/WLAN-PD or
   WLFW/BDF markers advance.
