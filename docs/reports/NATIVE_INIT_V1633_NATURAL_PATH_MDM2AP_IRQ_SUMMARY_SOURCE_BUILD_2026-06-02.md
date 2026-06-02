# Native Init V1633 Natural-path MDM2AP IRQ Summary Source Build

## Summary

- Cycle: `V1633`
- Type: source/build-only rollbackable Wi-Fi test boot artifact
- Decision: `v1633-natural-path-mdm2ap-irq-summary-source-build-pass`
- Result: PASS
- Reason: built a natural-path test boot that records `mdm2ap_timing.*` IRQ deltas in the PID1 window result, independent of helper process exit
- Manifest: `tmp/wifi/v1633-natural-path-mdm2ap-irq-summary-test-boot/manifest.json`
- Boot image: `tmp/wifi/v1633-natural-path-mdm2ap-irq-summary-test-boot/boot_linux_v1633_natural_mdm2ap_irq_summary.img`
- Boot SHA256: `cec663be484b15245200e2409cdd863f7976b204e064613295546b8a9a316691`
- Init: `A90 Linux init 0.9.113 (v1633-natural-mdm2ap-irq-summary)`
- Init SHA256: `27bbccbcd96c94aab222e1174d8357c4aea5fd45d041bbb07eb08c233b0481f9`
- Helper marker: `a90_android_execns_probe v303`
- Helper SHA256: `d58f637ce53b12f16f7143b388b20007553fe8d47bd6ed06379bde96a69c8798`

## Capture Contract

- Trigger remains natural `__subsystem_get(esoc0)` -> `mdm_subsys_powerup` only.
- PID1 provider window records GPIO1270/PON, GPIO135/AP2MDM, GPIO142/MDM2AP state samples, and now `mdm2ap_timing.gpio142_irq_delta` plus `mdm2ap_timing.errfatal_irq_delta` directly in the window result.
- The IRQ summary samples `/proc/interrupts` read-only for 120 samples at 50 ms after the provider micro-window, using initial counts collected immediately after provider detection.
- Helper result remains useful but is no longer the sole source of `mdm2ap_timing.*` evidence.
- No forced RC1 enumerate, fake ONLINE, PMIC/GPIO/GDSC/regulator write, eSoC notify/`BOOT_DONE`, PCI rescan, platform bind/unbind, Wi-Fi HAL, scan/connect, credentials, DHCP/routes, or external ping.

## Artifact Paths

- Log path: `/cache/native-init-wifi-test-boot-v1633.log`
- Summary path: `/cache/native-init-wifi-test-boot-v1633.summary`
- Helper result path: `/cache/native-init-wifi-test-boot-v1633-helper.result`
- Watcher result path: `/cache/native-init-wifi-test-boot-v1633-natural-watcher.result`
- Window result path: `/cache/native-init-wifi-test-boot-v1633-natural-window.result`

## Next

Run local artifact sanity first.  A later live handoff, if explicitly chosen, should flash only this V1633 image, collect the V1633 window result, roll back to `stage3/boot_linux_v724.img`, and classify using the stricter V1632 wrapper logic.
