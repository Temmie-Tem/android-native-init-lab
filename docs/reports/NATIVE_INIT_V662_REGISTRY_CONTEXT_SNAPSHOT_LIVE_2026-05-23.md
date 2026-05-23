# Native Init V662 Registry/Context Snapshot Live Report

- date: `2026-05-23 KST`
- status: `live passed`; Wi-Fi external ping is **not** complete
- runner: `scripts/revalidation/native_wifi_registry_context_snapshot_v662.py`
- deploy wrapper: `scripts/revalidation/wifi_execns_helper_v108_deploy_preflight.py`
- plan: `docs/plans/NATIVE_INIT_V662_REGISTRY_CONTEXT_SNAPSHOT_PLAN_2026-05-23.md`
- precondition evidence:
  - `tmp/wifi/v662-rerun-preconditions-20260523-113537/`
  - `tmp/wifi/v662-v490-current-run/`
- live evidence: `tmp/wifi/v662-registry-context-snapshot-live-rerun/`
- decision: `v662-registry-context-snapshot-pass`

## Scope

V662 used helper `a90_android_execns_probe v108` and kept the V659-proven
sequence:

```text
service 74 -> servicemanager/hwservicemanager/vndservicemanager
  -> vndservicemanager_ready -> registry_snapshot
```

The run deliberately kept `cnss_retry.enabled=0`. It did not start Wi-Fi HAL,
`wificond`, supplicant, hostapd, scan/connect/link-up, credentials, DHCP, route
changes, external ping, `qcwlanstate`, boot-image writes, or partition writes.

## Prerequisites

| prerequisite | result | evidence |
| --- | --- | --- |
| helper v108 current | pass | remote helper SHA and mode verified |
| V641 clean-DSP one-shot | pass | ADSP/CDSP/DSPS RPMSG nodes present |
| V401 SELinuxfs mount | pass | `toybox-selinuxfs-mount-live-executor-run-pass` |
| V490 current-boot policy load | pass | `v490-selinux-policy-load-proof-pass` |
| firmware mount cleanup | pass | global firmware mounts were unmounted before V662 live |

## Result

```text
decision: v662-registry-context-snapshot-pass
pass: True
reason: registry snapshot begin/end markers were captured before and after the initial cnss-daemon cleanup
next: classify snapshot evidence before deciding whether property namespace or service registration needs repair before CNSS retry
```

## Snapshot Surface

| field | value |
| --- | --- |
| `service74_gate.seen` | `1` |
| `service74_gate.open` | `1` |
| `service74_gate.wait_ms` | `15` |
| `vndservicemanager_readiness.ready` | `1` |
| `initial_cnss_daemon.cleanup_safe` | `1` |
| `cnss_retry.enabled` | `0` |
| `registry_snapshot.enabled` | `1` |
| `registry_snapshot.before_end` | `1` |
| `registry_snapshot.after_end` | `1` |
| `registry_snapshot.before_files_captured` | `0` |
| `registry_snapshot.after_files_captured` | `0` |

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

## Interpretation

V662 closes the parser/observability gap from V661. The helper reached service
`74`, started the service-manager trio, proved `vndservicemanager` readiness,
kept the fresh CNSS retry tail disabled, and emitted registry snapshot
begin/end markers on both sides of the initial `cnss-daemon` cleanup.

The snapshot itself found no populated Binder debugfs/property/socket rows from
the helper namespace. That means the next blocker is narrower than ordering:
the service-manager trio is observable and cleanup-safe, but `cnss-daemon` still
does not progress into WLFW/WLAN-PD/QMI/BDF/`wlan0`. The next gate should
classify whether this is due to missing private Binder debugfs visibility,
property service namespace materialization, or a vendor service registration
surface that `cnss-daemon` expects before WLFW.

## Cleanup

The proof used reboot cleanup. The reboot command loses its serial END marker
during reset, but post-reboot health checks succeeded:

- `version_seen=true`
- `status_healthy=true`
- wait time: `32.34s`
- helper-owned children were observable and postflight-safe
- Wi-Fi bring-up remained disabled

## Next Gate

Proceed to a host-only V663 classifier:

1. parse V662 snapshot blocks and explain why captured file/dir counts are zero;
2. compare private namespace Binder/property/socket visibility against Android
   reference and prior V658/V661 evidence;
3. choose the smallest bounded repair target before any new CNSS retry, Wi-Fi
   HAL start, scan/connect, credential use, DHCP, route change, or external
   ping.
