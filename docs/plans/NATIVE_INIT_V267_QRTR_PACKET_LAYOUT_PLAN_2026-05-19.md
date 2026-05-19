# Native Init v267 QRTR Packet Layout Plan

## Summary

- target: v267 QRTR nameservice packet layout artifact
- boot image change: none
- daemon start: not executed
- QRTR/QMI packet transmission: not executed
- new host tool: `scripts/revalidation/wifi_qrtr_nameservice_packet_layout.py`
- expected output: `tmp/wifi/v267-qrtr-packet-layout/`

v266 created the runner skeleton but deliberately left transmission
unimplemented. v267 prepares the exact host-side byte layout for a future
`QRTR_TYPE_NEW_LOOKUP` and matching `QRTR_TYPE_DEL_LOOKUP` control packet.

## Scope

- Generate packed little-endian `struct qrtr_ctrl_pkt` bytes.
- Validate:
  - `cmd=QRTR_TYPE_NEW_LOOKUP` is `10`
  - `cmd=QRTR_TYPE_DEL_LOOKUP` is `11`
  - packet length is `20` bytes
  - service and instance are explicit uint32 values
  - wildcard lookup remains blocked by default
- Do not open sockets, contact the device, run bridge commands, or transmit.

## Guardrails

v267 must not:

- run bridge commands
- open QRTR sockets
- send QRTR nameservice packets
- issue QMI requests
- run `cnss-daemon`, `cnss_diag`, HAL, supplicant, wificond, hostapd, DHCP, or
  routing commands
- scan/connect/link-up Wi-Fi
- mutate rfkill, ICNSS, firmware, Android partitions, property service, perfd,
  kmsg, `/data/vendor/wifi`, or routing

## Validation

Static:

```bash
python3 -m py_compile scripts/revalidation/wifi_qrtr_nameservice_packet_layout.py
git diff --check
```

Host-only layout:

```bash
python3 scripts/revalidation/wifi_qrtr_nameservice_packet_layout.py \
  --out-dir tmp/wifi/v267-qrtr-packet-layout \
  --service 1 \
  --instance 1
```

## Acceptance

- Decision is `qrtr-packet-layout-ready`.
- NEW_LOOKUP and DEL_LOOKUP packet lengths are `20`.
- Service/instance are encoded little-endian at the expected offsets.
- No socket or bridge command is executed.
- The output clearly states that actual packet transmission still requires
  explicit approval.
