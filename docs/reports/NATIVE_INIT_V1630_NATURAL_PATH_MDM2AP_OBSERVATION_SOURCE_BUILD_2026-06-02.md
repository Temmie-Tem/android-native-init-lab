# Native Init V1630 Natural-path MDM2AP Observation Source Build

## Summary

- Cycle: `V1630`
- Type: source/build-only rollbackable Wi-Fi test boot artifact
- Decision: `v1630-natural-path-mdm2ap-observation-source-build-pass`
- Result: PASS
- Reason: built the contract-defined natural `__subsystem_get(esoc0)` MDM2AP observation image without contacting or flashing the device
- Manifest: `tmp/wifi/v1630-natural-path-mdm2ap-observation-test-boot/manifest.json`
- Boot image: `tmp/wifi/v1630-natural-path-mdm2ap-observation-test-boot/boot_linux_v1630_natural_mdm2ap.img`
- Boot SHA256: `836b995cd9ffe7d1323a45327bc0e5bd56aa360ee623a6c82978bee54bb58c86`
- Init: `A90 Linux init 0.9.112 (v1630-natural-mdm2ap)`
- Init SHA256: `1e6706e295c8054432d9ead0e416049c162d51b7f0a572d43c50c2cd06cd16f6`
- Helper marker: `a90_android_execns_probe v303`
- Helper SHA256: `d58f637ce53b12f16f7143b388b20007553fe8d47bd6ed06379bde96a69c8798`

## Live Contract Encoded

- Trigger remains the natural PM-first / `mdm_helper` / `pm-service` route into `__subsystem_get(esoc0)` and `mdm_subsys_powerup`.
- The PID1 watcher is enabled only to detect the natural provider line; because the provider-trigger micro endpoint sampler is enabled, it samples rather than writing RC1 debugfs controls.
- Arms GPIO tracepoints and `msm_pil_event:pil_notif` to capture GPIO1270/PM8150L GPIO9 PON, GPIO135/AP2MDM, GPIO142/MDM2AP, GPIO141/errfatal, and `fw=esoc0`.
- Helper command keeps the existing `mdm2ap_timing.*` summary contract: GPIO142 IRQ delta, errfatal IRQ delta, PCIe/MHI/WLFW/`wlan0` context, and explicit safety-zero markers.
- No forced RC1 enumerate, fake ONLINE, PMIC/GPIO/GDSC/regulator write, eSoC notify/`BOOT_DONE`, PCI rescan, platform bind/unbind, Wi-Fi HAL, scan/connect, credentials, DHCP/routes, or external ping.

## Artifact Paths

- Log path: `/cache/native-init-wifi-test-boot-v1630.log`
- Summary path: `/cache/native-init-wifi-test-boot-v1630.summary`
- Watcher result path: `/cache/native-init-wifi-test-boot-v1630-natural-watcher.result`
- Window result path: `/cache/native-init-wifi-test-boot-v1630-natural-window.result`

## Verification

- Static init and helper verification passed.
- Ramdisk entries include `/init`, `/bin/a90_android_execns_probe`, `/bin/a90_tcpctl`, and `/bin/a90_rshell`.
- Boot marker verification passed, including the exact-provider PIL+GPIO tracepoint contract.
- Forbidden credential-like byte scan over init/helper/ramdisk/boot image passed.

## Next

V1631 should run local-only artifact sanity.  V1632 may then perform one rollbackable live handoff and assign exactly one label: `mdm2ap-responds`, `mdm2ap-silent-natural-path`, or `provider-did-not-trigger`.
