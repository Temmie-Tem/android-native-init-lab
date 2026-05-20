# Native Init V433 Android Wi-Fi Auto-connect Containment Plan

Date: 2026-05-20

## Goal

V433 characterizes the Android Wi-Fi state that V432 found already connected at
boot-complete.  The goal is not Wi-Fi bring-up.  The goal is to determine
whether Android auto-connect creates route, DNS, default-network, or listener
exposure before any explicit scan/connect/server work is allowed.

## Scope

Allowed:

- temporarily flash the known Android boot image;
- wait for Android ADB and `sys.boot_completed=1`;
- run bounded read-only samples of Android Wi-Fi status, route lookup, netdev
  state, connectivity state, listening sockets, and filtered `dumpsys wifi`;
- use `ip route get` as a local route lookup only;
- restore native init v319 with rollback evidence;
- redact MAC, IP, SSID/BSSID, serial, credential-like fields, and Wi-Fi
  security-type tokens.

Not allowed:

- Wi-Fi enable/disable, scan, connect, link-up, credentials, DHCP, or routing
  changes;
- `ping`, `curl`, `wget`, `nc`, `dig`, `nslookup`, or any external packet probe;
- `svc wifi`, mutating `cmd wifi`, `iw` scan/connect/set, `wpa_cli`, rfkill or
  sysfs writes, module load/unload, `setprop`, or direct daemon starts.

## Implementation

- Collector: `scripts/revalidation/wifi_android_autoconnect_containment_v433.py`
  - captures one-shot Android identity/settings/services/process/socket state;
  - captures three default samples of `cmd wifi status`, `ip route`, local
    `ip route get`, `wlan0` state, filtered `dumpsys connectivity`, and filtered
    `dumpsys wifi`;
  - blocks mutating Wi-Fi commands and external packet-probe commands before
    execution;
  - classifies stable Wi-Fi connection, `wlan0` IP, default route over `wlan0`,
    local route candidate over `wlan0`, validated Wi-Fi connectivity, DNS
    surface, and global listener presence.
- Handoff wrapper:
  `scripts/revalidation/android_wifi_autoconnect_containment_handoff_v433.py`
  - reuses the Android boot-complete handoff and native rollback path;
  - runs V433 only after boot-complete settle;
  - maps collector results into a rollback-verified handoff decision.

## Validation Plan

```text
python3 -m py_compile \
  scripts/revalidation/wifi_android_control_gate_v432.py \
  scripts/revalidation/wifi_android_autoconnect_containment_v433.py \
  scripts/revalidation/android_wifi_autoconnect_containment_handoff_v433.py

python3 scripts/revalidation/wifi_android_autoconnect_containment_v433.py \
  --out-dir tmp/wifi/v433-android-autoconnect-containment-plan-<ts> plan

python3 scripts/revalidation/android_wifi_autoconnect_containment_handoff_v433.py \
  --out-dir tmp/wifi/v433-android-autoconnect-containment-handoff-dryrun-<ts> \
  --allow-android-boot-flash --assume-yes --i-understand-native-rollback \
  dry-run

git diff --check
```

Live sequence:

1. confirm native v319 status over the bridge;
2. flash Android boot image from recovery;
3. wait for Android `sys.boot_completed=1`;
4. run V433 read-only containment samples;
5. reboot to recovery and restore native v319;
6. verify native `version`, `selftest`, and `status`.

## Expected Decisions

- `v433-android-autoconnect-containment-plan-ready`
- `v433-handoff-plan-ready`
- `v433-handoff-dryrun-ready`
- `v433-android-wifi-autoconnect-exposure-mapped`
- `v433-android-wifi-autoconnect-contained-map-pass`
- `v433-android-wifi-enabled-ip-contained-map-pass`
- `v433-android-wifi-disabled-contained-pass`
- `v433-android-autoconnect-containment-review-required`
- `v433-android-autoconnect-containment-blocked`

Any PASS decision must keep `wifi_bringup_executed=False`.

## Next Gate Rule

If V433 maps Wi-Fi default-route or validated-network exposure, the next gate is
a policy choice before serverization: either disable/contain Android
auto-connect for lab runs, or continue with bounded exposure-aware stability
sampling under explicit risk acceptance.
