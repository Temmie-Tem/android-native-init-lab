# Native Init V726 Wi-Fi Lifecycle Source Build

## Summary

- Baseline tag: `v726-wifi-lifecycle`
- Type: source/build-only baseline candidate.
- Decision: `v726-wifi-lifecycle-source-build-pass`
- Result: PASS
- Reason: the V726 boot/init baseline incorporates the validation-route V2168 QCACLD firmware_class feeder path with a PID1-owned `/dev/subsys_modem` lifecycle holder, while preserving the V725 fasttransport ramdisk contract.
- Manifest: `workspace/private/builds/native-init/v726-wifi-lifecycle-test-boot/manifest.json`
- Base boot: `workspace/private/inputs/boot_images/boot_linux_v725_fasttransport.img`
- Boot image: `workspace/private/inputs/boot_images/boot_linux_v726_wifi_lifecycle.img`
- Boot SHA256: `6b34aac93d4fa6d5b40355b9e13b2c1ae847c24a3685d84b0d1cd78751351d40`
- Boot SHA verification: source/build output; flash/readback/selftest verification is recorded in the V726 baseline promotion report.
- Init: `A90 Linux init 0.9.246 (v726-wifi-lifecycle)`
- Helper marker: `a90_android_execns_probe helper-v427` (binary marker string: `a90_android_execns_probe v427`)
- Helper SHA256: `99bdd67f0cd2fcaf6557478a97f85d405a0de3d6b0858ea17b4d46d7ce162ca1`
- Version axes: `v726-wifi-lifecycle` is the boot/init baseline tag; `helper-v427` is the helper binary marker; `V2167`/`V2168` are validation-route/report identifiers, not newer boot baselines.

## Included Route

- Helper runtime mode: `wifi-companion-wlan-pd-post-pm-lower-state-observer-start-only`
- Helper timeout: `75`
- Property root: `/mnt/sdext/a90/private-property-v317/v726/dev/__properties__`
- Kept from validation route V2168: firmware mounts, `firmware_class.path` vendor path, RFS bridges, post-FW_READY `boot_wlan`, and bounded QCACLD firmware_class feeder.
- Added: PID1 starts a persistent internal-modem lifecycle owner that opens only `/dev/subsys_modem` and records `/cache/native-init-wifi-lifecycle-modem-owner.*`.
- Added: PID1 starts a lightweight Wi-Fi runtime summary sampler at `/cache/native-init-wifi-runtime.summary`; the HUD consumes it for Wi-Fi MAC/IP/RX/TX state and optional SSID/RSSI/link-speed labels.

## Safety Scope

- No `/dev/subsys_esoc0`, forced RC1/case, PMIC/GPIO/GDSC/regulator write, PCI rescan, platform bind/unbind, fake ONLINE, or eSoC notify/BOOT_DONE path is included.
- The live validation remains credential-redacted and rollbackable to `workspace/private/inputs/boot_images/boot_linux_v725_fasttransport.img`.
