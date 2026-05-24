# Native Init V799 Post-V798 Route Classifier Plan

## Goal

Reconcile the current V797/V798 lower-only negative path with prior
service-notifier `74` positive evidence and select the next live gate toward
native Wi-Fi readiness.

## Scope

- Read only existing manifests:
  - V797 PIL trace payload.
  - V798 PIL code gap classifier.
  - V653/V657/V659/V668 service-notifier `74` positive CNSS windows.
  - V694 PeripheralManager `vndservice` query proof.
- Classify whether the next useful action is another lower-only replay, custom
  kernel work, or a below-HAL CNSS tail replay.

## Hard Gates

- No device command.
- No service-manager, Wi-Fi HAL, scan/connect, credential use, DHCP/routes, or
  external ping.
- No reboot, flash, boot image write, partition write, raw `esoc0`, bind/unbind,
  or custom kernel path.
- No Wi-Fi secret material in tracked output.

## Validation

```bash
python3 -m py_compile scripts/revalidation/native_wifi_post_v798_route_classifier_v799.py
python3 scripts/revalidation/native_wifi_post_v798_route_classifier_v799.py --out-dir tmp/wifi/v799-static-plan-check plan
python3 scripts/revalidation/native_wifi_post_v798_route_classifier_v799.py run
git diff --check
```

## Expected Routing

- If the current V797 lower-only path is negative but prior service-notifier
  `74` positive paths are reproducible, do not repeat lower-only replay as the
  next gate.
- If V694 confirms PeripheralManager `vndservice` registration and all
  service-notifier `74` positive CNSS tails still lack WLFW/WLAN-PD/BDF/`wlan0`,
  route to a below-HAL CNSS tail replay with PeripheralManager readiness and
  PIL/readback instrumentation.
