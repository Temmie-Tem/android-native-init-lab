# Native Init V653 Service74-Gated Service-Manager Plan

- date: `2026-05-23 KST`
- cycle: `v653`
- scope: helper/runner prep; bounded live proof after deployment
- target: preserve lower CNSS companion state and start the service-manager trio
  only after a fresh `service-notifier 74` kernel marker is observed

## Background

V652 proved that helper v104's fixed CNSS-first delayed service-manager mode is
cleanup-safe, but it regressed the lower publication path:

```text
service_notifier_180=0
service_notifier_74=0
cnss-daemon netlink/cld80211 activity present
binder transaction failures present
Wi-Fi HAL/scan/connect/external ping not executed
```

That means another fixed-delay retry is weak. V653 moves the decision point into
the helper: lower companion/CNSS children run first, the helper polls kernel log
state for a fresh service `74` publication, and the service-manager trio is
withheld if the gate does not open.

## Guardrails

V653 must not:

- write direct ADSP/CDSP/SLPI boot nodes;
- open or hold `esoc0`;
- write `qcwlanstate` or force driver state;
- start Wi-Fi HAL, `wificond`, supplicant, or hostapd;
- scan/connect/link-up, use credentials, run DHCP, change routes, or ping
  externally;
- treat stale same-boot service `74` log lines as a fresh gate pass.

## Implementation

1. Build helper `a90_android_execns_probe v105`.
2. Add mode:
   `wifi-companion-service74-gated-vnd-service-manager-start-only`.
3. Start lower children in this order:
   `qrtr_ns,rmt_storage,tftp_server,pd_mapper,cnss_diag,cnss_daemon`.
4. Record a baseline kernel-log count for service-notifier `74`.
5. Wait up to `12000ms` for the service `74` count to increase.
6. Start `servicemanager`, `hwservicemanager`, and `vndservicemanager` only if
   the fresh service `74` gate opens.
7. Always clean up all started children and record postflight safety.

## Success Criteria

V653 prep passes if:

- helper v105 builds as a static AArch64 binary;
- helper strings expose the new mode, gate keys, and no credential strings;
- V653 runner and v105 deploy wrapper pass Python compilation and plan smoke;
- live preflight is able to identify current deployment prerequisites.

V653 live passes if it selects one of these bounded outcomes:

- `v653-service74-gate-timeout`: service-manager correctly withheld because
  no fresh service `74` publication occurred;
- `v653-service74-gated-wlfw-advanced`: service `74` gate opened and WLFW moved;
- `v653-binder-loop-persists`: service `74` gate opened but binder remains the
  active blocker;
- `v653-service74-binder-clean-wlfw-missing`: service `74` and binder are clean,
  but WLFW/BDF still does not advance.

Passing V653 does not authorize Wi-Fi HAL start, scan/connect, credentials, DHCP,
route changes, or external ping. Those remain separate gates after lower
publication and WLFW/BDF state advance.
