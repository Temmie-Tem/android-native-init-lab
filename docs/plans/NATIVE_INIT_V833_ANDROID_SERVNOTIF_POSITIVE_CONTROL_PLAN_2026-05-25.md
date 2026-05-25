# Native Init V833 Android Service-notifier Positive-control Plan

## Goal

Run a bounded Android-success positive control for the same
`msm/modem/wlan_pd` service-notifier listener request that returned `uninit` in
native V830/V831.

## Why This Gate

V829 proved `wlan/fw -> msm/modem/wlan_pd` instance `180`.
V830 and V831 proved native can register the listener against service-notifier
`66/46081`, but current state remains `uninit`. The remaining ambiguity is
whether:

1. native genuinely lacks the lower WLAN-PD state transition; or
2. the QMI listener payload/model/state interpretation is incomplete.

The least ambiguous next proof is to run the same listener query on an
Android-success runtime.

## Scope

V833 adds:

- `stage3/linux_init/helpers/a90_servnotif_listener_probe.c`
- `scripts/revalidation/build_servnotif_listener_probe_helper.sh`
- `scripts/revalidation/native_wifi_android_servnotif_positive_control_v833.py`
- `scripts/revalidation/android_servnotif_positive_control_handoff_v833.py`

## Live Handoff Contract

The handoff wrapper:

1. builds the static helper;
2. verifies native v724 rollback and a stock Android boot candidate;
3. enters recovery/TWRP;
4. flashes the stock Android boot image;
5. waits for Android `sys.boot_completed=1`;
6. pushes and runs the bounded service-notifier helper;
7. removes the helper;
8. reboots to recovery;
9. restores native v724 and verifies rollback.

## Hard Guardrails

- No Wi-Fi enable, scan, connect, link-up, credential use, DHCP, route change,
  or external ping.
- No service-manager, Wi-Fi HAL, wificond, supplicant, or hostapd start/stop by
  V833.
- The only QMI payload is the bounded service-notifier `REGISTER_LISTENER` and
  optional ACK for `msm/modem/wlan_pd`.
- Boot image writes are limited to stock Android handoff and native v724
  rollback in the handoff wrapper.
- No custom OSRC diagnostic kernel flash.

## Success Criteria

- Prep: helper builds static, collector plan passes, handoff dry-run passes.
- Live positive control:
  - Android returns or indicates `up`: native lower-state transition is the
    active gap.
  - Android also returns `uninit`: listener payload/model/state interpretation
    needs correction before more native retries.

## Validation

```bash
python3 -m py_compile \
  scripts/revalidation/native_wifi_android_servnotif_positive_control_v833.py \
  scripts/revalidation/android_servnotif_positive_control_handoff_v833.py

scripts/revalidation/build_servnotif_listener_probe_helper.sh \
  tmp/wifi/v833-servnotif-helper-build/a90_servnotif_listener_probe

python3 scripts/revalidation/native_wifi_android_servnotif_positive_control_v833.py \
  --out-dir tmp/wifi/v833-android-servnotif-positive-control-plan-check \
  plan

python3 scripts/revalidation/android_servnotif_positive_control_handoff_v833.py \
  --out-dir tmp/wifi/v833-android-servnotif-handoff-dryrun \
  dry-run
```

## Live Command

```bash
python3 scripts/revalidation/android_servnotif_positive_control_handoff_v833.py \
  --allow-android-boot-flash \
  --assume-yes \
  --i-understand-native-rollback \
  run
```
