# Native Init V3085 DOOMGENERIC Serial Preserve Live Validation

## Summary

- Cycle: `V3085`
- Candidate flashed: `V3084`
- Build: `A90 Linux init 0.10.99 (v3084-doomgeneric-serial-preserve)`
- Boot image: `workspace/private/inputs/boot_images/boot_linux_v3084_doomgeneric_serial_preserve.img`
- Boot SHA256: `d7a4e8f503a4501151380ec115253c1af4a1004e864c6868bc4b1a1b28d423d5`
- Decision: `v3085-doomgeneric-serial-preserve-live-pass-with-30fps-pacing-followup`
- Result: PASS
- Rollback: not needed

## Flash Gate

- Rollback image `boot_linux_v2321_usb_clean_identity_rodata.img` matched the required SHA256.
- Rollback image `boot_linux_v2237_supplicant_terminate_poll.img` matched the required SHA256.
- Final fallback `boot_linux_v48.img` exists.
- TWRP recovery image and archive exist.
- Pre-flash resident health was clean: `version`, `status`, and `selftest` completed with fail count `0`.
- Flash used only `workspace/public/src/scripts/revalidation/native_init_flash.py`.
- Remote boot-block readback SHA256 matched the local V3084 image SHA256.

## Post-Flash Health

- `native_init_flash.py` verified V3084 after reboot through cmdv1.
- Post-flash `selftest` completed with fail count `0`.
- Final post-validation `selftest` also completed with fail count `0`.

## DOOM Live Validation

- `video demo doom status` required `--hide-on-busy` once because the boot autohud/menu owned the display. After hide, the DOOM status command completed normally.
- Runtime WAD was present, regular, size-ok, and SHA256 matched the expected runtime-private hash.
- Engine helper was present and executable.
- Live markers confirmed:
  - `video.demo.engine.bridge=v3084-doomgeneric-serial-preserve`
  - `video.demo.doom.frame.ipc=shared-mmap-seq`
  - `video.demo.doom.presenter.pacing=presenter-pageflip-pace-socket`
  - `video.demo.doom.presenter.present_mode=pageflip`
  - `video.demo.doom.presenter.reader=shared-mmap-copy`
  - `video.demo.doom.dashboard.large_frame=1`
  - `video.demo.doom.dashboard.frame_scale=3:2`
  - `video.demo.doom.dashboard.scale_path=fast-3to2-rowcopy`
  - `video.demo.doom.loop_start.background_cancel=disabled-serial-preserve`

## Bounded Loop Timing

Command:

`video demo doom loop 120 --wad runtime-private --sha256 <expected-runtime-wad-sha256>`

Result:

- Frames presented: `120`
- Loop rc: `0`
- Buffer allocations: `1`
- Shared-frame reader: active
- Pace socket active: `1`
- Pace tokens sent: `120`
- Pace socket failures: `0`
- Pace socket wait timeouts: `0`

Timing:

- Read avg/max: `188us / 994us`
- Begin avg/max: `4521us / 4681us`
- Draw avg/max: `4299us / 4547us`
- Present avg/max: `18723us / 19062us`
- Total avg/max: `27732us / 27874us`
- Pageflip delta min/max/avg: `33232us / 33262us / 33244us`

Interpretation:

- Shared-frame IPC is no longer a meaningful bottleneck in this run.
- Fast 3:2 scaler is active and draw cost is around `4.3ms`.
- Presentation is stable but effectively locked to about `30fps`.

## Background Serial Preserve Check

Command:

`video demo doom loop-start 0 --wad runtime-private --sha256 <expected-runtime-wad-sha256>`

Result:

- Background continuous loop started.
- `background_cancel=disabled-serial-preserve` marker was present.
- Audio co-run start returned rc `0`.
- While the background loop was active, these serial/cmdv1 commands completed normally:
  - `version`
  - `status`
  - `video demo doom loop-status`
- `video demo doom loop-stop` completed with rc `0`.
- Audio stop/reset path completed with rc `0`.

This validates the V3084 fix: the background DOOM presenter no longer consumes serial command bytes.

## Additional Cause Check

KMS/pageflip baseline was measured separately:

Command:

`video flipprobe 120`

Result:

- Frames presented: `120`
- Measured fps: about `60.4fps`
- Path: KMS dumb-buffer pageflip

Conclusion:

- The panel/KMS pageflip path can present at roughly `60fps`.
- The remaining visible stutter is not explained by KMS being limited to `30fps`.
- The DOOM path is currently pacing at roughly `30fps` because the presenter work plus `VIDEO_DEMO_DOOMGENERIC_PAGEFLIP_MIN_SUBMIT_INTERVAL_MS=18` lands on every other vblank.

## Remaining Issues / Next Suspects

1. DOOM smoothness: V3084 is stable but effectively `30fps`. Next useful unit is a pacing experiment that lowers or disables the pageflip minimum submit interval and measures whether the loop reaches a better 35fps/60Hz cadence or just becomes uneven.
2. Audio: current DOOM audio mode is `native-audio-corun-tone-v3053`; live output marks real DOOM SFX as disabled. If no game sound is heard, that is expected for this candidate. The audio worker start/stop path returns rc `0`, but it is a co-run tone path, not DOOM mixer output.
3. Autohud/menu ownership: boot autohud can make first DOOM command return busy. Operator workaround is `a90ctl.py --hide-on-busy ...`; code improvement is to have DOOM launch commands hide/stop autohud automatically.
4. Foreground loop verbosity: foreground `video demo doom loop` prints per-frame dashboard markers to serial. This is useful for validation but noisy. Continuous background loop avoids this serial log flood during actual play.

## Recommended Next Unit

- Run ID: `V3086`
- Purpose: DOOM pageflip cadence experiment.
- Candidate changes:
  - set `VIDEO_DEMO_DOOMGENERIC_PAGEFLIP_MIN_SUBMIT_INTERVAL_MS` to `0` or a lower bounded value,
  - keep shared-frame IPC and fast 3:2 scaler,
  - run `video demo doom loop 180` and `video flipprobe 180`,
  - compare flip delta distribution, total frame time, and visual smoothness.
