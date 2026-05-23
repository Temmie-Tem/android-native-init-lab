# Native Init V662 Registry/Context Snapshot Plan

- date: `2026-05-23 KST`
- cycle: `v662`
- scope: bounded live readout, no Wi-Fi bring-up
- target: capture Binder registry/debugfs and property runtime context after
  service `74` and `vndservicemanager` readiness, but before any fresh
  `cnss-daemon` retry

## Background

V661 classified the V660 blocker as a dynamic registration/context gap:

```text
service 74 -> service-manager trio -> vndservicemanager_ready -> fresh CNSS retry
  -> cnss-daemon binder transaction -22 -> no WLFW/WLAN-PD/QMI/BDF/wlan0
```

V662 adds helper `a90_android_execns_probe v108` with a new mode:

```text
wifi-companion-service74-gated-vnd-service-manager-registry-snapshot-start-only
```

The mode preserves the V659 readiness sequence and captures read-only runtime
surface before and after initial `cnss-daemon` cleanup.

## Guardrails

V662 must not:

- run a fresh `cnss-daemon` retry tail;
- start Wi-Fi HAL, `wificond`, supplicant, or hostapd;
- scan/connect/link-up, use credentials, run DHCP, change routes, or ping
  externally;
- write DSP boot nodes, `boot_wlan`, `qcwlanstate`, partitions, or boot image.

## Snapshot Contract

The helper captures:

- `/sys/kernel/debug/binder/{state,stats,transactions,transaction_log,failed_transaction_log}`;
- `/sys/kernel/debug/binder/proc` and per-child Binder debug entries when
  available;
- `/dev/__properties__` directory presence;
- `/dev/socket` filtered for relevant runtime sockets;
- service-manager child PIDs and observability markers.

Debugfs may be unavailable. That is still useful evidence if the snapshot
records `open-error` and the summary keys prove the capture path ran.

## Success Criteria

V662 passes if:

1. helper v108 is deployed and reports the registry snapshot mode;
2. service `74` gate opens;
3. service-manager trio and `vndservicemanager_ready` are observable;
4. initial `cnss-daemon` cleanup is safe;
5. `cnss_retry.enabled=0`;
6. both `before_initial_cnss_cleanup` and `after_initial_cnss_cleanup`
   snapshot blocks complete;
7. reboot cleanup leaves the device healthy.

Passing V662 only selects the next repair target. It does not authorize Wi-Fi
HAL, scan/connect, credentials, DHCP, route changes, or external ping.
