# Native Init V430 Android lshal Explicit Mirror Plan

Date: 2026-05-20

## Goal

V430 mirrors the V429 native `lshal` question inside the fully booted Android
runtime.  V429 proved that the native private composite stack can keep the core
managers and first Samsung Wi-Fi HAL child alive, but
`/system/bin/lshal list --types=binderized --neat -S` still timed out.

V430 answers whether Android boot-complete returns the same Samsung Wi-Fi
`ISehWifi/default` target surface when Android owns the real service managers.

## Scope

Allowed:

- temporarily flash the known Android boot image;
- wait for Android ADB and `sys.boot_completed=1`;
- run only read-only ADB shell captures;
- run these `lshal` mirror commands:
  - `lshal list --types=vintf --neat -V -S -i`;
  - `lshal list --types=binderized --neat -S`;
  - `lshal list --types=binderized --neat` with Wi-Fi filtering;
- restore native init v319 with readback/rollback evidence.

Not allowed:

- Wi-Fi enable, scan, connect, link-up, credentials, DHCP, or routing;
- `svc wifi`, `cmd wifi`, `iw`, `wpa_cli`, rfkill/sysfs writes, or module
  load/unload;
- direct Wi-Fi daemon start commands;
- persistent boot/autostart changes.

## Implementation

- Collector: `scripts/revalidation/wifi_android_lshal_explicit_v430.py`
  - records Android boot-complete, Wi-Fi processes, framework service names,
    VINTF status rows, binderized status rows, and binderized neat rows;
  - classifies Samsung `ISehWifi/default` targets as absent, declared,
    listed, or not-fetchable;
  - treats `lshal -S` nonzero/crash separately from target presence.
- Handoff wrapper: `scripts/revalidation/android_lshal_explicit_handoff_v430.py`
  - reuses the V424/V425 Android boot/rollback path;
  - inserts V430 collector after boot-complete settle;
  - compares V430 Android output to the latest V429 native runtime-gap result.

## Validation Plan

```text
python3 -m py_compile \
  scripts/revalidation/wifi_android_lshal_explicit_v430.py \
  scripts/revalidation/android_lshal_explicit_handoff_v430.py

python3 scripts/revalidation/wifi_android_lshal_explicit_v430.py \
  --out-dir tmp/wifi/v430-android-lshal-explicit-plan-<ts> plan

python3 scripts/revalidation/android_lshal_explicit_handoff_v430.py \
  --out-dir tmp/wifi/v430-android-lshal-explicit-handoff-dryrun-<ts> \
  --allow-android-boot-flash --assume-yes --i-understand-native-rollback \
  dry-run

git diff --check
```

Live sequence:

1. confirm native v319 status over the bridge;
2. flash Android boot image from recovery;
3. wait for Android `sys.boot_completed=1`;
4. run V430 read-only explicit-column `lshal` mirror;
5. reboot to recovery and restore native v319;
6. verify native `version`, `selftest`, and `status`.

## Expected Decisions

- `v430-android-lshal-explicit-plan-ready`
- `v430-handoff-plan-ready`
- `v430-handoff-dryrun-ready`
- `v430-android-explicit-targets-present-native-gap`
- `v430-android-explicit-targets-present-status-crash`
- `v430-android-explicit-targets-present-status-gap`
- `v430-android-explicit-no-targets`

Any PASS decision must still keep `wifi_bringup_executed=False`.
