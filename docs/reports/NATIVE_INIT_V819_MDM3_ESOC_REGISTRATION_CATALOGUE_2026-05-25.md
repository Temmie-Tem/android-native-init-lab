# Native Init V819 mdm3/esoc0 Registration Catalogue Report

## Result

- decision: `v819-mdm3-esoc-registration-catalogue-captured`
- pass: `true`
- runner: `scripts/revalidation/native_wifi_mdm3_esoc_registration_catalogue_v819.py`
- evidence: `tmp/wifi/v819-mdm3-esoc-registration-catalogue/`

## What Ran

```bash
python3 -m py_compile scripts/revalidation/native_wifi_mdm3_esoc_registration_catalogue_v819.py

python3 scripts/revalidation/native_wifi_mdm3_esoc_registration_catalogue_v819.py \
  --out-dir tmp/wifi/v819-mdm3-esoc-registration-catalogue-plan-check \
  plan

python3 scripts/revalidation/native_wifi_mdm3_esoc_registration_catalogue_v819.py run

timeout 30 python3 scripts/revalidation/a90ctl.py --json selftest
```

## Evidence Summary

| Signal | before holder | after holder | after companion |
| --- | --- | --- | --- |
| catalogue captured | yes | yes | yes |
| mss/modem | `OFFLINING` | `ONLINE` | `ONLINE` |
| mdm3/esoc0 | `OFFLINING` | `OFFLINING` | `OFFLINING` |
| `sysmon_qmi` | `0` | `0` | `1` |
| debugfs service surfaces | missing | missing | missing |
| `/proc/net/qrtr` | missing | missing | missing |
| per-process QRTR sections | `0` | `0` | `0` |
| WLAN-PD/WLFW | absent | absent | absent |

V819 preserves the V817 result while adding a narrower registration catalogue:
mss/QRTR/sysmon advances, but the public read-only service registration
surfaces still do not expose service-notifier/service-locator state, global
`/proc/net/qrtr` is absent, and no per-process QRTR catalogue sections are
visible through the sampled companion processes.

## Safety

- Stock v724 remained the runtime kernel and native init build.
- No custom kernel flash, boot image write, or bootloader handoff executed.
- No `esoc0` open, bind/unbind, driver override, or module load/unload
  executed.
- No service-manager, Wi-Fi HAL, wificond, scan/connect/link-up, credential use,
  DHCP, route change, or external ping executed.
- Cleanup reboot returned to stock v724; postflight `selftest` passed with
  `selftest: pass=11 warn=1 fail=0`.
- No Wi-Fi secret material was written to tracked output.

## Classification

V819 narrows the next step:

```text
lower window:
  mss ONLINE
  sysmon-qmi appears
  mdm3 remains OFFLINING
  WLAN-PD/WLFW absent

registration catalogue:
  esoc/mdm3 sysfs surfaces exist
  debugfs service surfaces absent
  /proc/net/qrtr absent
  per-process QRTR catalogue sections empty
```

The next useful step is not HAL/connect or another broad lower retry. V820
should inspect helper/per-process QRTR namespace state and service-locator
visibility more directly, still below service-manager, Wi-Fi HAL, scan/connect,
DHCP, and external ping.

## Implementation Note

Two guardrail issues were fixed before the passing run:

- the first catalogue command was too long for the serial command decoder, so it
  was split into short read-only commands;
- shell `echo` and implicit `cat/ls` were replaced with validator-safe
  `printf` and explicit toybox calls.

## Next

V820 should inspect helper/per-process QRTR namespace state and service-locator
visibility without service-manager, Wi-Fi HAL, scan/connect, credentials, DHCP,
or external ping.
