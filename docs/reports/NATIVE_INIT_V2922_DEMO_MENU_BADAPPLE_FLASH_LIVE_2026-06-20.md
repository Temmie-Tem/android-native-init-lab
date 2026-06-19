# Native Init V2922 DEMO Bad Apple Menu Flash Live

## Summary

- Cycle: `V2922`
- Track: active Video playback pipeline / Bad Apple Player HUD menu integration.
- Decision: `v2922-demo-menu-badapple-flash-live-pass`
- Result: PASS
- Flashed image: `workspace/private/inputs/boot_images/boot_linux_v2921_demo_menu_badapple.img`
- Boot SHA256: `2dbfbc86158d06f3459f359022d41b10f189805e478542722cd715f14bb1fddd`
- Resident init after flash: `A90 Linux init 0.10.39 (v2921-demo-menu-badapple)`
- Rollback target preserved: `v2321-usb-clean-identity-rodata`

## Scope

- Implemented and flashed a new native-init boot image that adds a `DEMO >` main-menu page.
- Added `BAD APPLE HUD` as a bounded 120-frame video-only Player HUD preview entry.
- Kept the full Bad Apple frame/audio assets outside the boot image; the menu path uses the existing SD SHA-addressed video cache.
- Did not add Venus, GPU, raw DSI, backlight, PMIC, PWM, regulator, GPIO, GDSC, or telemetry write paths.

## Flash Evidence

- Local boot image marker check passed for `A90 Linux init 0.10.39 (v2921-demo-menu-badapple)`.
- Local image size: `61046784` bytes.
- Local image SHA256: `2dbfbc86158d06f3459f359022d41b10f189805e478542722cd715f14bb1fddd`.
- Recovery handoff: native bridge requested recovery successfully.
- ADB recovery ready: `RFCM90CFWXA recovery`.
- ADB push speed: `83.3 MB/s`.
- Remote `/tmp/native_init_boot.img` SHA256 matched local.
- Boot partition write completed via checked helper only.
- Boot block prefix readback SHA256 matched local.
- Post-flash native serial verify passed: `version` and `status` returned `rc=0 status=ok`.
- Total helper wall time: `63.665s`.

## Live Validation

- `version`: `A90 Linux init 0.10.39 (v2921-demo-menu-badapple)`.
- `status`: `selftest: pass=12 warn=1 fail=0`, storage SD mounted RW, display `1080x2400`, transport bridge ready.
- `selftest verbose`: `pass=12 warn=1 fail=0` before and after video/menu checks.
- `video status`: KMS path active, raw DSI/power writes blocked, cache/demo command surfaces present.
- `video demo badapple status`: cache manifest OK, stream exists, stream size `150490668`, frames `6962`, format `mono1`, size `480x360`, SHA preset `9e938aa83ef40aa692d0f42080821dc21a627f1dddd90cc9c2696aafe6ac6eb0`.
- `screenmenu`: returned `screenmenu: show requested on background HUD`; menu then hidden again with `hidemenu`.
- Bounded Player HUD preview command: `video demo badapple play --trust-cache --frames 30 --present pageflip --layout player-hud`.
- Preview result: `presented=30`, `dropped_frames=0`, `present_mode=pageflip`, `layout=player-hud`, `rc=0`.

## Notes

- A chained first validation attempt hit stale serial output and then `status=busy` because the background menu was active. The bridge remained healthy; rerunning with `--input-mode slow` and hiding the menu resolved it.
- The menu item itself is compiled into the image with markers `DEMO >`, `BAD APPLE HUD`, `4S PLAYER HUD PREVIEW`, `menu.demo.badapple.frames=120`, and `menu.demo.badapple.restore=menu`.
- The live direct preview used 30 frames for a short validation; the menu item is intentionally bounded at 120 frames and restores the menu after returning.

## Safety

- Flash path used only `workspace/public/src/scripts/revalidation/native_init_flash.py`.
- Only the boot partition was written.
- No rollback was required.
- Raw streams, boot image, private run logs, and generated binaries remain private/untracked.
