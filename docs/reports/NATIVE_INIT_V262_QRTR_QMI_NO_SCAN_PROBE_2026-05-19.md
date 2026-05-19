# Native Init v262 QRTR/QMI No-Scan Probe Report

## Summary

- status: PASS
- decision: `qrtr-qmi-no-scan-ready`
- baseline device build: `A90 Linux init 0.9.60 (v261)`
- boot image change: none
- daemon start: not executed
- QRTR send/connect/nameservice packet: not executed
- Wi-Fi scan/connect/link-up: not executed
- host tool: `scripts/revalidation/wifi_qrtr_qmi_no_scan_probe.py`
- plan: `docs/plans/NATIVE_INIT_V262_QRTR_QMI_NO_SCAN_PROBE_PLAN_2026-05-19.md`
- output: `tmp/wifi/v262-qrtr-qmi-no-scan-probe/`
- post-audit: `tmp/wifi/v262-cnss-zombie-audit-post-qrtr-qmi/`

v262 re-checked the QRTR/QMI runtime surface after the v261 PID1 orphan reaper
and clean CNSS live retry. It did not start `cnss-daemon` or any Wi-Fi control
component. The existing v250 static helper was reused only for a no-send
`AF_QIPCRTR` socket open/bind sanity check.

## Validation

Static validation:

```bash
python3 -m py_compile \
  scripts/revalidation/wifi_qrtr_qmi_no_scan_probe.py \
  scripts/revalidation/wifi_qrtr_socket_probe.py \
  scripts/revalidation/wifi_cnss_zombie_audit.py
git diff --check
```

Helper presence/hash:

```bash
python3 scripts/revalidation/a90ctl.py stat /cache/bin/a90_qrtr_probe
python3 scripts/revalidation/a90ctl.py run /cache/bin/toybox sha256sum /cache/bin/a90_qrtr_probe
```

Result:

```text
mode=0755 uid=0 gid=0 size=597920
92500fa51a7c910877d59b704210b915dfeed4abb0daca36d894b10f319be8a5  /cache/bin/a90_qrtr_probe
```

Live no-scan probe:

```bash
python3 scripts/revalidation/wifi_qrtr_qmi_no_scan_probe.py \
  --out-dir tmp/wifi/v262-qrtr-qmi-no-scan-probe \
  --expect-version "A90 Linux init 0.9.60 (v261)"
```

Result:

```text
decision: qrtr-qmi-no-scan-ready
pass: True
reason: clean v261 baseline, QIPCRTR socket no-send probe, and read-only endpoint inventory are consistent
```

Post CNSS process audit:

```bash
python3 scripts/revalidation/wifi_cnss_zombie_audit.py \
  --out-dir tmp/wifi/v262-cnss-zombie-audit-post-qrtr-qmi
```

Result:

```text
decision: cnss-process-clean
pass: True
reason: no CNSS target processes found
```

## Evidence

| Check | Result | Detail |
| --- | --- | --- |
| expected-version | PASS | `A90 Linux init 0.9.60 (v261)` |
| required-captures | PASS | `failed=[]` |
| cnss-process-clean | PASS | `target_process_count=0`, `target_running_count=0`, `target_zombie_count=0` |
| qipcrtr-protocol-listed | PASS | `QIPCRTR` present in `/proc/net/protocols` |
| helper-sha | PASS | `92500fa51a7c910877d59b704210b915dfeed4abb0daca36d894b10f319be8a5` |
| qrtr-helper-socket-open | PASS | `AF_QIPCRTR=42`, `socket.rc=0`, `status=bind-pass` |
| qrtr-helper-no-send-connect | PASS | `send_attempted=0`, `connect_attempted=0` |
| no-wlan-link-surface | PASS | no `wlan*` in `/proc/net/dev` or `/sys/class/net` |
| endpoint-inventory-collected | PASS | `/dev` matches 0, `/sys` matches 69 |

Inventory highlights:

```text
qipcrtr_protocol_present=True
proc_net_qrtr_present=False
dev_qrtr_present=False
dev_diag_present=False
dev_ipa_present=False
dev_wlan_present=False
dev_inventory_matches=0
sys_inventory_matches=69
wlan_in_proc_net_dev=False
wlan_in_sys_class_net=False
qrtr_helper_status=bind-pass
qrtr_helper_send_attempted=0
qrtr_helper_connect_attempted=0
```

## Interpretation

- QRTR remains available at kernel socket-family and local bind level.
- No `/dev/qrtr`, `/dev/diag`, `/dev/ipa`, or `/dev/wlan` node is visible in the
  current native init runtime.
- The QRTR/QMI gap is therefore still a userspace/runtime endpoint/service gap,
  not a basic kernel socket blocker.
- The v261 reaper and postflight audit path stayed clean after the no-scan QRTR
  helper run.
- This result does not authorize Wi-Fi scan/connect/link-up; the next safe work
  should either model the userspace QRTR/QMI nameservice requirement without
  transmitting packets, or clean up the known CNSS warning surface.

## References

- <https://sbexr.rabexc.org/latest/sources/a9/0605b7d2f4022b.html>
- <https://codebrowser.dev/linux/linux/net/qrtr/af_qrtr.c.html>
- <https://github.com/linux-mobile-broadband/libqmi>

## Guardrails Preserved

- no `cnss-daemon` execution
- no `cnss_diag`
- no QRTR send/connect/nameservice packet
- no QMI request command
- no rfkill unblock, `wlan*` link-up, scan/connect, credentials, DHCP, or routing
- no ICNSS bind/unbind, firmware mutation, Android partition write, or reboot

## Next Step

v263 should avoid live Wi-Fi expansion. The best next candidates are:

1. CNSS warning surface cleanup/model: classify or shim the known
   `perfd-client-unavailable`, `/dev/kmsg` write denial, and shell quote noise.
2. QRTR/QMI userspace nameservice model: document what an actual nameservice
   lookup would require and keep any packet-transmitting helper behind a new
   explicit approval gate.
