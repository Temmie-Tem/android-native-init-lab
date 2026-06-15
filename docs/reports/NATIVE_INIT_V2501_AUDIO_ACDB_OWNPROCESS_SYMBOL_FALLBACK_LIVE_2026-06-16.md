# NATIVE_INIT V2501 — audio ACDB own-process symbol fallback live

Date: 2026-06-16

## Decision

`v2501-namespace-visible-load-failed-libaudcal`

V2501 ran the V2500 ARM32 own-process ACDB helper once through the checked
Android handoff and rolled back to V2321. The helper no longer stops at the
public `android_get_exported_namespace` wrapper gap: it resolved the loader
private namespace getter and public `android_dlopen_ext`, enumerated visible
namespaces, and attempted namespaced loads. The remaining blocker is that every
visible namespace still reports `/vendor/lib/libaudcal.so` as not found.

No ACDB GET call was reached. No raw ACDB payload was captured.

## Live Run

Private run directory, not committed:

```text
workspace/private/runs/audio/v2501-acdb-ownprocess-loader-fallback-live-20260616-022906
```

Helper artifact used:

```text
path: workspace/private/builds/audio/v2489-acdb-ownprocess-get-host-only/bin/a90_acdb_ownprocess_get_v2489
sha256: 176253735d7fc42e49909c75b0aeb7a2864db73f43c00ca3c81b63626b9ed413
```

Runner decision:

```text
v2490-namespace-visible-load-failed-before-rollback-rollback-pass
```

The runner name/build tag remains the reused V2490 live handoff harness; the
iteration/result identity for this report is V2501.

## Observed Events

`symbol_probe` records were preserved by the V2501 parser update:

```text
libdl:android_get_exported_namespace                 found=false detail="undefined symbol: android_get_exported_namespace"
default:android_get_exported_namespace               found=false detail="dlsym failed: library handle is null"
default:__loader_android_get_exported_namespace      found=false detail="dlsym failed: library handle is null"
libdl:__loader_android_get_exported_namespace        found=true
libdl:android_dlopen_ext                             found=true
```

Namespace probing then started:

```text
sphal   visible=true   load /vendor/lib/libaudcal.so: failed, not found
vendor  visible=false
default visible=true   load /vendor/lib/libaudcal.so: failed, not found
vndk    visible=true   load /vendor/lib/libaudcal.so: failed, not found
```

Final helper error:

```text
stage: namespace-visible-load-failed-libaudcal
code: -5
```

Artifact summary:

```text
acdb_ioctl row_count: 0
raw_file_count: 0
target_4916_count: 0
namespace_event_count: 7
symbol_event_count: 5
ownget stdout/stderr: empty
```

## Boundary Check

The live unit stayed inside the own-process pure-read boundary:

- no in-HAL `LD_PRELOAD` or wrapper-exec injection;
- no Magisk module install;
- no HAL restart;
- no AudioTrack/playback;
- no native speaker write;
- no `/dev/msm_audio_cal` open or SET ioctl;
- no `0xC00461CB` path;
- no raw payload committed.

## Rollback / Health

The checked handoff booted Android, staged and ran the helper, pulled the private
artifact directory, cleaned `/data/local/tmp/a90-acdb-ownget`, rebooted recovery,
and flashed V2321 through `native_init_flash.py`.

Post-rollback native health was verified:

```text
version: 0.9.285 build=v2321-usb-clean-identity-rodata
selftest: fail=0
```

A first host `a90ctl` health read saw a stray `AT` response and failed protocol
parsing, but a bridge status check selected the expected `A90-LNX` ACM device and
repeat `version`/`selftest verbose` succeeded. The device is back on V2321.

## Validation

Host-side validation before live:

```text
python3 -m py_compile \
  workspace/public/src/scripts/revalidation/native_audio_acdb_ownprocess_get_live_handoff_v2490.py \
  tests/test_native_audio_acdb_ownprocess_get_live_handoff_v2490.py

PYTHONPATH=tests:workspace/public/src/scripts/revalidation python3 -m unittest \
  tests.test_native_audio_acdb_ownprocess_get_live_handoff_v2490 -v

python3 workspace/public/src/scripts/revalidation/native_audio_acdb_ownprocess_get_live_handoff_v2490.py \
  --dry-run --from-native
```

Result:

```text
py_compile: pass
unit tests: 9 passed
dry-run: live_ready=true, command_safety.ok=true
```

## Interpretation

V2501 narrows the blocker. The prior V2499 failure was not final: the device's
`libdl` exposes `__loader_android_get_exported_namespace`, and the helper can see
`sphal`, `default`, and `vndk`. The unresolved problem is load policy/path
resolution for `/vendor/lib/libaudcal.so` from this shell/su own-process helper.

The next useful unit should be host-first or measurement-only:

1. pull or inspect the device-matched `/system/lib/libdl.so`, `/system/bin/linker`,
   `/linkerconfig`, and `/vendor/lib/libaudcal.so` metadata privately; or
2. modify the helper to stage a private copy of the ACDB dependency set into the
   same executable directory and load by local filename, still pure-read and
   without `/dev/msm_audio_cal`.

Do not return to in-HAL injection or wrapper-exec. That path remains on hold.
