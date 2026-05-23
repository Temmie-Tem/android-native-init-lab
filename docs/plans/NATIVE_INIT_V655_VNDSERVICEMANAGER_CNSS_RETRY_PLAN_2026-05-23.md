# Native Init V655 vndservicemanager CNSS Retry Plan

- date: `2026-05-23 KST`
- cycle: `v655`
- scope: helper/runner prep; bounded live proof after helper v106 deployment
- target: prove whether a ready `vndservicemanager` plus fresh
  `cnss-daemon` attempt clears the native vndbinder transaction blocker

## Background

V653 preserved fresh service-notifier `180/74` and started the service-manager
trio only after service `74` appeared, but `cnss-daemon` still stopped before
WLFW:

```text
service-notifier 180/74: present
cnss-daemon binder:      transaction failed -22
WLAN-PD/WLFW/BDF/wlan0: absent
```

V654 classified that failure as a narrower binder-runtime mismatch. The likely
gap is not missing binder devnodes or generic SELinux surface. The native-only
sequence starts `cnss-daemon` before `vndservicemanager` readiness is proven.

## Guardrails

V655 must not:

- write direct ADSP/CDSP/SLPI boot nodes;
- open or hold `esoc0`;
- write `qcwlanstate` or force driver state;
- start Wi-Fi HAL, `wificond`, supplicant, or hostapd;
- scan/connect/link-up, use credentials, run DHCP, change routes, or ping
  externally;
- modify boot images, partitions, Android firmware files, or Wi-Fi credentials.

## Implementation

1. Build helper `a90_android_execns_probe v106`.
2. Add mode:
   `wifi-companion-service74-gated-vnd-service-manager-cnss-retry-start-only`.
3. Preserve the V653 lower sequence and fresh service `74` gate:
   `qrtr_ns,rmt_storage,tftp_server,pd_mapper,cnss_diag,cnss_daemon`.
4. Start `servicemanager`, `hwservicemanager`, and `vndservicemanager` only if
   the service `74` gate opens.
5. Wait `1000ms` after `vndservicemanager` start, capture process/fd state, and
   classify readiness.
6. Clean up the initial `cnss-daemon` child before retry.
7. Start a fresh `cnss_daemon_retry` only if `vndservicemanager` is observable
   and the initial `cnss-daemon` cleanup is safe.
8. Capture only lower Wi-Fi markers up to WLFW/WLAN-PD/QMI/BDF/`wlan0`.

Expected helper order:

```text
qrtr_ns,rmt_storage,tftp_server,pd_mapper,cnss_diag,cnss_daemon,service74_gate,servicemanager,hwservicemanager,vndservicemanager,vndservicemanager_ready,cnss_daemon_initial_cleanup,cnss_daemon_retry
```

## Success Criteria

V655 prep passes if:

- helper v106 builds as a static AArch64 binary;
- helper strings expose the new mode and readiness/retry keys;
- V655 runner and v106 deploy wrapper pass Python compilation and plan smoke;
- deploy preflight identifies whether helper v106 is already current or needs
  deployment;
- no credential strings are introduced into source or docs.

V655 live passes if it selects one of these bounded outcomes:

- `v655-service74-gate-timeout`: service-manager and retry correctly withheld;
- `v655-vndservicemanager-readiness-blocked`: service-manager started but
  vendor binder manager readiness was not proven;
- `v655-cnss-retry-not-executed`: retry withheld because initial cleanup was
  unsafe or readiness was incomplete;
- `v655-cnss-retry-wlfw-advanced`: fresh CNSS retry reached WLFW;
- `v655-cnss-retry-binder-loop-persists`: fresh CNSS retry still hits the
  binder transaction blocker.

Passing V655 does not authorize Wi-Fi HAL start, scan/connect, credentials,
DHCP, route changes, or external ping. Those remain later gates after native
reaches WLFW/BDF cleanly.
