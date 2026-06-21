# Native Init V3032 DOOMGENERIC Visible Frame Live Validation

## Summary

- Cycle: `V3032`
- Track: active Video playback / DOOM capstone.
- Decision: `v3032-doomgeneric-visible-frame-live-pass-before-rollback`
- Result before rollback: `1`
- Candidate: `A90 Linux init 0.10.75 (v3031-doomgeneric-visible-frame)`
- Candidate image: `workspace/private/inputs/boot_images/boot_linux_v3031_doomgeneric_visible_frame.img`
- Candidate SHA256: `1fefa60b9530cf4cfeb21f2419b77e7d9ca4258078899e3826a0c99918912fb4`
- Candidate helper SHA256: `45fca3ed017420c8368c99dcdd3b351053000b9bf26e653daa5d79bde704ce47`
- Runtime WAD path: `/mnt/sdext/a90/runtime/doom/v3028/DOOM1.WAD`
- Runtime WAD SHA256: `1d7d43be501e67d927e415e0b8f3e29c3bf33075e859721816f652a526cac771`
- Rollback attempted: `1`
- Rollback health: version_ok=`1` selftest_fail0=`1`

## Preflight

- Rollback v2321 SHA256 ok: `1`
- Fallback v2237 SHA256 ok: `1`
- Fallback v48 present/hash recorded: `1`
- Candidate SHA256 ok: `1`
- Bridge status ok: `1`
- Current resident before candidate flash: `A90 Linux init 0.9.285 (v2321-usb-clean-identity-rodata)`
- Current resident selftest fail=0 before candidate flash: `1`
- TWRP recovery confirmed before candidate boot write: `1`
- Flash helper: `workspace/public/src/scripts/revalidation/native_init_flash.py`

## Flash Evidence

- Candidate flashed through checked helper: `1`
- Candidate remote SHA256 matched local: `1`
- Candidate boot readback SHA256 matched expected: `1`
- Candidate post-flash version rc/status: `0` / `ok`
- Candidate post-flash status rc/status: `0` / `ok`
- Candidate post-flash selftest fail=0: `1`

## Visible Frame Evidence

- `video demo doom status` rc/status: `0` / `ok`
- `video.demo.engine.bridge=v3031-doomgeneric-visible-frame`: `1`
- `video.demo.engine.active=doomgeneric-private-link-v3031-visible-frame`: `1`
- `video.demo.engine.helper.present=1`: `1`
- `video.demo.engine.helper.executable=1`: `1`
- `video.demo.asset.wad.runtime_path=/mnt/sdext/a90/runtime/doom/v3028/DOOM1.WAD`: `1`
- `video.demo.asset.wad.expected_sha256=1d7d43be501e67d927e415e0b8f3e29c3bf33075e859721816f652a526cac771`: `1`
- `video.demo.asset.wad.present=1`: `1`
- `video.demo.asset.wad.bytes=4196020`: `1`
- `video.demo.asset.wad.size_ok=1`: `1`
- `video.demo.asset.wad.embedded_in_boot=0`: `1`
- `video.demo.input.otg_required=0`: `1`
- `video.demo.doom.frame.width=640`: `1`
- `video.demo.doom.frame.height=400`: `1`
- `video.demo.doom.frame.stride=2560`: `1`
- `video.demo.doom.frame.bytes=1024000`: `1`

## Frame Command Evidence

