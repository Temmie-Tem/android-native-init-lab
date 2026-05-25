# Native Init V818 mdm3/esoc0 Registration Classifier Report

## Result

- decision: `v818-mdm3-esoc-registration-gap-classified`
- pass: `true`
- runner: `scripts/revalidation/native_wifi_mdm3_esoc_registration_classifier_v818.py`
- evidence: `tmp/wifi/v818-mdm3-esoc-registration-classifier/`

## What Ran

```bash
python3 -m py_compile scripts/revalidation/native_wifi_mdm3_esoc_registration_classifier_v818.py

python3 scripts/revalidation/native_wifi_mdm3_esoc_registration_classifier_v818.py \
  --out-dir tmp/wifi/v818-mdm3-esoc-registration-classifier-plan-check \
  plan

python3 scripts/revalidation/native_wifi_mdm3_esoc_registration_classifier_v818.py run
```

V818 was host-only. It did not execute any device command.

## Evidence Summary

| Evidence | Classification |
| --- | --- |
| V817 | lower window moves mss `OFFLINING -> ONLINE -> ONLINE` and reaches `sysmon_qmi`, but mdm3 remains `OFFLINING` |
| V817 service publication | service-notifier/service74/WLAN-PD/WLFW/BDF/`wlan0` stay absent |
| V798 | modem PIL notification sequence is complete; modem PIL absence is not the blocker |
| V795 | holder-only path already moves mss to `ONLINE` but leaves mdm3 `OFFLINING` |
| esoc surface | `/sys/bus/esoc/devices/esoc0` and `subsys_esoc0` are visible, but `/dev/esoc*` and `/dev/subsys*` are absent |
| QRTR publication | helper QRTR window exists, but service events and service69 readback events are `0` |

## Classification

V818 closes three retry paths:

```text
holder-only retry:
  already moves mss ONLINE
  does not move mdm3 or publish WLAN services

PIL/custom-kernel retry:
  V798 already mapped complete modem PIL notifications
  custom OSRC kernel flash remains paused after V771/V774 failures

HAL/connect retry:
  lower service-publication is still absent
  credentials/DHCP/external ping are above the current blocker
```

The next useful live step is a narrower read-only catalogue of mdm3/esoc0
registration surfaces inside the same lower window. The catalogue should inspect
sysfs/debugfs/proc registration state and per-process QRTR visibility, but it
must not open `esoc0`, write subsystem state, start service-manager/HAL, scan or
connect Wi-Fi, use credentials, change routes, or ping externally.

## Safety

- Host-only classifier; no device command executed.
- No custom kernel flash, boot image write, partition write, reboot, or
  bootloader handoff.
- No `esoc0` open, bind/unbind, driver override, module load/unload,
  service-manager, Wi-Fi HAL, scan/connect/link-up, credential use, DHCP, route
  change, or external ping.
- No Wi-Fi secret material was written to tracked output.

## Next

V819 should run a bounded read-only mdm3/esoc0 service-locator/sysmon
registration catalogue below service-manager, Wi-Fi HAL, scan/connect, DHCP,
and external ping.
