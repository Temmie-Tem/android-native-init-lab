# NATIVE_INIT V2514 — ACDB own-process logcat observability hardening (host-only)

## Summary

- **Decision:** `v2514-acdb-ownprocess-logcat-observability-host-only`
- **Scope:** host-only runner hardening after V2513 still blocked at `acdb_loader_init_v3 == -19`.
- **Device action:** none.
- **Flash action:** none.

V2513 proved that switching the helper to `/vendor/etc/audconf/OPEN` was not sufficient: `acdb_loader_init_v3` still returned `-19` before any `acdb_ioctl` row. The operator spec identifies two source-confirmed `-19` branches, both logged under `ACDB-LOADER`, so repeating the same live helper without log capture would be low-value churn.

## Changes

Updated `workspace/public/src/scripts/revalidation/native_audio_acdb_ownprocess_get_live_handoff_v2490.py`:

- Clear Android logcat immediately before the helper run:
  - `ownget-logcat-clear`
- Capture diagnostics immediately after the helper run:
  - `logcat-acdb-loader.txt`
  - `logcat-avc-acdb-filter.txt`
  - `dmesg-avc-acdb-filter.txt`
- Pull those files as part of the existing private `/data/local/tmp/a90-acdb-ownget` artifact directory.
- Extend artifact parsing so an `acdb_loader_init_v3` error can classify into:
  - `init-v3-block-acdb-files-load`
  - `init-v3-block-acph-init`
  - `init-v3-block-avc-denial`
  - or the existing generic `init-v3-block`.

## Safety Boundary

The change is observability-only:

- No in-HAL injection.
- No Magisk module install.
- No HAL restart.
- No AudioTrack or playback.
- No native speaker write.
- No `/dev/msm_audio_cal` open or calibration ioctl.
- No `0xC00461CB` SET ioctl.
- Existing rollback-to-V2321 path is unchanged.

## Validation

Commands run:

```bash
python3 -m py_compile \
  workspace/public/src/scripts/revalidation/native_audio_acdb_ownprocess_get_live_handoff_v2490.py

PYTHONPATH=tests:workspace/public/src/scripts/revalidation \
  python3 -m unittest tests.test_native_audio_acdb_ownprocess_get_live_handoff_v2490 -v

PYTHONPATH=workspace/public/src/scripts/revalidation \
  python3 workspace/public/src/scripts/revalidation/native_audio_acdb_ownprocess_get_live_handoff_v2490.py \
    --dry-run \
    --helper-path workspace/private/builds/audio/v2512-acdb-ownprocess-exec-linked-host-only/bin/a90_acdb_ownprocess_get_exec_linked_v2512 \
    --helper-sha256 aab66000e12d6c976a96b3d73d603e6bb9c935dcd5dc801d3f25410f46887dc6
```

Result:

- Focused `py_compile` passed.
- Focused V2490 unittest passed: `12` tests.
- Dry-run with the V2512 helper remains `ok=True`, `live_ready=True`, `command_safety_ok=True`.
- Dry-run command plan contains `logcat -c`, `logcat-acdb-loader.txt`, `logcat-avc-acdb-filter.txt`, and `dmesg-avc-acdb-filter.txt`.
- `git diff --check` passed for the V2514-scoped paths.

## Next Step

Next live unit should rerun the V2490 own-process handoff with the same V2512 helper, now expecting a branch classification rather than a repeated generic `-19`.

Expected useful outcomes:

- `init-v3-block-acdb-files-load`: standalone ACDB DB load still fails; check path/SELinux/file context.
- `init-v3-block-acph-init`: ACPH dependency/environment is missing in the standalone su-domain.
- `init-v3-block-avc-denial`: evaluate a bounded, reverted SELinux policy measurement path.
- first `acdb_ioctl` row emitted: proceed to ordered pure-read GET analysis.

