# Native Init V678 Binder Failure Target Classifier Report

## Summary

- script: `scripts/revalidation/native_wifi_binder_failure_target_classifier_v678.py`
- plan evidence: `tmp/wifi/v678-binder-failure-targets-plan/`
- run evidence: `tmp/wifi/v678-binder-failure-targets/`
- decision: `v678-property-clean-binder-transaction-targets-classified`
- pass: `true`
- device command/live mutation: not executed
- scan/connect/DHCP/external ping: not executed

V678 consumed the V677 replay evidence after the private property runtime repair.
It confirms the blocker moved from property layout to Binder
registration/transaction state.

## Checks

| Check | Result |
| --- | --- |
| V677 input ready | pass |
| property denials cleared | pass |
| Binder devnodes ready | pass |
| service-manager surface ready | pass |
| post-HAL surface ready | pass |
| CNSS retry surface ready | pass |
| lower Wi-Fi markers absent | pass |
| Binder failures persist | finding |
| CNSS transaction gap present | finding |
| registry/debug snapshot missing | finding |

## Property Surface

| Metric | Value |
| --- | ---: |
| property denial total | `0` |
| property denial unique | `0` |
| Binder failure count | `5` |

## Binder Failure Classification

| Actor | Kind | Code | Errno | Count |
| --- | --- | --- | --- | ---: |
| `servicemanager` | ioctl | `40046210` | `-22` | `1` |
| `hwservicemanager` | ioctl | `40046210` | `-22` | `1` |
| `wificond` | ioctl | `40046210` | `-22` | `2` |
| `cnss-daemon` | transaction | `29189` | `-22` | `1` |

The generic service-manager and `wificond` ioctl `-22` class is not enough by
itself to explain the stop. The actionable blocker is the `cnss-daemon`
vndbinder transaction failure while WLFW/BDF/`wlan0` remain absent.

## Child Binder Surface

| Child | Binder FD class | SELinux domain | Result |
| --- | --- | --- | --- |
| `servicemanager` | binder | `u:r:servicemanager:s0` | ready |
| `hwservicemanager` | hwbinder | `u:r:hwservicemanager:s0` | ready |
| `vndservicemanager` | vndbinder | `u:r:vndservicemanager:s0` | ready |
| Wi-Fi HAL legacy | hwbinder | `u:r:hal_wifi_default:s0` | ready |
| Wi-Fi HAL ext | hwbinder | `u:r:hal_wifi_default:s0` | ready |
| `wificond` | binder + hwbinder | `u:r:wificond:s0` | ready |
| `cnss-daemon` retry | vndbinder | `u:r:vendor_wcnss_service:s0` | ready |

## Lower Wi-Fi Markers

| Marker | Count |
| --- | ---: |
| WLFW start/request | `0` |
| WLAN-PD | `0` |
| QMI server connected | `0` |
| BDF `regdb.bin` | `0` |
| BDF `bdwlan.bin` | `0` |
| WLAN firmware ready | `0` |
| `wlan0` | `0` |

## Interpretation

V678 closes the V675 through V677 transition:

```text
V677 private property root
  -> property denials = 0
  -> service-manager/HAL/wificond/CNSS child surfaces ready
  -> Binder failures remain
  -> CNSS vndbinder transaction fails before WLFW
  -> WLFW/BDF/wlan0 still absent
```

The next useful unit is not another property pass and not a Wi-Fi connection
attempt. V679 should enable a bounded Binder registry/debug/failed-transaction
snapshot around the same failing window, preferably without widening to
supplicant, scan/connect, credentials, DHCP, routes, or external ping.

## Validation

```sh
python3 -m py_compile \
  scripts/revalidation/native_wifi_binder_failure_target_classifier_v678.py

python3 scripts/revalidation/native_wifi_binder_failure_target_classifier_v678.py \
  --out-dir tmp/wifi/v678-binder-failure-targets-plan \
  plan

python3 scripts/revalidation/native_wifi_binder_failure_target_classifier_v678.py \
  --out-dir tmp/wifi/v678-binder-failure-targets \
  run
```

The validation passed. The run decision was
`v678-property-clean-binder-transaction-targets-classified`.
