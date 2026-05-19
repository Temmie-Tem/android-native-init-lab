# Native Init v265 QRTR Nameservice Approval Contract Plan

## Summary

- target: v265 QRTR nameservice packet approval contract
- boot image change: none
- daemon start: not executed
- QRTR/QMI packet transmission: not executed
- new host tool: `scripts/revalidation/wifi_qrtr_nameservice_approval_contract.py`
- expected output: `tmp/wifi/v265-qrtr-nameservice-approval-contract/`

v264 established that QRTR/QMI packet transmission is the next hard approval
boundary. v265 should not cross that boundary. It should produce the explicit
contract for a later bounded QRTR nameservice experiment: required flags,
forbidden actions, packet type limits, postflight gates, and rollback checklist.

## References

- Linux QRTR Kconfig says QRTR service lookups require nameservice support:
  <https://sbexr.rabexc.org/latest/sources/a9/0605b7d2f4022b.html>
- Linux UAPI `qrtr.h` defines `QRTR_PORT_CTRL`, `QRTR_TYPE_NEW_LOOKUP`, and
  `struct qrtr_ctrl_pkt`:
  <https://codebrowser.dev/linux/include/linux/qrtr.h.html>
- Linux `net/qrtr/ns.c` handles `QRTR_TYPE_NEW_LOOKUP` and announces matching
  servers:
  <https://codebrowser.dev/linux/linux/net/qrtr/ns.c.html>

## Scope

- Consume the v264 userspace nameservice model manifest.
- Generate:
  - approval contract
  - future command template
  - rollback/postflight checklist
  - summary/report manifest
- Do not implement or run the transmit-capable QRTR helper.

## Guardrails

v265 must not:

- run bridge commands
- open QRTR sockets
- send QRTR nameservice packets
- issue QMI requests
- run `cnss-daemon`, `cnss_diag`, HAL, supplicant, wificond, hostapd, DHCP, or
  routing commands
- scan/connect/link-up Wi-Fi
- mutate rfkill, ICNSS, firmware, Android partitions, property service, perfd,
  kmsg, or `/data/vendor/wifi`

## Contract Requirements

A future QRTR nameservice runner must require all of:

- `--allow-qrtr-ns-transmit`
- `--assume-yes`
- `--i-understand-qrtr-packet-transmission`
- explicit `--service` and `--instance` values
- bounded runtime
- postflight process audit
- postflight `wlan*` link surface audit
- no scan/connect/link-up behavior

Wildcard service lookup (`service=0 instance=0`) must not be the default. If it
is ever used, it needs a separate approval because it is broader than a
service-specific lookup.

## Validation

Static:

```bash
python3 -m py_compile scripts/revalidation/wifi_qrtr_nameservice_approval_contract.py
git diff --check
```

Host-only contract run:

```bash
python3 scripts/revalidation/wifi_qrtr_nameservice_approval_contract.py \
  --v264-manifest tmp/wifi/v264-qrtr-qmi-nameservice-model/manifest.json \
  --out-dir tmp/wifi/v265-qrtr-nameservice-approval-contract
```

## Acceptance

- Decision is `qrtr-nameservice-approval-contract-ready`.
- v264 model prerequisite is PASS.
- The generated command template includes explicit approval flags.
- The generated contract blocks wildcard lookup by default.
- The generated contract says no QRTR/QMI transmission happened in v265.
- The next actual transmit-capable step is clearly marked as requiring explicit
  user approval.
