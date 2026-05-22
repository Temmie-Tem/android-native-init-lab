# Native Init V618 RFS Alias and Companion Order Classifier Report

- date: `2026-05-23 KST`
- runner: `scripts/revalidation/native_wifi_rfs_alias_order_classifier_v618.py`
- evidence: `tmp/wifi/v618-rfs-alias-order-classifier/`
- decision: `v618-rfs-alias-pd-mapper-order-gap-classified`
- status: pass; host-only; no device command and no Wi-Fi bring-up attempted

## Scope

V618 resolves the V617 open question around `rfs_access`. It uses only existing
Android/native evidence and does not perform live device actions.

The run did not contact the device, write sysfs, write `boot_wlan`, start any
daemon, start service-manager, start Wi-Fi HAL, scan/connect/link-up, use
credentials, run DHCP, change routes, or ping externally.

## Result

```text
decision: v618-rfs-alias-pd-mapper-order-gap-classified
pass: True
reason: `rfs_access` is not proven as a standalone service; Android maps RFS
        access to `vendor.tftp_server` in `vendor_rfs_access`, which V615
        already replayed. The remaining actionable delta is companion order:
        android=qrtr_ns,pd_mapper,rmt_storage,tftp_server
        native=qrtr_ns,rmt_storage,tftp_server,pd_mapper
next: V619 should implement a bounded no-CNSS/no-HAL Android-order observer:
      qrtr_ns -> pd_mapper -> rmt_storage -> tftp_server
```

## Key Findings

| subject | classification | evidence |
| --- | --- | --- |
| `rfs_access` standalone service | not proven | vendor init has `start rfs_access`, but no `service rfs_access` block was found |
| `vendor_rfs_access` runtime domain | already replayed | Android `tftp_server` runs as `u:r:vendor_rfs_access:s0`; V615 starts `tftp_server` with the same SELinux exec domain |
| `pd_mapper` order | actionable delta | Android starts `qrtr_ns,pd_mapper,rmt_storage,tftp_server`; V615 starts `qrtr_ns,rmt_storage,tftp_server,pd_mapper` |
| `rmt_storage`/`tftp_server` readiness | not sufficient alone | Android service-notifier `180` appears about `13.469ms` before `rmt_storage_ready`; native has `rmt_storage_ready` but no notifier |
| service-locator | insufficient alone | native V615 reaches service-locator but still lacks service-notifier `180/74` |
| CNSS/HAL/`boot_wlan` | still blocked | service-notifier is earlier than WLAN-PD; V615 also has `23` `pm_qos_add_request` warnings |

## Timing Delta

Android order/timing from existing evidence:

| delta | ms |
| --- | ---: |
| `pd_mapper_start → rmt_storage_start` | `50.644` |
| `pd_mapper_start → tftp_server_start` | `59.648` |
| `pd_mapper_start → service_notifier_180` | `63.858` |
| `sysmon_modem → service_notifier_180` | `49.029` |
| `service_notifier_180 → rmt_storage_ready` | `13.469` |

Native V615 timing:

| delta | ms |
| --- | ---: |
| `sysmon_modem → service_locator_fail` | `21.528` |
| `sysmon_modem → rmt_storage_ready` | `314.360` |
| `sysmon_modem → service_locator` | `731.950` |
| `sysmon_modem → service_notifier_180` | missing |

## Interpretation

`rfs_access` should not be treated as a new live daemon target. The useful
remaining delta is ordering: Android starts `pd_mapper` before `rmt_storage` and
`tftp_server`, while V615 starts `pd_mapper` last.

This keeps the next gate below CNSS/HAL/scan/connect. The next live observer
should only test whether Android-order companion startup restores lower QMI
publication (`service-notifier 180/74`) in a bounded cleanup-safe window.

## Next Gate

Proceed with V619:

```text
qrtr_ns → pd_mapper → rmt_storage → tftp_server
```

Constraints:

- no CNSS daemon;
- no service-manager;
- no Wi-Fi HAL, `wificond`, supplicant, or hostapd;
- no `boot_wlan`/`qcwlanstate`;
- no scan/connect, credentials, DHCP, route change, or external ping.
