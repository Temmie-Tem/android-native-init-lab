# Native Init V676 V535 Property-seeded Android Userspace-order Plan

## Objective

Replay the V671 service74-gated Android userspace-order path with the V535
private property root. V535 already covers all V675 property targets, so this
gate checks whether the expanded private property surface removes the
post-HAL/`wificond` property blocker before any supplicant, scan/connect, DHCP,
or external ping attempt.

## Inputs

- V675 property/Binder target classifier:
  `tmp/wifi/v675-property-binder-targets/manifest.json`
- V535 private property layout:
  `tmp/wifi/v535-rmt-storage-private-property-runtime/manifest.json`
- V535 deployed property root:
  `/mnt/sdext/a90/private-property-v317/v535/dev/__properties__`
- Helper:
  `a90_android_execns_probe v111`

## Gate

V676 has two scripts:

1. `scripts/revalidation/native_wifi_v535_property_android_order_v676.py`
   - wraps the V671 live proof;
   - replaces the old private property root with the V535 root;
   - verifies V675 target coverage;
   - reports remaining property-denial and Binder surfaces.
2. `scripts/revalidation/native_wifi_v535_property_android_order_orchestrator_v676.py`
   - refreshes current-boot prerequisites with V641 clean-DSP, V401, and V490;
   - runs the V676 proof with the fresh V490 manifest;
   - performs bounded cleanup verification.

## Forbidden Actions

- No supplicant or hostapd start.
- No Wi-Fi scan/connect/link-up.
- No credential use.
- No DHCP, route change, or external ping.
- No boot image or partition write.

## Success Criteria

- V675 target input passes.
- V535 layout covers all V675 denied property keys.
- V641/V401/V490 current-boot prep passes.
- V676 live arm starts Android userspace-order children cleanup-safely.
- Property denial count and WLFW/BDF/`wlan0` markers are classified.
- Cleanup reboot returns to healthy native control.

## Commands

```sh
python3 -m py_compile \
  scripts/revalidation/native_wifi_v535_property_android_order_v676.py \
  scripts/revalidation/native_wifi_v535_property_android_order_orchestrator_v676.py

python3 scripts/revalidation/native_wifi_v535_property_android_order_orchestrator_v676.py \
  --out-dir tmp/wifi/v676-v535-property-android-order-orchestrated-plan \
  plan

python3 scripts/revalidation/native_wifi_v535_property_android_order_orchestrator_v676.py \
  --out-dir tmp/wifi/v676-v535-property-android-order-orchestrated-live \
  --apply \
  --assume-yes \
  run
```

## Expected Routing

- If WLFW/BDF/`wlan0` advances, classify the first `wlan0` state before any
  supplicant or scan/connect attempt.
- If V675 property denials disappear and Binder remains, move to a narrow
  Binder registration/transaction gate.
- If property denials remain, extend the private property layout with the new
  denial set before Binder repair.
