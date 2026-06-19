# Native Init V2869 Video Animation Scaffold Live Validation

## Summary

- Cycle: `V2869`
- Track: active Video display/framebuffer path toward framebuffer demos.
- Decision: `v2869-video-animation-scaffold-live-pass`
- Result: PASS
- Candidate flashed: `workspace/private/inputs/boot_images/boot_linux_v2868_video_animation_scaffold.img`
- Candidate SHA256: `9fbcb7a22c5263aa54631a7ecfbaaa2976da70ff8baf0d52d3e9cae8db572e3e`
- Candidate init: `A90 Linux init 0.10.21 (v2868-video-animation-scaffold)`
- Rollback target: `workspace/private/inputs/boot_images/boot_linux_v2321_usb_clean_identity_rodata.img`
- Rollback SHA256: `ca978551aabe4b39563abaf529ccf2522054952d8b2ad852e632d26da88168cb`
- Private evidence: `workspace/private/runs/video/v2869-video-animation-live-20260619-190558`

## Preflight

- Re-read `GOAL.md`, `AGENTS.md`, and `CLAUDE.md` for the active Video epic and flash gates.
- Confirmed rollback image SHA256 for `v2321`, deeper fallback SHA256 for `v2237`, and `boot_linux_v48.img` presence.
- Confirmed current resident `v2321` over the serial bridge before flashing.
- Current preflash `selftest verbose`: `pass=11 warn=1 fail=0`.
- Confirmed candidate SHA256 and marker string `0.10.21` before flashing.

## Flash Result

- Flash helper: `workspace/public/src/scripts/revalidation/native_init_flash.py`
- Flash mode: `--from-native`, boot partition only.
- Remote image SHA256: matched candidate SHA256.
- Boot block readback SHA256: matched candidate SHA256.
- Candidate booted as `0.10.21 build=v2868-video-animation-scaffold`.
- Candidate status after boot: `selftest pass=12 warn=1 fail=0`.

## Video Animation Validation

| Step | Result | Evidence |
| --- | --- | --- |
| `video status` | PASS | KMS path initialized, size `1080x2400`, connector `28`, encoder `27`, CRTC `133`; safety markers `venus=not-used`, `kgsl=not-used`, `raw_dsi=blocked`, `power_writes=blocked`; advertised `video.status.next_anim`. |
| `hide` | PASS | Stopped active menu/HUD before animation rendering. |
| `video anim bars 5 20` | PASS | Five `videoanim: presented framebuffer 1080x2400 on crtc=133` lines; `video.anim.presented=5`, `pattern=bars`, `delay_ms=20`, duration `144ms`. |
| `video anim pulse 3 0` | PASS | Three `videoanim: presented framebuffer 1080x2400 on crtc=133` lines; `video.anim.presented=3`, `pattern=pulse`, `delay_ms=0`, duration `46ms`. |
| `video status` after animation | PASS | KMS remained initialized and command surface remained responsive. |
| `autohud 2` restore | PASS | HUD restarted after animation validation. |
| Candidate `selftest verbose` | PASS | `pass=12 warn=1 fail=0`, KMS row `1080x2400 fb=207 crtc=133`. |

## Safety

- Rendering used the existing KMS dumb-buffer path only.
- No Venus, KGSL, raw DSI, panel init, backlight, PMIC, PWM, regulator, GPIO, or GDSC path was touched.
- The animation loop is bounded by command arguments and compiled caps: `frames<=240`, `delay_ms<=1000`; it is cancelable via existing console cancel polling.
- No demo/media assets were committed or deployed; this is only the generic frame-loop primitive for future Bad Apple / Nyan / DOOM scaffolding.

## Rollback

- Rollback helper: `workspace/public/src/scripts/revalidation/native_init_flash.py`
- Rollback mode: `--from-native`, boot partition only.
- Remote rollback image SHA256: matched `v2321` SHA256.
- Boot block readback SHA256: matched `v2321` SHA256.
- Post-rollback version: `A90 Linux init 0.9.285 (v2321-usb-clean-identity-rodata)`.
- Final `selftest verbose`: `pass=11 warn=1 fail=0`.

## Decision

`v2869-video-animation-scaffold-live-pass`: V2868 is device-proven for bounded KMS frame-loop animation over the already-proven framebuffer path. The next aligned unit is a host-side demo asset/frame pipeline design that feeds this loop without introducing copyrighted media or uncontrolled long-running rendering.
