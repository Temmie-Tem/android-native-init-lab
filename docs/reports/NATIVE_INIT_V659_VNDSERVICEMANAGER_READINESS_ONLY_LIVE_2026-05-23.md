# Native Init V659 vndservicemanager Readiness-Only Live Report

- date: `2026-05-23 KST`
- status: `live passed`; Wi-Fi external ping is **not** complete
- runner: `scripts/revalidation/native_wifi_vndservicemanager_readiness_only_v659.py`
- deploy wrapper: `scripts/revalidation/wifi_execns_helper_v107_deploy_preflight.py`
- plan: `docs/plans/NATIVE_INIT_V659_VNDSERVICEMANAGER_READINESS_ONLY_PLAN_2026-05-23.md`
- helper build evidence: `tmp/wifi/v659-execns-helper-v107-build/`
- helper deploy evidence:
  - `tmp/wifi/v659-execns-helper-v107-deploy-run2/`
  - `tmp/wifi/v659-execns-helper-v107-deploy-verify-current/`
- prerequisite evidence:
  - `tmp/wifi/v659-prereq-refresh-20260523-103232/`
  - `tmp/wifi/v659-v490-current-run/`
  - `tmp/wifi/v659-vndservicemanager-readiness-only-preflight-ready2/`
- live evidence: `tmp/wifi/v659-vndservicemanager-readiness-only-live/`
- post-run health evidence: `tmp/wifi/v659-post-live-device-health-20260523-103842/`
- decision: `v659-vndservicemanager-readiness-pass`

## Scope

V659 adds helper `a90_android_execns_probe v107` and a new mode:

```text
wifi-companion-service74-gated-vnd-service-manager-readiness-start-only
```

The live proof starts the lower companion stack, waits for fresh service `74`,
starts `servicemanager`, `hwservicemanager`, and `vndservicemanager`, and then
checks `vndservicemanager` readiness. It intentionally does **not** run the
fresh `cnss-daemon` retry tail.

No Wi-Fi HAL, `wificond`, supplicant, hostapd, scan/connect/link-up,
credential, DHCP, route change, external ping, boot image change, or partition
write was executed.

## Implementation Notes

| item | result |
| --- | --- |
| helper version | `a90_android_execns_probe v107` |
| helper SHA-256 | `67776f512c47eb048147c312d5a0a618ff30b4a3bbab7e60af790ce727940995` |
| new mode | `wifi-companion-service74-gated-vnd-service-manager-readiness-start-only` |
| expected order | `qrtr_ns,rmt_storage,tftp_server,pd_mapper,cnss_diag,cnss_daemon,service74_gate,servicemanager,hwservicemanager,vndservicemanager,vndservicemanager_ready` |
| CNSS retry tail | disabled; `cnss_retry.enabled=0` |

The serial helper deploy path also received a correctness fix: serial line-size
preflight `ok` no longer overwrites install-result `ok`, and a `busy` result
now sends `hide` and retries once. This prevented a failed first append from
being misclassified as a successful helper install.

## Prerequisites

| prerequisite | result | evidence |
| --- | --- | --- |
| helper v107 build | pass | local helper has v107 marker, V659 mode, readiness keys, and expected SHA |
| helper v107 deploy | pass | serial deploy wrote `739` chunks, verified target SHA, and follow-up preflight reports `remote-helper-v107=pass` |
| V641 clean-DSP one-shot | pass | timeline has `complete failures=0 timeouts=0`; ADSP/CDSP/DSPS RPMSG nodes present |
| V641 firmware mount cleanup | pass | `/vendor/firmware_mnt` and `/vendor/firmware-modem` unmounted before V659 preflight |
| V490 current-boot policy load | pass | `v490-selinux-policy-load-proof-pass` |
| V659 preflight | pass | `v659-vndservicemanager-readiness-only-preflight-ready` |

## Result

```text
decision: v659-vndservicemanager-readiness-pass
pass: True
next: plan fresh cnss-daemon binder attempt after proven vndservicemanager readiness; still block Wi-Fi HAL and scan/connect
```

## Readiness Surface

| field | value |
| --- | --- |
| `service74_gate.seen` | `1` |
| `service74_gate.open` | `1` |
| `service74_gate.wait_ms` | `16` |
| `vndservicemanager_readiness.enabled` | `1` |
| `vndservicemanager_readiness.observable` | `1` |
| `vndservicemanager_readiness.fd_summary_captured` | `1` |
| `vndservicemanager_readiness.ready` | `1` |
| `initial_cnss_daemon.observable` | `1` |
| `initial_cnss_daemon.cleanup_safe` | `1` |
| `cnss_retry.enabled` | `0` |
| `cnss_retry.retry_start_order` | empty |

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

V659 proves the isolated service-manager readiness prerequisite that V658
selected:

```text
QRTR RX -> service 180/74 -> service-manager trio -> vndservicemanager ready
```

The blocker is now narrower. `vndservicemanager` readiness is no longer the
unknown. The remaining failure surface is the next `cnss-daemon` binder/QMI
transition: one `cnss-daemon` vndbinder transaction still fails before
WLFW/WLAN-PD/QMI/BDF/`wlan0`.

The fresh CNSS retry tail was deliberately not executed in V659, so the next
gate can test that tail with the readiness prerequisite proven instead of
mixing readiness discovery and retry behavior in one run.

The single `pm_qos_add_request` warning still matters. It matches the known
post-service `74` warning class and must be carried into the next gate's
classification. It did not break cleanup, but it means Wi-Fi HAL and
scan/connect remain blocked.

## Cleanup

The proof used reboot cleanup. The reboot command lost the serial END marker
during reset, but post-reboot checks succeeded:

- `version_seen=true`
- `status_healthy=true`
- wait time: `32.34s`
- post-run `bootstatus`: `BOOT OK`, `fail=0`
- post-run `selftest`: `fail=0`
- no active `servicemanager`, `hwservicemanager`, `vndservicemanager`, or
  `cnss-daemon` residue was found
- exposure remains USB-local: NCM absent, `tcpctl` stopped, `rshell` stopped

## Next Gate

Proceed to a fresh `cnss-daemon` binder-attempt gate using the proven V659
readiness prerequisite:

1. keep V641 clean-DSP, firmware cleanup, V490 policy-load, and helper v107
   prerequisites explicit;
2. start the fresh CNSS retry only after service `74` and
   `vndservicemanager_readiness.ready=1`;
3. classify whether binder `-22`, WLFW, WLAN-PD, QMI server, BDF, firmware
   ready, or `wlan0` advances;
4. keep Wi-Fi HAL, scan/connect, credentials, DHCP, routes, and external ping
   blocked until WLFW/WLAN-PD/BDF or a safe `wlan0` surface advances.
