# NATIVE_INIT V2416 — Android ACDB payload capture live result

## Scope

- Unit: AUD-5D / N3-CAP live Android-good `/dev/msm_audio_cal` payload observation.
- Goal: capture stock Android audio HAL `msm_audio_cal` ioctl command order and private request-buffer bytes around bounded speaker `AudioTrack` playback.
- Safety boundary: Android/Magisk measurement only; no native calibration ioctl, no native speaker write, no persistent Magisk module, rollback to V2321.
- Private evidence roots:
  - `workspace/private/runs/audio/v2416-acdb-payload-capture-20260615-094018/`
  - `workspace/private/runs/audio/v2416-acdb-payload-capture-20260615-094624/`

## Result

V2416 did not capture ioctl payloads, but it produced a useful discriminator.

| Attempt | Decision | Rollback | Payload capture |
| --- | --- | --- | --- |
| `20260615-094018` | `target-pids-found-helper-did-not-start` | V2321 pass | artifact pull failed on helper JSONL permissions |
| `20260615-094624` | `no-msm-audio-cal-ioctl-observed` | V2321 pass | two helpers started, zero ioctl entries/exits |

The second run fixed the artifact permission issue by adding a root chmod step before `adb pull`.
It confirmed the helper could start and artifacts could be collected, but the process-level ptrace attachment missed the real ACDB ioctl edge.

## Key evidence

- Final device rollback state after the second run:
  - `A90 Linux init 0.9.285 (v2321-usb-clean-identity-rodata)`
  - `selftest: pass=11 warn=1 fail=0`
- Second-run capture summary:
  - target audio HAL PID: `795`
  - target audioserver PID: `917`
  - helper starts: `2`
  - ioctl entries: `0`
  - ioctl exits: `0`
  - raw payload in public summary: `false`
- The audio HAL had `/dev/msm_audio_cal` open during capture:
  - `proc-795-fd.txt`: fd `14 -> /dev/msm_audio_cal`
- Android logcat proves the calibration edge did occur during the capture window, but on an audio HAL worker thread:
  - `select_devices` switched to speaker with `acdb 15`
  - `send_app_type_cfg_for_device PLAYBACK app_type 69941, acdb_dev_id 15, sample_rate 48000`
  - `AUDIO_SET_AUDPROC_CAL cal_type[11] acdb_id[15] app_type[69941]`
  - `AUDIO_SET_AFE_CAL cal_type[16] acdb_id[15]`
  - logcat PID/TID pair for the relevant edge: `795/4198`

## Interpretation

The miss is not evidence that `msm_audio_cal` payload capture is impossible and not a reason to escalate immediately to a Magisk boot module.
The current helper attaches only to process main threads (`android.hardware.audio.service` PID and `audioserver` PID). The observed ACDB edge runs in a separate audio HAL worker TID. Linux `ptrace(PTRACE_ATTACH, pid)` attaches a single thread, not a full thread group, so the helper can miss ioctl syscalls issued by sibling threads even while the process owns `/dev/msm_audio_cal`.

## Magisk direction

Keep the Wi-Fi-style Magisk model, but do not jump to M1 yet.

- M0 remains the default: transient Android/Magisk-root observer staged under `/data/local/tmp`, cleaned before rollback, no persistent module install.
- The immediate fix is a thread-complete M0 observer: enumerate `/proc/<pid>/task/*` for the audio HAL and audioserver and attach one helper per TID.
- M1 temporary Magisk boot module is justified only if thread-complete M0 still reports a true `missed-early-payload` condition, meaning the payload occurs before a transient helper can attach.
- A Magisk module remains a measurement delivery mechanism only. It must not become a native-init runtime dependency.

## Next unit

V2417 should be host-only first:

1. Update the capture controller to enumerate every TID under each target audio process.
2. Start the existing helper per TID with per-thread JSONL names.
3. Preserve process-level fd/maps snapshots and add thread list snapshots.
4. Keep the same AUD-5D safety boundary: Android-good observation only, no native calibration ioctl, no native speaker write, no persistent Magisk install.
5. Re-run the exact-gated live capture only after static validation.

Expected discriminator:

- If thread-complete M0 captures `msm_audio_cal` ioctl entries, proceed to offline decode and native replay design.
- If thread-complete M0 sees no ioctl entries while logcat still shows ACDB edges, classify as true early/opaque payload miss and then design M1 temporary Magisk boot-module capture as a separate V-iteration.
