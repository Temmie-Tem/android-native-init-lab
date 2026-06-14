# NATIVE_INIT_V2371_ANDROID_ROUTE_DELTA_LIVE_STIMULUS_KILLED_2026-06-15

## Scope

V2371 used the exact AUD-3D2 gate to perform the first rollbackable Android route-delta live capture attempt.

Approval phrase used:

```text
AUD-3D2-android-route-delta go: rollbackable Android AudioTrack speaker route-delta capture, checked-helper boot handoff only, low-amplitude framework playback, no native speaker write, rollback to V2321
```

This run intentionally used Android framework `AudioTrack` through `app_process`; it did not run native `tinymix set`, native `/dev/snd` open/write, `tinyplay`, Wi-Fi, credentials, DHCP, routes, or ping. Only the boot partition was flashed through `native_init_flash.py`.

## Run Artifact

Private evidence directory:

```text
workspace/private/runs/audio/v2369-android-route-delta-20260615-033214/
```

The runner still records its internal historical live tag as `V2369`; this report is the V2371 live execution record.

## Preflight

- Worktree was clean before live execution.
- Rollback images verified:
  - V2321 SHA256 `ca978551aabe4b39563abaf529ccf2522054952d8b2ad852e632d26da88168cb`
  - V2237 SHA256 `b2ea2d26d160b7702ce7d4438b84367788eea26c6a5bbe4ed93f3d270292ac7f`
  - V48 SHA256 `1c87fa59712395027c5c2e489b15c4f6ddefabc3c50f78d3c235c4508a63e042`
- Resident V2321 health before the run: `selftest fail=0`, version `0.9.285`.
- Route-delta dry-run with the private DEX reported:
  - `ok=True`
  - `live_ready=True`
  - `command_safety.ok=True`
  - Android boot candidate OK
  - V2321 rollback image OK
  - stimulus DEX OK
  - V2345 `tinymix` OK

## Execution Result

Runner result:

```text
decision=v2369-android-route-delta-live-captured-before-rollback
ok=True
rolled_back=True
steps=26
```

Major phases:

| Phase | Result |
| --- | --- |
| Flash Android boot | `rc=0`, Android root check passed |
| Stage `tinymix` + DEX | `rc=0` for all staging steps |
| Baseline snapshots | `tinymix`, `dumpsys`, `/proc/asound` captured |
| Background AudioTrack stimulus | command dispatched with `--amplitude 0.05` |
| Active snapshots | captured |
| Playback result | `Killed`, rc `137` |
| Post snapshots | captured |
| Cleanup | remote temp dir removed |
| Android reboot recovery | `rc=0` |
| V2321 rollback | `rc=0` |
| Final V2321 health | `selftest fail=0`, version `0.9.285` |

## Audio Findings

The route-delta measurement did **not** reveal a speaker mixer route because the Java stimulus did not stay alive.

- Stimulus stdout: `Killed`
- Stimulus rc: `137`
- Parsed `tinymix -D 0 --all-values` controls:
  - baseline controls: `381`
  - active controls: `381`
  - post controls: `381`
  - changed controls across baseline/active/post: `0`
- Watch controls stayed stable:
  - `SEC_TDM_RX_0`: unchanged
  - `WSA_CDC_DMA_RX_0`: unchanged
  - `RX INT7`: no active delta observed
  - `COMP7`: unchanged (`Off`)
  - `Spkr` / `SPKR`: unchanged
  - `SLIMBUS_0_RX`: no active delta observed
- `dumpsys media.audio_policy` was identical across baseline/active/post.
- `/proc/asound/cards` and `/proc/asound/pcm` were identical across baseline/active/post.
- `dumpsys media.audio_flinger` showed speaker-capable output threads, but no nonzero active `Tracks` were present in baseline, active, or post snapshots.

Interpretation: this is a valid rollbackable Android handoff and capture attempt, but it is **not** a valid Android speaker-route delta. The blocker is now the Android stimulus execution method, not the native audio route itself.

## Decision

```text
android-route-delta-stimulus-killed-no-mixer-delta
```

The next unit should not blindly rerun the same capture. It should first fix observability/execution for the Android stimulus path. Minimum next design points:

1. Capture Android `logcat` around the stimulus window to identify who kills `app_process` and why.
2. Consider replacing raw `app_process` with a small debuggable APK or shell-compatible Android component if raw `app_process` is policy-killed.
3. Keep the same exact AUD-3D2 gate for any future Android playback attempt.
4. Keep native speaker writes, `tinymix set`, PCM playback, and `tinyplay` blocked until a real Android route delta exists.

## Validation

```text
python3 workspace/public/src/scripts/revalidation/native_init_flash.py --verify-only --expect-version 0.9.285 --verify-protocol selftest
```

Final validation passed: V2321 `selftest fail=0`, version `0.9.285`.

`git diff --check` is recorded in the V2371 commit validation.
