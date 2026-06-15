# NATIVE_INIT V2504 — audio ACDB local dependency staging host-only

Date: 2026-06-16

## Decision

`v2504-acdb-local-staging-host-only`

V2503 closed the cheap linker namespace name variants: `libaudcal.so` and the
absolute `/vendor/lib/libaudcal.so` both failed in all visible namespaces. V2504
prepares the next bounded live unit by removing namespace search from the first
ACDB dependency load: the helper now tries same-directory local copies under
`/data/local/tmp/a90-acdb-ownget/` before falling back to the V2503 namespace
path, and the live runner now stages the available private ACDB libraries next
to the helper.

No live device action was performed in this unit.

## Implementation

Updated `workspace/public/src/android/acdb_payload_capture/a90_acdb_ownprocess_get_v2489.c`:

- first tries plain `dlopen()` of:
  - `/data/local/tmp/a90-acdb-ownget/libaudcal.so`
  - `/data/local/tmp/a90-acdb-ownget/libacdbloader.so`
- records these attempts as `namespace_load` events with scope `plain-local`;
- if local `libaudcal.so` is absent or blocked, falls back to the existing
  namespace API path from V2502/V2503;
- preserves the same pure-read ACDB GET matrix after `acdb_loader_init_v3` and
  `acdb_ioctl` are resolved.

Updated `workspace/public/src/scripts/revalidation/native_audio_acdb_ownprocess_get_live_handoff_v2490.py`:

- adds private dependency state to dry-run output;
- pushes available private ACDB libraries from the V2324 vendor dump next to the
  helper before execution;
- prefixes `LD_LIBRARY_PATH` with `/data/local/tmp/a90-acdb-ownget`;
- includes staged libs in the existing chmod/listing step;
- requires the staged dependency set to exist for `live_ready=true`.

## Private Dependency Inventory

Current private V2324 vendor dump contains only these ACDB helper dependencies:

```text
libaudcal.so     sha256=3f214dc18758d360cbc39d8a5323ff76baf6b5eb6c247de141bd6d5e91f4295d
libacdbloader.so sha256=25ae25afda6f52fc75d9b72e7f9df22094c7e3b243efb7257654ec9445bcd0a1
```

The operator-requested auxiliary libs (`libacdb-fts.so`, `libacdbrtac.so`,
`libadiertac.so`) are not present in this private dump. V2504 therefore stages
only the two available libs and treats any missing DT_NEEDED dependency as the
next live outcome to classify, not as a host-only blocker.

Host readelf inventory confirms:

```text
libaudcal.so NEEDED: libutils, liblog, libdiag, libc++, libc, libm, libdl
libacdbloader.so NEEDED: libcutils, libutils, liblog, libaudcal, libtinyalsa,
                         libacdbrtac, libadiertac, libacdb-fts, libion,
                         libc++, libc, libm, libdl
```

## Boundary Check

Unchanged hard boundaries:

- no `/dev/msm_audio_cal`;
- no `0xC00461CB`;
- no `AUDIO_SET_CALIBRATION` or calibration SET path;
- no `acdb_loader_send_common_custom_topology`;
- no HAL injection, Magisk module, HAL restart, AudioTrack/playback, or native
  speaker write;
- no raw ACDB payload committed;
- staged vendor libraries stay private and are not committed.

The public helper still imports only `dlopen`, `dlsym`, and `dlerror`.

## Private Build Artifact

Private build output, not committed:

```text
path: workspace/private/builds/audio/v2489-acdb-ownprocess-get-host-only/bin/a90_acdb_ownprocess_get_v2489
sha256: 4fe262f5ef57390c306656ce6693ca57430b67479efac16c4b87f0ef75321834
file: ELF 32-bit LSB shared object, ARM, EABI5, dynamically linked, interpreter /system/bin/linker
readelf undefined imports: dlopen, dlsym, dlerror only
```

## Validation

Commands run:

```text
python3 -m py_compile \
  workspace/public/src/scripts/revalidation/build_android_acdb_ownprocess_get_v2489.py \
  workspace/public/src/scripts/revalidation/native_audio_acdb_ownprocess_get_live_handoff_v2490.py \
  tests/test_build_android_acdb_ownprocess_get_v2489.py \
  tests/test_native_audio_acdb_ownprocess_get_live_handoff_v2490.py

PYTHONPATH=tests:workspace/public/src/scripts/revalidation python3 -m unittest \
  tests.test_build_android_acdb_ownprocess_get_v2489 \
  tests.test_native_audio_acdb_ownprocess_get_live_handoff_v2490 -v

python3 workspace/public/src/scripts/revalidation/build_android_acdb_ownprocess_get_v2489.py --build

python3 workspace/public/src/scripts/revalidation/native_audio_acdb_ownprocess_get_live_handoff_v2490.py \
  --dry-run --from-native
```

Result:

```text
py_compile: pass
unit tests: 14 passed
source required_ok: true
source prohibited_ok: true
build: ok
live dry-run: live_ready=true, command_safety.ok=true, dependency push_count=2
```

## Next Unit

Run one bounded Android handoff with the V2504 helper SHA:

```text
4fe262f5ef57390c306656ce6693ca57430b67479efac16c4b87f0ef75321834
```

Expected decisive outcomes:

- `plain-local` `libaudcal.so` succeeds and `libacdbloader.so` reaches the next
  missing dependency, giving an exact DT_NEEDED blocker;
- both local and namespace loads fail, proving `/data/local/tmp` path loading is
  also linker-policy blocked;
- local loader succeeds and the helper reaches `acdb_loader_init_v3` or the
  pure-read GET matrix.

Do not return to in-HAL injection or wrapper-exec.
