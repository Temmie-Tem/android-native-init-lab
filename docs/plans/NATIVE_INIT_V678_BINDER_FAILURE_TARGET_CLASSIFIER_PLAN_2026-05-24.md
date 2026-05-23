# Native Init V678 Binder Failure Target Classifier Plan

## Objective

Classify the remaining V677 blocker after the private property runtime repair.
V677 removed all property denials, but the replay still shows five Binder `-22`
failures and no WLFW/BDF/`wlan0` progress. V678 is host-only and decides the
next smallest Binder-focused live gate.

## Inputs

- V677 replay manifest:
  `tmp/wifi/v677-v676-residual-property-replay-live/manifest.json`
- V677 arm manifest:
  `tmp/wifi/v677-v676-residual-property-replay-live/arm-v676-v535/live/manifest.json`
- V677 native dmesg delta:
  `tmp/wifi/v677-v676-residual-property-replay-live/arm-v676-v535/live/native/dmesg-delta.txt`
- V677 helper transcript surface:
  `tmp/wifi/v677-v676-residual-property-replay-live/arm-v676-v535/live/native/companion-start-only-with-holder.txt`

## Gate

Run `scripts/revalidation/native_wifi_binder_failure_target_classifier_v678.py`
to extract only bounded summary data:

1. confirm V677 and the V676-style arm passed;
2. confirm property denial total and unique count are zero;
3. confirm Binder devnodes and child Binder FD surfaces are present;
4. classify Binder failures by actor, kind, code, and errno;
5. confirm WLFW/BDF/`wlan0` markers remain absent;
6. identify whether Binder registry/debug snapshots were already captured.

## Forbidden Actions

- No device command.
- No sysfs write.
- No DSP boot-node write.
- No `esoc0` open.
- No daemon or service-manager start.
- No Wi-Fi HAL start.
- No supplicant or hostapd start.
- No scan/connect/link-up.
- No credential, DHCP, route change, or external ping.
- No boot image or partition write.

## Success Criteria

- The classifier runs without contacting the device.
- V677 property surface is confirmed clean.
- Binder failure actors and codes are classified from existing evidence.
- Child Binder FD and SELinux execution surfaces are summarized.
- The next V679 gate is scoped to Binder registry/debug/transaction capture,
  not property repair or Wi-Fi connection attempts.

## Commands

```sh
python3 -m py_compile \
  scripts/revalidation/native_wifi_binder_failure_target_classifier_v678.py

python3 scripts/revalidation/native_wifi_binder_failure_target_classifier_v678.py \
  --out-dir tmp/wifi/v678-binder-failure-targets-plan \
  plan

python3 scripts/revalidation/native_wifi_binder_failure_target_classifier_v678.py \
  --out-dir tmp/wifi/v678-binder-failure-targets \
  run
```

## Expected Routing

If property denials are zero, child Binder surfaces are ready, Binder failures
persist, and WLFW/BDF/`wlan0` remains absent, V679 should capture Binder
registry/debug/failed-transaction state in the same private namespace. It should
not start supplicant, scan, connect, use credentials, run DHCP, change routes,
or ping externally.
