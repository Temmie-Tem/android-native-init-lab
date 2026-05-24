# Native Init V770 Instrumented Diagnostic Boot Staging Report

## Result

- decision: `v770-instrumented-diagnostic-boot-staged`
- pass: `true`
- runner: `scripts/revalidation/native_wifi_diag_boot_staging_v770.py`
- evidence: `tmp/wifi/v770-instrumented-diagnostic-boot-staging/`
- local boot image: `tmp/wifi/v770-instrumented-diagnostic-boot-staging/boot_linux_v770_icnss_diag.img`

## What Ran

```bash
python3 -m py_compile scripts/revalidation/native_wifi_diag_boot_staging_v770.py
python3 scripts/revalidation/native_wifi_diag_boot_staging_v770.py plan
python3 scripts/revalidation/native_wifi_diag_boot_staging_v770.py run
```

## Evidence Summary

| Signal | Value |
| --- | --- |
| staged boot size | `52977664` bytes |
| staged boot sha256 | `bcf0721df68c5de56c09e737397392fd06189b5ca4b0a40761b4a71a3327fcbb` |
| base boot sha256 | `4ca72f17aec64153d49def4ad42a49714d27bd833623aa9423220ce2181fc682` |
| kernel `Image-dtb` sha256 | `bad44b6f9dd6925c9e2ddae70c9f5258f731c93e216855931c9954d806841d49` |
| kernel roundtrip hash | `true` |
| native-init marker count | `1` |
| `A90V765` marker count | `19` |
| staged boot mode | `0600` |

## Interpretation

V770 proves the V769 instrumented kernel can be packaged into a local boot image
with the current native-init ramdisk/header metadata. The repacked image
roundtrips through `unpack_bootimg.py`, and the extracted kernel hash matches
the V769 `Image-dtb`.

This still does not execute the diagnostic kernel on-device. The next useful
gate is a controlled flash/reboot/capture loop that observes whether the
`A90V765` logs reveal the ICNSS/QMI/WLFW/HDD boundary that currently blocks
`wlan0`.

## Safety

- local boot image created: yes
- device command: not executed
- partition write/flash: not executed
- reboot: not executed
- service-manager/Wi-Fi HAL: not started
- scan/connect/credential use: not executed
- DHCP/routes/external ping: not executed
