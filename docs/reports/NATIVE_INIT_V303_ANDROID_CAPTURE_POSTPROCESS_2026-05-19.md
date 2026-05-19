# Native Init v303 Android Capture Postprocess Report

- date: `2026-05-19`
- scope: host-only postprocess harness for Android capture artifacts
- boot image change: none
- baseline device build: `A90 Linux init 0.9.60 (v261)`
- plan: `docs/plans/NATIVE_INIT_V303_ANDROID_CAPTURE_POSTPROCESS_PLAN_2026-05-19.md`
- tool: `scripts/revalidation/android_capture_postprocess.py`

## Summary

v303 adds a host-only postprocess harness for the approval-gated Android capture
maintenance window. It reads the future v300 live manifest and v297/v298 Android
property artifacts, then reports the next decision. If Android capture and
compare are ready, `run` invokes the existing host-only v301 property shim seed
model and records the resulting seed state.

No live handoff was executed.

## Evidence

| item | path | result |
| --- | --- | --- |
| waiting status | `tmp/wifi/v303-android-capture-postprocess-waiting/` | `android-capture-postprocess-waiting-for-live` |
| waiting run | `tmp/wifi/v303-android-capture-postprocess-waiting-run/` | `android-capture-postprocess-waiting-for-live` |
| synthetic ready path | `tmp/wifi/v303-synthetic/out/` | `android-capture-postprocess-seed-ready` |

## Validation

```bash
python3 -m py_compile scripts/revalidation/android_capture_postprocess.py
python3 scripts/revalidation/android_capture_postprocess.py \
  --out-dir tmp/wifi/v303-android-capture-postprocess-waiting \
  status
python3 scripts/revalidation/android_capture_postprocess.py \
  --out-dir tmp/wifi/v303-android-capture-postprocess-waiting-run \
  run
# synthetic ready-input fixture validates the v301 seed execution branch
python3 scripts/revalidation/android_capture_postprocess.py \
  --out-dir tmp/wifi/v303-synthetic/out \
  --v300-live-manifest tmp/wifi/v303-synthetic/v300/manifest.json \
  --v295-manifest tmp/wifi/v303-synthetic/v295/manifest.json \
  --v297-manifest tmp/wifi/v303-synthetic/v297/manifest.json \
  --v298-manifest tmp/wifi/v303-synthetic/v298/manifest.json \
  --v301-out-dir tmp/wifi/v303-synthetic/v301 \
  run
git diff --check
```

Result: PASS.

## Decisions

| state | meaning |
| --- | --- |
| `android-capture-postprocess-waiting-for-live` | v300 live handoff has not run yet |
| `android-capture-postprocess-live-failed` | live handoff or native rollback needs inspection |
| `android-capture-postprocess-waiting-for-capture` | Android capture/compare artifact is absent or incomplete |
| `android-capture-postprocess-seed-ready` | Android-backed v301 seed is ready for review |
| `android-capture-postprocess-seed-blocked` | seed generation failed or required keys remain blocked |

## Safety

- No device command execution.
- No ADB command execution.
- No reboot/recovery/flash.
- No property mutation or property runtime creation.
- No service-manager/HAL/Wi-Fi daemon execution.
- No Wi-Fi scan/connect/link-up/credential/DHCP/routing.

## Interpretation

The host-side path after v300 live handoff is now deterministic:

1. execute v300 live handoff only after explicit operator approval;
2. run v303 `run` to classify v300/v297/v298 and produce Android-backed v301
   seed if inputs are ready;
3. use the seed result to decide whether a future read-only property shim design
   has enough Android-backed data.

The current blocker remains explicit operator approval for the v300 live handoff.
