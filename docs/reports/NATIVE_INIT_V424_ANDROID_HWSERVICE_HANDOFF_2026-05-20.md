# Native Init V424 Android hwservice Handoff Report

Date: 2026-05-20

## Scope

V424 implemented and live-validated a bounded Android boot handoff for V423.
The sequence temporarily boots stock Android, collects read-only hwservice/lshal
Wi-Fi evidence, then restores native init v319.

No Wi-Fi enable, scan/connect/link-up, credentials, DHCP, routing, rfkill/sysfs
write, module load/unload, property mutation, or direct Wi-Fi daemon start
command was executed.

## Implementation

```text
scripts/revalidation/android_hwservice_handoff_v424.py
scripts/revalidation/wifi_android_hwservice_inventory_v423.py
```

Changes:

- added V424 handoff executor with `plan`, `dry-run`, and approval-gated `run`;
- defaulted rollback to `stage3/boot_linux_v319.img` and marker `A90 Linux init 0.9.61 (v319)`;
- added Android boot SHA/readback verification before booting Android;
- added `wait-android-before-rollback` to avoid transient ADB disconnects before rollback;
- accepted native `hide requested` as a successful hide request;
- fixed V423 classification to match against full private command evidence, not truncated manifest text.

## Validation

Static checks:

```text
python3 -m py_compile scripts/revalidation/wifi_android_hwservice_inventory_v423.py scripts/revalidation/android_hwservice_handoff_v424.py
git diff --check
```

Plan evidence:

```text
tmp/wifi/v424-android-hwservice-handoff-plan-20260520-132955/
decision: v424-handoff-plan-ready
pass: True
device_commands_executed: False
device_mutations: False
wifi_bringup_executed: False
```

Dry-run evidence after retry guard:

```text
tmp/wifi/v424-android-hwservice-handoff-dryrun-hidebusy-20260520-133426/
decision: v424-handoff-dryrun-ready
pass: True
device_commands_executed: False
device_mutations: False
wifi_bringup_executed: False
```

Final live evidence:

```text
tmp/wifi/v424-android-hwservice-handoff-live-classifierfix-20260520-133829/
decision: v424-handoff-pass
pass: True
device_commands_executed: True
device_mutations: True
wifi_bringup_executed: False
```

Final V423 Android evidence inside the handoff:

```text
tmp/wifi/v424-android-hwservice-handoff-live-classifierfix-20260520-133829/v423-android-hwservice-run/
decision: v423-android-hwservice-targets-present
pass: True
matched_targets:
- vendor.samsung.hardware.wifi@2.0::ISehWifi/default
- vendor.samsung.hardware.wifi@2.1::ISehWifi/default
- vendor.samsung.hardware.wifi@2.2::ISehWifi/default
```

Native rollback verification after the final live run:

```text
A90 Linux init 0.9.61 (v319)
cmdv1 version/status: rc=0 status=ok
adbd: stopped
netservice: disabled tcpctl=stopped
storage: backend=sd writable=yes
```

## Observations

- Android boot and native rollback images were both SHA/readback verified.
- Android runtime had Wi-Fi-related processes such as `android.hardware.wifi@1.0-service`, `vendor.samsung.hardware.wifi@2.0-service`, `wificond`, `cnss_diag`, and `cnss-daemon` during the read-only capture.
- `lshal` showed the three Samsung `ISehWifi/default` targets, but also emitted fetch warnings and `N/A` rows.
- `sys.boot_completed` was still empty in the captured Android property set, so this evidence is early-boot registration/declaration evidence, not final boot-complete service readiness proof.

## Corrections Found During Live Work

Initial live runs exposed two harness issues:

1. `adb reboot recovery` could run during a transient post-capture ADB gap.  V424 now waits for Android ADB again before rollback.
2. V423 classification used truncated manifest preview text, which could miss later `lshal` target lines.  V423 now classifies from the full private command evidence file.

Both fixes were validated by the final V424 live PASS.

## Interpretation

V424 closes the handoff/rollback safety gap: we can temporarily boot Android,
collect passive hwservice evidence, and return to native v319 without Wi-Fi
bring-up.

The Android evidence proves the Samsung Wi-Fi target names exist in the Android
runtime surface, but it does not yet prove stable boot-complete registration.
The next step should wait for Android boot completion/settle, rerun the same
read-only inventory, and then compare that result against the native private
runtime V422/V407 behavior.
