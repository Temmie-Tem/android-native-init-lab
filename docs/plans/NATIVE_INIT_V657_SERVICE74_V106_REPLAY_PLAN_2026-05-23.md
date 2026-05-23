# Native Init V657 Helper-v106 Service74 Replay Plan

- date: `2026-05-23 KST`
- cycle: `v657`
- scope: bounded live replay below Wi-Fi bring-up
- target: rerun the V653 service `74` gated service-manager proof with helper
  `a90_android_execns_probe v106`

## Background

V656 classified the V655 regression: V655 had QRTR TX, sibling `sysmon-qmi`,
and current-boot V490 parity, but the fresh service `74` gate timed out before
service-manager or the CNSS retry tail could run.

V657 narrows the question to one variable:

```text
V653 mode + helper v105 -> service 74 gate opened
V653 mode + helper v106 -> ?
```

If service `74` returns under helper v106, then the V655 CNSS retry mode can be
retried from the same prerequisite shape. If it does not return, the blocker is
broader lower service-notifier nondeterminism or prerequisite freshness, not the
new CNSS retry tail.

## Guardrails

V657 must not:

- write DSP boot nodes, `qcwlanstate`, or driver state;
- open or hold `esoc0`;
- run the V655 `vndservicemanager` readiness or CNSS retry tail;
- start Wi-Fi HAL, `wificond`, supplicant, or hostapd;
- scan/connect/link-up, use credentials, run DHCP, change routes, or ping
  externally;
- change boot images or partitions.

Allowed live scope is limited to the V653-compatible private namespace sequence:

```text
qrtr_ns,rmt_storage,tftp_server,pd_mapper,cnss_diag,cnss_daemon,
service74_gate,servicemanager,hwservicemanager,vndservicemanager
```

The service-manager trio may start only after the helper observes a fresh
service `74` gate.

## Inputs

- V653 positive evidence:
  `tmp/wifi/v653-service74-gated-live-20260523-085337/manifest.json`
- V655 timeout evidence:
  `tmp/wifi/v655-vndservicemanager-cnss-retry-live/manifest.json`
- V656 classifier:
  `tmp/wifi/v656-service74-regression-classifier/manifest.json`
- helper v106 deployment:
  `tmp/wifi/v655-execns-helper-v106-deploy-run/manifest.json`
- current-boot V641/V490 prerequisites, refreshed before live run if stale

## Execution Plan

1. Verify bridge/device health and helper v106 SHA on `/cache/bin`.
2. Refresh V641 clean-DSP one-shot state if the current boot does not have a
   fresh completed V641 proof.
3. Mount system/vendor runtime surfaces and rerun V490 policy-load proof for
   current boot into `tmp/wifi/v657-v490-current-run/`.
4. Run V657 preflight:
   `scripts/revalidation/native_wifi_service74_v106_replay_v657.py preflight`.
5. Run V657 live only with the exact V657 approval phrase; use bounded timeout
   and reboot cleanup.
6. Document service `74`, service-manager, CNSS binder, WLFW, warning, and
   cleanup results.

## Success Criteria

V657 passes if it produces one of these outcomes:

- `v657-service74-gated-wlfw-advanced`
- `v657-binder-loop-persists`
- `v657-service74-binder-clean-wlfw-missing`
- `v657-service74-gate-timeout`

Passing V657 does not authorize Wi-Fi HAL, scan/connect, credentials, DHCP,
route changes, or external ping. A Wi-Fi bring-up gate requires service
`74`/WLAN-PD/WLFW/BDF evidence to advance first.
