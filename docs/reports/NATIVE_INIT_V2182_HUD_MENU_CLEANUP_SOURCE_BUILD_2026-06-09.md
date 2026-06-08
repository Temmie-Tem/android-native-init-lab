# Native Init V2182 HUD/Menu Cleanup Source Build

## Summary

- Baseline tag: `v2182-hud-menu-cleanup`
- Parent baseline: `v2178-wifi-profile-autoconnect`
- Type: source/build baseline candidate.
- Decision: `v2182-hud-menu-cleanup-source-build-pass`
- Result: PASS
- Reason: V2182 keeps the V2178 Wi-Fi profile/autoconnect baseline and adds HUD storage/Wi-Fi glance improvements, shared HUD layout geometry, and menu navigation cleanup.
- Manifest: `workspace/private/builds/native-init/v2182-hud-menu-cleanup-test-boot/manifest.json`
- Base boot: `workspace/private/inputs/boot_images/boot_linux_v725_fasttransport.img`
- Boot image: `workspace/private/inputs/boot_images/boot_linux_v2182_hud_menu_cleanup.img`
- Boot SHA256: `8e3e16f68d019ef5f56d2246ddcc7dbf14aa5ae08b40a0b983688812d792f839`
- Init: `A90 Linux init 0.9.255 (v2182-hud-menu-cleanup)`
- Helper marker: `a90_android_execns_probe helper-v427` (binary marker string: `a90_android_execns_probe v427`)
- Helper SHA256: `99bdd67f0cd2fcaf6557478a97f85d405a0de3d6b0858ea17b4d46d7ce162ca1`

## Included Route

- Helper runtime mode: `wifi-companion-wlan-pd-post-pm-lower-state-observer-start-only`
- Helper timeout: `75`
- Property root: `/mnt/sdext/a90/private-property-v317/v726/dev/__properties__`
- Preserved from V2178: Wi-Fi profile inventory, explicit autoconnect controls, boot-background autoconnect worker, V2176 connect/DHCP/cleanup route, V726 lifecycle route, and transport contract fields.
- Added: HUD storage free/free-percent/read-write-rate line and Wi-Fi state/profile/decision surfacing.
- Added: shared HUD status geometry so menu/log/preview layouts follow the six-row HUD height.
- Added: menu cleanup that removes duplicate STATUS/LIVE STATUS navigation and clarifies USB NET STATUS versus Wi-Fi HUD status.

## Safety Scope

- Raw SSID/PSK remain private-only; HUD consumes redacted runtime/autoconnect summaries.
- No scan/connect/DHCP/ping is initiated by this UI baseline change.
- No `/dev/subsys_esoc0`, forced RC1/case, PMIC/GPIO/GDSC/regulator write, PCI rescan, platform bind/unbind, fake ONLINE, or eSoC notify/BOOT_DONE path is included.
