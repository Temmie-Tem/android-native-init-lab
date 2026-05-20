# Native Init V423 Android hwservice Inventory Report

Date: 2026-05-20

## Scope

V423 adds a read-only Android-side hwservice/lshal inventory collector.  It is
the next evidence step after V422 timed out on all three targeted Samsung
`ISehWifi/default` fqinstances inside the private native runtime.

This is not Wi-Fi bring-up.  No Wi-Fi enable, scan/connect/link-up, credentials,
DHCP, routing, rfkill/sysfs write, daemon start command, property mutation,
reboot, flash, or partition write was executed.

## Implementation

```text
scripts/revalidation/wifi_android_hwservice_inventory_v423.py
docs/plans/NATIVE_INIT_V423_ANDROID_HWSERVICE_INVENTORY_PLAN_2026-05-20.md
```

The script:

- validates its command list against active Wi-Fi and mutation patterns;
- redacts serial, MAC, SSID/passphrase-like fields;
- writes private 0700/0600 evidence through `EvidenceStore`;
- loads the latest V422 live manifest by default;
- matches Android-side `lshal` output against the three V414/V422 target
  fqinstances.

## Validation

Static checks:

```text
python3 -m py_compile scripts/revalidation/wifi_android_hwservice_inventory_v423.py
git diff --check
```

Plan evidence:

```text
tmp/wifi/v423-android-hwservice-plan-20260520-132041/
decision: v423-android-hwservice-inventory-plan-ready
pass: True
device_commands_executed: False
device_mutations: False
wifi_bringup_executed: False
```

Live preflight evidence:

```text
tmp/wifi/v423-android-hwservice-preflight-20260520-132051/
decision: v423-android-hwservice-waiting-for-android
pass: True
reason: Android ADB is not online yet (state=error: no devices/emulators found)
device_commands_executed: True
device_mutations: False
wifi_bringup_executed: False
```

Evidence permissions:

```text
directories: 0700
files: 0600
```

## Interpretation

V423 is ready, but the current device state is still native-init rather than
Android ADB.  Therefore the Android-side hwservice inventory did not run yet.

The next useful step is a bounded Android handoff/rollback packet:

1. verify native state and rollback image;
2. boot or flash the known Android boot image;
3. wait for Android ADB;
4. run `wifi_android_hwservice_inventory_v423.py run`;
5. reboot/flash back to native init and verify native protocol recovery.

Wi-Fi bring-up remains blocked until Android-side registration evidence and the
native private-runtime gap are reconciled.

## V424 Follow-up Correction

V424 live evidence showed that `lshal list --types=binderized --neat` can place
Samsung Wi-Fi target rows after the truncated manifest preview.  The V423
classifier now reads the full private command evidence files for matching while
still keeping the manifest preview bounded.
