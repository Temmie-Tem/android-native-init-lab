# Native Init V2187 Screenapp UI Validation Source Build

## Summary

- Candidate tag: `v2187-screenapp-ui-validation`
- Parent baseline: `v2186-wifi-ui-polish`
- Type: source/build-only test boot candidate.
- Decision: `v2187-screenapp-ui-validation-source-build-pass`
- Result: PASS
- Reason: V2187 keeps the promoted V2186 Wi-Fi UI baseline and adds a bounded `screenapp` command for reproducible network screen validation.
- Manifest: `workspace/private/builds/native-init/v2187-screenapp-ui-validation-boot/manifest.json`
- Base boot: `workspace/private/inputs/boot_images/boot_linux_v725_fasttransport.img`
- Boot image: `workspace/private/inputs/boot_images/boot_linux_v2187_screenapp_ui_validation.img`
- Boot SHA256: `0422f854b3e78d36e225012fd89a53016067155e200291d067ff7d71f32091ca`
- Boot SHA verification: source/build output only; live flash/readback/selftest must be recorded separately before promotion.
- Init: `A90 Linux init 0.9.259 (v2187-screenapp-ui-validation)`
- Helper marker: `a90_android_execns_probe helper-v427` (binary marker string: `a90_android_execns_probe v427`)
- Helper SHA256: `99bdd67f0cd2fcaf6557478a97f85d405a0de3d6b0858ea17b4d46d7ce162ca1`

## Included Route

- Helper runtime mode: `wifi-companion-wlan-pd-post-pm-lower-state-observer-start-only`
- Helper timeout: `75`
- Property root: `/mnt/sdext/a90/private-property-v317/v726/dev/__properties__`
- Added: `screenapp [network|wifi-status|wifi-profiles|wifi-scan|wifi-ping]` direct display validation command.
- Preserved: V2186 `NETWORK > WIFI STATUS` labels and redacted WPA/RSSI/link/frequency metrics.
- Preserved: V2186 Wi-Fi UI polish, V2185 network ping menu/CLI, V2178 profile/autoconnect commands, and V2169 transport contract.

## Safety Scope

- `screenapp wifi-status` and `screenapp wifi-profiles` are read-only display validation paths.
- Wi-Fi scan is bounded and credential-free; it does not associate, run DHCP, install routes/DNS, or ping.
- `screenapp wifi-ping` is explicit user/test action only and uses the same bounded ping collector as `NETWORK > PING TEST`.
- Gateway target is redacted in command output; public reports must redact private LAN details.
- Scan result SSID/frequency/RSSI/security is rendered on screen only; raw BSSID/SSID results are not written to serial logs or public artifacts.
- No `/dev/subsys_esoc0`, forced RC1/case, PMIC/GPIO/GDSC/regulator write, PCI rescan, platform bind/unbind, fake ONLINE, or eSoC notify/BOOT_DONE path is included.
