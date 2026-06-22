# Native Init V3099 DOOMGENERIC Gametic Frame Telemetry Live Validation

## Summary

- Cycle: `V3099`
- Candidate flashed: `V3098` / `A90 Linux init 0.10.105 (v3098-doomgeneric-gametic-frame-telemetry)`
- Track: active Video playback / DOOM fixed-tic root-cause isolation.
- Decision: `v3099-doomgeneric-gametic-frame-telemetry-live-pass-fixed-tic-stepping-confirmed`
- Result: PASS
- Boot SHA256: `b87ff2045aa43b96706a743a6d4fa8095bafd2644caa6fc8a98bd5204ceca16f`
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
- Post-flash resident version matched `A90 Linux init 0.10.105 (v3098-doomgeneric-gametic-frame-telemetry)`.
- Post-flash status and selftest completed with selftest `fail=0`.

## Live Configuration

- Engine bridge: `v3098-doomgeneric-gametic-frame-telemetry`
- Engine active: `doomgeneric-private-link-v3098-gametic-frame-telemetry`
- Frame IPC: `shared-mmap-seq`
- Input path: `udp-ncm-to-DG_GetKey-with-serial-doompad-fallback`
- Presenter pacing: `presenter-pageflip-pace-socket`
- Presenter mode: `pageflip`
- Presenter poll: `4ms`
- Timing probe: enabled
- Sequence telemetry: enabled
- Gametic frame telemetry: enabled
- Dashboard profile: native minimal fastdraw
- Large dashboard frame: `0`
- Frame scale: `1:1`
- Runtime WAD: SD runtime WAD verified by SHA256 and IWAD magic.

## Loop Results

| metric | 180-frame loop | 300-frame loop |
| --- | ---: | ---: |
| frames_presented | 180 | 300 |
| poll_count | 190 | 312 |
| helper_done | 1 | 1 |
| display.rc | 0 | 0 |
| loop.rc | 0 | 0 |
| pace_socket.tokens_sent | 180 | 300 |
| pace_socket.failures | 0 | 0 |
| pace_socket.wait_timeouts | 0 | 0 |

## Presenter / Frame IPC Telemetry

| metric | 180-frame loop | 300-frame loop |
| --- | ---: | ---: |
| read_attempts | 191 | 313 |
| read_ok | 180 | 301 |
| read_errors | 11 | 12 |
| new_frame_polls | 180 | 300 |
| duplicate_frame_polls | 0 | 1 |
| polls_without_new_frame | 11 | 13 |
| presented_frames | 180 | 300 |
| shared_sequence_samples | 180 | 300 |
| shared_first_sequence | 2 | 2 |
| shared_last_sequence | 360 | 600 |
| shared_missed_frames | 0 | 0 |
| shared_max_sequence_gap_frames | 1 | 1 |

## Pageflip / Stage Timing

| metric | 180-frame loop | 300-frame loop |
| --- | ---: | ---: |
| read.avg_us | 179 | 182 |
| begin.avg_us | 4550 | 4550 |
| draw.avg_us | 774 | 792 |
| present.avg_us | 5693 | 5651 |
| total.avg_us | 11197 | 11176 |
| total.max_us | 13364 | 19875 |
| flip_delta_min_us | 16606 | 16599 |
| flip_delta_avg_us | 16621 | 16622 |
| flip_delta_max_us | 16650 | 16664 |

## Gametic Frame Telemetry

| field | 180-frame loop | 300-frame loop |
| --- | ---: | ---: |
| frames_requested | 180 | 300 |
| loop_iterations | 180 | 300 |
| helper-presented_frames | 222 | 342 |
| fake_ticks_ms | 3773 | 5487 |
| i_get_time | 132 | 192 |
| final_gametic | 95 | 155 |
| frame_gametic.samples | 180 | 300 |
| frame_gametic.first | 6 | 6 |
| frame_gametic.last | 95 | 155 |
| frame_gametic.changed_transitions | 89 | 149 |
| frame_gametic.repeated_transitions | 90 | 150 |
| frame_gametic.positive_delta_total | 89 | 149 |
| frame_gametic.max_delta | 1 | 1 |
| frame_gametic.reset_transitions | 0 | 0 |
| frame_gametic.max_same_run | 2 | 2 |
| frame_gametic.transition_samples | 179 | 299 |
| ticrate | 35 | 35 |

## Findings

1. V3099 confirms fixed-tic stepping as the remaining visible choppiness source. In the 300-frame run, 150 of 299 frame-to-frame transitions repeated the same `gametic`, while only 149 advanced. The 180-frame run matches the same pattern: 90 repeated, 89 advanced.
2. Each `gametic` advance is clean: `max_delta=1`, `reset_transitions=0`, and `max_same_run=2`. This is not random frame loss; it is a stable 35Hz game-state cadence shown through a stable 60Hz presenter.
3. The output path remains healthy: both loops had `shared_missed_frames=0`, `shared_max_sequence_gap_frames=1`, and pageflip average around `16.62ms`.
4. The single 300-frame `duplicate_frame_polls=1` was a polling observation, not a duplicate presentation. `new_frame_polls=300`, `presented_frames=300`, and shared sequence still had no misses.
5. The serial command echo remains mildly fragile after reboot: stray/garbled echo appeared before valid `A90P1 BEGIN` on two commands. The command protocol still returned `A90P1 END` and `rc=0`; gameplay input remains on UDP/NCM and is not affected.

## Next Suspects

1. Decide presentation policy: either accept the classic DOOM 35Hz motion cadence, or make it explicit by emitting/presenting only on `gametic` changes and holding frames on exact vblank cadence.
2. If smoother motion is required, investigate interpolation in the DOOM render path. That is a larger engine-level change and not a KMS/IPC bottleneck fix.
3. Harden serial command echo/recovery for dashboard/status tooling separately from gameplay input.
4. DOOM audio remains separate: current image uses `native-audio-corun-tone-v3053`, not real DOOM SFX/music.

## Validation

- Static source/build validation from V3098: PASS.
- Candidate boot image SHA256 check before flash: PASS.
- Flash via checked helper with readback SHA256: PASS.
- Post-flash version/status/selftest: PASS.
- DOOM status: confirmed V3098 helper, `large_frame=0`, `frame_scale=1:1`, `shared-mmap-seq`, sequence telemetry, UDP input, and pageflip presenter.
- DOOM 180-frame loop: PASS, `loop.rc=0`, no shared-frame misses, fixed-tic repeat pattern observed.
- DOOM 300-frame loop: PASS, `loop.rc=0`, no shared-frame misses, fixed-tic repeat pattern observed.
- Tick/gametic telemetry readback: PASS.
- Post-loop selftest: PASS, `fail=0`.
