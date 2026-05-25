# Native Init V828 Service-Locator Domain-List Payload Plan

## Goal

Derive the exact bounded QMI `GET_DOMAIN_LIST` request for `wlan/fw` from OSRC
source and V827 endpoint evidence, without sending any live QMI payload.

## Scope

- Target runner:
  - `scripts/revalidation/native_wifi_servloc_domain_list_payload_v828.py`
- Inputs:
  - `tmp/wifi/v827-service-notifier-continuation-classifier/manifest.json`
  - `service-locator-private.h`
  - `service-locator.c`
  - `qmi.h`
  - `qmi_encdec.c`
- Destination from evidence:
  - service-locator `64/257`
  - node `1`
  - port `16475`

## Hard Gates

- Host-only analysis.
- No bridge command, device command, reboot, bootloader handoff, boot image
  write, partition write, or custom kernel flash.
- No QRTR socket open or QRTR/QMI packet transmission.
- No service-manager, Wi-Fi HAL, scan/connect/link-up, credential use, DHCP,
  route change, or external ping.

## Derived Request

```text
00 01 00 21 00 11 00 01 07 00 77 6c 61 6e 2f 66 77 10 04 00 00 00 00 00
```

| Field | Value |
| --- | --- |
| QMI type | request `0` |
| transaction id | `1` |
| message id | `0x0021` / `GET_DOMAIN_LIST` |
| payload length | `17` |
| TLV `0x01` | service name `wlan/fw` |
| TLV `0x10` | domain offset `0` |

## Success Criteria

- V827 manifest exists and passed with decision
  `v827-service-notifier-continuation-requires-domain-list-qmi-classified`.
- Source anchors confirm the request struct, TLV types, QMI header shape, and
  encoding rules.
- Request bytes are deterministic and match the derived hex above.
- Guardrails remain false for device commands, QRTR socket open, QMI payload,
  Wi-Fi HAL, scan/connect, external ping, boot image writes, partition writes,
  and custom kernel flashes.

## Validation

```bash
python3 -m py_compile \
  scripts/revalidation/native_wifi_servloc_domain_list_payload_v828.py

python3 scripts/revalidation/native_wifi_servloc_domain_list_payload_v828.py \
  --out-dir tmp/wifi/v828-servloc-domain-list-payload-plan-check \
  plan

python3 scripts/revalidation/native_wifi_servloc_domain_list_payload_v828.py \
  run
```

## Next

V829 should implement a bounded no-HAL live probe that sends only this request
to the visible service-locator endpoint and parses the response. It must still
avoid service-manager, Wi-Fi HAL, scan/connect, credentials, DHCP/routes,
external ping, boot image writes, partition writes, and custom kernel flashes.
