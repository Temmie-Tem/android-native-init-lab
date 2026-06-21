# Native Init V3039 DOOMGENERIC Large Dashboard Live Validation

## Summary

- Cycle: `V3039`
- Track: active Video playback / DOOM capstone.
- Decision: `v3038-doomgeneric-large-dashboard-live-superseded`
- Result: HEALTH PASS, FUNCTIONAL PASS WITH SERIAL-LOG CONTENTION.
- Device flash: yes, boot partition only.
- Flash helper: `workspace/public/src/scripts/revalidation/native_init_flash.py`
- Candidate image: `workspace/private/inputs/boot_images/boot_linux_v3038_doomgeneric_large_dashboard.img`
- Candidate SHA256: `0274bc86e77875f7c426b9cb031374b5157143889197f6553b250ce952addb29`
- Flashed init: `A90 Linux init 0.10.78 (v3038-doomgeneric-large-dashboard)`
- Final state: candidate remained healthy; DOOM loop stopped and doompad reset. This candidate is superseded by a follow-up quiet-presenter candidate because per-frame serial logs interfere with host command framing during active loop playback.

## Safety Gates

- Forbidden partitions: not touched.
- Write target: boot partition only through the checked flash helper.
- Rollback image `boot_linux_v2321_usb_clean_identity_rodata.img`: present and SHA256 matched.
- Deeper fallback `boot_linux_v2237_supplicant_terminate_poll.img`: present and SHA256 matched.
- Final fallback `boot_linux_v48.img`: present and SHA256 matched.
- Recovery availability: TWRP `3.7.0_12-0` reached before flash.
- Wi-Fi actions: none.
- OTG, evdev injection, uinput, GPIO, PMIC, regulator, modem, vbmeta, bootloader, `/efs`, `/sec_efs`, keymaster, RPMB: not touched.

## Preflash Health

- Bridge wrapper: running and probe connected.
- Baseline before flash: `A90 Linux init 0.10.77 (v3036-doomgeneric-native-dashboard)`.
- Preflash status: `BOOT OK`.
- Preflash selftest: `pass=12 warn=1 fail=0`.
- Prior DOOM loop state was stopped and doompad state was reset before rebooting to recovery.

## Flash Result

- Local Android boot magic check: PASS.
- Local marker check for `A90 Linux init 0.10.78 (v3038-doomgeneric-large-dashboard)`: PASS.
- Local candidate SHA256: matched.
- Remote pushed candidate SHA256 in recovery: matched.
- Boot write via checked helper: PASS.
- Boot readback prefix verification: PASS.
- Reboot to native init: PASS.
- Flash helper native verification: `version/status rc=0 status=ok`.
- Total helper elapsed time: `46.276s`.
- Rollback performed: no, because candidate booted and passed health checks.

## Postflash Health

- `version`: `A90 Linux init 0.10.78 (v3038-doomgeneric-large-dashboard)`.
- `status`: `BOOT OK`.
- `selftest`: `pass=12 warn=1 fail=0`.
- Storage backend: SD runtime workspace mounted read-write.
- Display: native KMS display ready.
- Thermal/power sample from status: CPU `45.2C`, GPU `43.4C`, power `0.4W`.

## DOOM Status

- Runtime WAD path: `/mnt/sdext/a90/runtime/doom/v3028/DOOM1.WAD`
- Runtime WAD SHA256 contract: `1d7d43be501e67d927e415e0b8f3e29c3bf33075e859721816f652a526cac771`
- Runtime WAD present: `1`
- Runtime WAD regular file: `1`
- Runtime WAD bytes: `4196020`
- Runtime WAD size_ok: `1`
- WAD embedded in boot: `0`
- Helper path: `/bin/a90_doomgeneric_private_engine_v3038`
- Helper present: `1`
- Helper executable: `1`
- Frame path: `/tmp/a90-doomgeneric-v3038-large-dashboard-frame.xbgr8888`
- Input state path: `/tmp/a90-doomgeneric-v3038-input.state`
- Loop visible: `1`
- Loop frame ms: `50`
- Native dashboard marker: `video.demo.doom.dashboard.native=1`
- Large frame marker: `video.demo.doom.dashboard.large_frame=1`
- Frame mode marker: `video.demo.doom.dashboard.frame_mode=large-overlay-title`
- Frame scale marker: `video.demo.doom.dashboard.frame_scale=3:2`
- Host dashboard marker: `video.demo.input.host_dashboard=host_doompad_dashboard_v3035.py`
- OTG required marker: `video.demo.input.otg_required=0`

## Loop And Input Validation

- `doompad reset`: PASS, state path updated.
- `video demo doom loop-start 300 --wad runtime-private --sha256 EXPECTED`: PASS.
- Background loop pid reported: present.
- First `video demo doom loop-status`: active `1`.
- KMS dashboard presenter log: `doomdash: presented framebuffer 1080x2400 on crtc=133`.
- `doompad key forward 1`: PASS, state changed to `forward=1 active=1`.
- `doompad status`: PASS, state retained `forward=1 active=1`.
- `doompad key fire 1`: PASS, state changed to `forward=1 fire=1 active=1`.
- `doompad key fire 0`: PASS, state changed to `forward=1 fire=0 active=1`.
- `doompad key forward 0`: PASS, state changed to all roles released and `active=0`.
- Second loop-status while active loop was printing per-frame serial logs: command framing was corrupted and returned `rc=-22`.
- `video demo doom loop-stop`: PASS.
- Final `doompad reset`: PASS, final state all roles released and `active=0`.
- Final loop-status after cleanup: active `0`.
- Final selftest after cleanup: `pass=12 warn=1 fail=0`.

## Finding

- The enlarged native dashboard itself rendered and the scripted input path worked.
- The active presenter still called `a90_kms_present("doomdash", true)`, which emits a serial line on every frame.
- During active playback those per-frame serial lines interleaved with host commands and caused one `video demo doom loop-status` command to be parsed incorrectly.
- Follow-up fix: build a new large-dashboard candidate that keeps the native display unchanged but changes the `doomdash` present path to quiet per-frame serial output.

## Operator State

- Device is healthy on V3038 at the end of this iteration.
- DOOM loop is stopped.
- Doompad state is reset.
- V3038 is safe enough as a booted baseline, but it should not be the final demo candidate because serial command framing is noisy while the loop is active.
