# Native Init V675 Property/Binder Target Classifier Plan

## Objective

Classify the V674 post-HAL/`wificond` runtime gap into concrete property and
Binder repair targets before any new live mutation.

V674 proved that Wi-Fi HAL legacy/ext, `wificond`, and a fresh `cnss-daemon`
can start with the expected identity and Binder FD surface, but WLFW service
`69`, BDF download, firmware-ready, and `wlan0` remain absent. V675 narrows the
next action without contacting the device.

## Inputs

- V674 post-HAL classifier manifest:
  `tmp/wifi/v674-post-hal-wificond-classifier/manifest.json`
- V673 V671-arm live manifest and helper transcript:
  `tmp/wifi/v673-same-helper-replay-live-retry2/arm-v671-v111/live/manifest.json`
- Android full getprop capture:
  `tmp/wifi/v297-android-property-capture-android/commands/all-getprop.txt`
- Android property context captures:
  `tmp/wifi/v295-property-snapshot-live-20260519-142740/native/cat-context-*.txt`
- Android Wi-Fi init service snapshot:
  `tmp/wifi/v520-companion-service-availability-plan/inputs/v206_initrc.txt`

## Gate

V675 is host-only:

1. Parse all property lookup failures from the V673 V671-arm helper transcript.
2. Map every denied property through captured Android `property_contexts`.
3. Check whether runtime-required values exist in the Android full getprop
   capture.
4. Split log/debug/defaultable lookups from real runtime-required seed targets.
5. Parse Binder `-22` failures by actor so Binder repair remains a separate
   target from property-info completeness.

## Forbidden Actions

- No device command.
- No daemon start.
- No Wi-Fi HAL start.
- No supplicant or hostapd start.
- No scan/connect/link-up.
- No credential, DHCP, routing, or external ping.
- No boot image or partition write.

## Success Criteria

- V674 input decision is `v674-post-hal-property-binder-gap-classified`.
- Full Android getprop input is present.
- Captured property-context rule count is sufficient.
- Every denied property key maps to a known Android context.
- Runtime-required denied properties have Android values available.
- Binder failures are summarized separately by actor and failure kind.

## Commands

```sh
python3 -m py_compile scripts/revalidation/native_wifi_property_binder_target_classifier_v675.py
python3 scripts/revalidation/native_wifi_property_binder_target_classifier_v675.py --out-dir tmp/wifi/v675-property-binder-targets-plan plan
python3 scripts/revalidation/native_wifi_property_binder_target_classifier_v675.py --out-dir tmp/wifi/v675-property-binder-targets run
```

## Expected Output

The expected pass label is `v675-property-binder-targets-classified`. If it
passes, the next gate should be V676: expand private `property_info`/seed
materialization for the identified targets, then run a bounded Binder
registration/transaction capture. Supplicant, scan/connect, DHCP, and external
ping stay blocked until WLFW/BDF/`wlan0` advances.
