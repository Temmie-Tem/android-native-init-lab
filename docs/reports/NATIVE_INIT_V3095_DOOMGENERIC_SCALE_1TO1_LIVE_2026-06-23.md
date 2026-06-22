# Native Init V3095 DOOMGENERIC 1:1 Scale Live Validation

## Summary

- Cycle: `V3095`
- Candidate flashed: `V3094` / `A90 Linux init 0.10.103 (v3094-doomgeneric-scale-1to1)`
- Track: active Video playback / DOOM stutter root-cause isolation.
- Decision: `v3095-doomgeneric-scale-1to1-live-pass-large-scaler-is-stutter-source`
- Result: PASS
- Boot SHA256: `bb64e3046ed5caf2e496527f7970c73d50591af01404ef25499040d4dc88f66e`
- Flash method: `workspace/public/src/scripts/revalidation/native_init_flash.py`
- Device safety result: booted, health checked, post-loop selftest `fail=0`.

## Gate Evidence

- Rollback images were present and SHA256 checked before flash:
  - `boot_linux_v2321_usb_clean_identity_rodata.img`
  - `boot_linux_v2237_supplicant_terminate_poll.img`
  - `boot_linux_v48.img`
- TWRP recovery image was present.
- Pre-flash resident health was OK: version/status/selftest completed with selftest `fail=0`.
- Flash wrote only the boot partition through the checked helper, and readback SHA256 matched the candidate image.
- Post-flash resident version matched `A90 Linux init 0.10.103 (v3094-doomgeneric-scale-1to1)`.
- Post-flash health status and selftest completed with selftest `fail=0`.

## Live Configuration

- Engine bridge: `v3094-doomgeneric-scale-1to1`
- Engine active: `doomgeneric-private-link-v3094-scale-1to1`
- Frame IPC: `shared-mmap-seq`
- Input path: `udp-ncm-to-DG_GetKey-with-serial-doompad-fallback`
- Presenter pacing: `presenter-pageflip-pace-socket`
- Presenter mode: `pageflip`
- Timing probe: enabled
- Dashboard profile: native minimal fastdraw
- Large dashboard frame: `0`
- Frame scale: `1:1`
- Scale path: `raw-rowcopy`
- Metrics pacing: disabled minimal
- Runtime WAD: SD runtime WAD verified by SHA256 and IWAD magic.

## Loop Result

- Command shape: `video demo doom loop 180 --wad runtime-private --sha256 <expected-wad-sha256>`
- `frames_presented=180`
- `poll_count=190`
- `helper_done=1`
- `display.rc=0`
- `loop.rc=0`
- `buffer_allocations=1`
- `pace_socket.tokens_sent=180`
- `pace_socket.failures=0`
- `pace_socket.wait_timeouts=0`

## Stage Timing

| metric | V3091 large 3:2 fake-time | V3093 wall-clock large 3:2 | V3095 1:1 fake-time |
| --- | ---: | ---: | ---: |
| frames_presented | 179 | 179 | 180 |
| read.avg_us | 183 | 186 | 173 |
| begin.avg_us | 4514 | 4480 | 4558 |
| draw.avg_us | 4350 | 4281 | 766 |
| draw.max_us | 16416 | 5569 | 967 |
| present.avg_us | 3770 | 10911 | 5751 |
| present.max_us | 16901 | 15763 | 11360 |
| total.avg_us | 12818 | 19859 | 11249 |
| total.max_us | 27839 | 27633 | 17781 |
| flip_delta_avg_us | 18582 | 29311 | 16617 |
| flip_delta_max_us | 33256 | 33264 | 16638 |

## Tick Telemetry

| field | value |
| --- | ---: |
| marker | `a90.doomgeneric.v3094.tick_telemetry=scale-1to1-fake-time-summary` |
| frames_requested | 180 |
| loop_iterations | 180 |
| loop_rc | 0 |
| presented_frames | 222 |
| fake_ticks_ms | 3773 |
| sleep_calls | 3773 |
| sleep_ms_total | 3773 |
| getticks_calls | 7923 |
| i_get_time | 132 |
| gametic | 95 |
| ticrate | 35 |
| fake_time_model | `DG_SleepMs-accumulated` |
| pacing_model | `presenter-pageflip-token` |
| input_model | `udp-ncm-unix-dgram-file-fallback` |

## Findings

1. Large 3:2 CPU scaling was a real visible-stutter source. Disabling it reduced draw average from roughly `4.3ms` to `0.8ms`, draw max below `1ms`, total max from roughly `27-28ms` to `17.8ms`, and pageflip cadence from occasional `33ms` gaps to a tight `16.6ms`.
2. The presenter/pageflip path is now capable of stable 60Hz delivery when the large scaler is removed. V3095 `flip_delta_min/avg/max` was `16602/16617/16638us`.
3. The remaining perceived choppiness is therefore more likely the content/update model than raw scanout jitter: DOOM logic is `35Hz`, while the panel pageflip path is `60Hz`. Without interpolation or duplicate-frame smoothing, motion can still feel stepped even with perfect 16.6ms flips.
4. V3093 remains rejected: wall-clock sleeps worsened average flip cadence and pushed output toward every-other-vblank behavior.
5. The serial management path showed an unrelated fragility after flash: one read-only `status` command lost framing before `A90P1 END`. Restarting the host bridge and using `A90CTL_INPUT_CHAR_DELAY=0.05` recovered status/selftest. This does not affect UDP gameplay input, but status/dashboard command transport should keep the slower/recovered mode for validation.

## Next Suspects

1. Keep V3094-style 1:1 or optimize large scaling with a bounded row-copy/line-doubling strategy before re-enlarging the demo view.
2. Add a present policy that repeats DOOM frames on exact vblank cadence while only accepting new frame sequence numbers from the helper. This separates 35Hz game update from 60Hz scanout.
3. Add sequence-aware presenter metrics: new-frame count, repeated-frame count, missed sequence count, and helper-to-present latency.
4. For a larger visual demo, prefer pre-scaled helper output or direct KMS/shared-buffer rendering over per-frame CPU scaling in the presenter.
5. Treat serial status polling as separate from gameplay input and keep dashboard/status refresh sparse or transport-recovered.

## Validation

- Static source/build validation from V3094: PASS.
- Candidate boot image SHA256 check before flash: PASS.
- Flash via checked helper with readback SHA256: PASS.
- Post-flash version/status/selftest: PASS after host bridge recovery for one serial framing issue.
- DOOM status: confirmed `large_frame=0`, `frame_scale=1:1`, `shared-mmap-seq`, UDP input, and pageflip presenter.
- DOOM 180-frame loop: PASS, `loop.rc=0`.
- Tick telemetry readback: PASS.
- Post-loop selftest: PASS, `fail=0`.
