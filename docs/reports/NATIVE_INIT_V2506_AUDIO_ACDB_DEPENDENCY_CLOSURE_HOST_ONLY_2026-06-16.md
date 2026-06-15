# NATIVE_INIT V2506 — audio ACDB dependency closure host-only

Date: 2026-06-16

## Decision

`v2506-acdb-dependency-closure-host-only`

V2505 proved same-directory local staging reaches the staged
`libaudcal.so`, then blocks on its first missing DT_NEEDED dependency:
`libdiag.so`. V2506 closes that host-side gap by extracting the private vendor
ACDB dependency closure from the stock vendor ext4 image and teaching the
own-process live runner to stage that closure before the helper runs.

No device action was performed in this unit.

## Implementation

Added:

```text
workspace/public/src/scripts/revalidation/prepare_audio_acdb_dependency_closure_v2506.py
tests/test_prepare_audio_acdb_dependency_closure_v2506.py
```

The prep script is host-only and uses `debugfs` to extract the required
proprietary vendor libraries from:

```text
workspace/private/tmp/vendor-spl-check-20260612/vendor.raw.ext4
```

Private output, not committed:

```text
workspace/private/inputs/audio/acdb-deps-v2506/vendor-lib/
workspace/private/inputs/audio/acdb-deps-v2506/manifest.json
```

Updated:

```text
workspace/public/src/scripts/revalidation/native_audio_acdb_ownprocess_get_live_handoff_v2490.py
tests/test_native_audio_acdb_ownprocess_get_live_handoff_v2490.py
```

The runner now prefers the V2506 closure directory when all expected vendor
libraries are present. It falls back to the legacy V2324 two-library dump only
when the closure is absent, and reports a live blocker in that fallback state.

## Extracted Private Closure

Vendor image:

```text
path: workspace/private/tmp/vendor-spl-check-20260612/vendor.raw.ext4
sha256: 2d1e9e86923ce2ca9b03176030d0837c9743eab235b36db1e9c29af7bbe026ee
```

Extracted libraries:

```text
libaudcal.so      size=162124  sha256=3f214dc18758d360cbc39d8a5323ff76baf6b5eb6c247de141bd6d5e91f4295d
libdiag.so        size=175756  sha256=771920e96bbc1796288a430c315d93ddfb14941432baeca000c4e79292819d22
libacdb-fts.so    size=5248    sha256=800eaf98197debbb6191172b6f22df3dbb09a0d80f6a471363c925a320f1b4db
libacdbrtac.so    size=19584   sha256=2cef5b0f7444c3c94076f273f6b5841dad57d7ccb48da78f497338ded43ae6a4
libadiertac.so    size=15904   sha256=a5abcac1573133c36f0575f6dd8b3e221daab07f889c13e83fdd6b730fb4c121
libacdbloader.so  size=92500   sha256=25ae25afda6f52fc75d9b72e7f9df22094c7e3b243efb7257654ec9445bcd0a1
```

The closure satisfies the vendor-private ACDB dependencies that are present in
the vendor ext4 image. The remaining DT_NEEDED entries are treated as Android
runtime libraries expected from the normal system/default linker search path:

```text
libc++.so
libc.so
libcutils.so
libdl.so
libion.so
liblog.so
libm.so
libtinyalsa.so
libutils.so
```

`libtinyalsa.so` and `libion.so` were not present under `/vendor/lib` in this
vendor image, so V2506 does not fabricate or commit copies. The next live run
will either resolve them from the Android runtime path already in
`LD_LIBRARY_PATH`, or produce the next exact missing-library blocker.

## Dry-Run State

After extraction, the live runner dry-run reports:

```text
live_ready: true
command_safety.ok: true
source_kind: v2506-vendor-ext4-closure
closure_missing: []
staged dependency names:
  libaudcal.so
  libdiag.so
  libacdb-fts.so
  libacdbrtac.so
  libadiertac.so
  libacdbloader.so
```

The planned command still uses the same own-process pure-read execution path:

```text
LD_LIBRARY_PATH=/data/local/tmp/a90-acdb-ownget:/vendor/lib:/system/lib:/system_ext/lib:/product/lib
```

## Boundary Check

Unchanged hard boundaries:

- no in-HAL `LD_PRELOAD` or wrapper-exec injection;
- no Magisk module install;
- no HAL restart;
- no AudioTrack/playback;
- no native speaker write;
- no `/dev/msm_audio_cal` open or SET ioctl;
- no `0xC00461CB` path;
- no `acdb_loader_send_common_custom_topology`;
- no raw ACDB payload or proprietary vendor libraries committed.

## Validation

Commands run:

```text
python3 workspace/public/src/scripts/revalidation/prepare_audio_acdb_dependency_closure_v2506.py --extract

python3 workspace/public/src/scripts/revalidation/native_audio_acdb_ownprocess_get_live_handoff_v2490.py \
  --dry-run --from-native

python3 -m py_compile \
  workspace/public/src/scripts/revalidation/prepare_audio_acdb_dependency_closure_v2506.py \
  workspace/public/src/scripts/revalidation/native_audio_acdb_ownprocess_get_live_handoff_v2490.py \
  workspace/public/src/scripts/revalidation/build_android_acdb_ownprocess_get_v2489.py \
  tests/test_prepare_audio_acdb_dependency_closure_v2506.py \
  tests/test_native_audio_acdb_ownprocess_get_live_handoff_v2490.py \
  tests/test_build_android_acdb_ownprocess_get_v2489.py

PYTHONPATH=tests:workspace/public/src/scripts/revalidation python3 -m unittest \
  tests.test_prepare_audio_acdb_dependency_closure_v2506 \
  tests.test_native_audio_acdb_ownprocess_get_live_handoff_v2490 \
  tests.test_build_android_acdb_ownprocess_get_v2489 -v

git diff --check
```

Result:

```text
dependency extraction: ok
live dry-run: live_ready=true, command_safety.ok=true
py_compile: pass
unit tests: 16 passed
git diff --check: pass
```

## Next Unit

Run one checked Android handoff with the same helper SHA and the V2506 staged
dependency closure. Expected decisive outcomes:

- ACDB libraries load and the helper reaches `acdb_loader_init_v3`;
- Android runtime resolves `libtinyalsa.so`/`libion.so`, then the pure-read GET
  matrix runs and captures the topology or the full ordered out-buffer set;
- a new exact missing-library or init blocker is reported.

Do not return to in-HAL injection or wrapper-exec.
