# S22+ M25 No-ACM Postmortem (2026-07-08)

## Verdict

PASS, host-only postmortem.

M25 was a useful negative result. It proved that the FYG8 DTBO high-speed cap
itself is recoverable and Android-compatible, but the M25 boot candidate still
did not expose an ACM control channel. The candidate returned to Odin/Download
about 30 seconds after boot flash with no ACM, no ADB, and no retained progress
marker available.

Do not repeat M25 unchanged. The next useful unit is not another ACM park
candidate. It should be a prefix/download discriminator that loads bounded
prefixes of the M25 HS-only module list and immediately self-returns to Download
mode after each prefix.

## Inputs

- Live report:
  `docs/reports/S22PLUS_M25_HS_ONLY_USB2_ACM_LIVE_RESULT_2026-07-08.md`
- Live run:
  `workspace/private/runs/s22plus_m25_hs_only_usb2_acm_live_gate_20260708T122411Z`
- Stock-DTBO restore run:
  `workspace/private/runs/s22plus_m25_hs_only_usb2_acm_live_gate_20260708T122816Z`
- Builder:
  `workspace/public/src/scripts/revalidation/build_s22plus_m25_hs_only_usb2_acm.py`
- Generated runtime:
  `workspace/private/outputs/s22plus_native_init/m25_hs_only_usb2_acm_v0_1/build/s22plus_init_usb_acm_m25_hs_only.c`
- Manifest:
  `workspace/private/outputs/s22plus_native_init/m25_hs_only_usb2_acm_v0_1/manifest.json`

Private logs and private build outputs remain uncommitted.

## Live Facts

M25 DTBO stage:

- DTBO candidate flash passed: `m25_dtbo_candidate_odin_rc=0`.
- Android/Magisk returned after the DTBO flash.
- The patched DTBO hash was verified from Android:
  `8962cbbded722c85dbdebfbdc2eba5476b9a64e2a2933888b81f947159eddc17`.

M25 boot stage:

- Boot candidate flash passed: `m25_boot_candidate_odin_rc=0`.
- Observation sample 1 through 30 saw no ACM endpoint:
  `m25_observe_*_acm_devices=[]`.
- No ADB transport appeared during the candidate observation window.
- Odin/Download appeared at sample 30:
  `m25_odin_returned=1 device=/dev/bus/usb/002/016`.
- Magisk boot rollback passed: `magisk_boot_rollback_odin_rc=0`.
- Stock DTBO restore later passed and verified stock DTBO:
  `97a4864fee4e61892d733962d1ec76f8d14b52bc19e6f47440bc27d9dfc4bd0c`.

Canonical first live timeline:

```text
candidate_flash_done  2026-07-08T12:26:45.758671Z
candidate_boot_ready  2026-07-08T12:27:16.034576Z
rollback_flash_start  2026-07-08T12:27:16.034728Z
```

The `candidate_boot_ready` event means "Odin/Download returned", not "M25
native-init became healthy". The delta from boot flash done to Odin return is
about 30.3 seconds.

## Current Baseline Recheck

After the operator later reported another bootloop/manual-Download observation,
host inspection found the phone back in Android ADB, not Odin mode:

```text
adb: RFCT519XWGK device product:g0qksx model:SM_S906N device:g0q
boot_completed=1
bootanim=stopped
verifiedbootstate=orange
bootreason=reboot,download
Magisk uid=0(root)
```

The final baseline hashes still match the intended clean rooted Android state:

```text
boot        2e541703951dc725bad35850faf7028c2d910dd5f21166449b63f1248c29967e
dtbo        97a4864fee4e61892d733962d1ec76f8d14b52bc19e6f47440bc27d9dfc4bd0c
vendor_boot 096e433e049fb088cd956e083d5a1039b33cdf0ca907e713bba7feaaf1b080b7
```

No additional rollback flash was needed for that later report.

## Source Facts

M25 generated `/init` does this in order:

