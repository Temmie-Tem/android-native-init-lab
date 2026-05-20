# Native Init V434 Android Wi-Fi Auto-connect Policy Plan

Date: 2026-05-20

## Goal

V434 turns V433 containment evidence into an explicit operating policy before
any Wi-Fi server exposure or explicit scan/connect work.  V433 showed stable
Android auto-connect with `wlan0` route/DNS exposure, so V434 defaults to the
safer policy: contain auto-connect first.

## Scope

Allowed:

- consume V433 containment evidence and select a host-side policy;
- optionally rerun the V433 read-only Android handoff to refresh evidence before
  policy selection;
- restore native init v319 through the inherited V433 rollback path;
- document blocked and allowed next actions.

Not allowed:

- Wi-Fi enable/disable, scan, connect, credentials, DHCP/routing mutation, or
  external packet probes;
- server exposure, new listeners, or port forwarding over Wi-Fi;
- direct Wi-Fi daemon starts, rfkill/sysfs writes, module operations, or
  `setprop`.

## Implementation

- Policy selector: `scripts/revalidation/wifi_android_autoconnect_policy_v434.py`
  - loads the latest or specified V433 manifest;
  - selects `contain-first` when stable Wi-Fi auto-connect has route/DNS exposure;
  - keeps server exposure, explicit scan/connect, credentials, routing mutation,
    external probes, and new Wi-Fi-facing listeners blocked.
- Handoff wrapper:
  `scripts/revalidation/android_wifi_autoconnect_policy_handoff_v434.py`
  - reruns V433 read-only containment in Android boot-complete mode;
  - restores native init through the V433 rollback path;
  - runs the V434 host-side policy selector against the fresh V433 manifest.

## Validation Plan

```text
python3 -m py_compile \
  scripts/revalidation/wifi_android_autoconnect_policy_v434.py \
  scripts/revalidation/android_wifi_autoconnect_policy_handoff_v434.py

python3 scripts/revalidation/wifi_android_autoconnect_policy_v434.py \
  --out-dir tmp/wifi/v434-android-autoconnect-policy-plan-<ts> plan

python3 scripts/revalidation/wifi_android_autoconnect_policy_v434.py \
  --out-dir tmp/wifi/v434-android-autoconnect-policy-hostrun-<ts> run

python3 scripts/revalidation/android_wifi_autoconnect_policy_handoff_v434.py \
  --out-dir tmp/wifi/v434-android-autoconnect-policy-handoff-dryrun-<ts> \
  --allow-android-boot-flash --assume-yes --i-understand-native-rollback \
  dry-run

git diff --check
```

Live sequence:

1. confirm native v319 status over the bridge;
2. run the V434 handoff wrapper;
3. let the wrapper boot Android, rerun V433 read-only containment, select V434
   policy, and restore native v319;
4. verify native `version`, `selftest`, and `status`;
5. scan evidence for raw SSID/BSSID/security-type leaks.

## Expected Decisions

- `v434-android-wifi-policy-plan-ready`
- `v434-handoff-plan-ready`
- `v434-handoff-dryrun-ready`
- `v434-android-wifi-policy-contain-first-pass`
- `v434-android-wifi-policy-hard-contain-pass`
- `v434-android-wifi-policy-stability-first-pass`
- `v434-android-wifi-policy-review-exposure-pass`
- `v434-android-wifi-policy-missing-v433`

Any PASS decision must keep `wifi_bringup_executed=False`.

## Next Gate Rule

For the current evidence, `contain-first` means V435 should prove an intentional
auto-connect disable/containment path and post-cleanup route/DNS/listener state.
It still must not scan, connect, expose a server, or handle credentials.
