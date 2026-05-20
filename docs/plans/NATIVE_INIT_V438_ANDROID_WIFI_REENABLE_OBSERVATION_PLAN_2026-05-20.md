# Native Init V438 Android Wi-Fi Re-enable Observation Plan

Date: 2026-05-20

## Goal

V438 is the first controlled Android Wi-Fi re-enable gate after V435/V436 proved
that framework Wi-Fi disable can contain the saved auto-connect exposure.  V437
selected this branch because the project still needs Wi-Fi functionality, but
must not jump directly to scan/connect, credentials, server exposure, or
external traffic.

The gate answers one narrow question:

```text
If Android framework Wi-Fi is re-enabled once, does Android immediately expose
wlan0 route/DNS/connectivity or global listening surface?
```

## Scope

Allowed:

- boot Android to `sys.boot_completed=1` through the existing handoff wrapper;
- issue exactly one Wi-Fi setting mutation:

  ```text
  cmd wifi set-wifi-enabled enabled
  ```

- observe pre/post Wi-Fi status, `wlan0` address state, routes, Android
  connectivity service output, DNS-related surface, filtered Wi-Fi dumpsys
  lines, and listening sockets;
- restore native v319 and verify rollback.

Not allowed:

- scan/connect commands or credential operations;
- DHCP, route, interface, sysfs/rfkill, module, property, or daemon-start
  mutation;
- external packet probes such as `ping`, `curl`, `nc`, `dig`, or `nslookup`;
- server exposure or new Wi-Fi-facing listeners.

## Implementation

- Collector: `scripts/revalidation/wifi_android_reenable_observation_v438.py`
  - reuses the V435 redacted capture/parsing helpers;
  - adds filtered `dumpsys wifi` capture for enabled/connected/autojoin clues;
  - records `wifi_enable_executed=True` and `wifi_bringup_executed=True` only
    when the bounded enable command is actually executed;
  - classifies the result into contained, auto-connect observed, not-enabled,
    command-failed, or approval-required states.
- Handoff: `scripts/revalidation/android_wifi_reenable_observation_handoff_v438.py`
  - temporarily flashes the baseline Android boot image;
  - waits for Android boot-complete;
  - runs the V438 collector with explicit enable approval flags;
  - reboots to recovery and restores native v319.

## Validation Plan

```text
python3 -m py_compile \
  scripts/revalidation/wifi_android_reenable_observation_v438.py \
  scripts/revalidation/android_wifi_reenable_observation_handoff_v438.py

python3 scripts/revalidation/wifi_android_reenable_observation_v438.py \
  --out-dir tmp/wifi/v438-android-wifi-reenable-plan-<ts> \
  --allow-wifi-enable --i-understand-android-wifi-setting-mutation \
  plan

python3 scripts/revalidation/android_wifi_reenable_observation_handoff_v438.py \
  --out-dir tmp/wifi/v438-android-wifi-reenable-handoff-dryrun-<ts> \
  --allow-android-boot-flash --assume-yes --i-understand-native-rollback \
  --allow-wifi-enable --i-understand-android-wifi-setting-mutation \
  dry-run

python3 scripts/revalidation/android_wifi_reenable_observation_handoff_v438.py \
  --out-dir tmp/wifi/v438-android-wifi-reenable-handoff-live-<ts> \
  --allow-android-boot-flash --assume-yes --i-understand-native-rollback \
  --allow-wifi-enable --i-understand-android-wifi-setting-mutation \
  run

python3 scripts/revalidation/a90ctl.py --json version
python3 scripts/revalidation/a90ctl.py --json selftest
python3 scripts/revalidation/a90ctl.py --json status

git diff --check
```

## Expected Decisions

- `v438-android-wifi-reenable-plan-ready`
- `v438-android-wifi-reenable-preflight-ready`
- `v438-android-wifi-reenable-enabled-contained-pass`
- `v438-android-wifi-reenable-autoconnect-observed-pass`
- `v438-android-wifi-reenable-not-enabled`
- `v438-android-wifi-reenable-command-failed`
- `v438-android-wifi-reenable-approval-required`
- `v438-handoff-dryrun-ready`

## Pass Criteria

A PASS decision must show:

- the Android boot-complete gate passed before the collector ran;
- only the bounded framework enable command mutated Wi-Fi state;
- no scan/connect, credential, route, DHCP, sysfs/rfkill, module, property,
  daemon-start, server, or external packet-probe operation ran;
- the post-enable listener surface stayed safe;
- native v319 rollback completed.

If `wlan0` IP, route, DNS, validated Wi-Fi connectivity, or Wi-Fi connection is
observed, the result may still be a PASS only as observation evidence.  It does
not approve server exposure or explicit scan/connect.

## Next Gate Rule

V438 intentionally leaves Android framework Wi-Fi enabled if the command
succeeds.  The next cycle must therefore choose one of two bounded branches:

- V439 extended enabled observation with no scan/connect or external probes; or
- V439 cleanup/containment that disables Wi-Fi again before further native or
  server-side work.

The safer default is to observe persistence/exposure briefly, then restore
containment before any server or credential work.
