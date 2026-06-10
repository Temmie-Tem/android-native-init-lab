# Native Init V2189 Security P0 Stage Fix Source Build

## Summary

- Candidate tag: `v2189-security-p0-stage-fix`
- Parent candidate: `v2188-security-p0-hardening`
- Type: source/build-only test boot candidate.
- Decision: `v2189-security-p0-stage-fix-source-build-pass`
- Result: PASS
- Reason: V2189 preserves V2188 P0 hardening and fixes the live validation gap where stale staged Wi-Fi executables remained non-root-owned.
- Manifest: `workspace/private/builds/native-init/v2189-security-p0-stage-fix-boot/manifest.json`
- Base boot: `workspace/private/inputs/boot_images/boot_linux_v725_fasttransport.img`
- Boot image: `workspace/private/inputs/boot_images/boot_linux_v2189_security_p0_stage_fix.img`
- Boot SHA256: `a7332612199cfd275f2dfc6fdb25843af401a1ecef2fa54ac0f52afe705f1ffe`
- Boot SHA verification: source/build output only; live flash/readback/selftest must be recorded separately before promotion.
- Init: `A90 Linux init 0.9.261 (v2189-security-p0-stage-fix)`
- Helper marker: `a90_android_execns_probe helper-v427` (binary marker string: `a90_android_execns_probe v427`)
- Helper SHA256: `99bdd67f0cd2fcaf6557478a97f85d405a0de3d6b0858ea17b4d46d7ce162ca1`

## Included Route

- Helper runtime mode: `wifi-companion-wlan-pd-post-pm-lower-state-observer-start-only`
- Helper timeout: `75`
- Property root: `/mnt/sdext/a90/private-property-v317/v726/dev/__properties__`
- Preserved: V2187 screenapp/UI validation baseline and V2188 flash artifact identity hardening.
- Fixed: generated Wi-Fi runtime files are re-owned as root when rewritten by PID1.
- Fixed: `wifi status` and `wifi connect` report standalone supplicant root-exec verification explicitly.
- Fixed: host Wi-Fi profile/connect staging hardens existing `/cache/a90-wifi/wpa-standalone` ownership before connect.

## Safety Scope

- This source build does not initiate Wi-Fi connect, DHCP, route/DNS changes, or ping.
- Runtime validation should flash this image with `native_init_flash.py --expect-sha256` and then run selftest/status plus bounded Wi-Fi smoke.
- No `/dev/subsys_esoc0`, forced RC1/case, PMIC/GPIO/GDSC/regulator write, PCI rescan, platform bind/unbind, fake ONLINE, or eSoC notify/BOOT_DONE path is included.
