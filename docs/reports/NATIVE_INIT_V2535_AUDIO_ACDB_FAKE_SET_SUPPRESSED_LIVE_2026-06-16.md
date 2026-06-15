# NATIVE_INIT_V2535 — ACDB fake allocate with SET suppression

Date: 2026-06-16

## Scope

V2534 proved that fake-success for `AUDIO_ALLOCATE_CALIBRATION` advances `acdb_loader_init_v3` into the custom-topology path, but the first fake-mode preload allowed one real `AUDIO_SET_CALIBRATION` pass-through and the helper crashed before producing raw GET rows.

V2535 reran the same own-process Android handoff after host-only hardening:

```text
A90_ACDB_FAKE_ALLOCATE=1 => fake-success for AUDIO_ALLOCATE_CALIBRATION, AUDIO_DEALLOCATE_CALIBRATION, and AUDIO_SET_CALIBRATION only
```

All unrelated ioctls still pass through. No native speaker write was performed. Raw artifacts remain private.

## Private artifacts

Run directory:

```text
workspace/private/runs/audio/v2535-acdb-fake-allocate-set-suppressed-get-20260616-062322
```

Preload staged in the run:

```text
workspace/private/builds/audio/v2531-acdb-ioctl-trace-preload-host-only/bin/liba90_ioctl_trace_v2531.so
sha256=3fddb586520fe277af9d1f2102cb3ad35d089dbc81bf1fab28b33ce1a635dd23
```

## Result

Runner decision:

```text
v2490-ownprocess-context-only-no-events-before-rollback-rollback-pass
```

With the updated parser, the pulled artifact directory classifies as:

```text
ownprocess-helper-sigsegv-no-events
```

Final rollback state:

```text
A90 Linux init 0.9.285 (v2321-usb-clean-identity-rodata)
selftest: pass=11 warn=1 fail=0
```

## Evidence

Ioctl trace summary:

```json
{
  "ioctl_trace_event_count": 57,
  "audio_allocate_ioctl_count": 26,
  "audio_allocate_ioctl_intercepts": ["fake-success"],
  "audio_allocate_ioctl_fake_success_count": 26,
  "audio_deallocate_ioctl_count": 1,
  "audio_deallocate_ioctl_intercepts": ["fake-success"],
  "audio_deallocate_ioctl_fake_success_count": 1,
  "audio_set_ioctl_count": 1,
  "audio_set_ioctl_intercepts": ["fake-success"],
  "audio_set_ioctl_fake_success_count": 1,
  "audio_set_ioctl_pass_through_count": 0
}
```

This closes the V2534 boundary gap: no real kernel `AUDIO_SET_CALIBRATION` pass-through occurred in V2535.

The topology path still executes:

```text
ACDB -> send_common_custom_topology
ACDB -> ACDB_CMD_GET_AVCS_CUSTOM_TOPO_INFO_SIZE_V3
Reallocate memory for Custom Topology to size: 4916
ACDB -> allocate_cal_block: mmap
ACDB -> ACDB_CMD_GET_AVCS_CUSTOM_TOPO_INFO_V3
ACDB -> ACDB_CMD_GET_AVCS_CUSTOM_TOPO_INFO_V3: size:0x1334 ret=0
ACDB -> CORE_CUSTOM_TOPOLOGIES
ACDB -> acdb_loader_send_common_custom_topology: Common custom topology in use
```

But the helper crashes immediately afterward:

```text
ownget.rc: 139
ownget.stderr.txt: Segmentation fault
```

Crash excerpt:

```text
Fatal signal 11 (SIGSEGV), code 1 (SEGV_MAPERR), fault addr 0x0 in tid 4108
#00 pc 00008b30 /data/local/tmp/a90-acdb-ownget/libacdbloader.so
#01 pc 00009195 /data/local/tmp/a90-acdb-ownget/libacdbloader.so
#02 pc 000097a1 /data/local/tmp/a90-acdb-ownget/libacdbloader.so
```

No `acdb-ownget-events.jsonl` rows and no `acdb-ownget-*.bin` payloads were created. The helper never reached its direct `acdb_ioctl` matrix loop after init.

## Interpretation

- Fake allocation remains effective: the original V2533 `EINVAL` no longer blocks init.
- SET suppression is effective: the corrected V2535 preload kept the run inside the intended measurement boundary.
- The remaining blocker is not kernel allocation or SELinux; it is a user-space `libacdbloader.so` crash after `send_common_custom_topology` completes its internal GET and no-op SET path.
- The topology bytes likely pass through `acdb_ioctl` inside `send_common_custom_topology` before the crash, but the current V2529 helper only writes raw `acdb_ioctl` rows from its post-init direct GET loop. That loop is never reached.

## Host changes in this iteration

`native_audio_acdb_ownprocess_get_live_handoff_v2490.py` now treats a real `AUDIO_SET_CALIBRATION` pass-through as a first-class boundary violation:

```text
ownprocess-real-audio-set-passthrough
```

It also classifies a no-row helper crash as:

```text
ownprocess-helper-sigsegv-no-events
```

The older V2534 artifact now reclassifies correctly as `ownprocess-real-audio-set-passthrough`; V2535 classifies as `ownprocess-helper-sigsegv-no-events`.

## Validation

```text
python3 -m py_compile \
  workspace/public/src/scripts/revalidation/build_android_ioctl_trace_preload_v2531.py \
  workspace/public/src/scripts/revalidation/native_audio_acdb_ownprocess_get_live_handoff_v2490.py \
  tests/test_build_android_ioctl_trace_preload_v2531.py \
  tests/test_native_audio_acdb_ownprocess_get_live_handoff_v2490.py

PYTHONPATH=tests python3 -m unittest \
  tests.test_build_android_ioctl_trace_preload_v2531 \
  tests.test_native_audio_acdb_ownprocess_get_live_handoff_v2490

Ran 31 tests in 0.577s — OK
```

V2535 live rollback check:

```text
version: 0.9.285 build=v2321-usb-clean-identity-rodata
selftest: pass=11 warn=1 fail=0
```

## Next

Do not advance to native replay from V2535. The next useful unit is to capture `acdb_ioctl` inside the loader's internal `send_common_custom_topology` call before the crash, instead of waiting for the helper's post-init direct GET loop. The lowest-risk route is an own-process `acdb_ioctl` interposer stacked with the existing ioctl fake-success preload, writing raw `out_buf` rows before `libacdbloader.so` reaches the crashing post-topology path.
