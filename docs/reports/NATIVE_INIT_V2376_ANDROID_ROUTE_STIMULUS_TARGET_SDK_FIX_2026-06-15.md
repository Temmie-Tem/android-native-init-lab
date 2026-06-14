# NATIVE_INIT V2376 — Android route stimulus APK target SDK fix

## Scope

V2376 is a host-only fix after V2375. V2375 proved that APK-mode route-delta handoff, APK install, cleanup, Android rollback, and final V2321 health all work, but the stimulus Activity did not execute because Android redirected first launch to PermissionController review.

This unit changes only the public APK manifest/test source and rebuilds the private APK under `workspace/private/`. It does not flash, boot Android, install the APK on a device, play audio, run native `tinymix set`, open/write `/dev/snd`, run `tinyplay`, or touch Wi-Fi/network state.

## Root Cause Addressed

V2375 `aapt dump badging` showed the APK had no explicit target SDK, causing Android to treat it as `targetSdkVersion < 4` and add implied dangerous permissions:

```text
WRITE_EXTERNAL_STORAGE
READ_PHONE_STATE
READ_EXTERNAL_STORAGE
```

Those implied permissions triggered `android.intent.action.REVIEW_PERMISSIONS` before the Activity reached `onCreate()`.

## Change

`workspace/public/src/android/audio_route_stimulus_apk/AndroidManifest.xml` now declares an explicit modern SDK envelope:

```xml
<uses-sdk android:minSdkVersion="23" android:targetSdkVersion="31" />
```

The existing `MODIFY_AUDIO_SETTINGS` permission remains because the stimulus uses `AudioManager.setSpeakerphoneOn(true)` as a speaker-route hint.

The builder regression test now asserts the manifest contains both SDK attributes so this failure mode cannot silently return.

## Private Rebuild Result

The private APK was rebuilt in place:

```text
apk=workspace/private/builds/audio/v2373-android-route-stimulus-apk/A90AudioRouteStimulus.apk
apk_sha256=fef87886bd1fb5f3dd07b857bbe3c4c00f9046f797ba9c84d48b89dc1d2d13f3
apk_size=12691
apk_mode=0o600
file=Android package (APK), with AndroidManifest.xml, with APK Signing Block
apksigner=Verifies; v1=true v2=true v3=true signers=1
```

Host `aapt dump badging` now reports:

```text
sdkVersion:'23'
targetSdkVersion:'31'
uses-permission: name='android.permission.MODIFY_AUDIO_SETTINGS'
```

The previous implied dangerous permissions are absent:

```text
uses-implied-permission=0
WRITE_EXTERNAL_STORAGE=0
READ_PHONE_STATE=0
READ_EXTERNAL_STORAGE=0
targetSdkVersion < 4=0
```

The route-delta runner dry-run with the rebuilt APK reports:

```text
runner_ok=True
runner_live_ready=True
runner_safety=True
apk_sha=fef87886bd1fb5f3dd07b857bbe3c4c00f9046f797ba9c84d48b89dc1d2d13f3
```

## Magisk Direction

The V2375 permission-review blocker was a normal APK manifest bug, not evidence that APK delivery is structurally impossible. Magisk-module delivery remains deferred. Reconsider it only if the modern-target APK still cannot launch or produce an AudioFlinger-active stimulus window.

## Validation

```text
python3 workspace/public/src/scripts/revalidation/build_android_audio_route_stimulus_apk_v2373.py
file workspace/private/builds/audio/v2373-android-route-stimulus-apk/A90AudioRouteStimulus.apk
apksigner verify --verbose workspace/private/builds/audio/v2373-android-route-stimulus-apk/A90AudioRouteStimulus.apk
workspace/private/inputs/android-sdk-v2368/build-tools/35.0.0/aapt dump badging workspace/private/builds/audio/v2373-android-route-stimulus-apk/A90AudioRouteStimulus.apk
workspace/private/inputs/android-sdk-v2368/build-tools/35.0.0/aapt dump permissions workspace/private/builds/audio/v2373-android-route-stimulus-apk/A90AudioRouteStimulus.apk
python3 workspace/public/src/scripts/revalidation/native_audio_android_route_delta_handoff_v2365.py --dry-run --stimulus-mode apk --stimulus-apk workspace/private/builds/audio/v2373-android-route-stimulus-apk/A90AudioRouteStimulus.apk
python3 -m py_compile workspace/public/src/scripts/revalidation/build_android_audio_route_stimulus_apk_v2373.py tests/test_build_android_audio_route_stimulus_apk_v2373.py workspace/public/src/scripts/revalidation/native_audio_android_route_delta_handoff_v2365.py
PYTHONPATH=tests python3 -m unittest tests.test_build_android_audio_route_stimulus_apk_v2373 tests.test_native_audio_android_route_delta_handoff_v2365 -v
python3 -m unittest discover -s tests -p 'test_*.py'
git diff --check
```

Results:

```text
focused APK/route-delta tests: 14 passed
full unittest discovery: 1051 passed
git diff --check: passed
```

## Decision

```text
android-route-stimulus-modern-target-apk-ready
```

Next unit should rerun the preauthorized Android route-delta live path with this rebuilt APK and V2372 logcat observability. If the Activity launches and AudioFlinger sees the package, inspect the active route/mixer delta. If Android still blocks launch, classify the new blocker from logcat before considering Magisk-module delivery.
