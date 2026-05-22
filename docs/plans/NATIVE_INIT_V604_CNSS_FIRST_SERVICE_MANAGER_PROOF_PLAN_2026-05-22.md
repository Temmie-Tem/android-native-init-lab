# Native Init V604 CNSS-First Service-Manager Proof Plan

- date: `2026-05-22 KST`
- status: `planned`; helper v102 preparation
- helper source: `stage3/linux_init/helpers/a90_android_execns_probe.c`
- deploy wrapper: `scripts/revalidation/wifi_execns_helper_v102_deploy_preflight.py`
- live runner: `scripts/revalidation/native_wifi_modem_holder_cnss_first_service_manager_v604.py`

## Objective

Test the ordering gap left by V603.

V598 reached QRTR TX, `sysmon-qmi`, and service-notifier `180` when CNSS ran
without service-manager, but binder transaction failures persisted. V603 kept
service-manager and binder clean, but service-notifier `180` disappeared again.

V604 therefore starts CNSS before service-manager, waits briefly, then starts
the service-manager trio:

```text
qrtr-ns
  -> rmt_storage
  -> tftp_server
  -> pd-mapper
  -> cnss_diag
  -> cnss-daemon
  -> servicemanager
  -> hwservicemanager
  -> vndservicemanager
```

The goal is to see whether `cnss-daemon` can publish service-notifier `180`
first and then recover binder access after service-manager appears.

## Guardrails

- No Wi-Fi HAL, `wificond`, supplicant, or hostapd start.
- No `qcwlanstate` or sysfs driver-state write.
- No scan/connect/link-up.
- No credential, DHCP, route, or external ping.
- No boot image write.
- No persistent partition write.
- `subsys_modem` only; do not open or hold `esoc0`.
- Reboot cleanup remains the live-proof cleanup boundary.

## Success Criteria

Preparation succeeds when:

- helper v102 builds as a static ARM64 artifact;
- helper v102 exposes
  `wifi-companion-cnss-first-delayed-vnd-service-manager-start-only`;
- deploy wrapper refuses mutation without the exact V604 deploy phrase;
- live runner plan-only validation passes.

The later live proof advances only if:

- service-notifier `180` appears; and
- `binder_transaction_failed == 0`.

If service-notifier `180` appears but binder failures persist, the next proof
should extend the CNSS runtime window after service-manager starts. If both are
absent, compare V598/V604 timing and test a longer pre-service-manager CNSS
window.
