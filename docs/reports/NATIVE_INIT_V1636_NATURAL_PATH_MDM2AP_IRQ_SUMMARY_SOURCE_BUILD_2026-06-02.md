# Native Init V1636 Natural-path MDM2AP IRQ Summary Source Build

## Summary

- Cycle: `V1636`
- Type: source/build-only rollbackable Wi-Fi test boot artifact
- Decision: `v1636-natural-path-mdm2ap-irq-summary-source-build-pass`
- Result: PASS
- Reason: built a natural-path test boot that records `mdm2ap_timing.*` IRQ deltas in the PID1 window result, independent of helper process exit
- Manifest: `tmp/wifi/v1636-natural-path-mdm2ap-irq-summary-test-boot/manifest.json`
- Boot image: `tmp/wifi/v1636-natural-path-mdm2ap-irq-summary-test-boot/boot_linux_v1636_natural_mdm2ap_irq_summary.img`
- Boot SHA256: `402da2b0599e135345c53d1514638daa49ade923d2079ac22ff9d4432fb990df`
- Init: `A90 Linux init 0.9.114 (v1636-natural-mdm2ap-irq-summary)`
- Init SHA256: `b0a871ca2711955bc33aee8986a8f667e6355f5f6b17df0b3f33300d1e46f8e6`
- Helper marker: `a90_android_execns_probe v303`
- Helper SHA256: `d58f637ce53b12f16f7143b388b20007553fe8d47bd6ed06379bde96a69c8798`

## Capture Contract

- Trigger remains natural `__subsystem_get(esoc0)` -> `mdm_subsys_powerup` only.
- PID1 provider window records GPIO1270/PON, GPIO135/AP2MDM, GPIO142/MDM2AP state samples, and now `mdm2ap_timing.gpio142_irq_delta` plus `mdm2ap_timing.errfatal_irq_delta` directly in the window result.
- The IRQ summary samples `/proc/interrupts` read-only for 120 samples at 50 ms after the provider micro-window, using initial counts collected immediately after provider detection.
- Helper result remains useful but is no longer the sole source of `mdm2ap_timing.*` evidence.
- No forced RC1 enumerate, fake ONLINE, PMIC/GPIO/GDSC/regulator write, eSoC notify/`BOOT_DONE`, PCI rescan, platform bind/unbind, Wi-Fi HAL, scan/connect, credentials, DHCP/routes, or external ping.

## Artifact Paths

- Log path: `/cache/native-init-wifi-test-boot-v1636.log`
- Summary path: `/cache/native-init-wifi-test-boot-v1636.summary`
- Helper result path: `/cache/native-init-wifi-test-boot-v1636-helper.result`
- Watcher result path: `/cache/native-init-wifi-test-boot-v1636-natural-watcher.result`
- Window result path: `/cache/native-init-wifi-test-boot-v1636-natural-window.result`

## Next

Run local artifact sanity first.  A later live handoff, if explicitly chosen, should flash only this V1636 image, collect the V1636 window result, roll back to `stage3/boot_linux_v724.img`, and classify using the stricter V1632 wrapper logic.