- `video demo doom frame 8 --wad runtime-private --sha256 EXPECTED` rc/status: `0` / `ok`
- `video.demo.doom.frame=doomgeneric-sd-wad-visible-frame`: `1`
- `video.demo.doom.frame.frames=8`: `1`
- `video.demo.doom.frame.verify.sha256_checked=1`: `1`
- `video.demo.doom.frame.verify.sha256_match=1`: `1`
- `video.demo.doom.frame.verify.magic=IWAD`: `1`
- `video.demo.doom.frame.verify.magic_ok=1`: `1`
- `video.demo.doom.frame.verify.ok=1`: `1`
- `video.demo.doom.frame.render.bytes=1024000`: `1`
- `video.demo.doom.frame.render.size_ok=1`: `1`
- `video.demo.doom.frame.render.geometry_ok=1`: `1`
- `video.demo.doom.frame.render.ok=1`: `1`
- `video.demo.doom.frame.helper_rc=0`: `1`
- `video.demo.doom.frame.timed_out=0`: `1`
- `doomframe: presented framebuffer 1080x2400`: `1`
- `video.demo.doom.frame.display.presented=1`: `1`
- `video.demo.doom.frame.display.path=kms-dumb-buffer`: `1`
- `video.demo.doom.frame.display.format=xbgr8888-raw`: `1`
- `video.demo.doom.frame.display.rc=0`: `1`

## Play Smoke Evidence

- `video demo doom play 4 --wad runtime-private --sha256 EXPECTED` rc/status: `0` / `ok`
- `video.demo.doom.play=doomgeneric-sd-wad-smoke`: `1`
- `video.demo.doom.play.frames=4`: `1`
- `video.demo.doom.play.verify.sha256_checked=1`: `1`
- `video.demo.doom.play.verify.sha256_match=1`: `1`
- `video.demo.doom.play.verify.magic_ok=1`: `1`
- `video.demo.doom.play.verify.ok=1`: `1`
- `video.demo.doom.play.rc=0`: `1`
- `video.demo.doom.play.duration_ms=100`: `1`
- `video.demo.doom.play.timed_out=0`: `1`

## Rollback Evidence

- Rollback target: `A90 Linux init 0.9.285 (v2321-usb-clean-identity-rodata)`
- Rollback SHA256: `ca978551aabe4b39563abaf529ccf2522054952d8b2ad852e632d26da88168cb`
- Rollback flashed through checked helper: `1`
- Rollback remote SHA256 matched local: `1`
- Rollback boot readback SHA256 matched expected: `1`
- Rollback post-flash version rc/status: `0` / `ok`
- Rollback post-flash status rc/status: `0` / `ok`
- Rollback health: version_ok=`1` selftest_fail0=`1`
- Final rollback version re-check: `A90 Linux init 0.9.285 (v2321-usb-clean-identity-rodata)`
- Final rollback selftest fail=0 re-check: `1`

## Notes

- One immediate rollback selftest retry hit serial input framing corruption before `A90P1 END`; the bridge and v2321 version were still reachable, and a slow-input retry returned `selftest fail=0`. This is recorded as transport noise, not a device health regression.
- `video demo doom frame 8` proves that a WAD-backed doomgeneric frame can be rendered and presented on the panel through KMS.
- `video demo doom play 4` proves the bounded WAD-backed helper run path remains playable-capable after the visible-frame changes, but it is still a smoke run rather than the final continuous visible playable DOOM loop.

## Safety

- Only the boot partition was flashed, through `native_init_flash.py`.
- The exact V3031 and V2321 SHA256 values were checked before flash and confirmed by boot readback.
- Rollback target remained `v2321`; deeper fallbacks `v2237` and `v48` plus TWRP were preflighted.
- WAD/IWAD bytes stayed on the SD runtime path only; no WAD data was copied into public paths, ramdisk, or boot image.
- No Wi-Fi connect/DHCP/ping, forbidden partition, evdev injection, uinput, sysfs write, Venus, GPU, raw DSI, panel init, backlight, PMIC, PWM, regulator, GPIO, or GDSC path was used.
- Raw command transcripts and bridge logs remain private/untracked; this report includes metadata only and omits raw serial, MAC/BSSID/IP, and SD UUID values.

## Next Unit

- Run ID: `V3033`
- Type: host-only visible playable DOOM loop/menu integration.
- Scope: use the V3032-proven SD WAD hash gate, helper frame render, KMS present path, bounded play smoke, and serial-doompad input bridge to design/build the next bounded visible/playable loop path without embedding WAD bytes or widening the flash surface.
