# Native Init V598 Modem Holder WLFW Readback Report

- date: `2026-05-22 KST`
- status: `classified`; Wi-Fi external ping is **not** complete
- runner: `scripts/revalidation/native_wifi_modem_holder_wlfw_readback_v598.py`
- evidence: `tmp/wifi/v598-modem-holder-wlfw-readback/`
- policy-load evidence: `tmp/wifi/v598-v490-current-run/`

## Scope

V598 reused the V596 lower readiness path and added only WLFW QRTR nameservice
readback. It did not send QMI payloads, open `esoc0`, start service-manager,
start Wi-Fi HAL, write `qcwlanstate`, scan, connect, use credentials, run DHCP,
change routes, or ping externally.

## Result

```text
decision: v598-wlfw-readback-empty
pass: True
reason: WLFW QRTR readback reached end-of-list; timeouts=0
next: inspect missing service-notifier/WLAN-PD registration before qcwlanstate/HAL retry
```

## Readiness Markers

V598 reached a slightly stronger post-sysmon state than V596:

```text
qrtr_rx=1
qrtr_tx=1
sysmon_qmi=1
service_notifier=1
kernel_warning=0
```

Dmesg focus:

```text
qrtr: Modem QMI Readiness RX cmd:0x2 node[0x0]
qrtr: Modem QMI Readiness TX cmd:0x2 node[0x1]
sysmon-qmi: ssctl_new_server: Connection established between QMI handle and modem's SSCTL service
service-notifier: service_notifier_new_server: Connection established between QMI handle and 180 service
```

Still missing:

```text
service-notifier 74 service
WLAN-PD indication
WLFW start/thread
icnss_qmi QMI Server Connected
BDF regdb/bdwlan
WLAN FW ready
wlan0
```

## WLFW QRTR Readback

The helper sent QRTR nameservice lookup for WLFW service `69` instances `0` and
`1`. No QMI payload was sent.

```text
allowed=1
send_attempted=1
result=complete
service_events=0
end_of_list=2
timeouts=0
qmi_attempted=0
```

Per case:

```text
case_0 service=69 instance=0 new_lookup_rc=0 service_events=0 end_of_list=1 timeout=0 qmi_attempted=0
case_1 service=69 instance=1 new_lookup_rc=0 service_events=0 end_of_list=1 timeout=0 qmi_attempted=0
```

This proves the native window can send/receive QRTR nameservice messages, but
WLFW service registration is not published in that window.

## Cleanup

V598 used reboot as the cleanup boundary. Post-reboot:

```text
version_seen=True
status_healthy=True
A90 Linux init 0.9.61 (v319)
selftest: pass=11 warn=1 fail=0
```

Post-reboot process and mount checks found no residual companion/CNSS/QRTR/TFTP
processes and no global firmware/vendor mounts.

## Interpretation

- V597's inference was mostly right: the gap is QMI/service-registration level,
  not a missing ordinary userspace daemon.
- V598 shows native can now reach service-notifier instance `180`, but not the
  full Android pair (`180`, `74`) and not WLAN-PD.
- WLFW service `69` is absent from QRTR nameservice readback despite QRTR TX,
  sysmon, and partial service-notifier.
- Direct `qcwlanstate`, HAL, scan/connect, and credential work remains
  premature.

## Next Gate

Recommended V599:

1. Compare Android and native service-notifier instance coverage:
   - Android: `180` and `74`, then `msm/modem/wlan_pd`
   - Native V598: `180` only
2. Inspect whether service instance `74` corresponds to a non-modem PD
   dependency such as SLPI/CDSP/ADSP service notification.
3. Add a bounded service-notifier/QRTR instance matrix before retrying WLFW,
   CNSS HAL, or `qcwlanstate`.
4. Keep scan/connect/external ping blocked until WLFW/BDF/`wlan0` appears.
