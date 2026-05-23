# Native Init V660 Ready CNSS Retry Live Report

- date: `2026-05-23 KST`
- status: `live classified`; Wi-Fi external ping is **not** complete
- runner: `scripts/revalidation/native_wifi_ready_cnss_retry_v660.py`
- plan: `docs/plans/NATIVE_INIT_V660_READY_CNSS_RETRY_PLAN_2026-05-23.md`
- prerequisite evidence:
  - `tmp/wifi/v660-prereq-refresh-20260523-104437/`
  - `tmp/wifi/v660-v490-current-run/`
  - `tmp/wifi/v660-ready-cnss-retry-preflight-ready/`
- live evidence: `tmp/wifi/v660-ready-cnss-retry-live/`
- post-run health evidence: `tmp/wifi/v660-post-live-device-health-20260523-104847/`
- decision: `v660-cnss-retry-binder-loop-persists`

## Scope

V660 reused helper `a90_android_execns_probe v107` and enabled the fresh
`cnss_daemon_retry` tail after the V659-proven readiness sequence:

```text
service 74 -> servicemanager/hwservicemanager/vndservicemanager -> vndservicemanager_ready -> cnss_daemon_retry
```

No Wi-Fi HAL, `wificond`, supplicant, hostapd, scan/connect/link-up,
credential, DHCP, route change, external ping, boot image change, or partition
write was executed.

## Prerequisites

| prerequisite | result | evidence |
| --- | --- | --- |
| helper v107 current | pass | remote helper SHA and mode already verified |
| V641 clean-DSP one-shot | pass | timeline has `complete failures=0 timeouts=0`; ADSP/CDSP/DSPS RPMSG nodes present |
| V490 current-boot policy load | pass | `v490-selinux-policy-load-proof-pass` |
| V641 firmware mount cleanup | pass | firmware mounts unmounted before V660 preflight |
| V660 preflight | pass | `v660-vndservicemanager-cnss-retry-preflight-ready` |

## Result

```text
decision: v660-cnss-retry-binder-loop-persists
pass: True
reason: fresh cnss retry executed but binder transaction failure persisted
next: classify vndservicemanager context-manager readiness or missing vendor binder service registration before HAL
```

## Retry Surface

| field | value |
| --- | --- |
| `service74_gate.seen` | `1` |
| `service74_gate.open` | `1` |
| `service74_gate.wait_ms` | `15` |
| `vndservicemanager_readiness.ready` | `1` |
| `cnss_retry.enabled` | `1` |
| `cnss_retry.initial_cleanup_safe` | `1` |
| `cnss_retry.retry_start_order` | `10` |
| `cnss_retry.retry_observable` | `1` |
| `cnss_retry.retry_postflight_safe` | `1` |

## Marker Summary

| marker | count |
| --- | ---: |
| `service_notifier_180` | 1 |
| `service_notifier_74` | 1 |
| `cnss_daemon_netlink` | 10 |
| `cnss_daemon_cld80211` | 4 |
| `cnss_binder_transaction_failed` | 1 |
| `binder_transaction_failed` | 1 |
| `binder_ioctl_unsupported` | 2 |
| `wlfw_start` | 0 |
| `wlfw_service_request` | 0 |
| `wlan_pd` | 0 |
| `qmi_server_connected` | 0 |
| `bdf_regdb` | 0 |
| `bdf_bdwlan` | 0 |
| `wlan_fw_ready` | 0 |
| `wlan0` | 0 |
| `kernel_warning` | 1 |

## Interpretation

V660 closes the "retry was never executed" uncertainty. The retry tail ran
only after:

1. fresh service `74`;
2. service-manager trio startup;
3. `vndservicemanager_readiness.ready=1`;
4. safe cleanup of the initial `cnss-daemon`.

The result still does not reach WLFW, WLAN-PD, QMI server connected, BDF,
firmware-ready, or `wlan0`. The next blocker is therefore not readiness
ordering but the actual vendor binder service/registration surface seen by
`cnss-daemon`.

The single known `pm_qos_add_request` warning class also remains present. It
did not prevent cleanup, but it should remain part of the next classifier.

## Cleanup

The proof used reboot cleanup. The reboot command lost the serial END marker
during reset, but post-reboot checks succeeded:

- `version_seen=true`
- `status_healthy=true`
- wait time: `32.34s`
- post-run `bootstatus`: `BOOT OK`, `fail=0`
- post-run `selftest`: `fail=0`
- no active service-manager/CNSS residue was found
- exposure remains USB-local: NCM absent, `tcpctl` stopped, `rshell` stopped

## Next Gate

Proceed to a host-only V661 binder registration/context classifier before any
new live retry:

1. compare native `servicemanager`, `hwservicemanager`, `vndservicemanager`,
   and binderfs/devnode context against Android reference;
2. classify whether `cnss-daemon` expects a missing vendor binder service,
   context-manager state, property, or namespace file;
3. keep Wi-Fi HAL, scan/connect, credentials, DHCP, routes, and external ping
   blocked until WLFW/WLAN-PD/BDF or safe `wlan0` evidence advances.
