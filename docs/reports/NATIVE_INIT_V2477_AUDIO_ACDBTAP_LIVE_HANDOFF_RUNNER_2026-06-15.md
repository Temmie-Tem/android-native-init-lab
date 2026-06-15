# NATIVE_INIT_V2477_AUDIO_ACDBTAP_LIVE_HANDOFF_RUNNER_2026-06-15

## Decision

`v2477-acdbtap-live-handoff-runner-host-only`

V2477 implements the recoverable Android-good live handoff runner for the V2475
ACDB `acdb_ioctl` interposer and V2476 preload plan. No live Android boot,
Magisk staging, HAL restart, AudioTrack playback, native speaker write, or
native `/dev/msm_audio_cal` calibration ioctl ran in this unit.

## Scope

Added:

- `workspace/public/src/scripts/revalidation/native_audio_acdbtap_live_handoff_v2477.py`
- `tests/test_native_audio_acdbtap_live_handoff_v2477.py`

The runner is dry-run by default. Live execution requires the explicit
`--run-live` flag, but no additional human phrase: current `GOAL.md` broadly
pre-authorizes recoverable-envelope Android/Magisk measurement actions. The flag
exists to prevent accidental invocation, not to override `GOAL.md`.

## Runner behavior

V2477 composes the existing checked Android handoff and rollback functions with
the V2476 tap plan:

1. Flash the pinned stock Android boot image through the checked helper.
2. Wait for Android ADB/root settle.
3. Stage `libacdbtap.so` under `/data/local/tmp/a90-acdbtap-v2476/lib/`.
4. Stop init's `vendor.audio-hal` service and manually re-exec
   `/vendor/bin/hw/android.hardware.audio.service` with `LD_PRELOAD`.
5. Verify `/proc/<pid>/maps` contains `libacdbtap`.
6. **Abort before playback** if preload is not confirmed.
7. Start logcat capture and run the known-good bounded Android `AudioTrack`
   speaker stimulus.
8. Pull the complete `/data/local/tmp/a90-acdb-tap/` directory and summarize
   the full ordered `out_len>0` call metadata set.
9. Cleanup temporary Android paths, restart `vendor.audio-hal`, reboot to
   recovery, and checked-rollback to V2321.

## Safety gates

The runner has hard stops for:

- `preload-not-confirmed-before-rollback`: no playback runs if the tap is absent
  from the HAL maps.
- SELinux/linker denial evidence: captured by verify/logcat/dmesg; no silent
  `setenforce 0` or policy assist.
- Native replay boundary: no native calibration ioctl, no native mixer write,
  no native PCM playback.
- Own-process fallback boundary: no `acdb_loader_init_v4` guessing.

The command-safety scan rejects native calibration symbols, `tinyplay`,
`tinymix set`, silent permissive, raw partition write patterns, and
`magisk --install-module` in the executable command plan.

## Dry-run result

Command:

```bash
PYTHONPATH=workspace/public/src/scripts/revalidation \
  python3 workspace/public/src/scripts/revalidation/native_audio_acdbtap_live_handoff_v2477.py
```

Result:

- decision: `v2477-acdbtap-live-handoff-dry-run`
- `future_live_ready`: `true`
- `future_live_blockers`: `[]`
- command-safety: OK

The live-ready result means the runner inputs are present and command shape is
safe. It does not imply the manual HAL re-exec will succeed; that is the next
live discriminator.

## Acceptance and artifact summary contract

The live acceptance is **not** "one `out_len==4916` record exists." The
4916-byte `CORE_CUSTOM_TOPOLOGIES` payload is necessary, but the native playback
blocker also includes missing AFE / ASM / ADM per-device calibration. Therefore
V2477 treats the live unit as accepted only if the pulled capture contains:

- at least one ordered `acdb_ioctl` metadata record with `out_len>0`;
- private raw `.bin` bytes for every ordered metadata record;
- zero malformed JSONL event lines;
- at least one `out_len==4916` record within that complete set.

If records exist but raw bytes are missing, the result is classified as
`acdbtap-metadata-with-missing-raw`, not accepted. If records exist but no
`4916` record appears, the result is classified as
`captured-acdbtap-full-outbuf-set-no-4916`: useful evidence, but not the target
capture.

The live runner parses `acdbtap-events.jsonl` privately and publishes only:

- ordered per-call records;
- `cmd`
- `in_len`
- `out_len`
- `ret`
- `sha256`
- `raw_written`
- `is_target_4916`
- `is_size_query_4`

It deliberately strips `raw_path` from public summaries. Raw `.bin` payloads
stay under `workspace/private/runs/audio/<run>/` only. V2477 does **not** map
`cmd`/size/order to ACDB `cal_type` or construct a replay manifest; that is an
operator verification step against the V2461 `AUDIO_SET_CALIBRATION` sequence.

## Validation

Commands run:

```bash
PYTHONPATH=workspace/public/src/scripts/revalidation \
  python3 -m py_compile \
    workspace/public/src/scripts/revalidation/native_audio_acdbtap_live_handoff_v2477.py \
    tests/test_native_audio_acdbtap_live_handoff_v2477.py

PYTHONPATH=tests:workspace/public/src/scripts/revalidation \
  python3 -m unittest tests.test_native_audio_acdbtap_live_handoff_v2477 -v

PYTHONPATH=workspace/public/src/scripts/revalidation \
  python3 workspace/public/src/scripts/revalidation/native_audio_acdbtap_live_handoff_v2477.py

PYTHONPATH=tests:workspace/public/src/scripts/revalidation \
  python3 -m unittest discover -s tests -v

git diff --check
```

Results:

- focused V2477 tests: `5` passed;
- full test suite: `1270` passed;
- `git diff --check`: passed;
- dry-run: live-ready;
- live device action: none.

## Next

Run the V2477 live discriminator inside the already pre-authorized recoverable
envelope. Expected first outcomes are:

- `captured-acdbtap-full-outbuf-set-with-4916`: full ordered ACDB out-buffer
  record set captured; operator can map size/order to cal types and assemble the
  replay manifest.
- `preload-not-confirmed`: stop before playback; inspect linker/SELinux output.
- `captured-acdbtap-full-outbuf-set-no-4916`: preload path works, but the HAL did
  not hit the topology call in the observed window.
- `acdbtap-metadata-with-missing-raw`: metadata arrived, but the private raw
  payload set is incomplete; do not use it for native replay.
- `no-acdbtap-events`: preload path works or is ambiguous, but no captured
  out-buffer event reached the pulled artifact set.
