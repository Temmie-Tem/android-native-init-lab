# Native Init V3097 DOOMGENERIC Sequence Telemetry Live Validation

## Summary

- Cycle: `V3097`
- Candidate flashed: `V3096` / `A90 Linux init 0.10.104 (v3096-doomgeneric-seq-telemetry)`
- Track: active Video playback / DOOM stutter root-cause isolation.
- Decision: `v3097-doomgeneric-seq-telemetry-live-pass-new-frame-path-not-root-cause`
- Result: PASS
- Boot SHA256: `3fd4c94b855138da76c895698195699715fe15b3381e1510e5f8bb2f1e8055f8`
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
- Post-flash resident version matched `A90 Linux init 0.10.104 (v3096-doomgeneric-seq-telemetry)`.
- Post-flash status and selftest completed with selftest `fail=0` after one host bridge recovery noted below.

## Live Configuration

- Engine bridge: `v3096-doomgeneric-seq-telemetry`
- Engine active: `doomgeneric-private-link-v3096-seq-telemetry`
- Frame IPC: `shared-mmap-seq`
- Input path: `udp-ncm-to-DG_GetKey-with-serial-doompad-fallback`
- Presenter pacing: `presenter-pageflip-pace-socket`
- Presenter mode: `pageflip`
- Presenter poll: `4ms`
- Timing probe: enabled
- Sequence telemetry: enabled
- Sequence model: `frame-id-upper32-shared-seq`
- Dashboard profile: native minimal fastdraw
- Large dashboard frame: `0`
- Frame scale: `1:1`
- Scale path: `raw-rowcopy`
- Runtime WAD: SD runtime WAD verified by SHA256 and IWAD magic.

## Loop Results

| metric | 180-frame loop | 300-frame loop |
| --- | ---: | ---: |
| frames_presented | 180 | 300 |
| poll_count | 190 | 310 |
| helper_done | 1 | 1 |
| display.rc | 0 | 0 |
| loop.rc | 0 | 0 |
| buffer_allocations | 1 | 1 |
| pace_socket.tokens_sent | 180 | 300 |
| pace_socket.failures | 0 | 0 |
| pace_socket.wait_timeouts | 0 | 0 |

## Stage Timing

| metric | V3095 1:1 fake-time | V3097 180-frame | V3097 300-frame |
| --- | ---: | ---: | ---: |
| frames_presented | 180 | 180 | 300 |
| read.avg_us | 173 | 187 | 186 |
| read.max_us | - | 989 | 834 |
| begin.avg_us | 4558 | 4523 | 4513 |
| begin.max_us | - | 4683 | 4793 |
| draw.avg_us | 766 | 767 | 779 |
| draw.max_us | 967 | 906 | 1631 |
| present.avg_us | 5751 | 5739 | 5718 |
| present.max_us | 11360 | 15960 | 5897 |
| total.avg_us | 11249 | 11217 | 11196 |
| total.max_us | 17781 | 22221 | 11273 |
| flip_delta_avg_us | 16617 | 16616 | 16619 |
| flip_delta_max_us | 16638 | 16643 | 16644 |

## Sequence Telemetry

| metric | 180-frame loop | 300-frame loop |
| --- | ---: | ---: |
| read_attempts | 191 | 311 |
| read_ok | 180 | 300 |
| read_errors | 11 | 11 |
| new_frame_polls | 180 | 300 |
| duplicate_frame_polls | 0 | 0 |
| polls_without_new_frame | 11 | 11 |
| presented_frames | 180 | 300 |
| shared_sequence_samples | 180 | 300 |
| shared_first_sequence | 2 | 2 |
| shared_last_sequence | 360 | 600 |
| shared_missed_frames | 0 | 0 |
| shared_max_sequence_gap_frames | 1 | 1 |

## Tick Telemetry

| field | 180-frame loop | 300-frame loop |
| --- | ---: | ---: |
| marker | `a90.doomgeneric.v3096.tick_telemetry=seq-telemetry-fake-time-summary` | `a90.doomgeneric.v3096.tick_telemetry=seq-telemetry-fake-time-summary` |
| frames_requested | 180 | 300 |
| loop_iterations | 180 | 300 |
| loop_rc | 0 | 0 |
| helper-presented_frames | 222 | 342 |
| fake_ticks_ms | 3773 | 5487 |
| sleep_calls | 3773 | 5487 |
| sleep_ms_total | 3773 | 5487 |
| getticks_calls | 7923 | 12371 |
| i_get_time | 132 | 192 |
| gametic | 95 | 155 |
| ticrate | 35 | 35 |
| fake_time_model | `DG_SleepMs-accumulated` | `DG_SleepMs-accumulated` |
| pacing_model | `presenter-pageflip-token` | `presenter-pageflip-token` |

## Findings

1. The V3097 evidence rules out the current shared-frame sequence path as the dominant stutter cause. Both 180-frame and 300-frame loops had `duplicate_frame_polls=0`, `shared_missed_frames=0`, and `shared_max_sequence_gap_frames=1`.
2. Producer/presenter double-sleep is not active in this candidate. With the pace socket enabled, the presenter sends one token after each successful pageflip and the helper produces one new shared frame per token.
3. Pageflip cadence is stable. The 300-frame loop produced `flip_delta_min/avg/max=16593/16619/16644us`, which is effectively locked to the display refresh.
4. The remaining visible stepping is therefore more likely the DOOM content/update model than raw output jitter: the port uses `DG_SleepMs`-accumulated fake time, DOOM logic is fixed at `35Hz`, and the current presenter displays new rendered frames at roughly display cadence without interpolation.
5. A separate host-serial robustness issue was observed once after flashing: a `selftest verbose` transaction lost the command framing and no `A90P1 END` marker was parsed. Restarting the managed bridge and using `A90CTL_INPUT_CHAR_DELAY=0.05` recovered `version`, `status`, and `selftest`. Gameplay input uses UDP/NCM and is not coupled to this serial status path.
6. Foreground `video demo doom loop` rejects values above the current max frame cap. `loop 600` returned `EINVAL`; `loop 300` is the largest bounded foreground loop validated here. Longer-session testing should use `loop-start 0` plus `loop-status`/`loop-stop`.

## Next Suspects

1. Instrument per-frame `gametic` deltas, not just final `gametic`, to prove whether rendered motion changes only on 35Hz tic boundaries while scanout remains 60Hz.
2. Try a display policy that presents each DOOM game tic on an even vblank pattern, or a helper policy that only emits frames when `gametic` changes, so repeated visual states are deliberate instead of appearing as uneven motion.
3. For demo polish, consider interpolation only if feasible in the DOOM port; otherwise accept that classic DOOM movement is fixed-tic and optimize around consistent cadence rather than chasing 60 unique motion states.
4. Harden host serial status commands separately: bridge restart/recovery is currently enough for validation, but dashboard/status tooling should tolerate one lost transaction without confusing it with gameplay input failure.

## Validation

- Static source/build validation from V3096: PASS.
- Candidate boot image SHA256 check before flash: PASS.
- Flash via checked helper with readback SHA256: PASS.
- Post-flash version/status/selftest: PASS after host bridge recovery for one serial framing issue.
- DOOM status: confirmed `large_frame=0`, `frame_scale=1:1`, `shared-mmap-seq`, sequence telemetry, UDP input, and pageflip presenter.
- DOOM 180-frame loop: PASS, `loop.rc=0`, no duplicate polls, no shared-frame misses.
- DOOM 300-frame loop: PASS, `loop.rc=0`, no duplicate polls, no shared-frame misses.
- Tick telemetry readback: PASS.
- Post-loop selftest: PASS, `fail=0`.
