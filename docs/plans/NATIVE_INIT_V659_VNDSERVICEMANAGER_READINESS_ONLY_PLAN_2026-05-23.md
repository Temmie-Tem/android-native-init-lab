# Native Init V659 Vndservicemanager Readiness-Only Plan

- date: `2026-05-23 KST`
- cycle: `v659`
- scope: helper/runner prep, then bounded live proof
- target: prove `vndservicemanager` readiness after service `74` without the
  V655 fresh `cnss-daemon` retry tail

## Background

V657 proved helper v106 can reproduce the V653 exact service `74` gate:

```text
service 74 gate -> service-manager trio -> cnss-daemon vndbinder transaction -22
```

V658 then classified the next split:

- retrying full V655 unchanged is low value because V655 timed out before
  service `74` and never tested `vndservicemanager` readiness;
- V653/V657 both preserve service `74` but still stop before WLFW;
- the next gate should isolate `vndservicemanager` readiness before attempting
  any fresh `cnss-daemon` retry.

## Required Helper Change

Add helper `a90_android_execns_probe v107` with a new mode:

```text
wifi-companion-service74-gated-vnd-service-manager-readiness-start-only
```

The mode should reuse the V653/V657 sequence and add only the readiness probe:

```text
qrtr_ns,rmt_storage,tftp_server,pd_mapper,cnss_diag,cnss_daemon,
service74_gate,servicemanager,hwservicemanager,vndservicemanager,
vndservicemanager_ready
```

It must not append:

```text
cnss_daemon_initial_cleanup,cnss_daemon_retry
```

## Helper Contract

V659 should report:

- `wifi_companion_start.service74_gate.*`
- `wifi_companion_start.vndservicemanager_readiness.enabled=1`
- `wifi_companion_start.vndservicemanager_readiness.settle_done`
- `wifi_companion_start.vndservicemanager_readiness.observable`
- `wifi_companion_start.vndservicemanager_readiness.fd_summary_captured`
- `wifi_companion_start.vndservicemanager_readiness.ready`
- initial `cnss-daemon` observability and cleanup safety if the helper stops it
  to keep the window bounded

V659 must keep these as zero/absent:

- `wifi_companion_start.cnss_retry.enabled=0`
- `wifi_companion_start.child.cnss_daemon_retry.*`
- Wi-Fi HAL, `wificond`, supplicant, hostapd
- scan/connect/link-up, credential, DHCP, routes, external ping

## Runner Plan

Add:

- `scripts/revalidation/native_wifi_vndservicemanager_readiness_only_v659.py`
- `scripts/revalidation/wifi_execns_helper_v107_deploy_preflight.py`

The runner should reuse V655/V657 infrastructure:

1. require native version `A90 Linux init 0.9.67 (v641)`;
2. require helper marker `a90_android_execns_probe v107`;
3. require current-boot V641 clean-DSP state;
4. require current-boot V490 policy-load proof;
5. require real linkerconfig/APEX config inputs;
6. run preflight before any live mutation;
7. run live only with an exact V659 approval phrase and reboot cleanup.

## Guardrails

V659 must not:

- write DSP boot nodes, `qcwlanstate`, or driver state;
- open or hold `esoc0`;
- run the fresh `cnss-daemon` retry tail;
- start Wi-Fi HAL, `wificond`, supplicant, or hostapd;
- scan/connect/link-up, use credentials, run DHCP, change routes, or ping
  externally;
- change boot images or partitions.

## Success Criteria

V659 passes if it produces one of these outcomes:

- `v659-vndservicemanager-readiness-pass`
- `v659-vndservicemanager-readiness-blocked`
- `v659-service74-gate-timeout`
- `v659-cleanup-review`

Passing V659 does not authorize Wi-Fi HAL, scan/connect, credentials, DHCP,
route changes, or external ping. If readiness passes, the next gate can attempt
a fresh `cnss-daemon` binder attempt after proven `vndservicemanager` readiness.
