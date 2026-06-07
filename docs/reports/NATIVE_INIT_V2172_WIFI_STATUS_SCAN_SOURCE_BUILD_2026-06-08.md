# Native Init V2172 Wi-Fi Status/Scan Source Build

## Summary

- Candidate tag: `v2172-wifi-status-scan`
- Parent baseline: `v2169-transport-contract`
- Type: source/build-only test boot candidate.
- Decision: `v2172-wifi-status-scan-source-build-pass`
- Result: PASS
- Reason: V2172 keeps the V2169 transport contract and adds native-init `wifi status` plus bounded credential-free `wifi scan [delay_ms]`.
- Manifest: `workspace/private/builds/native-init/v2172-wifi-status-scan-test-boot/manifest.json`
- Base boot: `workspace/private/inputs/boot_images/boot_linux_v725_fasttransport.img`
- Boot image: `workspace/private/inputs/boot_images/boot_linux_v2172_wifi_status_scan.img`
- Boot SHA256: `c806de3fa5e22afa5a0a5c4040a8f40139e50e8b40e14bff98a6a30197de09f4`
- Live validation:
  `docs/reports/NATIVE_INIT_V2172_WIFI_STATUS_SCAN_LIVE_VALIDATION_2026-06-08.md`
- Boot SHA verification: source/build output and live flash/readback are both
  recorded before any promotion decision.
- Init: `A90 Linux init 0.9.249 (v2172-wifi-status-scan)`
- Helper marker: `a90_android_execns_probe helper-v427` (binary marker string: `a90_android_execns_probe v427`)
- Helper SHA256: `99bdd67f0cd2fcaf6557478a97f85d405a0de3d6b0858ea17b4d46d7ce162ca1`

## Included Route

- Helper runtime mode: `wifi-companion-wlan-pd-post-pm-lower-state-observer-start-only`
- Helper timeout: `75`
- Property root: `/mnt/sdext/a90/private-property-v317/v726/dev/__properties__`
- Preserved from V2169: V726 Wi-Fi lifecycle route, PID1 modem lifecycle holder, fasttransport ramdisk, and device-side `transport.contract=1` status fields.
- Property root intentionally reuses the verified V726 snapshot; no V2172 private-property tree is required on the SD workspace.
- Added: `wifi status` read-only status/UI primitive and `wifi scan [delay_ms]` direct nl80211 scan primitive.
- Not added: boot autoconnect, association, DHCP, route installation, external ping, or credential logging.

## Safety Scope

- No `/dev/subsys_esoc0`, forced RC1/case, PMIC/GPIO/GDSC/regulator write, PCI rescan, platform bind/unbind, fake ONLINE, or eSoC notify/BOOT_DONE path is included.
- The live validation must remain credential-free, scan-only, and rollbackable to `workspace/private/inputs/boot_images/boot_linux_v2169_transport_contract.img`.
