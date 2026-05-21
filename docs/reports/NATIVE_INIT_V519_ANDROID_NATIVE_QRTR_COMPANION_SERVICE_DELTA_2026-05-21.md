# Native Init V519 Android/Native QRTR Companion-Service Delta

## Summary

- target: host-only Android/native QRTR, modem, and companion-service delta
- runner: `scripts/revalidation/native_wifi_android_native_qrtr_modem_delta_v519.py`
- decision: `v519-qrtr-companion-service-gap-classified`
- pass: `true`
- device commands: not executed
- daemon start: not executed
- Wi-Fi bring-up: not executed

V519 incorporates the SDM845 companion-service model into the Wi-Fi bring-up
blocker analysis. V517 proved `cnss_diag` and `cnss-daemon` can reach CNSS
netlink and that the private `/data/vendor/wifi/sockets` gap is closed, but
still produced no `WLFW`, `QMI Server Connected`, BDF, FW-ready, or `wlan0`
marker. V518 showed native has the `QIPCRTR` protocol surface but no
`/dev/qrtr`, `/proc/net/qrtr`, QRTR process, perfd runtime, or property runtime.

The Android baseline reaches this sequence before firmware-ready:

1. firmware partitions mounted;
2. WLAN driver initialized;
3. QRTR modem readiness RX;
4. `vendor.qrtr-ns` started;
5. QRTR modem readiness TX;
6. `sysmon-qmi` and `service-notifier` QMI services connected;
7. `cnss_diag` and `cnss-daemon` reached netlink;
8. `cnss-daemon` started WLFW;
9. `msm/modem/wlan_pd` indication arrived;
10. `icnss_qmi: QMI Server Connected`;
11. `regdb.bin` and `bdwlan.bin` BDF requests;
12. `icnss: WLAN FW is ready` and `wlan0`.

The local extracted roots only contain `cnss-daemon` and `cnss_diag` from the
candidate service set. They do not contain directly startable
`qrtr-ns`, `qmiproxy`, `rmtfs`, `pd-mapper`, or `tqftpserv` binaries.

## Evidence

Evidence root:

```text
tmp/wifi/v519-android-native-qrtr-modem-delta/
```

Key result:

```text
decision: v519-qrtr-companion-service-gap-classified
pass: True
reason: Android reaches QRTR/QMI/service-notifier/WLAN-PD/BDF/FW-ready while native reaches only CNSS netlink; SDM845 references point to rmtfs/pd-mapper/tqftpserv as companion services, but the local extracted roots do not contain that full startable set
next: plan companion-service availability proof before any qcwlanstate retry
device_commands_executed: False
device_mutations: False
daemon_start_executed: False
wifi_bringup_executed: False
```

## Findings

| item | result |
| --- | --- |
| Android QRTR readiness | RX at `6.356s`, TX at `7.001s` |
| Android QRTR userspace | `vendor.qrtr-ns` starts and `qrtr-ns` process is present |
| Android QMI support | `sysmon-qmi` and `service-notifier` connect before CNSS QMI |
| Android WLAN PD | `msm/modem/wlan_pd` indication precedes `QMI Server Connected` |
| Native CNSS userspace | `cnss_diag_netlink=21`, `cnss_daemon_netlink=39` |
| Native WLFW/QMI/BDF | all absent in V517 |
| Native QRTR | `QIPCRTR` protocol present, `/dev/qrtr` and `/proc/net/qrtr` absent |
| Local companion binaries | `rmtfs=0`, `pd-mapper=0`, `tqftpserv=0`, `qrtr-ns=0`, `qmiproxy=0` |
| Perfd/property | warning context only; not proven as QMI blocker |

Interpretation:

- `qcwlanstate` retry remains blocked. Without native WLFW/QMI/BDF markers it
  would likely reproduce the previous timeout.
- `cnss-daemon` netlink is no longer enough evidence for the next step.
- The stronger current hypothesis is a QRTR/modem companion-service gap before
  CNSS QMI/WLFW/BDF can complete.
- The local vendor/system evidence does not prove that Android ships the
  mainline-style `rmtfs`/`pd-mapper`/`tqftpserv` binaries under those exact
  names; Android may provide equivalent behavior through vendor services such as
  `qrtr-ns`, `qmiproxy`, `sysmon-qmi`, and `service-notifier`.

## Source Basis

External references used for the companion-service model:

- postmarketOS SDM845 mainlining notes:
  `https://wiki.postmarketos.org/wiki/SDM845_Mainlining`
- postmarketOS SDM845/SDM850 Wi-Fi notes:
  `https://wiki.postmarketos.org/wiki/Qualcomm_Snapdragon_845/850_(SDM845/SDM850)#WiFi`
- postmarketOS WCN399x Wi-Fi issue:
  `https://gitlab.com/postmarketOS/pmaports/-/issues/863`
- Debian `tqftpserv` source:
  `https://sources.debian.org/src/tqftpserv/1.1-4/tqftpserv.c`
- Debian `protection-domain-mapper` package:
  `https://packages.debian.org/sid/protection-domain-mapper`
- Debian `pd-mapper` source:
  `https://sources.debian.org/src/protection-domain-mapper/1.0-4/pd-mapper.c`
- ath10k WCN3990 discussion mentioning `tqftpserv`, `pd-mapper`, `qrtr-ns`, and
  `rmtfs`:
  `https://lists.infradead.org/pipermail/ath10k/2023-August/014701.html`

## Validation

Commands run:

```bash
python3 -m py_compile scripts/revalidation/native_wifi_android_native_qrtr_modem_delta_v519.py
python3 scripts/revalidation/native_wifi_android_native_qrtr_modem_delta_v519.py plan
python3 scripts/revalidation/native_wifi_android_native_qrtr_modem_delta_v519.py run
```

No device command was executed by V519.

## Next Gate

Recommended V520:

1. decide whether to capture a broader Android process/init/service baseline for
   `qrtr-ns`, `qmiproxy`, `sysmon-qmi`, `service-notifier`, `rmtfs`,
   `pd-mapper`, and `tqftpserv`;
2. decide whether native should use Android vendor-equivalent services or
   separately built static `rmtfs`/`pd-mapper`/`tqftpserv` tools;
3. if binaries must be built/deployed, create a bounded start-only proof that
   starts companion services before `cnss-daemon`;
4. continue blocking `qcwlanstate`, scan/connect, DHCP, route changes, and
   external ping until native WLFW/QMI/BDF or `wlan0` evidence appears.
