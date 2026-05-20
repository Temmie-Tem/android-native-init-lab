# Native Init V441 Android Wi-Fi Exposure-aware Stability Plan

Date: 2026-05-20

## Goal

V441 runs the first bounded exposure-aware Android-managed Wi-Fi stability
cycle after V440 selected `contained-lab-default`.

The gate starts from the contained lab baseline, uses the proven V438 enable
handoff to activate Android framework Wi-Fi, then uses the proven V439
post-reenable handoff to observe auto-connect stability and cleanup containment.

It answers:

```text
Can Android-managed Wi-Fi stay connected and externally routed across a bounded
sample window, with no global listener exposure, and can cleanup disable restore
containment afterward?
```

## Scope

Allowed:

- run V438 controlled framework Wi-Fi enable handoff;
- run V439 post-reenable observation for a bounded sample window;
- run V439 cleanup disable;
- restore native v319 after each nested handoff.

Not allowed:

- explicit scan/connect;
- credential operations or credential capture;
- server exposure or new Wi-Fi-facing listeners;
- external packet probes such as `ping`, `curl`, `nc`, `dig`, or `nslookup`;
- DHCP/routing mutation, sysfs/rfkill writes, module operations, `setprop`, or
  direct daemon starts.

## Implementation

- Orchestrator: `scripts/revalidation/wifi_android_exposure_stability_v441.py`
  - calls `android_wifi_reenable_observation_handoff_v438.py` for enable;
  - calls `android_wifi_post_reenable_handoff_v439.py` for stability and
    cleanup;
  - consumes nested manifests and classifies stable exposure, listener safety,
    and cleanup containment.

The implementation deliberately reuses V438/V439 rather than duplicating another
Android boot/rollback handoff path.

## Validation Plan

```text
python3 -m py_compile scripts/revalidation/wifi_android_exposure_stability_v441.py

python3 scripts/revalidation/wifi_android_exposure_stability_v441.py \
  --out-dir tmp/wifi/v441-android-wifi-exposure-stability-plan-<ts> \
  --allow-android-boot-flash --assume-yes --i-understand-native-rollback \
  --allow-wifi-enable --i-understand-android-wifi-setting-mutation \
  --allow-wifi-disable-cleanup --i-understand-android-wifi-cleanup-mutation \
  --sample-duration 60 --sample-interval 20 \
  plan

python3 scripts/revalidation/wifi_android_exposure_stability_v441.py \
  --out-dir tmp/wifi/v441-android-wifi-exposure-stability-dryrun-<ts> \
  --allow-android-boot-flash --assume-yes --i-understand-native-rollback \
  --allow-wifi-enable --i-understand-android-wifi-setting-mutation \
  --allow-wifi-disable-cleanup --i-understand-android-wifi-cleanup-mutation \
  --sample-duration 60 --sample-interval 20 \
  dry-run

python3 scripts/revalidation/wifi_android_exposure_stability_v441.py \
  --out-dir tmp/wifi/v441-android-wifi-exposure-stability-live-<ts> \
  --allow-android-boot-flash --assume-yes --i-understand-native-rollback \
  --allow-wifi-enable --i-understand-android-wifi-setting-mutation \
  --allow-wifi-disable-cleanup --i-understand-android-wifi-cleanup-mutation \
  --sample-duration 300 --sample-interval 30 \
  run

python3 scripts/revalidation/a90ctl.py --json version
python3 scripts/revalidation/a90ctl.py --json selftest
python3 scripts/revalidation/a90ctl.py --json status

git diff --check
```

## Expected Decisions

- `v441-android-wifi-exposure-stability-plan-ready`
- `v441-android-wifi-exposure-stability-dryrun-ready`
- `v441-android-wifi-exposure-stability-cleanup-pass`
- `v441-android-wifi-exposure-flap-cleanup-pass`
- `v441-android-wifi-no-exposure-cleanup-pass`
- `v441-android-wifi-exposure-stability-listener-observed`
- `v441-android-wifi-exposure-stability-cleanup-not-contained`
- `v441-android-wifi-exposure-stability-enable-failed`
- `v441-android-wifi-exposure-stability-observation-failed`

## Pass Criteria

A stable PASS must show:

- V438 controlled enable handoff passed;
- V439 stability/cleanup handoff passed;
- all V439 samples saw Wi-Fi route/DNS/connectivity exposure;
- no global listening socket exposure was observed;
- cleanup disable contained active `wlan0` IP, route, DNS, and validated
  connectivity;
- native v319 rollback completed and native postflight checks passed.

V441 still does not approve server exposure or explicit scan/connect.

## Next Gate Rule

If V441 passes, Wi-Fi can be considered functional in Android-managed mode for
bounded test windows.  The next step should be either:

- V442 credential/target allowlist design for explicit scan/connect; or
- a longer exposure-aware stability run if duration confidence is still needed.

Serverization remains blocked until binding, ACL, authentication, and listener
policy are explicit.
