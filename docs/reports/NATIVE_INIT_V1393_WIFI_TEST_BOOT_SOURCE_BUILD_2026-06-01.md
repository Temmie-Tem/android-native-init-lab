# Native Init V1393 Wi-Fi Test Boot Source Build

## Summary

- Cycle: `V1393`
- Type: source/build-only
- Decision: `v1393-wifi-test-boot-source-build-pass`
- Builder: `scripts/revalidation/build_native_init_wifi_test_boot_v1393.py`
- Base boot image: `stage3/boot_linux_v724.img`
- Test native identity: `A90 Linux init 0.9.69 (v1393-wifitest)`
- Staged manifest:
  `tmp/wifi/v1393-wifi-test-boot/manifest.json`
- Staged boot image:
  `tmp/wifi/v1393-wifi-test-boot/boot_linux_v1393_wifi_test.img`

## Build Outputs

| artifact | path | sha256 |
| --- | --- | --- |
| PID1 | `tmp/wifi/v1393-wifi-test-boot/init_v1393_wifi_test` | `047d01bce2f60974a9e134c5affe062ed32f8ca62fc285231d58f238f030420a` |
| helper | `tmp/wifi/v1393-wifi-test-boot/a90_android_execns_probe_v286` | `e5fc81a5becb2c6e6efd2ca026800560ed9e0e72a692f0fbb07861cf26d5380f` |
| ramdisk | `tmp/wifi/v1393-wifi-test-boot/ramdisk_v1393_wifi_test.cpio` | `6f2e123962011d9b9bece706146138de9e04ea2eb61d17ae693326fd9f4aaa2e` |
| boot image | `tmp/wifi/v1393-wifi-test-boot/boot_linux_v1393_wifi_test.img` | `ebb4097db71dee77cdf7a26b671a1535a8e0afe1e53b4a23400af518d4d63048` |

## Implemented Changes

- `stage3/linux_init/a90_config.h` now permits build-time overrides for
  `INIT_VERSION`, `INIT_BUILD`, `INIT_CREATOR`, and `INIT_BANNER`.
- `stage3/linux_init/v724/90_main.inc.c` now has a compile-time
  `A90_WIFI_TEST_BOOT` hook.
- The V1393 test hook runs before USB ACM console attach and before late
  interactive services.
- The hook invokes the ramdisk helper path `/bin/a90_android_execns_probe`.
- The helper is bundled into the V1393 test ramdisk and verified as
  `a90_android_execns_probe v286`.
- The test hook writes private evidence to
  `/cache/native-init-wifi-test-boot-v1393.log` and PID metadata to
  `/cache/native-init-wifi-test-boot-v1393.pid`.
- A runtime disable flag is available at
  `/cache/native-init-wifi-test-boot-v1393.disable`.

## Safety Scope

This was a source/build-only gate.

- No device command was run.
- No flash, reboot, boot partition write, or partition write was performed.
- No Wi-Fi HAL, scan/connect, credential handling, DHCP/routes, or external
  ping was performed.
- No PMIC/GPIO/GDSC direct write or blind eSoC notify/`BOOT_DONE` spoof was
  performed.
- The staged boot image and ramdisk were written with private mode `0600`.
- The builder checks expected markers, static aarch64 binaries, required
  ramdisk entries, and forbidden credential-like byte patterns.

## Build Verification

The builder completed:

- rebuilt the helper from source
- verified helper SHA256 and marker
- compiled static aarch64 PID1
- verified no `INTERP` segment and no dynamic section for PID1/helper
- packed ramdisk with `/init`, `/bin/a90_android_execns_probe`, `/bin/a90_tcpctl`,
  and `/bin/a90_rshell`
- repacked a boot image using v724 header/kernel metadata and the V1393 ramdisk
- verified boot image markers:
  - `A90 Linux init 0.9.69 (v1393-wifitest)`
  - `a90_android_execns_probe v286`
  - `A90v1393: wifi test boot armed`
  - `native-init-wifi-test-boot-v1393`
  - `/bin/a90_android_execns_probe`

## Decision

V1393 passes source/build-only. The next gate is V1394 local artifact sanity
verification, then V1395 bounded live handoff only if V1394 passes and the
rollback target is explicitly named as `stage3/boot_linux_v724.img`.
