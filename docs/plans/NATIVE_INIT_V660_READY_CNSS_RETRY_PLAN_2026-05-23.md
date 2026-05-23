# Native Init V660 Ready CNSS Retry Plan

- date: `2026-05-23 KST`
- cycle: `v660`
- scope: bounded live proof after V659 readiness pass
- target: run the fresh `cnss-daemon` retry tail only after service `74`,
  service-manager trio startup, and `vndservicemanager` readiness are proven in
  the same native-init window

## Background

V659 proved the prerequisite that V655 could not isolate:

```text
QRTR RX -> service 180/74 -> service-manager trio -> vndservicemanager ready
```

V659 deliberately left `cnss_retry.enabled=0`, so `cnss_daemon_retry` did not
run. The remaining blocker is the `cnss-daemon` binder/QMI transition after
the vendor service-manager surface is ready.

## Guardrails

V660 must not:

- write direct ADSP/CDSP/SLPI boot nodes;
- open or hold `esoc0`;
- write `qcwlanstate` or force WLAN driver state;
- start Wi-Fi HAL, `wificond`, supplicant, or hostapd;
- scan/connect/link-up, use credentials, run DHCP, change routes, or ping
  externally;
- modify boot images, partitions, Android firmware files, or Wi-Fi credentials.

## Preconditions

1. Helper `a90_android_execns_probe v107` is deployed and SHA-verified.
2. Current boot has fresh V641 clean-DSP proof and ADSP/CDSP/DSPS RPMSG nodes.
3. V641 firmware mounts are unmounted before preflight/live.
4. Current boot has V490 SELinux policy-load proof.
5. Real Android linkerconfig and APEX library config are present in `/cache/bin`.
6. No service-manager, CNSS, HAL, or Wi-Fi link residue is active.

## Implementation

V660 reuses helper mode:

```text
wifi-companion-service74-gated-vnd-service-manager-cnss-retry-start-only
```

Expected helper order:

```text
qrtr_ns,rmt_storage,tftp_server,pd_mapper,cnss_diag,cnss_daemon,service74_gate,servicemanager,hwservicemanager,vndservicemanager,vndservicemanager_ready,cnss_daemon_initial_cleanup,cnss_daemon_retry
```

The runner must:

1. require helper v107 and current V490/V641 prerequisites;
2. wait for fresh service `74` before service-manager startup;
3. require `vndservicemanager_readiness.ready=1`;
4. require initial `cnss-daemon` cleanup to be safe;
5. run exactly one fresh `cnss_daemon_retry`;
6. classify WLFW/WLAN-PD/QMI/BDF/firmware-ready/`wlan0` markers;
7. use reboot cleanup after live execution.

## Success Criteria

V660 passes if it selects one of these bounded outcomes:

- `v660-service74-gate-timeout`
- `v660-vndservicemanager-readiness-blocked`
- `v660-cnss-retry-not-executed`
- `v660-cnss-retry-wlfw-advanced`
- `v660-cnss-retry-binder-loop-persists`
- `v660-cnss-retry-review-required`

Passing V660 does not authorize Wi-Fi HAL start, scan/connect, credentials,
DHCP, route changes, or external ping unless WLFW/BDF/`wlan0` advances enough
to justify a separate scan/connect gate.
