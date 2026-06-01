# Native Init V1411 Wi-Fi Test Boot Kmsg Fallback Source Build

## Summary

- Cycle: `V1411`
- Type: source/build-only rollbackable Wi-Fi test boot artifact
- Decision: `v1411-wifi-test-boot-kmsg-fallback-source-build-pass`
- Result: PASS for local source/build; no device command or flash executed
- Reason: V1410 showed the PID1 RC1 watcher failed because `/dev/kmsg` is absent; V1411 adds `/proc/kmsg` fallback and drains existing records before watching future `esoc0`/powerup markers.
- Evidence: `tmp/wifi/v1411-wifi-test-boot-kmsg-fallback`

## Artifact

- Boot image: `tmp/wifi/v1411-wifi-test-boot-kmsg-fallback/boot_linux_v1411_wifi_test.img`
- Init marker: `A90 Linux init 0.9.74 (v1411-wifitest)`
- Init SHA256: `0026a4b5909ade1f7eeef3b31a303228316b54b0d9beba30def287255d08674d`
- Boot SHA256: `1985b680df1ab486f60723c4a3776842e1de7ee0c667caefc6b31b6c18906c62`
- Helper marker: `a90_android_execns_probe v286`

## Implementation

- PID1 watcher first attempts `/dev/kmsg`.
- If `/dev/kmsg` is absent, it falls back to `/proc/kmsg`.
- On `/proc/kmsg`, it drains existing records until `EAGAIN` before watching future marker lines.
- Result strings now include the kmsg source path on trigger/timeout/failure.
- Corrected RC1 is still limited to `rc_sel=2` plus `case=11`; no PMIC/GPIO/GDSC direct write was added.

## Verification

- `python3 -m py_compile scripts/revalidation/build_native_init_wifi_test_boot_v1393.py scripts/revalidation/build_native_init_wifi_test_boot_v1411.py`
- `python3 scripts/revalidation/build_native_init_wifi_test_boot_v1411.py`
- Static init check: `readelf -d` reports no dynamic section and no `INTERP` segment.
- Boot image strings contain the V1411 marker, `/dev/kmsg`, `/proc/kmsg`, PID1 watcher strings, and `/sys/kernel/debug/pci-msm/rc_sel`.
- Build script scanned generated init/helper/ramdisk/boot artifacts for credential-like bytes and passed.

## Safety Scope

This cycle is source/build-only. It executes no device command, flash,
partition write, Wi-Fi scan/connect, credential handling, DHCP/routes, external
ping, PMIC/GPIO/GDSC direct write, or blind eSoC notify/`BOOT_DONE` spoof.

## Next

V1412 should independently sanity-check the exact V1411 manifest and boot image
before any rollbackable live handoff. A later live gate may flash only the V1411
test image, collect the V1411 log/summary/RC1 watcher result/dmesg/`wlan0`
state, and roll back to `stage3/boot_linux_v724.img`.
