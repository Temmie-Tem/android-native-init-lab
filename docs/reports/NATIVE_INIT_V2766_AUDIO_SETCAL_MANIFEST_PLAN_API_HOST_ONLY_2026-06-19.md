# NATIVE_INIT_V2766_AUDIO_SETCAL_MANIFEST_PLAN_API_HOST_ONLY_2026-06-19

## Summary

V2766 moves the `audio setcal` manifest verifier from a streaming-only verifier toward a reusable executor input model.

The native-init audio command now materializes a verified `audio_setcal_manifest_plan` in memory. The plan records the manifest header, totals, per-entry cal type/role/dmabuf expectation, arg/payload paths, declared sizes, hashes, and loaded byte counts. `audio setcal --execute` still refuses before any `/dev/ion` or `/dev/msm_audio_cal` access, but its execute-plan output is now emitted from the verified plan entries rather than loose totals.

## Why

The active audio epic requires turning the one-shot speaker proof into a clean native-init feature. The SET-cal replay executor needs a single trusted input object that can later drive ION allocation and `AUDIO_SET_CALIBRATION` calls without reparsing manifest lines or re-discovering private payload metadata.

## Behavior

- Adds `struct audio_setcal_manifest_plan` and `struct audio_setcal_manifest_plan_entry`.
- Stores only entries that pass manifest order, file existence, size, SHA-256, and optional load checks.
- Carries header fields and totals into the plan after full manifest validation succeeds.
- Extends `audio.setcal.execute.plan.*` output with manifest validity/header fields and per-entry execution inputs.
- Keeps the hard safety gate: `audio setcal --execute` returns `-EPERM` before any audio device open or ioctl.

## Safety

- Host-only change; no device step and no flash.
- No `/dev/ion` open.
- No `/dev/msm_audio_cal` open.
- No calibration ioctl attempted.
- Private raw payload bytes remain under `workspace/private/`; none are committed.

## Validation

```text
python3 -m py_compile tests/test_native_audio_setcal_manifest_plan_v2766.py tests/test_native_audio_setcal_execute_gate_v2763.py
PYTHONPATH=tests python3 -m unittest tests.test_native_audio_setcal_manifest_plan_v2766 tests.test_native_audio_setcal_execute_gate_v2763
# 8 tests OK

aarch64-linux-gnu-gcc -std=gnu11 -Wall -Wextra -Werror -Iworkspace/public/src/native-init -c workspace/public/src/native-init/a90_audio.c -o /tmp/a90_audio_v2766.o
file /tmp/a90_audio_v2766.o
# ELF 64-bit LSB relocatable, ARM aarch64
sha256sum /tmp/a90_audio_v2766.o
# df7c02db9690dbfab8e465d2137c3701336e411d38897afadb193e8f6ea7a7d7

PYTHONPATH=tests python3 -m unittest discover -s tests -p 'test_native_audio_*v27*.py'
# 139 tests OK

git diff --check
# pass
```

## Next

The next non-churn step is to make a similarly explicit executor-side boundary for either:

1. `audio setcal --execute`: open-plan phase for `/dev/ion` and `/dev/msm_audio_cal` with refusal before the first ioctl, or
2. `audio play --execute`: replace the current PCM execute refusal with a bounded ALSA/tinyalsa writer after SET-cal remains proven active.
