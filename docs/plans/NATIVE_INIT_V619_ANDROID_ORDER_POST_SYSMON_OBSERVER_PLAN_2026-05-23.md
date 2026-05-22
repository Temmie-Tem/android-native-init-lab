# Native Init V619 Android-Order Post-Sysmon Observer Plan

- date: `2026-05-23 KST`
- cycle: `v619`
- scope: bounded native observer prep
- target: test whether Android's lower companion order restores the missing
  QMI service-notifier publication before any CNSS/HAL/scan/connect step

## Background

V617/V618 narrowed the current Wi-Fi blocker to a lower QMI service
registration gap. Android reaches `sysmon-qmi` and publishes
`service-notifier` `180/74` almost immediately after lower modem readiness,
while native V615 reaches sibling `sysmon-qmi`/service-locator but still lacks
`service-notifier`.

V618 ruled out `rfs_access` as a standalone daemon target. The useful remaining
delta is companion order:

```text
Android: qrtr_ns -> pd_mapper -> rmt_storage -> tftp_server
V615:    qrtr_ns -> rmt_storage -> tftp_server -> pd_mapper
```

## Guardrails

V619 must not:

- start CNSS (`cnss_diag` or `cnss-daemon`);
- start service-manager, Wi-Fi HAL, `wificond`, supplicant, or hostapd;
- write `boot_wlan` or `qcwlanstate`;
- scan/connect/link-up, use credentials, run DHCP, change routes, or ping
  externally;
- send QMI payloads from the observer.

V619 may reuse the V615 lower-surface preconditions only inside the same
bounded/reboot-cleanup observer model:

- Android-equivalent firmware mounts;
- ADSP/CDSP/SLPI boot-node writes;
- `subsys_modem` hold-open;
- QRTR readback without QMI payload.

## Implementation

1. Build helper `a90_android_execns_probe v104`.
2. Add mode:

```text
wifi-companion-android-order-post-sysmon-observer-start-only
```

3. In that mode, start only:

```text
qrtr_ns -> pd_mapper -> rmt_storage -> tftp_server
```

4. Add `native_wifi_android_order_post_sysmon_observer_v619.py`.
5. Add `wifi_execns_helper_v104_deploy_preflight.py`.

## Success Criteria

V619 passes the prep gate if:

- helper v104 builds static and contains the new mode token;
- runner/deploy plan commands pass without device mutation;
- live preflight reports only environmental blockers, not contract/parser
  blockers;
- summaries state that CNSS/HAL/scan/connect/external ping are not executed.

V619 live result is considered advanced only if service-notifier `180/74`
appears under Android-order lower companion startup. If it still does not
appear, the next gate must classify lower QMI service-registration dependencies
instead of retrying CNSS/HAL.

