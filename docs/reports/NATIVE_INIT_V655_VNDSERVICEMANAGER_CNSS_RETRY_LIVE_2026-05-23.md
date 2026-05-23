# Native Init V655 vndservicemanager CNSS Retry Live Report

- date: `2026-05-23 KST`
- status: `classified`; Wi-Fi external ping is **not** complete
- helper deploy evidence: `tmp/wifi/v655-execns-helper-v106-deploy-run/`
- V641 refresh evidence: `tmp/wifi/v655-prereq-refresh-20260523-093446/`
- V490 evidence: `tmp/wifi/v655-v490-current-run/`
- preflight evidence:
  `tmp/wifi/v655-vndservicemanager-cnss-retry-preflight-ready/`
- live evidence: `tmp/wifi/v655-vndservicemanager-cnss-retry-live/`
- decision: `v655-service74-gate-timeout`

## Scope

V655 deployed helper v106, refreshed the V641 clean-DSP one-shot state, mounted
Android system read-only, mounted SELinuxfs with toybox, loaded Android SELinux
policy through V490, and ran the bounded V655 live proof.

The live proof started only the lower companion/CNSS set before the service
`74` gate. Because service `74` did not appear, it correctly withheld
`servicemanager`, `hwservicemanager`, `vndservicemanager`, and fresh
`cnss_daemon_retry`.

V655 did not start Wi-Fi HAL, `wificond`, supplicant, or hostapd. It did not
scan/connect/link-up, use credentials, run DHCP, change routes, or ping
externally.

## Prerequisites

| prerequisite | result |
| --- | --- |
| helper v106 serial deployment | pass, sha256 verified on `/cache/bin/a90_android_execns_probe` |
| V641 one-shot clean-DSP refresh | pass, timeline reached `complete failures=0 timeouts=0` |
| sibling RPMSG nodes | pass, `adsp.IPCRTR`, `cdsp.IPCRTR`, and `dsps.IPCRTR` visible |
| Android system root | pass, `/mnt/system` mounted read-only |
| SELinuxfs | pass, toybox mount exposed `/sys/fs/selinux/status` |
| V490 policy load | pass, no init reexec, daemon start, HAL start, or Wi-Fi bring-up |
| V655 preflight | pass |

## Result

```text
decision: v655-service74-gate-timeout
pass: True
gate_status: timeout
baseline_74: 0
final_74: 0
wait_ms: 12232
service_manager_started: 0
wifi_bringup_executed: False
```

Lower companion/CNSS activity occurred, but service-notifier did not publish:

| marker | count |
| --- | --- |
| `qrtr_rx` | `1` |
| `qrtr_tx` | `1` |
| `sysmon_qmi` | `4` |
| `service_notifier_180` | `0` |
| `service_notifier_74` | `0` |
| `wlan_pd` | `0` |
| `wlfw_start` | `0` |
| `qmi_server_connected` | `0` |
| `bdf_regdb` | `0` |
| `bdf_bdwlan` | `0` |
| `wlan0` | `0` |
| `kernel_warning` | `0` |

The helper recorded `cnss-daemon` netlink and binder activity before the gate
timed out:

```text
cnss_daemon_netlink: 5
cnss_daemon_cld80211: 2
cnss_binder_transaction_failed: 33
```

## Interpretation

V655 did not prove or disprove `vndservicemanager` readiness, because the
fresh service `74` gate never opened. The guard behaved correctly:

- service-manager trio was not started;
- `vndservicemanager` readiness capture did not run;
- fresh `cnss_daemon_retry` did not run;
- cleanup completed and post-reboot health was good.

The active blocker moved back below service-manager ordering:

```text
current fresh boot: QRTR RX/TX + sibling sysmon + CNSS netlink/binder, but no service-notifier 180/74
previous V653 path: service-notifier 180/74 present, then CNSS binder blocker
```

That means the next step should not widen to Wi-Fi HAL or scan/connect. It
should compare V653/V655 prerequisites and live transcripts to find why the
fresh V655 lower path lost service `74` before the vndservicemanager retry gate.

## Next Gate

Proceed to V656 as a host-only regression classifier:

1. compare V644/V653 positive service `74` evidence against V655 timeout;
2. compare V490 timing, V641 refresh state, helper mode, linkerconfig/APEX
   source, firmware mount cleanup, and SELinuxfs mount differences;
3. classify whether V655 should replay the V653 gate exactly, extend the
   service `74` wait window, or first restore a lower CNSS/service-notifier
   precondition;
4. keep Wi-Fi HAL, scan/connect, credentials, DHCP, routes, and external ping
   blocked until service `74` is reproduced and WLFW/BDF advances.
