# Native Init V726 Wi-Fi Lifecycle Source Build

## Summary

- Cycle: `V726`
- Type: source/build-only baseline candidate.
- Decision: `v726-wifi-lifecycle-source-build-pass`
- Result: PASS
- Reason: V726 combines the V2168 QCACLD firmware_class feeder path with a PID1-owned `/dev/subsys_modem` lifecycle holder, while preserving the V725 fasttransport ramdisk contract.
- Manifest: `tmp/wifi/v726-wifi-lifecycle-test-boot/manifest.json`
- Base boot: `stage3/boot_linux_v725_fasttransport.img`
- Boot image: `stage3/boot_linux_v726_wifi_lifecycle.img`
- Boot SHA256: `2a8d3f946068d81b17882153058db06a6d795592a08ec2bd9057f0e6df2b501a`
- Init: `A90 Linux init 0.9.246 (v726-wifi-lifecycle)`
- Helper marker: `a90_android_execns_probe v427`
- Helper SHA256: `99bdd67f0cd2fcaf6557478a97f85d405a0de3d6b0858ea17b4d46d7ce162ca1`

## Included Route

- Helper runtime mode: `wifi-companion-wlan-pd-post-pm-lower-state-observer-start-only`
- Helper timeout: `75`
- Property root: `/mnt/sdext/a90/private-property-v317/v726/dev/__properties__`
- Kept from V2168: firmware mounts, `firmware_class.path` vendor path, RFS bridges, post-FW_READY `boot_wlan`, and bounded QCACLD firmware_class feeder.
- Added: PID1 starts a persistent internal-modem lifecycle owner that opens only `/dev/subsys_modem` and records `/cache/native-init-wifi-lifecycle-modem-owner.*`.

## Safety Scope

- No `/dev/subsys_esoc0`, forced RC1/case, PMIC/GPIO/GDSC/regulator write, PCI rescan, platform bind/unbind, fake ONLINE, or eSoC notify/BOOT_DONE path is included.
- The live validation remains credential-redacted and rollbackable to `stage3/boot_linux_v725_fasttransport.img`.
