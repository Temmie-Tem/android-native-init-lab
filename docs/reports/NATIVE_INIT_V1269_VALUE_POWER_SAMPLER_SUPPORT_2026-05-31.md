# V1269 AP2MDM Value/Power Sampler Support

## Result

- decision: `v1269-value-power-sampler-build-pass`
- evidence: `tmp/wifi/v1269-execns-helper-v265-build/manifest.json`
- helper: `a90_android_execns_probe v265`
- helper SHA256: `97ffa91a1aa7b8f4ab2c3a74716ae5664c703e98fe19a322351b1277fbd282b2`
- scope: source/build-only; no deploy, live command, GPIO line request, PMIC write, eSoC ioctl, Wi-Fi action, flash, boot image write, or partition write

## Changes

- Bumped `stage3/linux_init/helpers/a90_android_execns_probe.c` to helper v265.
- Extended the existing late `per_proxy` / PM-service response sampler with
  read-only debugfs GPIO and pinconf state:
  - `/sys/kernel/debug/gpio` line for global GPIO1270 / `AP2MDM_SOFT_RESET` if
    present.
  - `/sys/kernel/debug/gpio` lines for TLMM GPIO135 and GPIO142 if present.
  - PMIC GPIO9 pinconf from PM8150L pinctrl debugfs.
  - TLMM GPIO135/GPIO142 pinconf from TLMM pinctrl debugfs.
- Kept the existing GPIO142 IRQ, `mdm3`, PCI/MHI, MHI pipe, `wlan0`, and PCIe
  GDSC samples.

## Validation

- Static aarch64 build passed through
  `scripts/revalidation/build_android_execns_probe_helper.sh`.
- `readelf -l` shows no `INTERP` segment.
- `readelf -d` reports no dynamic section.
- Binary strings include helper v265 marker and the new `*_debugfs_*` /
  `*_pinconf_*` response-sample fields.

## Next

V1270 should deploy helper v265 only.  V1271 should run the bounded value/power
observer using the same late `per_proxy` / PM-service `/dev/subsys_esoc0`
response window.