1. `setup_minimal_fs();`
2. `emit(k_marker);`
3. `load_hs_only_usb2_modules();`
4. `force_usb_roles_device();`
5. `create_acm_gadget();`
6. `serial_probe_loop();`

The build verifies that M25 contains no arm64 `__NR_reboot=142` path and no
`download` runtime string. Therefore the Odin/Download return observed about
30 seconds after candidate flash was not an intentional M25 self-download
beacon. Treat it as an external reset/watchdog/bootloader return shape.

The M25 module list is a 40-module HS-only closure. It intentionally excludes:

- `phy-msm-ssusb-qmp.ko`
- `eud.ko`
- `ucsi_glink.ko`
- reset/watchdog/anomaly modules inherited through the blocklist

The risky tail of the M25 list starts at the USB/PHY/DWC3 region:

```text
25 arm_smmu.ko
26 phy-msm-snps-hs.ko
27 phy-msm-snps-eusb2.ko
28 dwc3-msm.ko
29 usb_f_ss_mon_gadget.ko
30 usb_f_ss_acm.ko
31 repeater.ko
32 redriver.ko
33 usb_notify_layer.ko
34 switch_class.ko
35 common_muic.ko
36 vbus_notifier.ko
37 usb_typec_manager.ko
38 if_cb_manager.ko
39 pdic_notifier_module.ko
40 qc_usb_audio.ko
```

## Interpretation

M25 did not prove "HS-only DWC3 cannot work." It proved that this all-at-once
40-module HS-only ACM park candidate does not reach a visible host ACM endpoint
before the device returns through Odin/Download.

Useful conclusions:

- The DTBO high-speed cap is not the immediate brick source. Android booted with
  the patched DTBO and the stock DTBO rollback path worked.
- Excluding QMP was not sufficient by itself. The no-ACM reset shape still
  exists with the 40-module HS-only closure.
- Retained log channels still do not localize native-init progress. M24 pmsg
  steps, pstore, `last_kmsg`, and reset-summary paths have all failed to capture
  a usable per-step marker for this class.
- A park-and-wait ACM candidate is now a weak proof shape because failure gives
  the same "no ACM then Download" result without localizing the fault.

## M26 Direction

Build M26 as a host-only prefix/download discriminator before any live request:

1. Start from the M25 build artifacts and stock DTBO high-speed cap mechanism.
2. Generate multiple boot candidates or a single parameterized builder for
   bounded prefixes of the M25 module list.
3. Each candidate must load its prefix, then immediately invoke a deliberate
   Download-mode reboot. Success is host-observed self-download after that
   prefix.
4. Do not create configfs/ACM in the first M26 unit. Keep the first pass focused
   on module-prefix survivability.
5. Choose coarse prefixes first, not one-module sweeps:
   `0`, `24`, `25`, `27`, `28`, `30`, `33`, `40`.
6. Only after a prefix self-downloads cleanly should later candidates add
   configfs/role-force/UDC bind or narrow the failing prefix.

Suggested first live batch, after host build and a fresh SHA-pinned exception:

```text
M26-P00 prefix=0   mount/dev floor then self-download
M26-P24 prefix=24  common substrate before arm_smmu/USB PHY
M26-P27 prefix=27  HS PHY/eUSB2 loaded, no dwc3
M26-P30 prefix=30  dwc3 + ACM function loaded
```

This directly answers which prefix can execute and return under native-init
without relying on retained markers.

## Validation

Host-only checks performed during this postmortem:

```bash
adb devices -l
adb shell 'getprop sys.boot_completed; getprop init.svc.bootanim; getprop ro.boot.verifiedbootstate; getprop ro.boot.bootreason; cat /proc/uptime'
adb shell su -c id
adb shell su -c 'sha256sum /dev/block/by-name/boot'
adb shell su -c 'sha256sum /dev/block/by-name/dtbo'
adb shell su -c 'sha256sum /dev/block/by-name/vendor_boot'
```

Result: Android/Magisk baseline is clean; no live write was performed in this
postmortem unit.
