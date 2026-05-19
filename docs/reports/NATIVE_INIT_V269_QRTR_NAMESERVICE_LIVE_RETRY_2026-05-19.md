# Native Init v269 QRTR Nameservice Live Retry Report

## Summary

- status: PASS
- boot image change: none
- baseline device build: `A90 Linux init 0.9.60 (v261)`
- runner: `scripts/revalidation/wifi_qrtr_nameservice_runner.py`
- helper device path: `/cache/bin/a90_qrtr_ns_probe`
- helper sha256: `c2d8707155b776c6c31e815136a66060f2087c4606c8a48cf9bd4b7944fdbb2a`
- live evidence: `tmp/wifi/v269-qrtr-nameservice-live-retry6-20260519-102134/`
- decision: `qrtr-ns-runner-lookup-sent`

v269 performed one explicitly approved, bounded QRTR nameservice live retry.
The helper sent a nameservice `NEW_LOOKUP` for service `1` instance `1`, then a
cleanup `DEL_LOOKUP`. No QMI payload, Wi-Fi scan, connect, link-up, DHCP, or
routing action was executed.

## Validation

Static validation:

```bash
python3 -m py_compile \
  scripts/revalidation/wifi_qrtr_nameservice_runner.py \
  scripts/revalidation/a90ctl.py \
  scripts/revalidation/tcpctl_host.py
git diff --check
```

Non-transmitting regression:

- `plan`: `qrtr-ns-runner-plan-ready`
- `preflight`: `qrtr-ns-runner-preflight-ready`
- no-approval `run`: `qrtr-ns-runner-fail-closed`

Approved live retry:

```text
decision: qrtr-ns-runner-lookup-sent
pass: True
reason: single QRTR nameservice lookup/delete packet pair executed; helper_status=lookup-sent
```

## Live Evidence

Run directory:

```text
tmp/wifi/v269-qrtr-nameservice-live-retry6-20260519-102134
```

Critical checks:

| check | result |
| --- | --- |
| `v264-model-ready` | PASS |
| `service-instance-valid` | PASS |
| `wildcard-blocked` | PASS |
| `qmi-payload-disallowed` | PASS |
| `expected-version` | PASS |
| `required-readonly-captures` | PASS |
| `cnss-daemon-absent` | PASS |
| `no-wlan-link-surface` | PASS |
| `approval-flag-check` | PASS |
| `host-ncm-ping-device` | PASS |
| `helper-build` | PASS |
| `helper-deploy` | PASS |
| `helper-command-rc` | PASS |
| `qrtr-lookup-sent` | PASS |
| `qrtr-send-attempted` | PASS |
| `qmi-not-attempted` | PASS |

Helper output:

```text
qrtr_ns.version=a90_qrtr_ns_probe v1
qrtr_ns.af=42
qrtr_ns.port_ctrl=4294967294
qrtr_ns.new_lookup=10
qrtr_ns.del_lookup=11
qrtr_ns.send_attempted=0
qrtr_ns.qmi_attempted=0
qrtr_ns.service=1
qrtr_ns.instance=1
qrtr_ns.have_service=1
qrtr_ns.have_instance=1
qrtr_ns.allow_transmit=1
qrtr_ns.allow_wildcard=0
qrtr_ns.socket.rc=0
qrtr_ns.initial.rc=0
qrtr_ns.initial.len=12
qrtr_ns.initial.family=42
qrtr_ns.initial.node=1
qrtr_ns.initial.port=0
qrtr_ns.send_attempted=1
qrtr_ns.new_lookup_send.rc=0
qrtr_ns.new_lookup_send.bytes=20
qrtr_ns.new_lookup_send.cmd=10
qrtr_ns.new_lookup_send.service=1
qrtr_ns.new_lookup_send.instance=1
qrtr_ns.del_lookup_send.rc=0
qrtr_ns.del_lookup_send.bytes=20
qrtr_ns.del_lookup_send.cmd=11
qrtr_ns.del_lookup_send.service=1
qrtr_ns.del_lookup_send.instance=1
qrtr_ns.status=lookup-sent
```

Deployment evidence:

- host NCM path restored before retry: `192.168.7.1/24 -> 192.168.7.2`
- transfer method: short-lived host HTTP server plus device `toybox wget`
- HTTP evidence: `served_count=1`, `GET /a90_qrtr_ns_probe HTTP/1.1 200`
- device hash check matched local helper sha256 before final move

## Postflight

- `version`: `A90 Linux init 0.9.60 (v261)`
- `status`: native init shell responsive, `netservice: disabled tcpctl=stopped`
- `pidof cnss-daemon`: rc `1`, process absent
- `/proc/net/dev`: NCM surface present; no `wlan*` interface observed
- `/cache/bin/a90_qrtr_ns_probe`: sha256 matched reviewed helper

## Interpretation

- QRTR kernel/nameservice control path accepted one bounded lookup/delete packet
  pair.
- The live retry did not create a visible `wlan*` link surface or leave
  `cnss-daemon` running.
- The remaining Wi-Fi blocker is not basic QRTR nameservice packet ability. The
  next step should classify endpoint/service visibility and decide whether a
  further QMI-control discovery plan is warranted.

## Guardrails Preserved

- no QMI payload
- no Wi-Fi scan/connect/link-up
- no credentials, DHCP, routing, or Internet-facing exposure
- no `cnss-daemon`, `cnss_diag`, HAL, supplicant, wificond, or hostapd start
- no rfkill write, ICNSS bind/unbind, firmware mutation, Android partition
  write, property service mutation, perfd mutation, kmsg mutation, or reboot

