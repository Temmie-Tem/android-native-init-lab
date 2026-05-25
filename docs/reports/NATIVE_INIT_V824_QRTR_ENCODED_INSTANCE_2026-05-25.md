# Native Init V824 QRTR Encoded Instance Classifier Report

## Result

- decision: `v824-qmi-encoded-instance-gap-classified`
- pass: `true`
- runner: `scripts/revalidation/native_wifi_qrtr_encoded_instance_classifier_v824.py`
- evidence: `tmp/wifi/v824-qrtr-encoded-instance-classifier/`

## What Ran

```bash
python3 -m py_compile \
  scripts/revalidation/native_wifi_qrtr_encoded_instance_classifier_v824.py

python3 scripts/revalidation/native_wifi_qrtr_encoded_instance_classifier_v824.py \
  --out-dir tmp/wifi/v824-qrtr-encoded-instance-classifier-plan-check \
  plan

python3 scripts/revalidation/native_wifi_qrtr_encoded_instance_classifier_v824.py \
  run
```

## Evidence Summary

| Signal | Result |
| --- | --- |
| V823 input | pass, `v823-ssctl-nameservice-clean-empty-below-hal` |
| OSRC source | present |
| `qmi_add_lookup()` | present, line `219` |
| QRTR lookup command | `QRTR_TYPE_NEW_LOOKUP` present |
| encoded instance expression | present, line `189` |
| device commands | `false` |
| device mutations | `false` |
| QMI payload | `false` |
| service-manager / Wi-Fi HAL | `false` |
| scan/connect / DHCP / external ping | `false` |

## Encoded Instances

| Label | Service | QMI version | Raw instance | Encoded QRTR instance | Raw in V823 | Encoded in V823 |
| --- | --- | --- | --- | --- | --- | --- |
| `servloc` | `64` | `1` | `1` | `257` | `true` | `false` |
| `ssctl` | `43` | `2` | `16` | `4098` | `true` | `false` |
| `servnotif` | `66` | `1` | `74` | `18945` | `true` | `false` |
| `servnotif` | `66` | `1` | `180` | `46081` | `true` | `false` |
| `wlfw` | `69` | `1` | `0` | `1` | `true` | `true` |

## Interpretation

V824 changes the interpretation of V821/V823. Those live matrices proved the
helper can open AF_QIPCRTR and send lookup/delete messages, but they mostly used
raw QMI instance IDs. Samsung OSRC `qmi_interface.c` shows kernel QMI clients
encode nameservice lookup instances as:

```c
svc->version | svc->instance << 8
```

That means V823 did not test the exact QRTR instance values that kernel
`qmi_add_lookup()` users send for service-locator, SSCTL, or service-notifier.
The WLFW `69/1` row was already present because encoded WLFW version `1`,
instance `0` equals `1`.

The V823 clean-empty result should therefore not be treated as final proof that
all kernel-visible services are absent from userspace nameservice lookup. The
next live gate must first repeat the no-QMI matrix with encoded instance values.

## Next Encoded Matrix

```text
servloc:64:257;ssctl:43:4098;servnotif:66:18945,46081;wlfw:69:1
```

## Safety

- Host-only classifier only.
- No bridge command, device command, reboot, bootloader handoff, boot image
  write, partition write, or custom kernel flash executed.
- No QRTR socket open, QRTR packet transmission, or QMI payload executed.
- No service-manager, Wi-Fi HAL, scan/connect/link-up, credential use, DHCP,
  route change, or external ping executed.
- V775 custom OSRC kernel flashing pause remains active.
- No Wi-Fi secret material was written to tracked output.

## Next

V825 should run the encoded-instance AF_QIPCRTR nameservice matrix below
HAL/connect and still avoid QMI payloads, service-manager, Wi-Fi HAL,
scan/connect, credentials, DHCP/routes, external ping, boot image writes,
partition writes, and custom kernel flashes.
