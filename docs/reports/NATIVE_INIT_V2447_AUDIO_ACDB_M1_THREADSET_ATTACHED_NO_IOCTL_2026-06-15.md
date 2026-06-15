# NATIVE_INIT_V2447_AUDIO_ACDB_M1_THREADSET_ATTACHED_NO_IOCTL_2026-06-15

## Summary

V2447 is the exact-gated live rerun of the V2446 M1 temporary Magisk module path.
It proves the V2446 post-module wait-budget fix: Android returned after the Magisk
module activation reboot within the new `300s` budget, the temporary module service
ran, Android framework playback ran, private artifacts were collected, cleanup ran, and
the device rolled back to V2321 with `selftest fail=0`.

The functional result is still negative for raw ACDB payload capture. The M1 service
started `10` threadset helpers, attached/followed `138` tracees including clone-created
audio HAL worker TID `12004`, and observed `90` clone events, but captured `0`
`/dev/msm_audio_cal` ioctl entries/exits while Android logcat showed the speaker ACDB
edge in that same audio HAL worker.

This closes the immediate staging/timing/wait-budget wall. The remaining wall is the
capture method or syscall boundary, not Magisk module delivery.

## Live Result

Run evidence is private under:

```text
workspace/private/runs/audio/v2447-acdb-m1-magisk-module-retry-20260615-151404/
```

Public metadata:

```json
{
  "project_iteration": "V2447",
  "runner_identity": "V2446",
  "build_tag": "v2446-audio-acdb-m1-post-module-wait",
  "decision": "v2446-acdb-m1-magisk-module-retry-threadset-attached-no-msm-audio-cal-ioctl-before-rollback-rollback-pass",
  "ok": true,
  "rolled_back": true,
  "approval_ok": true
}
```

Key live steps:

```text
android-post-module-reboot-settle-0-wait-for-device: ok, elapsed=191.618s, timeout=300.0s
android-post-module-reboot-root-check-1: ok, root_ready=true
playback-start-background: ok, elapsed=3.157s
collect-private-artifacts: ok
rollback-v2321: ok, elapsed=67.486s
post-run resident image: V2321 0.9.285
post-run selftest: fail=0
```

## Capture Evidence

Payload-capture summary:

```json
{
  "classification": "threadset-attached-no-msm-audio-cal-ioctl",
  "helper_starts": 10,
  "tracee_adds": 138,
  "clone_events": 90,
  "ioctl_entries": 0,
  "ioctl_exits": 0,
  "payload_hashes": [],
  "raw_payload_in_summary": false
}
```

Helper attach errors were limited to two unrelated attach attempts:

```text
tid 5071: PTRACE_ATTACH errno=1 Operation not permitted
tid 6983: PTRACE_ATTACH errno=1 Operation not permitted
```

The relevant audio HAL process was traced:

```text
audio-hal-pids.txt: 8795
audioserver-pids.txt: 8796
service.log: A90_M1_HELPER_START tgid=8795 remaining=49 helper_duration=49
service.log: A90_M1_HELPER_START tgid=8796 remaining=49 helper_duration=49
```

The helper followed the logcat-proven audio HAL worker:

```json
{"event":"tracee-add","tid":12004}
{"event":"clone","tid":9023,"child_tid":12004}
{"event":"clone-child-resumed","tid":12004}
```

Logcat showed the expected Android speaker playback and ACDB edge:

```text
A90_AUDIO_STIMULUS_BEGIN duration_ms=2000 sample_rate=48000 amplitude=0.05 speaker_hint=true
audio_hw_primary: start_output_stream: usecase(0: deep-buffer-playback) devices(0x2)
audio_hw_primary: select_devices: ... to (2: speaker, acdb 15)
audio_hw_utils: send_app_type_cfg_for_device PLAYBACK app_type 69941, acdb_dev_id 15, sample_rate 48000
ACDB-LOADER: ACDB -> send_audio_cal, acdb_id = 15, path = 0, app id = 0x11135
ACDB-LOADER: AUDIO_SET_AUDPROC_CAL cal_type[11] acdb_id[15] app_type[69941]
```

The relevant fd snapshots did not show a persistent `/dev/msm_audio_cal` fd for the new
audio HAL/audioserver pids at artifact collection time, which is consistent with a
short-lived open/ioctl/close sequence or a different lower-level path. It does not explain
the zero syscall events by itself because worker TID `12004` was added by the helper before
the run ended.

## Interpretation

V2447 proves:

- The M1 temporary Magisk module path can execute a boot-time service, survive the
  activation reboot, and return artifacts under the checked Android-handoff/V2321 rollback
  envelope.
- The V2446 `300s` post-module ADB wait budget is sufficient for this device class; V2445's
  `120s` timeout was too short.
- The earlier thread coverage gap is not the only explanation anymore: the logcat-proven
  ACDB worker TID `12004` was attached/followed, but no ioctl entry/exit was emitted.

V2447 does **not** prove that Android no longer uses `/dev/msm_audio_cal`; logcat still names
the ACDB loader and calibration commands. It only proves that the current ptrace syscall
observer did not capture the ioctl payload under M1.

## Magisk Module Direction

The user-side analogy to the Wi-Fi work is valid: Magisk modules are useful here as a
temporary Android-good measurement capsule. They can install boot-time service hooks,
package helper binaries/scripts, observe vendor userspace under normal Android, and cleanly
remove themselves before rollback.

The boundary should stay narrow:

- Use Magisk only for Android-good measurement and early boot/service placement.
- Keep modules temporary, exact-gated, self-cleaning, and private-output only.
- Do not make Magisk part of native-init runtime.
- Do not use Magisk to execute native speaker writes or native `/dev/msm_audio_cal` replay.
- Treat M1 as the fallback when M0 transient `su -c` helpers cannot observe an early edge.

After V2447, the module direction itself is no longer the blocker. The next unit should
analyze or change the capture mechanism inside that module, not keep reworking module
install/wait/cleanup plumbing.

## Safety

Unchanged safety boundary:

- Android-good measurement only.
- Temporary Magisk module only.
- No native speaker write.
- No native `/dev/msm_audio_cal` ioctl.
- No native ACDB replay.
- Private raw artifacts remain under `workspace/private/`.
- Rollback target remains V2321.

Independent post-run verification:

```text
A90 Linux init 0.9.285 (v2321-usb-clean-identity-rodata)
selftest: pass=11 warn=1 fail=0
```

## Next Unit

V2448 should be host-only first. Do not blind-rerun M1.

Recommended V2448 work:

1. Parse the V2447 private artifacts and source to classify why a followed TID emitted zero
   ioctl events:
   - helper syscall-trap state machine,
   - `PTRACE_O_TRACECLONE` / `PTRACE_SYSCALL` sequencing,
   - syscall ABI/register decoding for Android arm64,
   - possible seccomp/zygote/vendor constraints,
   - short-lived fd lifetime versus fd-resolution timing.
2. Add timestamps to future M1 service/helper JSONL so logcat ACDB edges can be aligned to
   helper start, tracee-add, clone, syscall-entry, and timeout events.
3. Consider an alternate Android-side capture path only if source/log analysis justifies it:
   `strace`-style syscall tracing with known-good options, vendor-library wrapper/uprobes,
   or Binder/HAL-level logging. Keep raw payload bytes private and avoid native replay until
   command sequence, decoded headers, and cleanup policy are pinned.

