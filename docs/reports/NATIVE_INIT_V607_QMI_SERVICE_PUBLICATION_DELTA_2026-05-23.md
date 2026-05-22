# Native Init V607 QMI Service-Publication Delta Report

- date: `2026-05-23 KST`
- status: `classified`; host-only
- runner: `scripts/revalidation/native_wifi_qmi_service_publication_delta_v607.py`
- evidence: `tmp/wifi/v607-qmi-service-publication-delta/`

## Scope

V607 compared existing evidence only. It did not contact the device, start
daemons, send QRTR/QMI payloads, start service-manager, start Wi-Fi HAL, write
`qcwlanstate`, scan/connect/link-up, use credentials, run DHCP, change routes,
ping externally, flash boot images, or write partitions.

## Result

```text
decision: v607-helper-version-delta
pass: True
reason: V598 and V606 match lower modem readiness, no-service-manager order, QRTR readback result, and CNSS timing, but service-notifier 180 disappears after helper marker changed from v100 to v102
next: run a bounded helper-v100 replay or audit helper v100-to-v102 companion deltas before another daemon-order live proof
```

## Diagnostic Matrix

```text
required_inputs_present: True
service_notifier_regressed: True
lower_ready_same: True
order_same: True
no_service_manager_same: True
readback_same_empty: True
cnss_window_same_250ms: True
helper_marker_differs: True
firmware_surface_same: True
binder_failure_after_cnss_daemon: True
```

## Marker Counts

| marker | V598 positive | V606 v102 replay |
| --- | ---: | ---: |
| qrtr_rx | 1 | 1 |
| qrtr_tx | 1 | 1 |
| sysmon_modem | 1 | 1 |
| service_notifier_180 | 1 | 0 |
| service_notifier_74 | 0 | 0 |
| wlan_pd | 0 | 0 |
| cnss_diag_netlink | 1 | 1 |
| cnss_daemon_netlink | 5 | 5 |
| binder_ioctl_unsupported | 1 | 1 |
| binder_transaction_failed | 21 | 21 |
| wlfw_start | 0 | 0 |
| wlfw_thread | 0 | 0 |
| qmi_server_connected | 0 | 0 |
| bdf_regdb | 0 | 0 |
| bdf_bdwlan | 0 | 0 |
| wlan_fw_ready | 0 | 0 |
| wlan0 | 0 | 0 |

## Timing Comparison

| delta | V598 positive | V606 v102 replay |
| --- | ---: | ---: |
| qrtr_rx_to_tx | 2493.398ms | 2387.996ms |
| qrtr_tx_to_sysmon | 2.449ms | 0.589ms |
| sysmon_to_service_notifier_180 | 721.370ms | missing |
| sysmon_to_cnss_diag | 945.115ms | 948.597ms |
| sysmon_to_cnss_daemon | 1140.232ms | 1143.320ms |
| service_notifier_180_to_cnss_diag | 223.745ms | missing |
| cnss_daemon_to_binder_failed | 50.515ms | 49.922ms |

The positive marker in V598 appeared before CNSS diag/daemon. V606 gave CNSS
nearly the same post-sysmon timing window, so the regression is not explained
by a shorter CNSS delay.

## Helper Surface

| field | V598 positive | V606 v102 replay |
| --- | --- | --- |
| helper_marker | `a90_android_execns_probe v100` | `a90_android_execns_probe v102` |
| order | `qrtr_ns,rmt_storage,tftp_server,pd_mapper,cnss_diag,cnss_daemon` | `qrtr_ns,rmt_storage,tftp_server,pd_mapper,cnss_diag,cnss_daemon` |
| with_service_manager | `0` | `0` |
| with_vnd_service_manager | `0` | `0` |
| qmi_payload | `0` | `0` |
| qrtr_readback | `1` | `1` |
| child_started | `6` | `6` |
| qipcrtr_sockets | `0` throughout | `0` throughout |

## Interpretation

The lower modem path is reproducible through QRTR RX, QRTR TX, and modem
`sysmon-qmi`. V598 and V606 also share the same no-service-manager companion
order, empty WLFW service `69` readback, firmware surface, and binder-failure
timing after CNSS daemon entry.

The strongest deterministic delta left in host evidence is the helper/runtime
version: V598 used helper v100 and produced `service-notifier` `180`; V606 used
helper v102 and did not. This does not prove helper v102 is the root cause, but
it makes a bounded helper v100 replay the shortest live gate before more daemon
ordering experiments.

## Next Gate

Recommended V608:

1. Re-deploy the existing helper v100 artifact only.
2. Refresh current-boot V401/V490 prerequisites after deployment.
3. Replay the V598 no-service-manager WLFW readback gate.
4. Keep service-manager, Wi-Fi HAL, `qcwlanstate`, scan/connect, credentials,
   DHCP, routes, and external ping blocked.
5. Classify:
   - if `service-notifier` `180` returns, helper v100/v102 behavior is the next
     diff target;
   - if it remains absent, lower modem publication is nondeterministic or has a
    current-boot precondition gap.
