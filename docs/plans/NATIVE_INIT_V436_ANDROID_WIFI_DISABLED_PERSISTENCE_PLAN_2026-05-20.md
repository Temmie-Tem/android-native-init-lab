# Native Init V436 Android Wi-Fi Disabled Persistence Plan

Date: 2026-05-20

## Goal

V436 verifies that the V435 containment state persists across a fresh Android
boot-complete handoff without issuing another Wi-Fi disable command.  This is a
read-only gate: it checks that Wi-Fi remains disabled and that route, DNS,
validated-connectivity, and listener exposure remain absent.

## Scope

Allowed:

- temporarily flash the known Android boot image;
- wait for Android ADB and `sys.boot_completed=1`;
- capture Wi-Fi status, settings, route tables, local route lookup, `wlan0`,
  filtered connectivity state, and listening sockets;
- restore native init v319 with rollback evidence.

Not allowed:

- Wi-Fi enable/disable, scan, connect, credentials, saved-network edits, or
  server exposure;
- DHCP/routing mutation, external packet probes, `ip link set`, rfkill/sysfs
  writes, module operations, `setprop`, or direct daemon starts.

## Implementation

- Collector: `scripts/revalidation/wifi_android_disabled_persistence_v436.py`
  - reuses V435's read-only capture and active-connectivity parser;
  - classifies disabled state, `wlan0` IP absence, route absence, active
    connectivity/DNS absence, and listener safety;
  - records `wifi_disable_executed=False`.
- Handoff wrapper:
  `scripts/revalidation/android_wifi_disabled_persistence_handoff_v436.py`
  - reuses Android boot-complete handoff and native rollback primitives;
  - replaces the Android inventory step with the V436 read-only persistence
    collector;
  - blocks Wi-Fi enable/disable, scan/connect, server/probe, and route-mutation
    command patterns from the handoff plan.

## Validation Plan

```text
python3 -m py_compile \
  scripts/revalidation/wifi_android_disabled_persistence_v436.py \
  scripts/revalidation/android_wifi_disabled_persistence_handoff_v436.py

python3 scripts/revalidation/wifi_android_disabled_persistence_v436.py \
  --out-dir tmp/wifi/v436-android-wifi-disabled-persistence-plan-<ts> plan

python3 scripts/revalidation/android_wifi_disabled_persistence_handoff_v436.py \
  --out-dir tmp/wifi/v436-android-wifi-disabled-persistence-handoff-dryrun-<ts> \
  --allow-android-boot-flash --assume-yes --i-understand-native-rollback \
  dry-run

git diff --check
```

Live sequence:

1. confirm native v319 status over the bridge;
2. boot Android and wait for boot-complete;
3. run V436 read-only disabled persistence collector;
4. restore native v319;
5. verify native `version`, `selftest`, and `status`;
6. scan evidence for raw SSID/BSSID/security-type leaks.

## Expected Decisions

- `v436-android-wifi-disabled-persistence-plan-ready`
- `v436-handoff-plan-ready`
- `v436-handoff-dryrun-ready`
- `v436-android-wifi-disabled-persistence-pass`
- `v436-android-wifi-disabled-partial-persistence`
- `v436-android-wifi-disabled-persistence-regression`
- `v436-handoff-forbidden-command-blocked`

Any PASS decision must keep both `wifi_disable_executed=False` and
`wifi_bringup_executed=False`.

## Next Gate Rule

If V436 passes, the lab has a persistent contained Android baseline.  The next
decision is V437: either plan a controlled Android Wi-Fi re-enable observation
gate, or branch back to native-side Wi-Fi work while leaving Android contained.
