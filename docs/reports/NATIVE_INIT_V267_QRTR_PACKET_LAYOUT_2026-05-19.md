# Native Init v267 QRTR Packet Layout Report

## Summary

- status: PASS
- decision: `qrtr-packet-layout-ready`
- boot image change: none
- daemon start: not executed
- QRTR/QMI packet transmission: not executed
- Wi-Fi scan/connect/link-up: not executed
- host tool: `scripts/revalidation/wifi_qrtr_nameservice_packet_layout.py`
- plan: `docs/plans/NATIVE_INIT_V267_QRTR_PACKET_LAYOUT_PLAN_2026-05-19.md`
- output: `tmp/wifi/v267-qrtr-packet-layout/`

v267 generates the exact host-side QRTR nameservice control packet bytes for a
future bounded experiment. It does not open sockets and does not transmit.

## Validation

Static:

```bash
python3 -m py_compile scripts/revalidation/wifi_qrtr_nameservice_packet_layout.py
git diff --check
```

Host-only packet layout:

```bash
python3 scripts/revalidation/wifi_qrtr_nameservice_packet_layout.py \
  --out-dir tmp/wifi/v267-qrtr-packet-layout \
  --service 1 \
  --instance 1
```

Result:

```text
decision: qrtr-packet-layout-ready
pass: True
```

Wildcard block regression:

```bash
python3 scripts/revalidation/wifi_qrtr_nameservice_packet_layout.py \
  --out-dir tmp/wifi/v267-qrtr-packet-layout-wildcard-blocked \
  --service 0 \
  --instance 0
```

Result:

```text
decision: qrtr-packet-layout-blocked
pass: False
exit: 1
reason: packet layout check failed: wildcard-blocked
```

## Packet Bytes

| Packet | Hex | Length |
| --- | --- | --- |
| `QRTR_TYPE_NEW_LOOKUP` | `0a00000001000000010000000000000000000000` | 20 |
| `QRTR_TYPE_DEL_LOOKUP` | `0b00000001000000010000000000000000000000` | 20 |

Field offsets:

- `cmd`: bytes `0..3`, little-endian uint32
- `service`: bytes `4..7`, little-endian uint32
- `instance`: bytes `8..11`, little-endian uint32
- `node`: bytes `12..15`, zero for lookup requests
- `port`: bytes `16..19`, zero for lookup requests

## Checks

| Check | Result | Detail |
| --- | --- | --- |
| new-lookup-cmd | PASS | `10` |
| del-lookup-cmd | PASS | `11` |
| packet-lengths | PASS | `20` bytes each |
| service-instance-explicit | PASS | `service=1`, `instance=1` |
| wildcard-blocked | PASS | default wildcard lookup blocked |
| host-only-no-transmit | PASS | no socket, bridge command, or packet transmission |

## Interpretation

- The byte layout is now explicit enough for helper code review.
- `service=0 instance=0` remains blocked by default.
- This result still does not authorize QRTR packet transmission.
- The next step can design a transmit-capable helper, but execution still needs
  explicit approval.

## References

- <https://codebrowser.dev/linux/include/linux/qrtr.h.html>
- <https://codebrowser.dev/linux/linux/net/qrtr/ns.c.html>

## Guardrails Preserved

- no bridge command
- no QRTR socket open
- no QRTR send/connect/nameservice packet
- no QMI request command
- no `cnss-daemon` or `cnss_diag`
- no Wi-Fi scan/connect/link-up/credential/DHCP/routing
- no rfkill write, ICNSS bind/unbind, firmware mutation, Android partition
  write, or reboot
