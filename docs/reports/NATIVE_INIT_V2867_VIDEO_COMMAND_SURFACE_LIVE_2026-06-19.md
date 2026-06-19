# Native Init V2867 Video Command Surface Live Validation

## Summary

- Cycle: `V2867`
- Track: active Video display/framebuffer feasibility recon.
- Decision: `v2867-video-command-surface-live-pass`
- Result: PASS
- Candidate flashed: `workspace/private/inputs/boot_images/boot_linux_v2866_video_command_surface.img`
- Candidate SHA256: `4ffc9040e45916ec74c894d5373594a335c8317f766c920744044df3d6fe33f1`
- Candidate init: `A90 Linux init 0.10.20 (v2866-video-command-surface)`
- Rollback target: `workspace/private/inputs/boot_images/boot_linux_v2321_usb_clean_identity_rodata.img`
- Rollback SHA256: `ca978551aabe4b39563abaf529ccf2522054952d8b2ad852e632d26da88168cb`
- Private evidence: `workspace/private/runs/video/v2867-video-command-live-20260619-185316`

## Preflight

- Re-read `GOAL.md`, `AGENTS.md`, and `CLAUDE.md` for the active Video epic and flash gates.
- Confirmed rollback image SHA256 for `v2321` and deeper fallback SHA256 for `v2237`; confirmed `boot_linux_v48.img` exists.
- Confirmed serial bridge at `127.0.0.1:54321` and current resident `v2321` health before flashing.
- Candidate boot image marker and SHA256 matched the V2866 source-build report.

## Flash Result

- Flash helper: `workspace/public/src/scripts/revalidation/native_init_flash.py`
- Flash mode: `--from-native`, boot partition only.
- Remote image SHA256: matched candidate SHA256.
- Boot block readback SHA256: matched candidate SHA256.
- Post-flash verification: native-init `version` / `status` passed.
- Candidate booted as `0.10.20 build=v2866-video-command-surface`.
- Candidate selftest after video exercise: `pass=12 warn=1 fail=0`.

## Video Validation

| Step | Result | Evidence |
| --- | --- | --- |
| `video status` while HUD active | PASS | `video.status.path=kms-dumb-buffer`; `venus=not-used`; `kgsl=not-used`; `raw_dsi=blocked`; `power_writes=blocked`; `kms.initialized=1`; `kms.size=1080x2400`; connector `28`, encoder `27`, CRTC `133`. |
| `hide` | PASS | Stopped the menu/HUD path before direct KMS frame presentation. |
| `video frame bars` after `hide` | PASS | `videoframe: presented framebuffer 1080x2400 on crtc=133`; `video.frame.presented=1`; `pattern=bars`; duration `12ms`. |
| `video status` after frame | PASS | KMS still initialized; current framebuffer changed from `208/1` to `207/0`, confirming command-owned presentation. |
| `autohud 2` restore | PASS | HUD restarted after the frame test. |
| Candidate `selftest verbose` | PASS | `fail=0`, KMS row `1080x2400 fb=207 crtc=133`. |

## Notes

- A deliberate `video frame bars` attempt while the menu/HUD was still active hit serial input contention and the host parser saw no complete A90P1 end marker. This did not affect the run: subsequent `hide`, `video frame bars`, `video status`, `autohud 2`, and `selftest verbose` all completed normally.
- The successful frame path used the existing KMS dumb-buffer API; it did not touch Venus, KGSL, raw DSI, panel init, backlight, PMIC, PWM, regulator, GPIO, or GDSC.
- This validates the first drawable display framebuffer command and unblocks downstream framebuffer demos such as Bad Apple/Nyan/DOOM planning.

## Rollback

- Rollback helper: `workspace/public/src/scripts/revalidation/native_init_flash.py`
- Rollback mode: `--from-native`, boot partition only.
- Remote rollback image SHA256: matched `v2321` SHA256.
- Boot block readback SHA256: matched `v2321` SHA256.
- Post-rollback version: `A90 Linux init 0.9.285 (v2321-usb-clean-identity-rodata)`.
- Final `selftest verbose`: `pass=11 warn=1 fail=0`.
- Final bridge state: alive, selected serial `/dev/ttyACM0` via `A90-LNX_A90_Linux_ARM64_A90NATIVE001`.

## Decision

`v2867-video-command-surface-live-pass`: the V2866 video command surface is device-proven for read-only KMS status and one bounded single-frame KMS dumb-buffer presentation, with clean rollback to `v2321` and final `selftest fail=0`.
