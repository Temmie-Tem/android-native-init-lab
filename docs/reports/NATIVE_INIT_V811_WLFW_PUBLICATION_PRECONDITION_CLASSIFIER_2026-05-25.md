# Native Init V811 WLFW Publication Precondition Classifier Report

## Result

- decision: `v811-wlfw-publication-precondition-mdm3-wlanpd-gap-selected`
- pass: `true`
- runner: `scripts/revalidation/native_wifi_wlfw_publication_precondition_classifier_v811.py`
- evidence: `tmp/wifi/v811-wlfw-publication-precondition-classifier/`

## What Ran

```bash
python3 -m py_compile scripts/revalidation/native_wifi_wlfw_publication_precondition_classifier_v811.py

python3 scripts/revalidation/native_wifi_wlfw_publication_precondition_classifier_v811.py \
  --out-dir tmp/wifi/v811-wlfw-publication-precondition-classifier-plan-check \
  plan

python3 scripts/revalidation/native_wifi_wlfw_publication_precondition_classifier_v811.py run
```

V811 was host-only. It did not execute any device command.

## Evidence Summary

| Signal | Result |
| --- | --- |
| V810 | PLD/SNOC/ICNSS register is not enough; probe is gated by WLFW/FW_READY |
| Android reference | mss/mdm3 `ONLINE`; WLAN-PD, WLFW, BDF, and `wlan0` present |
| Native V731/V733/V735/V738 | mss/QRTR/sysmon/service-notifier can advance, but mdm3 remains `OFFLINING` |
| Native service69 readback | clean-empty; service events `0`, timeouts `0` |
| V808 current overlap | service-notifier present, but WLAN-PD/WLFW/FW_READY/BDF/MHI/`wlan0` absent |

## Classification

The active blocker is now below ICNSS register/probe and below Wi-Fi HAL:

```text
Android:
  mdm3 ONLINE
    -> WLAN-PD / service 74
      -> WLFW service69
        -> ICNSS-QMI / FW_READY
          -> BDF / wiphy / wlan0

Native:
  mss ONLINE / QRTR / sysmon / service-notifier partial surfaces
    -> mdm3 stays OFFLINING
      -> WLAN-PD absent
        -> WLFW service69 absent
```

That means retrying `qcwlanstate`, register-driver, service-manager/HAL, or
scan/connect would still be premature. The next useful live work must target
the mdm3/WLAN-PD/service69 publication preconditions only.

## Safety

- Host-only classifier; no device command executed.
- No custom kernel flash, boot image write, partition write, or reboot.
- No Wi-Fi HAL, `wificond`, supplicant, hostapd, scan/connect, credential use,
  DHCP, route change, or external ping.
- No `boot_wlan`, `qcwlanstate`, `esoc0`, bind/unbind, module load/unload, or
  driver override.
- No Wi-Fi secret material was written to tracked output.

## Next

V812 should plan the smallest below-HAL live observer for mdm3/WLAN-PD/service69
publication preconditions. It should reuse current V401/V490, firmware mounts,
and established cleanup rules, and it must still avoid Wi-Fi HAL start,
scan/connect, credentials, DHCP/routes, and external ping.
