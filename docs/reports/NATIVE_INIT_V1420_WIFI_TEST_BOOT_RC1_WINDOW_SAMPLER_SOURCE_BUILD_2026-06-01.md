# Native Init V1420 Wi-Fi Test Boot RC1 Window Sampler Source Build

## Summary

- Cycle: `V1420`
- Type: source/build-only test boot artifact gate
- Decision: `v1420-wifi-test-boot-rc1-window-sampler-source-build-pass`
- Result: PASS
- Artifact:
  - `tmp/wifi/v1420-wifi-test-boot-rc1-window-sampler/boot_linux_v1420_wifi_test.img`
  - `tmp/wifi/v1420-wifi-test-boot-rc1-window-sampler/manifest.json`

## Build Identity

- Native init marker: `A90 Linux init 0.9.76 (v1420-wifitest)`
- Helper: `tmp/wifi/v1420-wifi-test-boot-rc1-window-sampler/a90_android_execns_probe_v286`
- Init SHA256: `2bbc75f64f13dcf5ca6800284d408218459965a6c4951cc90e1bbf394b914011`
- Helper SHA256: `e5fc81a5becb2c6e6efd2ca026800560ed9e0e72a692f0fbb07861cf26d5380f`
- Ramdisk SHA256: `636eb8f5016f7893f5f09d94dd610cd85b68a134d90634c9e66b283ae4fe0436`
- Boot image SHA256: `a938d3f3dfdfc85d1818ce9ba212c32e5bb9290144fa193151d2f8115bc0658d`

## Change

V1420 preserves the V1414 delayed corrected-RC1 path and adds a read-only PID1
RC1-window sampler. The sampler is armed when the PID1 kmsg watcher observes
the first `esoc0`/`mdm_subsys_powerup` trigger, records `pre_delay`, sleeps the
existing `250ms`, forks a child sampler immediately before the synchronous
corrected RC1 write, and records:

- `pre_rc1`
- `post_rc1_50ms`
- `post_rc1_150ms`
- `post_rc1_500ms`

The sampler reads only:

- `/proc/interrupts`
- `/sys/kernel/debug/gpio`
- `/sys/kernel/debug/pinctrl/3000000.pinctrl/pins`
- `/sys/kernel/debug/pinctrl/3000000.pinctrl/pinmux-pins`
- `/sys/kernel/debug/pinctrl/3000000.pinctrl/pinconf-pins`

The private result path is:

- `/cache/native-init-wifi-test-boot-v1420-rc1-window.result`

## Contract

Manifest `wifi_test` confirms:

- `label`: `v1420`
- `pid1_rc1_watcher`: `true`
- `rc1_watcher_delay_ms`: `250`
- `rc1_window_sampler`: `true`
- `rc1_window_result`: `/cache/native-init-wifi-test-boot-v1420-rc1-window.result`
- `mount_debugfs`: `true`
- `fresh_log`: `true`
- `supervise_helper`: `true`

## Safety Scope

This was a host/source/build-only cycle. It did not run live device commands,
flash or reboot the device, write partitions, handle credentials, scan/connect
Wi-Fi, start Wi-Fi HAL, run DHCP/routes, perform external ping, write
PMIC/GPIO/GDSC controls, spoof eSoC notify/`BOOT_DONE`, or add any pci-msm
`case` write beyond the existing corrected RC1 path in the generated
rollbackable test artifact.

## Validation

- Static aarch64 init and helper artifacts were produced.
- `readelf -d` showed no interpreter or dynamic dependency entries for the
  staged init/helper binaries.
- Boot image marker verification passed through the build script.
- Manifest was written with V1420 identity, hashes, and sampler contract.

## Next Gate

V1421 should sanity-check this exact artifact before any live handoff. V1422 may
then run a rollbackable live handoff if V1421 passes, with rollback to v724 and
selftest verification required after the test.
