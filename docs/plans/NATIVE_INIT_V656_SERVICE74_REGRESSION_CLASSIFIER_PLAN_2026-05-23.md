# Native Init V656 Service74 Regression Classifier Plan

- date: `2026-05-23 KST`
- cycle: `v656`
- scope: host-only classifier
- target: compare V644/V653 service `74` positives against V655 service `74`
  gate timeout before any new live mutation

## Background

V655 did not reach the intended `vndservicemanager` readiness proof. The fresh
service `74` gate did not open, so service-manager, `vndservicemanager`, and
fresh `cnss_daemon_retry` were correctly withheld.

The immediate question is whether the V655 timeout is caused by:

- missing lower QRTR/sysmon readiness;
- stale V641/V490 prerequisites;
- the new helper v106 mode;
- service-manager ordering;
- or a broader nondeterministic lower service-notifier regression.

## Guardrails

V656 must not:

- contact the device;
- write sysfs, DSP boot nodes, `qcwlanstate`, or driver state;
- open or hold `esoc0`;
- start daemons or service-manager;
- start Wi-Fi HAL, `wificond`, supplicant, or hostapd;
- scan/connect/link-up, use credentials, run DHCP, change routes, or ping
  externally.

## Inputs

- V644 positive evidence:
  `tmp/wifi/v644-live-20260523-071610/manifest.json`
- V653 positive evidence:
  `tmp/wifi/v653-service74-gated-live-20260523-085337/manifest.json`
- V655 timeout evidence:
  `tmp/wifi/v655-vndservicemanager-cnss-retry-live/manifest.json`
- V653/V655 helper transcripts
- V653/V655 V490 manifests

## Checks

1. Compare service-notifier `180/74` counts across V644, V653, and V655.
2. Confirm V653 and V655 both reached QRTR RX/TX and sibling `sysmon-qmi`.
3. Confirm V655 withheld service-manager, so service-manager is not the cause
   of the missing service `74`.
4. Confirm V653 and V655 both had successful current-boot V490 evidence.
5. Compare helper mode/order/gate behavior:
   - V653: service `74` gate opened and service-manager trio started;
   - V655: same lower prefix timed out before service-manager.
6. Select the next bounded live gate only if it stays below Wi-Fi HAL and
   scan/connect.

## Success Criteria

V656 passes if it produces one of these host-only outcomes:

- `v656-service74-regression-classified`
- `v656-service74-regression-review-required`

Passing V656 does not authorize Wi-Fi HAL, scan/connect, credentials, DHCP,
route changes, or external ping. The expected next gate is a bounded V657 exact
V653-mode replay using helper v106.
