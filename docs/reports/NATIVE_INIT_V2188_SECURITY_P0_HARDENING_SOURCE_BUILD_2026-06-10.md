# Native Init V2188 Security P0 Hardening Source Build

## Summary

- Candidate tag: `v2188-security-p0-hardening`
- Parent baseline: `v2187-screenapp-ui-validation`
- Type: source/build-only test boot candidate.
- Decision: `v2188-security-p0-hardening-source-build-pass`
- Result: PASS
- Reason: V2188 preserves the V2187 screenapp/UI baseline and adds P0 hardening for Wi-Fi root-exec paths and flash artifact identity.
- Manifest: `workspace/private/builds/native-init/v2188-security-p0-hardening-boot/manifest.json`
- Base boot: `workspace/private/inputs/boot_images/boot_linux_v725_fasttransport.img`
- Boot image: `workspace/private/inputs/boot_images/boot_linux_v2188_security_p0_hardening.img`
- Boot SHA256: `0329f977077009b9cdce9514ac940bd9c7fe828db712b82f2c264341f62969be`
- Boot SHA verification: source/build output only; live flash/readback/selftest must be recorded separately before promotion.
- Init: `A90 Linux init 0.9.260 (v2188-security-p0-hardening)`
- Helper marker: `a90_android_execns_probe helper-v427` (binary marker string: `a90_android_execns_probe v427`)
- Helper SHA256: `99bdd67f0cd2fcaf6557478a97f85d405a0de3d6b0858ea17b4d46d7ce162ca1`

## Included Route

- Helper runtime mode: `wifi-companion-wlan-pd-post-pm-lower-state-observer-start-only`
- Helper timeout: `75`
- Property root: `/mnt/sdext/a90/private-property-v317/v726/dev/__properties__`
- Preserved: V2187 `screenapp [network|wifi-status|wifi-profiles|wifi-scan|wifi-ping]` direct display validation command.
- Added: `/cache/a90-wifi` remains root-owned; only `/cache/a90-wifi/sockets` is Wi-Fi UID/GID writable.
- Added: root-executed Wi-Fi artifacts are checked for non-symlink regular-file/root-owned/not group-or-world-writable state before exec.
- Added: flash handoff tooling requires caller-pinned boot image SHA256 and selftest verification also checks expected version.

## Safety Scope

- This source build does not initiate Wi-Fi connect, DHCP, route/DNS changes, or ping.
- Runtime validation should flash this image with `native_init_flash.py --expect-sha256` and then run selftest/status plus bounded Wi-Fi smoke.
- No `/dev/subsys_esoc0`, forced RC1/case, PMIC/GPIO/GDSC/regulator write, PCI rescan, platform bind/unbind, fake ONLINE, or eSoC notify/BOOT_DONE path is included.
