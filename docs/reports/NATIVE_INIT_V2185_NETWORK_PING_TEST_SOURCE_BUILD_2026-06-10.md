# Native Init V2185 Network Ping Test Source Build

## Summary

- Candidate tag: `v2185-network-ping-test`
- Parent baseline: `v2182-hud-menu-cleanup`
- Type: source/build-only test boot candidate.
- Decision: `v2185-network-ping-test-source-build-pass`
- Result: PASS
- Reason: V2185 keeps the V2182 HUD/menu baseline and adds network menu Wi-Fi ping test screen and bounded ping primitive.
- Manifest: `workspace/private/builds/native-init/v2185-network-ping-test-boot/manifest.json`
- Base boot: `workspace/private/inputs/boot_images/boot_linux_v725_fasttransport.img`
- Boot image: `workspace/private/inputs/boot_images/boot_linux_v2185_network_ping_test.img`
- Boot SHA256: `3ab13707c4ad93cb0b23c26174407be9a0ca30460fce879131ba6bea0df253b7`
- Boot SHA verification: source/build output only; live flash/readback/selftest must be recorded separately before promotion.
- Init: `A90 Linux init 0.9.257 (v2185-network-ping-test)`
- Helper marker: `a90_android_execns_probe helper-v427` (binary marker string: `a90_android_execns_probe v427`)
- Helper SHA256: `99bdd67f0cd2fcaf6557478a97f85d405a0de3d6b0858ea17b4d46d7ce162ca1`

## Included Route

- Helper runtime mode: `wifi-companion-wlan-pd-post-pm-lower-state-observer-start-only`
- Helper timeout: `75`
- Property root: `/mnt/sdext/a90/private-property-v317/v726/dev/__properties__`
- Added: `NETWORK > WIFI STATUS` read-only wlan0/link/IP/autoconnect screen.
- Added: `NETWORK > WIFI PROFILES` redacted profile/autoconnect inventory screen.
- Added: `NETWORK > WIFI SCAN` one-shot bounded nl80211 scan screen.
- Added: `NETWORK > PING TEST` explicit bounded gateway plus `1.1.1.1` ping screen.
- Added: `wifi ping [gateway|internet|all]` CLI primitive for dev/test validation.
- Preserved: V2182 HUD storage/Wi-Fi glance, V2178 profile/autoconnect commands, and V2169 transport contract.

## Safety Scope

- Wi-Fi status and profile screens are read-only.
- Wi-Fi scan is bounded and credential-free; it does not associate, run DHCP, install routes/DNS, or ping.
- Wi-Fi ping is explicit user/test action only; it does not connect, run DHCP, change routes, or read credentials.
- Gateway target is redacted in command output; public reports must redact private LAN details.
- Scan result SSID/frequency/RSSI/security is rendered on screen only; raw BSSID/SSID results are not written to serial logs or public artifacts.
- No `/dev/subsys_esoc0`, forced RC1/case, PMIC/GPIO/GDSC/regulator write, PCI rescan, platform bind/unbind, fake ONLINE, or eSoC notify/BOOT_DONE path is included.
