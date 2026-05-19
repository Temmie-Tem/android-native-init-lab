# Native Init v299 Android Capture Handoff Report

- date: `2026-05-19`
- scope: Android boot handoff preflight for v297 capture
- boot image change: none
- baseline device build: `A90 Linux init 0.9.60 (v261)`
- plan: `docs/plans/NATIVE_INIT_V299_ANDROID_CAPTURE_HANDOFF_PLAN_2026-05-19.md`
- tool: `scripts/revalidation/android_capture_handoff_preflight.py`

## Summary

v299 prepares the operator-approved transition needed to unblock v297 Android
property capture. It does not reboot the phone, enter recovery, or write the
boot partition.

The current preflight result is ready:

- native bridge control: PASS
- native rollback image: present
- Android boot image candidate: present
- decision: `android-capture-handoff-ready-needs-operator`

## Evidence

| item | path | result |
| --- | --- | --- |
| plan | `tmp/wifi/v299-android-capture-handoff-plan/` | `android-capture-handoff-plan-ready` |
| preflight | `tmp/wifi/v299-android-capture-handoff-preflight/` | `android-capture-handoff-ready-needs-operator` |

## Validation

Static:

```bash
python3 -m py_compile scripts/revalidation/android_capture_handoff_preflight.py
git diff --check
```

Plan/preflight:

```bash
python3 scripts/revalidation/android_capture_handoff_preflight.py \
  --out-dir tmp/wifi/v299-android-capture-handoff-plan \
  plan

python3 scripts/revalidation/android_capture_handoff_preflight.py \
  --out-dir tmp/wifi/v299-android-capture-handoff-preflight \
  preflight
```

Result: PASS.

## Images

| role | path | size | sha256 prefix | note |
| --- | --- | --- | --- | --- |
| native rollback | `stage3/boot_linux_v261.img` | `53972992` | `5a314c2adbd5547b` | contains `A90 Linux init 0.9.60 (v261)` |
| Android boot candidate | `backups/baseline_a_20260423_025322/boot.img` | `67108864` | `c15ce425abb8da41` | `ANDROID!`, no native marker |
| Android boot duplicate | `backups/baseline_a_20260423_030309/boot.img` | `67108864` | `c15ce425abb8da41` | same hash as recommended candidate |

## Native Control

| check | result |
| --- | --- |
| `a90ctl.py --json version` | PASS |
| `a90ctl.py status` | PASS |

## Safety

- No reboot.
- No recovery transition.
- No boot partition write.
- No Android boot image flashing.
- No property mutation.
- No service-manager/HAL/Wi-Fi daemon execution.
- No Wi-Fi scan/connect/link-up/credential/DHCP/routing.

## Interpretation

The repository is ready for the Android capture maintenance step, but execution
requires explicit operator approval because it writes the boot partition to boot
Android and then writes it again to restore native init.

After Android is booted and ADB is online, run v297 capture and v298 compare:

```bash
python3 scripts/revalidation/wifi_android_property_capture.py \
  --out-dir tmp/wifi/v297-android-property-capture-android run

python3 scripts/revalidation/wifi_property_baseline_compare.py \
  --out-dir tmp/wifi/v298-property-baseline-compare-android \
  --v297-manifest tmp/wifi/v297-android-property-capture-android/manifest.json \
  run
```

Then restore native init through TWRP using `stage3/boot_linux_v261.img`.
