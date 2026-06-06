# Native Init V2168 QCACLD Firmware Class Fasttransport Source Build

## Summary

- Cycle: `V2168`
- Type: source/build-only v725-fasttransport based QCACLD firmware_class feeder test boot.
- Decision: `v2168-qcacld-fwclass-fasttransport-source-build-pass`
- Result: PASS
- Reason: V2168 keeps the V2137 QCACLD firmware_class feeder route but bumps the test boot above v725 and adds the v725 fasttransport ramdisk/PID1 transport contract.
- Manifest: `tmp/wifi/v2168-qcacld-fwclass-fasttransport-test-boot/manifest.json`
- Base boot: `stage3/boot_linux_v725_fasttransport.img`
- Boot image: `tmp/wifi/v2168-qcacld-fwclass-fasttransport-test-boot/boot_linux_v2168_qcacld_fwclass_fasttransport.img`
- Boot SHA256: `c68fc938a7ff453b5a0850fea988fc80dac7c5fbe59c27e4ecb5d2fc4d6a0e9f`
- Init: `A90 Linux init 0.9.245 (v2168-qcacld-fwclass-fasttransport)`
- Helper marker: `a90_android_execns_probe v427`
- Helper SHA256: `f99c65676762e4a17c14efa9ff14770db77741d8ff9078f1690581298aebfb16`

## Transport Baseline

- Test boot version is `0.9.245`, above `0.9.244 (v725-fasttransport)`.
- PID1 uses `/bin/a90_usbnet`, `/bin/a90_tcpctl`, `/bin/toybox`, and `/bin/busybox` fasttransport paths.
- Ramdisk includes `a90_usbnet`, `a90_tcpctl`, `toybox`, `busybox`, and the QCACLD feeder helper.

## Wi-Fi Route

- Helper runtime mode: `wifi-companion-wlan-pd-post-pm-lower-state-observer-start-only`
- Helper timeout: `75`
- Property root: `/mnt/sdext/a90/private-property-v317/v2168/dev/__properties__`
- Kept from V2137: firmware mounts, `firmware_class.path` vendor path, RFS bridges, post-FW_READY `boot_wlan`, firmware_class sampler, and bounded userspace feeder for observed QCACLD request nodes.

## Safety Scope

This build script performs host-side source/build work only. The eventual handoff remains rollbackable to `stage3/boot_linux_v725_fasttransport.img`.
