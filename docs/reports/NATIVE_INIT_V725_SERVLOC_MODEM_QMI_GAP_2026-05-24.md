# Native Init V725 Service-Locator to Modem/QMI Gap Report

- date: `2026-05-24 KST`
- runner: `scripts/revalidation/native_wifi_servloc_modem_gap_v725.py`
- evidence: `tmp/wifi/v725-servloc-modem-gap/`
- latest pointer: `tmp/wifi/latest-v725-servloc-modem-gap.txt`
- decision: `v725-servloc-live-modem-qmi-readiness-gap-classified`
- status: `pass`

## Scope Result

V725 was host-side classification only. The classifier did not contact the
device and did not start daemons, start service-manager, start Wi-Fi HAL,
scan/connect, use credentials, run DHCP, change routes, external ping, write
sysfs/debugfs, touch `esoc0`, or write boot partitions.

A separate read-only live spot-check was captured while the bridge was already
up. It is corroborative only; the V725 decision is based on existing Android
V612/V622 and native V724 evidence.

## Key Checks

| check | result |
| --- | --- |
| input evidence | Android V612/V622 and native V724 evidence present |
| model correction | analyze SM8250/CNSS2 SERVREG path, not SDM845 ICNSS-only path |
| Android lower chain | QRTR RX/TX, sysmon, service-locator, service `180/74` present |
| Android continuation | WLAN-PD, WLFW/QMI, BDF, fw-ready, and `wlan0` present |
| native service-locator | connected in V724 at boot window; `servloc_timeout=0` |
| native modem/QMI readiness | QRTR RX/TX `0`, sysmon modem `0`, sysmon esoc0 `0` |
| native subsystem state | `mss=OFFLINING`, `mdm3=OFFLINING`, rpmsg devices `0` |
| native service publication | service `180=0`, service `74=0`, WLFW/BDF/`wlan0=0` |

## Android Reference

Android V622/V612 shows the lower prerequisites that native lacks:

| marker/state | Android value |
| --- | ---: |
| QRTR RX | `1` |
| QRTR TX | `1` |
| sysmon modem | `1` |
| service-locator | `1` |
| service `180` | `1` |
| service `74` | `1` |
| WLAN-PD | `2` |
| WLFW start | `1` |
| QMI server connected | `1` |
| BDF `regdb.bin` | `1` |
| BDF `bdwlan.bin` | `1` |
| WLAN fw-ready | `1` |
| `wlan0` | `3` |
| `mss` state | `ONLINE` |
| `mdm3` state | `ONLINE` |

Important Android timing:

| delta | ms |
| --- | ---: |
| QRTR RX -> QRTR TX | `643.044` |
| QRTR TX -> sysmon modem | `2.741` |
| sysmon modem -> service-locator | `2.446` |
| sysmon modem -> service `180` | `30.43` |
| service `180` -> service `74` | `6.561` |
| service `180` -> WLFW start | `1415.75` |
| service `180` -> WLAN-PD | `2427.362` |
| WLAN-PD -> QMI server connected | `2.509` |
| WLAN-PD -> BDF `regdb.bin` | `79.675` |

## Native V724 Contrast

V724 lower companion order was correct and early:

```text
qrtr_ns,pd_mapper,rmt_storage,tftp_server
```

But the native boot-window evidence shows the missing lower modem/QMI edge:

| marker/state | Native V724 value |
| --- | ---: |
| service-locator | `2` |
| service-locator connected | `1` |
| `servloc` timeout | `0` |
| QRTR RX | `0` |
| QRTR TX | `0` |
| sysmon modem | `0` |
| sysmon esoc0 | `0` |
| rpmsg devices | `0` |
| QIPCRTR sockets | `0` |
| service `180` | `0` |
| service `74` | `0` |
| WLAN-PD | `0` |
| WLFW | `0` |
| BDF | `0` |
| `wlan0` | `0` |
| `mss` state | `OFFLINING` |
| `mdm3` state | `OFFLINING` |

The live read-only spot-check matched the same shape: QIPCRTR protocol present,
but `mss/mdm3` still OFFLINING and no CNSS process, QRTR RX/TX, sysmon, service
`180/74`, WLFW, or `wlan0`.

## Interpretation

V725 removes the `qrtr-ns too late` hypothesis for the current boot-window path:

```text
qrtr-ns/lower companion early enough -> service-locator connects
```

The remaining blocker is lower:

```text
modem/QMI readiness absent -> no SERVREG service 180/74 publication
  -> no CNSS2 pd_notifier/WLAN-PD callback
  -> no QCA6390/WLFW/BDF/fw-ready/wlan0
```

Do not retry `qcwlanstate`, CNSS daemon, Wi-Fi HAL, scan/connect, DHCP, routes,
credentials, or external ping until native reproduces QRTR RX/TX and sysmon.

Follow-up V726 model correction: on SM8250, service `180/74` is side evidence
rather than the primary CNSS2 trigger. The next blocker should be read as the
lower modem/WLAN-driver prerequisite layer: modem MPSS/MDM3 ONLINE state,
`wlan` module/load-state, MHI/QCA6390 progression, and `wlanmdsp` firmware
visibility.

## Validation

Executed:

```bash
python3 -m py_compile scripts/revalidation/native_wifi_servloc_modem_gap_v725.py

python3 scripts/revalidation/native_wifi_servloc_modem_gap_v725.py \
  --out-dir tmp/wifi/v725-servloc-modem-gap-plan plan

python3 scripts/revalidation/native_wifi_servloc_modem_gap_v725.py \
  --out-dir tmp/wifi/v725-servloc-modem-gap run
```

## Next Gate

V726 should be a bounded post-ACM modem/QMI readiness proof:

1. mount the required firmware surfaces read-only;
2. hold only `subsys_modem` through the known safer modem holder path;
3. do not open or hold `esoc0`;
4. start only lower companion services
   `qrtr-ns -> pd-mapper -> rmt_storage -> tftp_server`;
5. observe QRTR RX/TX, sysmon, service `180/74`, and subsystem state;
6. keep CNSS daemon, service-manager, Wi-Fi HAL, scan/connect, DHCP, credentials,
   routes, and external ping blocked.
