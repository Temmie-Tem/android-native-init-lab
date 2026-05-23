# Native Init V657 Helper-v106 Service74 Replay Live Report

- date: `2026-05-23 KST`
- status: `live classified`; Wi-Fi external ping is **not** complete
- runner: `scripts/revalidation/native_wifi_service74_v106_replay_v657.py`
- plan: `docs/plans/NATIVE_INIT_V657_SERVICE74_V106_REPLAY_PLAN_2026-05-23.md`
- prerequisite evidence:
  - `tmp/wifi/v657-prereq-refresh-20260523-095604/`
  - `tmp/wifi/v657-v490-current-run/`
  - `tmp/wifi/v657-service74-v106-replay-preflight-ready/`
- live evidence: `tmp/wifi/v657-service74-v106-replay-live/`
- decision: `v657-binder-loop-persists`

## Scope

V657 reran the V653-compatible service `74` gated service-manager mode with
helper `a90_android_execns_probe v106`.

No V655 `vndservicemanager` readiness tail, fresh CNSS retry tail, Wi-Fi HAL,
scan/connect/link-up, credential, DHCP, route change, external ping, boot image
change, or partition write was executed.

## Prerequisites

| prerequisite | result | evidence |
| --- | --- | --- |
| bridge/device health | pass | post-run `bootstatus` returned `BOOT OK`, `fail=0`, USB-local boundary |
| V641 clean-DSP one-shot | pass | timeline has `complete failures=0 timeouts=0`; ADSP/CDSP/SLPI RPMSG nodes present |
| firmware pre-mount cleanup | pass | V641 firmware mounts were unmounted before V657 preflight |
| V490 current-boot policy load | pass | `v490-selinux-policy-load-proof-pass`, `policy_load_executed=true` |
| V657 preflight | pass | `v657-service74-gated-service-manager-preflight-ready` |

## Result

```text
decision: v657-binder-loop-persists
pass: True
reason: service74 preserved but cnss binder transaction failures persisted
next: inspect service-manager namespace/SELinux/property mismatch before another live retry
```

## Marker Summary

| marker | count |
| --- | ---: |
| `service_notifier_180` | 1 |
| `service_notifier_74` | 1 |
| `cnss_daemon_netlink` | 5 |
| `cnss_daemon_cld80211` | 2 |
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

## Service74 Gate

| field | value |
| --- | --- |
| `baseline_count_74` | `0` |
| `baseline_syslog_available` | `1` |
| `final_count_74` | `1` |
| `seen` | `1` |
| `status` | `open` |
| `open` | `1` |
| `wait_attempts` | `1` |
| `wait_ms` | `16` |

## Interpretation

V657 proves helper v106 can still reproduce the V653 lower gate when using the
exact V653-compatible mode. Therefore V655's service `74` timeout is not simply
"helper v106 cannot publish service `74`".

The active blocker moves back to the post-service `74` service-manager/CNSS
binder surface:

```text
QRTR RX -> service 180/74 -> service-manager trio -> cnss-daemon binder -22
```

WLFW, WLAN-PD, QMI server connected, BDF, firmware-ready, and `wlan0` remain
absent. Wi-Fi bring-up is still blocked.

## Cleanup

The live proof used reboot cleanup. The reboot command lost its serial END
marker during reset, but post-reboot checks succeeded:

- `status_healthy=true`
- `version_seen=true`
- wait time: `32.34s`
- post-run `bootstatus`: `BOOT OK`, `fail=0`
- exposure remains USB-local: NCM absent, `tcpctl` stopped, `rshell` stopped

## Next Gate

Proceed to a host-only V658 binder/namespace classifier before another live
retry:

1. compare V653/V657 service-manager helper transcripts against V655
   `vndservicemanager` readiness intent;
2. inspect service-manager namespace, SELinux context, property/runtime files,
   and binder transaction failure surface;
3. decide whether the next live gate should modify namespace/property setup or
   service-manager readiness timing;
4. keep Wi-Fi HAL, scan/connect, credentials, DHCP, routes, and external ping
   blocked until WLFW/WLAN-PD/BDF evidence advances.
