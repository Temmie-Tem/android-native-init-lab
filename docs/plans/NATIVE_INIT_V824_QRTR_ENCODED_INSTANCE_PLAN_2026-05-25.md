# Native Init V824 QRTR Encoded Instance Classifier Plan

## Goal

Classify whether the V823 clean-empty AF_QIPCRTR nameservice matrix used raw
QMI instance values where kernel QMI clients actually send encoded QRTR
instance values.

## Scope

- Target runner:
  - `scripts/revalidation/native_wifi_qrtr_encoded_instance_classifier_v824.py`
- Inputs:
  - `tmp/wifi/v823-ssctl-nameservice-matrix/manifest.json`
  - `kernel_build/SM-A908N_KOR_12_Opensource/Kernel/drivers/soc/qcom/qmi_interface.c`
- Source rule:
  - `qmi_send_new_lookup()` sends `svc->version | svc->instance << 8`
  - `qmi_add_lookup()` stores raw QMI version/instance before that encoding

## Hard Gates

- Host-only analysis.
- No bridge command, device command, reboot, bootloader handoff, boot image
  write, partition write, or custom kernel flash.
- No QRTR socket open, QRTR packet transmission, or QMI payload transmission.
- No service-manager, Wi-Fi HAL, scan/connect/link-up, credential use, DHCP,
  route change, or external ping.
- Preserve the V775 custom OSRC kernel flashing pause.

## Encoded Matrix Candidate

| Label | Service | QMI version | Raw instance | Encoded QRTR instance |
| --- | --- | --- | --- | --- |
| `servloc` | `64` | `1` | `1` | `257` |
| `ssctl` | `43` | `2` | `16` | `4098` |
| `servnotif` | `66` | `1` | `74` | `18945` |
| `servnotif` | `66` | `1` | `180` | `46081` |
| `wlfw` | `69` | `1` | `0` | `1` |

Next live matrix if V824 passes:

```text
servloc:64:257;ssctl:43:4098;servnotif:66:18945,46081;wlfw:69:1
```

## Success Criteria

- V823 manifest exists and passed with decision
  `v823-ssctl-nameservice-clean-empty-below-hal`.
- OSRC `qmi_interface.c` exists and contains `qmi_add_lookup`,
  `QRTR_TYPE_NEW_LOOKUP`, and the encoded instance expression.
- V824 produces a host-only manifest with no device mutations.
- The classifier identifies that V823 queried raw or partial instances and that
  encoded service-locator, SSCTL, and service-notifier instances were missing.
- The next gate is limited to a no-QMI encoded-instance matrix.

## Validation

```bash
python3 -m py_compile \
  scripts/revalidation/native_wifi_qrtr_encoded_instance_classifier_v824.py

python3 scripts/revalidation/native_wifi_qrtr_encoded_instance_classifier_v824.py \
  --out-dir tmp/wifi/v824-qrtr-encoded-instance-classifier-plan-check \
  plan

python3 scripts/revalidation/native_wifi_qrtr_encoded_instance_classifier_v824.py \
  run
```

## Next

If V824 passes, V825 should run only the encoded-instance AF_QIPCRTR
nameservice matrix below HAL/connect. It must still avoid QMI payload,
service-manager, Wi-Fi HAL, scan/connect, credential use, DHCP, routes, external
ping, boot image writes, partition writes, and custom kernel flashes.
