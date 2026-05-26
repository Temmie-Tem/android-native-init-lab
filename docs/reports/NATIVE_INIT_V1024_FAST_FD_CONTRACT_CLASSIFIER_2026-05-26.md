# V1024 Fast FD Contract Classifier

- date: `2026-05-26`
- scope: V1022 target-fd-first sampler improvement + V1024 host-only classifier
- decision: `v1024-android-pm-esoc-fd-contract-captured`
- pass: `True`
- evidence: `tmp/wifi/v1024-fast-fd-contract-classifier/manifest.json`
- live handoff evidence: `tmp/wifi/v1024-fast-fd-android-timing-handoff-live-20260526-181232/manifest.json`

## Summary

V1024 captured the missing Android PM/eSoC fd contract and compared it with the
V1020 native failure.

The improved V1022 sampler now dumps target process fds before the broad
`ps`/`/proc` scan. During the first Android ADB window it captured:

| Process | FD |
| --- | --- |
| `pm_proxy_helper` | `/dev/subsys_modem` |
| `pm-service` | `/dev/subsys_modem` |
| `mdm_helper` | `/dev/esoc-0` |

The same handoff's late sampler captured the WLFW/FW-ready/`wlan0` chain. Native
rollback to v724 was verified.

## Android Timing

From the V1024 late sampler:

| Marker | Time |
| --- | ---: |
| `vendor.per_proxy_helper` start | `5.822268s` |
| `vendor.per_mgr` start | `6.961623s` |
| `vendor.per_proxy` start | `7.684133s` |
| `vendor.mdm_helper` start | `8.033871s` |
| `cnss-daemon wlfw_start` | `8.198751s` |
| `/dev/subsys_esoc0` get | `8.301226s` |
| `WLAN FW is ready` | `14.400537s` |
| `wlan0` event | `15.215998s` |

## Native Delta

V1020 native had:

- `mdm_helper` `/dev/esoc-0` fd: present
- `/dev/subsys_esoc0` open: attempted
- WLFW: absent
- `pm_proxy_helper`: not started
- `pm-proxy`: not started

This explains why V1020 reached `sdx50m_toggle_soft_reset` but did not progress:
the Android-good path has a PM proxy/subsystem modem fd contract that V1020 did
not reproduce.

## Interpretation

The next native gate should not retry the same V1020 subsystem open and should
not retry standalone `pm_proxy_helper` from V867. The next source/build unit
should model the Android PM full-contract surface:

```text
pm_proxy_helper -> /dev/subsys_modem
pm-service      -> /dev/subsys_modem
pm-proxy        -> service companion
mdm_helper      -> /dev/esoc-0
CNSS/Wi-Fi upper surface
bounded subsystem retry only after PM contract is present
```

The exact live order and cleanup policy still need a source/build support step
before another native live attempt.

## Guardrails

- no native `/dev/subsys_esoc0` retry in V1024
- no `/dev/esoc-*` ioctl
- no GPIO/sysfs/debugfs write
- no Wi-Fi command, scan/connect/link-up, credential use, DHCP/route, or external ping
- Android boot write was followed by native v724 readback and native `BOOT OK`

## Validation

Commands:

```bash
python3 -m py_compile \
  scripts/revalidation/native_wifi_android_pm_esoc_timing_v1022.py \
  scripts/revalidation/native_wifi_v1024_fast_fd_contract_classifier.py
python3 scripts/revalidation/native_wifi_v1024_fast_fd_contract_classifier.py run
```

Result:

```text
decision: v1024-android-pm-esoc-fd-contract-captured
pass: True
next: V1025 source/build helper support for Android PM full-contract gate before native subsystem retry
```

Current native status after rollback:

```text
boot: BOOT OK shell
selftest: pass=11 warn=1 fail=0
```

## Next

Proceed to V1025 as source/build-only helper support for an Android PM
full-contract gate. It should add observability and fail-closed safety first;
live actor start and subsystem retry should be separate later gates.

