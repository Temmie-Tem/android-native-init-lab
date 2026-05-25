# Native Init V821 QRTR Nameservice Matrix Report

## Result

- decision: `v821-qrtr-nameservice-matrix-empty-below-hal`
- pass: `true`
- runner: `scripts/revalidation/native_wifi_qrtr_nameservice_matrix_v821.py`
- evidence: `tmp/wifi/v821-qrtr-nameservice-matrix/`

## What Ran

```bash
python3 -m py_compile \
  scripts/revalidation/native_wifi_qrtr_nameservice_matrix_v821.py \
  scripts/revalidation/wifi_execns_helper_v125_deploy_preflight.py

scripts/revalidation/build_android_execns_probe_helper.sh \
  tmp/wifi/v821-execns-helper-v125-build/a90_android_execns_probe

python3 scripts/revalidation/native_wifi_qrtr_nameservice_matrix_v821.py \
  --out-dir tmp/wifi/v821-qrtr-nameservice-matrix-plan-check-current \
  plan

python3 scripts/revalidation/wifi_execns_helper_v125_deploy_preflight.py \
  --out-dir tmp/wifi/v821-helper-v125-deploy-plan-check-current \
  plan

python3 scripts/revalidation/native_wifi_qrtr_nameservice_matrix_v821.py \
  preflight

python3 scripts/revalidation/native_wifi_qrtr_nameservice_matrix_v821.py \
  run
```

## Evidence Summary

| Signal | Result |
| --- | --- |
| helper | `a90_android_execns_probe v125` |
| helper sha256 | `49194d47fc251d3201f6af65ff78909087f4734584383f1d600a5daab29d30da` |
| helper deploy | executed |
| V817 lower window | pass |
| reboot cleanup | executed |
| matrix result | complete |
| matrix case count | `5` |
| AF_QIPCRTR sockets | all socket rc `0`, family `42` |
| nameservice lookup sends | all new/delete lookup rc `0` |
| timeouts | `0` |
| QMI payload | `0` |
| service events | `0` |

## Matrix Rows

| Case | Label | Service | Instance | Service events | End-of-list | Timeout | QMI attempted |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 0 | `servloc` | `64` | `1` | `0` | `1` | `0` | `0` |
| 1 | `servnotif` | `66` | `74` | `0` | `1` | `0` | `0` |
| 2 | `servnotif` | `66` | `180` | `0` | `1` | `0` | `0` |
| 3 | `wlfw` | `69` | `0` | `0` | `1` | `0` | `0` |
| 4 | `wlfw` | `69` | `1` | `0` | `1` | `0` | `0` |

## Interpretation

V821 widens V820 from a WLFW-only readback to the candidate service-locator,
service-notifier, and WLFW service IDs without sending any QMI payload. The
transport path is working: every matrix entry opens AF_QIPCRTR, sends the lookup
request, receives an end-of-list response, and deletes the lookup without
timeout.

The important result is negative: none of the checked candidates published a
service event in the lower window. This means the current blocker is no longer
`/proc/net/qrtr` or debugfs visibility. It is also not an AF_QIPCRTR socket or
lookup-send failure. The gap is now between the kernel-side sysmon/service
progress seen in dmesg and the empty userspace nameservice publication seen by
the helper.

## Safety

- Helper deploy wrote only the approved helper path.
- Cleanup reboot restored healthy v724 native status.
- No custom kernel flash, boot image write, partition write, or bootloader
  handoff executed.
- No `esoc0` open, bind/unbind, driver override, or module load/unload
  executed.
- No QMI payload, service-manager, Wi-Fi HAL, wificond, scan/connect/link-up,
  credential use, DHCP, route change, or external ping executed.
- V775 custom OSRC kernel flashing pause remains active.
- No Wi-Fi secret material was written to tracked output.

## Next

V822 should classify why kernel sysmon/service-locator dmesg appears while
AF_QIPCRTR nameservice publication stays empty below HAL/connect. The next gate
should stay below QMI payload, service-manager, Wi-Fi HAL, scan/connect,
credentials, DHCP/routes, external ping, and custom-kernel flash.
