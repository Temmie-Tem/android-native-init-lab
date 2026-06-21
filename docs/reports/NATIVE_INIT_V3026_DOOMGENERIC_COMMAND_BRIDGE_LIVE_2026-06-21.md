# Native Init V3026 DOOMGENERIC Command Bridge Live Validation

## Summary

- Cycle: `V3026`
- Track: active Video playback / DOOM capstone.
- Decision: `v3026-doomgeneric-command-bridge-live-pass-before-rollback`
- Result before rollback: `1`
- Candidate: `A90 Linux init 0.10.73 (v3025-doomgeneric-command-bridge)`
- Candidate image: `workspace/private/inputs/boot_images/boot_linux_v3025_doomgeneric_command_bridge.img`
- Candidate SHA256: `d028ece642793a7a6242295c86cd6caedbd533f733282120c0575116f012e95f`
- Rollback attempted: `1`
- Rollback health: version_ok=`1` selftest_fail0=`1`

## Preflight

- Rollback v2321 SHA256 ok: `1`
- Fallback v2237 SHA256 ok: `1`
- Fallback v48 SHA256 ok: `1`
- Candidate SHA256 ok: `1`
- Candidate Android boot magic ok: `1`
- Bridge doctor ok: `1`
- Current resident before candidate flash: `A90 Linux init 0.9.285 (v2321-usb-clean-identity-rodata)`
- Current resident selftest fail=0 before candidate flash: `1`
- TWRP recovery confirmed before boot write: `1`
- Flash helper: `workspace/public/src/scripts/revalidation/native_init_flash.py`

## Flash Evidence

- Candidate flashed through checked helper: `1`
- Candidate remote SHA256 matched local: `1`
- Candidate boot readback SHA256 matched expected: `1`
- Candidate post-flash version rc/status: `0` / `ok`
- Candidate post-flash status rc/status: `0` / `ok`
- Candidate post-flash selftest fail=0: `1`

## Command Bridge Evidence

- `video demo doom status` rc/status: `0` / `ok`
- `video.demo.engine.bridge=v3025-doomgeneric-command-bridge`: `1`
- `video.demo.engine.active=doomgeneric-private-link-v3025`: `1`
- `video.demo.engine.helper.present=1`: `1`
- `video.demo.engine.helper.executable=1`: `1`
- `video.demo.asset.wad.active=runtime-private-not-bundled`: `1`
- `video.demo.asset.wad.runtime_root=/cache/a90-runtime/pkg/doom/v3024/`: `1`
- `video.demo.asset.wad.embedded_in_boot=0`: `1`
- `video.demo.input.active=serial-doompad-to-DG_GetKey`: `1`
- `video.demo.input.otg_required=0`: `1`
- `video.demo.sound.active=disabled-nosound-nomusic`: `1`
- `video.demo.doom.status_rc=0`: `1`

## Engine Probe Evidence

- `video demo doom engine-probe` rc/status: `0` / `ok`
- `video.demo.doom.engine_probe.status=ready`: `1`
- `video.demo.doom.engine_probe=doomgeneric-private-helper`: `1`
- `video.demo.doom.engine_probe.timeout_ms=3000`: `1`
- `video.demo.doom.engine_probe.rc=0`: `1`
- `video.demo.doom.engine_probe.duration_ms=101`: `1`
- `video.demo.doom.engine_probe.timed_out=0`: `1`

## Rollback Evidence

- Rollback target: `A90 Linux init 0.9.285 (v2321-usb-clean-identity-rodata)`
- Rollback SHA256: `ca978551aabe4b39563abaf529ccf2522054952d8b2ad852e632d26da88168cb`
- Rollback flashed through checked helper: `1`
- Rollback remote SHA256 matched local: `1`
- Rollback boot readback SHA256 matched expected: `1`
- Rollback post-flash version rc/status: `0` / `ok`
- Rollback post-flash status rc/status: `0` / `ok`
- Rollback selftest fail=0 after helper verify: `1`

## Interpretation

- V3026 validates that the V3025 boot candidate is rollback-safe and exposes the internal DOOM command bridge on-device.
- The primary controller path is internal serial `doompad` state into `DG_GetKey`; OTG keyboard is no longer required for this proof path.
- The private engine helper is present and executable, and the bounded `engine-probe` exits successfully.
- This is still not WAD-backed gameplay. WAD/IWAD bytes remain runtime-private, not bundled in the boot image or ramdisk.

## Safety

- Only the boot partition was flashed, through `native_init_flash.py`.
- The exact V3025 and V2321 SHA256 values were checked before flash and confirmed by boot readback.
- Rollback target remained `v2321`; deeper fallbacks `v2237` and `v48` plus TWRP were preflighted.
- No WAD/IWAD bytes were staged, copied, committed, embedded in ramdisk, or embedded in the boot image.
- No Wi-Fi connect/DHCP/ping, forbidden partition, evdev injection, uinput, sysfs write, Venus, GPU, raw DSI, panel init, backlight, PMIC, PWM, regulator, GPIO, or GDSC path was used.
- Raw command transcripts and bridge logs remain private/untracked; this report includes metadata only.

## Next Unit

- Run ID: `V3027`
- Type: runtime-private WAD staging preflight.
- Scope: inspect the private WAD root and define the exact hash/size/staging contract for a later bounded WAD-backed DOOM smoke; keep WAD bytes out of public, ramdisk, and boot image.
