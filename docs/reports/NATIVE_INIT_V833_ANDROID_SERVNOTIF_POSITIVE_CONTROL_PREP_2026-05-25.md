# Native Init V833 Android Service-notifier Positive-control Prep Report

## Result

- decision: `v833-handoff-dryrun-ready`
- pass: `true`
- collector: `scripts/revalidation/native_wifi_android_servnotif_positive_control_v833.py`
- handoff: `scripts/revalidation/android_servnotif_positive_control_handoff_v833.py`
- helper: `stage3/linux_init/helpers/a90_servnotif_listener_probe.c`
- dry-run evidence: `tmp/wifi/v833-android-servnotif-handoff-dryrun/`

## What Ran

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
  --out-dir tmp/wifi/v833-android-servnotif-handoff-plan-check \
  plan

python3 scripts/revalidation/android_servnotif_positive_control_handoff_v833.py \
  --out-dir tmp/wifi/v833-android-servnotif-handoff-dryrun \
  dry-run
```

## Prep Evidence

| Signal | Result |
| --- | --- |
| helper marker | `a90_servnotif_listener_probe v1` |
| helper sha256 | `0d0cc09d4b23b53b0797d9daac1d134b3fc02aa0c38b891ac0d9af8432078981` |
| helper binary | static aarch64, no dynamic section |
| native rollback image | `stage3/boot_linux_v724.img`, Android boot image format, native marker present |
| Android boot candidates | two baseline `boot.img` candidates, stock Android marker profile |
| handoff dry-run | complete, no device mutation |

## Classification

V833 is ready for a live Android handoff. The dry-run records the full sequence:

```text
build helper
  -> verify native v724 rollback
  -> flash stock Android boot candidate
  -> wait for Android boot-complete
  -> run bounded service-notifier positive-control
  -> restore native v724
```

The live result will decide whether the native `uninit` state is meaningful:

1. Android returns/indicates `up`: native lower WLAN-PD state transition is the
   blocker.
2. Android also returns `uninit`: the listener payload/model/state
   interpretation is incomplete.

## Safety

- Prep and dry-run did not execute device commands, boot writes, QRTR/QMI
  payloads, Wi-Fi HAL, scan/connect, credentials, DHCP/routes, or external ping.
- The live wrapper restricts boot writes to stock Android handoff and native
  v724 rollback.
- The Android collector pushes a temporary helper, sends one bounded
  service-notifier listener request, removes the helper, and does not alter
  Wi-Fi link state.
- No Wi-Fi secret material was written to tracked output.

## Next

Run the V833 live handoff if the current device state is native v724 and the
bridge is healthy. After rollback, record whether Android returned `up`,
`uninit`, no response, or no endpoint.
