# Native Init V2189 Security P0 Stage Fix Source Build

## Summary

- Candidate tag: `v2189-security-p0-stage-fix`
- Parent candidate: `v2188-security-p0-hardening`
- Type: source/build-only test boot candidate.
- Decision: `v2189-security-p0-stage-fix-source-build-pass`
- Result: PASS
- Reason: V2189 preserves V2188 P0 hardening, fixes the live validation gap where stale staged Wi-Fi executables remained non-root-owned, and adds the 2026-06-10 active security triage hardening set.
- Manifest: `workspace/private/builds/native-init/v2189-security-p0-stage-fix-boot/manifest.json`
- Base boot: `workspace/private/inputs/boot_images/boot_linux_v725_fasttransport.img`
- Boot image: `workspace/private/inputs/boot_images/boot_linux_v2189_security_p0_stage_fix.img`
- Boot SHA256: `f54becb2b720ad198413c2a0089912626ca295c79a96f13e0921cf4f05b39f51`
- Boot SHA verification: source/build output only; live flash/readback/selftest must be recorded separately before promotion.
- Init: `A90 Linux init 0.9.261 (v2189-security-p0-stage-fix)`
- Helper marker: `a90_android_execns_probe helper-v427` (binary marker string: `a90_android_execns_probe v427`)
- Helper SHA256: `a4ef028aee167ab6a66b17389ade37427e85647d18e45270634f666b8efe1a44`

## Included Route

- Helper runtime mode: `wifi-companion-wlan-pd-post-pm-lower-state-observer-start-only`
- Helper timeout: `75`
- Property root: `/mnt/sdext/a90/private-property-v317/v726/dev/__properties__`
- Preserved: V2187 screenapp/UI validation baseline and V2188 flash artifact identity hardening.
- Fixed: generated Wi-Fi runtime files are re-owned as root when rewritten by PID1.
- Fixed: `wifi status` and `wifi connect` report standalone supplicant root-exec verification explicitly.
- Fixed: host Wi-Fi profile/connect staging hardens existing `/cache/a90-wifi/wpa-standalone` ownership before connect.
- Fixed: host bridge repair, unsafe busy replay, NCM listener/repair scope, Wi-Fi identifier redaction, wificfg symlink traversal, bounded evidence reads, and Termux lab auth/limits.
- Fixed: helper temp paths use `mkdtemp()`/`mkstemp()`, private cnss-daemon bind sources are verified, and supplicant helper exec drops to UID/GID 1010 before exec.

## Safety Scope

- This source build does not initiate Wi-Fi connect, DHCP, route/DNS changes, or ping.
- Runtime validation should flash this image with `native_init_flash.py --expect-sha256` and then run selftest/status plus bounded Wi-Fi smoke.
- No `/dev/subsys_esoc0`, forced RC1/case, PMIC/GPIO/GDSC/regulator write, PCI rescan, platform bind/unbind, fake ONLINE, or eSoC notify/BOOT_DONE path is included.
