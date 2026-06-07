# Native Init V2169 Transport Contract Source Build

## Summary

- Baseline tag: `v2169-transport-contract`
- Type: source/build transport-contract baseline.
- Decision: `v2169-transport-contract-source-build-pass`
- Result: PASS
- Reason: the V2169 boot/init candidate keeps the V726 Wi-Fi lifecycle route and enables the native-init status transport contract consumed by the host bridge selector.
- Manifest: `workspace/private/builds/native-init/v2169-transport-contract-test-boot/manifest.json`
- Base boot: `workspace/private/inputs/boot_images/boot_linux_v725_fasttransport.img`
- Boot image: `workspace/private/inputs/boot_images/boot_linux_v2169_transport_contract.img`
- Boot SHA256: `190b93d0741a6eeba17913c940f3bb398fed765f38532d5e0009840112166d6d`
- Live validation: `docs/reports/NATIVE_INIT_V2169_TRANSPORT_CONTRACT_LIVE_VALIDATION_2026-06-08.md`
- Boot SHA verification: source/build output; flash/readback/selftest verification is recorded in the live validation report.
- Init: `A90 Linux init 0.9.247 (v2169-transport-contract)`
- Helper marker: `a90_android_execns_probe helper-v427` (binary marker string: `a90_android_execns_probe v427`)
- Helper SHA256: `99bdd67f0cd2fcaf6557478a97f85d405a0de3d6b0858ea17b4d46d7ce162ca1`
- Version axes: `v2169-transport-contract` is the promoted boot/init baseline tag; it is built from the V726 Wi-Fi lifecycle route and helper marker `helper-v427`.

## Included Route

- Helper runtime mode: `wifi-companion-wlan-pd-post-pm-lower-state-observer-start-only`
- Helper timeout: `75`
- Property root: `/mnt/sdext/a90/private-property-v317/v2169/dev/__properties__`
- Preserved from V726: V2168 QCACLD firmware_class feeder path, PID1-owned `/dev/subsys_modem` lifecycle holder, Wi-Fi HUD/runtime sampler, and V725 fasttransport ramdisk contract.
- Added: native-init `status` emits `transport.contract=1` plus serial/NCM/tcpctl/preferred/reason fields for the host selector.
- Behavior scope: no Wi-Fi bring-up path change beyond status observability.

## Safety Scope

- No `/dev/subsys_esoc0`, forced RC1/case, PMIC/GPIO/GDSC/regulator write, PCI rescan, platform bind/unbind, fake ONLINE, or eSoC notify/BOOT_DONE path is included.
- The live validation remains credential-redacted and rollbackable to `workspace/private/inputs/boot_images/boot_linux_v726_wifi_lifecycle.img`.
