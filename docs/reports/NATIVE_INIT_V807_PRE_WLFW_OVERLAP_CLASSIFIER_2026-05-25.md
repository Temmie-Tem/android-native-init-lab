# Native Init V807 Pre-WLFW Overlap Classifier Report

## Result

- decision: `v807-overlapped-companion-boot-wlan-gate-selected`
- pass: `true`
- runner: `scripts/revalidation/native_wifi_pre_wlfw_overlap_classifier_v807.py`
- evidence: `tmp/wifi/v807-pre-wlfw-overlap-classifier/`

## What Ran

```bash
python3 -m py_compile scripts/revalidation/native_wifi_pre_wlfw_overlap_classifier_v807.py

python3 scripts/revalidation/native_wifi_pre_wlfw_overlap_classifier_v807.py \
  --out-dir tmp/wifi/v807-pre-wlfw-overlap-plan-check \
  plan

python3 scripts/revalidation/native_wifi_pre_wlfw_overlap_classifier_v807.py run
```

V807 was host-only. It did not execute any device command.

## Evidence Summary

| Signal | Result |
| --- | --- |
| V805 route input | pass |
| V806 service69 absent input | pass |
| V752/V802 source order | companion helper completes before `boot_wlan` |
| provider-first mode | enabled |
| critical companion children | exited/postflight safe |
| service-notifier/sysmon first timestamp | before `wlan: Loading driver` |
| `boot_wlan` loading timestamp | later than service context |
| QRTR service `69` after boot observe | `0` |

## Classification

V807 separates a timing/lifetime gap from the lower-provider proof:

```text
V806/V802 current structure:
  helper provider-first context
    -> service74/180 observed
    -> service-manager / vndservice / cnss retry children cleaned up
  then boot_wlan observe
    -> wlan: Loading driver
    -> qcwlanstate OFF
    -> service69 absent
```

This means V806 did not prove that service74/180/provider/CNSS context was alive
during the actual WLFW publication attempt. It proved that the context can be
created, then later `boot_wlan` still stalls after that context has been cleaned
up.

The next useful live gate is therefore not another sequential provider-first
replay. V808 should overlap the companion services and `boot_wlan` observe in
one bounded window.

## Safety

- Host-only classifier; no device command executed.
- No custom kernel flash, boot image write, partition write, or reboot.
- No Wi-Fi HAL, `wificond`, supplicant, hostapd, scan/connect, credential use,
  DHCP, route change, or external ping.
- No `boot_wlan`, `qcwlanstate`, `esoc0`, bind/unbind, module load/unload, or
  driver override.
- No Wi-Fi secret material was written to tracked output.

## Next

V808 should be a bounded live gate that starts provider-first companion services
and runs `boot_wlan` while those services remain alive. It should still stop
before Wi-Fi HAL, scan/connect, credentials, DHCP, routes, and external ping.
