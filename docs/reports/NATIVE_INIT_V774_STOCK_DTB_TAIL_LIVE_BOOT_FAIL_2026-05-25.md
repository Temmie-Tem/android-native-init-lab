# Native Init V774 Stock-DTB Tail Live Boot-fail Report

## Result

- decision: `v774-stock-dtb-tail-kernel-boot-failed-recovery-mode`
- pass: `false`
- evidence: `tmp/wifi/v774-stockdtb-live-handoff-20260525-015926/`
- rollback evidence: `tmp/wifi/v774-rollback-v724-20260525-020056/`
- flashed image: `tmp/wifi/v773-stock-dtb-tail-repack/boot_linux_v773_icnss_diag_stockdtb.img`
- rollback image: `stage3/boot_linux_v724.img`

## What Ran

```bash
python3 scripts/revalidation/native_init_flash.py \
  tmp/wifi/v773-stock-dtb-tail-repack/boot_linux_v773_icnss_diag_stockdtb.img \
  --from-native \
  --expect-version 'A90 Linux init 0.9.68 (v724)' \
  --verify-protocol auto
```

Rollback:

```bash
python3 scripts/revalidation/native_init_flash.py \
  stage3/boot_linux_v724.img \
  --expect-version 'A90 Linux init 0.9.68 (v724)' \
  --verify-protocol auto
```

## Evidence Summary

| Signal | Value |
| --- | --- |
| V773 local image sha256 | `0fcde6e76fd0de3d2b974aad20dcbbba714e5a81b9fccf5ea2b6a67bdc06f400` |
| V773 local image size | `53972992` bytes |
| adb recovery reached | yes, `RFCM90CFWXA recovery` |
| adb push to TWRP | pass |
| remote V773 image sha256 | matched local |
| boot partition prefix sha256 | matched V773 image |
| reboot request | `twrp reboot` accepted |
| post-reboot native verify | not reached |
| abort-time ADB state | initially no devices |
| abort-time bridge state | listener still present on `127.0.0.1:54321` |
| subsequent recovery state | TWRP recovery ADB available |
| rollback image sha256 | `4ca72f17aec64153d49def4ad42a49714d27bd833623aa9423220ce2181fc682` |
| rollback remote sha256 | matched local |
| rollback boot prefix sha256 | matched rollback image |
| rollback native verify | `version/status rc=0 status=ok` |
| recovered version | `A90 Linux init 0.9.68 (v724)` |
| recovered boot status | `BOOT OK shell 4.2s` |
| recovered selftest | `pass=11 warn=1 fail=0` |

## Interpretation

V774 proves that appending the stock v724 DTB tail fixed the missing-FDT artifact
defect found by V772, but did not make the Samsung OSRC-built instrumented
kernel live-boot compatible on this device.

The failure did not occur during image transfer or boot partition write. TWRP
pushed the V773 image, the remote hash matched, `dd` completed, and the boot
partition prefix readback matched the staged image. The failure occurs after the
bootloader attempts to boot the image: native init never reaches command verify.

This is a different failure shape from V771. V771 fell into Samsung Download
mode after flashing the no-DTB-tail image. V774 returned to or remained reachable
through recovery/TWRP after flashing the stock-DTB-tail image. The common
conclusion is still that the current custom OSRC kernel artifact is not safe for
further live retries without a new host-only incompatibility explanation.

## Safety State

- rollback completed: yes
- native health after rollback: pass
- Wi-Fi scan/connect: not executed
- credential use: not executed
- DHCP/routes/external ping: not executed
- diagnostic `A90V765` dmesg capture: not reached

## Do Not Retry

Do not flash the V770 image or the V773 stock-DTB-tail image again as-is. The
missing appended DTB tail has been eliminated as the sole blocker, so the next
gate must classify remaining custom-kernel boot incompatibility without another
live custom-kernel flash.

## Next

V775 should be host-only. Compare the known-good v724 stock kernel payload and
the V773 combined diagnostic payload for remaining bootloader/kernel acceptance
differences, including kernel provenance, image size and payload deltas,
toolchain string, Samsung production transforms, RKP/CFP metadata, RTIC/DEFEX
packaging assumptions, and boot image header constraints. Prefer stock-kernel
runtime observability paths over further custom-kernel flashes until V775
identifies a safer gate.
