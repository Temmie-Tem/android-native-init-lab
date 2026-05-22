# Native Init V614 MDM3 Trigger-Path Classifier Report

- date: `2026-05-23 KST`
- runner: `scripts/revalidation/native_wifi_mdm3_trigger_path_classifier_v614.py`
- evidence: `tmp/wifi/v614-mdm3-trigger-path-classifier/`
- decision: `v614-dsp-boot-trigger-gap-classified`
- status: pass; no Wi-Fi bring-up attempted

## Scope

V614 compares:

1. Android V611 lower-surface recapture;
2. native V613 `mdm3/esoc0` targeted observer;
3. a fresh native read-only vendor init snapshot from temporary `sda29`
   `ro,noload` mount.

The run did not start CNSS, service-manager, Wi-Fi HAL, `wificond`,
supplicant, hostapd, scan/connect/link-up, credentials, DHCP, routing, or
external ping.

## Result

```text
decision: v614-dsp-boot-trigger-gap-classified
reason: Android boots ADSP/CDSP/SLPI before service-notifier; native V613 only boots MSS and raw esoc open does not publish lower services
next: plan V615 bounded DSP boot-node observer before any CNSS/HAL/scan/connect retry
```

The important shift is that the next blocker is no longer raw `esoc0` open.
Android's service-notifier path appears after ADSP/CDSP/SLPI PIL boot and
sibling `sysmon-qmi` publication, while V613 native only reproduced MSS modem
PIL plus QRTR/sysmon modem.

## Evidence

| surface | Android V611 | Native V613 |
| --- | --- | --- |
| MSS/modem PIL | present | present |
| ADSP PIL | present | absent |
| CDSP PIL | present | absent |
| SLPI PIL | present | absent |
| modem `sysmon-qmi` | present | present |
| sibling `sysmon-qmi` | present | absent |
| service-notifier `180/74` | present | absent |
| `mdm3` state | `ONLINE` | `OFFLINING` |
| raw `esoc0` open | not used as trigger | entered kernel get path, did not publish |

Vendor init contains Android's matching trigger surface:

- `/sys/kernel/boot_adsp/boot` write in `init.qcom.rc`
- `/sys/kernel/boot_cdsp/boot` write in `init.qcom.rc`
- `/sys/kernel/boot_slpi/boot` write in `init.vendor.sensors.rc`
- `vendor.qrtr-ns`, `vendor.rmt_storage`, `vendor.tftp_server`, and
  `vendor.pd_mapper` service definitions are present

Native currently exposes the write-only boot nodes for ADSP, CDSP, SLPI, and
WLAN, but V614 only listed them; it did not write them.

## Interpretation

V613 proved:

```text
MSS ONLINE → QRTR RX/TX → modem sysmon-qmi → rmt_storage/service-locator
```

V614 narrows the missing Android-equivalent lower path to:

```text
ADSP/CDSP/SLPI boot nodes → sibling sysmon-qmi → service-notifier 180/74
```

`mdm3=ONLINE` remains a useful Android/native state delta, but available timing
evidence does not support raw `esoc0` open as the next action primitive. The
safer next proof is to reproduce Android's DSP boot-node sequence first.

## Next Gate

V615 should be a bounded live observer:

1. refresh current-boot V401/V490 if needed;
2. mount firmware surfaces as in V613;
3. write only `1` to ADSP/CDSP/SLPI boot nodes;
4. hold only `subsys_modem`, not `esoc0`;
5. run the no-CNSS companion window;
6. capture dmesg/state/proc surfaces;
7. reboot cleanup;
8. keep CNSS/HAL/scan/connect blocked unless sibling sysmon and
   service-notifier publication advance.
