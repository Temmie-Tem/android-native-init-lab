# Native Init V828 Service-Locator Domain-List Payload Report

## Result

- decision: `v828-servloc-domain-list-payload-derived`
- pass: `true`
- runner: `scripts/revalidation/native_wifi_servloc_domain_list_payload_v828.py`
- evidence: `tmp/wifi/v828-servloc-domain-list-payload/`

## What Ran

```bash
python3 -m py_compile \
  scripts/revalidation/native_wifi_servloc_domain_list_payload_v828.py

python3 scripts/revalidation/native_wifi_servloc_domain_list_payload_v828.py \
  --out-dir tmp/wifi/v828-servloc-domain-list-payload-plan-check \
  plan

python3 scripts/revalidation/native_wifi_servloc_domain_list_payload_v828.py \
  run
```

## Evidence Summary

| Signal | Result |
| --- | --- |
| V827 input | pass |
| service-locator endpoint | service `64/257`, node `1`, port `16475` |
| source ABI anchors | pass |
| request total length | `24` bytes |
| request payload length | `17` bytes |
| device commands | `false` |
| QRTR socket open | `false` |
| QMI payload | `false` |
| Wi-Fi HAL / scan / external ping | `false` |

## Derived Request

```text
00 01 00 21 00 11 00 01 07 00 77 6c 61 6e 2f 66 77 10 04 00 00 00 00 00
```

| Bytes | Meaning |
| --- | --- |
| `00` | QMI request |
| `01 00` | transaction id `1` |
| `21 00` | message id `0x0021`, `GET_DOMAIN_LIST` |
| `11 00` | QMI payload length `17` |
| `01 07 00 77 6c 61 6e 2f 66 77` | TLV `0x01`, service name `wlan/fw` |
| `10 04 00 00 00 00 00` | TLV `0x10`, domain offset `0` |

## Expected Response Model

| TLV | Meaning |
| --- | --- |
| `0x02` | common response result/error |
| `0x10` | `total_domains` |
| `0x11` | `db_rev_count` |
| `0x12` | domain list entries with name, instance id, service data valid flag, and service data |

Success for the next live probe should require a successful response and at
least one domain entry for the `wlan/fw` service.

## Interpretation

V828 closes the ABI derivation step. The next probe does not need Android
service-manager, Wi-Fi HAL, scan/connect, credentials, DHCP, routes, external
ping, or custom kernel changes. It only needs a bounded QRTR/QMI request to the
visible service-locator endpoint captured by V826.

This is now the narrowest live test that can determine whether ICNSS can obtain
the WLAN-PD domain list in native init.

## Safety

- Host-only derivation only.
- No bridge command, device command, reboot, bootloader handoff, boot image
  write, partition write, or custom kernel flash executed.
- No QRTR socket open, QRTR packet transmission, or QMI payload executed.
- No service-manager, Wi-Fi HAL, scan/connect/link-up, credential use, DHCP,
  route change, or external ping executed.
- No Wi-Fi secret material was written to tracked output.

## Next

V829 should add a bounded helper/runner that sends only the derived request to
service-locator `64/257` at the visible node/port, parses the response TLVs, and
cleans up. It must not start service-manager, Wi-Fi HAL, scan/connect,
credentials, DHCP/routes, external ping, boot image writes, partition writes, or
custom kernel flashes.
