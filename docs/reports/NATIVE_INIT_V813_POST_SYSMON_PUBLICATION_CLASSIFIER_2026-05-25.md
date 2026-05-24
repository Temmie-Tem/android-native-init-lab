# Native Init V813 Post-Sysmon Publication Classifier Report

## Result

- decision: `v813-sibling-sysmon-service-publication-precondition-selected`
- pass: `true`
- runner: `scripts/revalidation/native_wifi_post_sysmon_publication_classifier_v813.py`
- evidence: `tmp/wifi/v813-post-sysmon-publication-classifier/`

## What Ran

```bash
python3 -m py_compile scripts/revalidation/native_wifi_post_sysmon_publication_classifier_v813.py

python3 scripts/revalidation/native_wifi_post_sysmon_publication_classifier_v813.py \
  --out-dir tmp/wifi/v813-post-sysmon-publication-classifier-plan-check \
  plan

python3 scripts/revalidation/native_wifi_post_sysmon_publication_classifier_v813.py run
```

V813 was host-only. It did not execute any device command.

## Evidence Summary

| Signal | Result |
| --- | --- |
| V812 current gate | `mss ONLINE`, QRTR RX/TX and `sysmon_qmi` present |
| V812 blocker | `mdm3 OFFLINING`, service69 events `0`, timeouts `0` |
| V812 absent markers | service-notifier, WLAN-PD, WLFW, BDF, `wlan0` |
| V785 | memshare/CMA failures are common/non-fatal; first divergence is sibling sysmon |
| V783 | native reaches sysmon but lacks service74/180 continuation |
| Android V626 | sysmon modem/esoc0/adsp/cdsp/slpi all present; service180/service74/WLAN-PD/WLFW/BDF/`wlan0` present |
| Native V626 | sysmon modem present; sysmon esoc0/adsp/cdsp/slpi absent; service74/WLAN-PD/WLFW/BDF/`wlan0` absent |

## Classification

V813 narrows the active blocker from generic mdm3/WLAN-PD publication to the
post-sysmon sibling-sysmon/service-publication preconditions:

```text
Android reference:
  sysmon_modem
    -> sibling sysmon esoc0/adsp/cdsp/slpi
      -> service-notifier 180 -> service-notifier 74
        -> WLAN-PD / WLFW / BDF / wlan0

Native:
  sysmon_modem / QRTR
    -> sibling sysmon missing
      -> service74/WLAN-PD/WLFW/service69 missing
        -> BDF / wlan0 missing
```

That means repeating memshare-only checks, `boot_wlan`, `qcwlanstate`,
service-manager/HAL, scan/connect, or custom-kernel flash is not justified.

## Safety

- Host-only classifier; no device command executed.
- No custom kernel flash, boot image write, partition write, reboot, or
  bootloader handoff.
- No Wi-Fi HAL, `wificond`, supplicant, hostapd, scan/connect/link-up, or
  credential use.
- No DHCP, route change, or external ping.
- No `boot_wlan`, `qcwlanstate`, `esoc0`, bind/unbind, driver override, or
  module load/unload.
- No Wi-Fi secret material was written to tracked output.

## Next

V814 should isolate sibling sysmon/service-publication prerequisites below
HAL/connect. It should not retry custom-kernel flashing. The smallest useful
gate is to classify the Android-vs-native inputs that make sibling sysmon and
service74 publish after sysmon_modem: service-locator/sysmon state, mdm3 owner
state, subsystem registration, and lower companion lifetime/order.
