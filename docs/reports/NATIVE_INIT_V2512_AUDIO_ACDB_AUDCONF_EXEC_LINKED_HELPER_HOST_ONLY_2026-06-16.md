# NATIVE_INIT V2512 — ACDB audconf exec-linked own-process helper (host-only)

## Summary

- **Decision:** `v2512-acdb-ownprocess-exec-linked-host-only`
- **Scope:** host-only build/test update for the ACDB own-process pure-read GET helper.
- **Device action:** none.
- **Flash action:** none.
- **Private artifact:** `workspace/private/builds/audio/v2512-acdb-ownprocess-exec-linked-host-only/bin/a90_acdb_ownprocess_get_exec_linked_v2512`
- **Private artifact SHA-256:** `aab66000e12d6c976a96b3d73d603e6bb9c935dcd5dc801d3f25410f46887dc6`

V2512 addresses the V2510/V2511 `acdb_loader_init_v3 == -19` blocker by changing the helper's ACDB file root from the sparse `/vendor/etc/acdbdata` directory to the production carrier calibration set at `/vendor/etc/audconf/OPEN`.

## Why

V2510 proved the exec-linked helper cleared the previous linker/TLS wall and reached `acdb_loader_init_v3`, but returned `-19` before any `acdb_ioctl` row was emitted. V2511 host analysis localized the likely cause to an ACDB root mismatch:

- V2510 live setup showed `/vendor/etc/acdbdata` contained only `adsp_avs_config.acdb`.
- V2324 inventory showed the full speaker/device calibration sets under `/vendor/etc/audconf/{SKC,OPEN,LUC,KTC}/`.
- The stock loader scans the supplied ACDB directory; pointing it at the sparse root can fail before the pure-read GET matrix starts.

The next bounded discriminator is therefore to keep the same own-process, pure-read helper design but initialize ACDB with `/vendor/etc/audconf/OPEN`.

## Changes

- Added V2512 ARM32 exec-linked helper source:
  - `workspace/public/src/android/acdb_payload_capture/a90_acdb_ownprocess_get_exec_linked_v2512.c`
- Added V2512 private-artifact builder:
  - `workspace/public/src/scripts/revalidation/build_android_acdb_ownprocess_get_exec_linked_v2512.py`
- Added focused builder tests:
  - `tests/test_build_android_acdb_ownprocess_get_exec_linked_v2512.py`
- Enhanced the existing V2490 live runner setup inventory to list both:
  - `/vendor/etc/acdbdata`
  - `/vendor/etc/audconf/OPEN`
  - all `/vendor/etc/audconf/*/*.acdb` files via Android-compatible `find ... -exec ls -l`.

## Safety Boundary

V2512 preserves the own-process measurement-only boundary:

- No in-HAL injection.
- No Magisk module install.
- No HAL restart.
- No AudioTrack or native playback.
- No native speaker write.
- No `/dev/msm_audio_cal` open or calibration ioctl.
- No `0xC00461CB` SET ioctl.
- No `acdb_loader_send_common_custom_topology` path.
- Raw capture bytes remain private-only.

## Build Result

The private helper builds as a 32-bit Android PIE with direct `DT_NEEDED` dependencies on the staged stock ACDB closure:

- `libacdbloader.so`
- `libaudcal.so`
- `libdiag.so`
- `libacdb-fts.so`
- `libacdbrtac.so`
- `libadiertac.so`

The manifest confirms:

- `acdb_loader_init_v3` is unresolved for runtime binding.
- `acdb_ioctl` is unresolved for runtime binding.
- `dlopen` / `dlsym` / `dlerror` are not used.
- `A90_ACDB_FILES_PATH` is `/vendor/etc/audconf/OPEN`.
- `/vendor/etc/acdbdata` is absent from the V2512 helper source.

Private manifest:

- `workspace/private/builds/audio/v2512-acdb-ownprocess-exec-linked-host-only/manifest.json`

## Runner Dry-Run

The V2490 runner was dry-run with the V2512 helper path and SHA:

- `ok=True`
- `live_ready=True`
- `sha256_ok=True`
- `live_blockers=[]`
- helper mode `0o700`
- setup plan includes `/vendor/etc/acdbdata`, `/vendor/etc/audconf/OPEN`, and `/vendor/etc/audconf` file enumeration.

Private dry-run:

- `workspace/private/builds/audio/v2512-acdb-ownprocess-exec-linked-host-only/v2490-v2512-helper-dry-run.json`

## Validation

Commands run:

```bash
python3 -m py_compile \
  workspace/public/src/scripts/revalidation/build_android_acdb_ownprocess_get_exec_linked_v2512.py \
  workspace/public/src/scripts/revalidation/native_audio_acdb_ownprocess_get_live_handoff_v2490.py

PYTHONPATH=tests:workspace/public/src/scripts/revalidation \
  python3 -m unittest \
    tests.test_build_android_acdb_ownprocess_get_exec_linked_v2512 \
    tests.test_native_audio_acdb_ownprocess_get_live_handoff_v2490 -v

PYTHONPATH=workspace/public/src/scripts/revalidation \
  python3 workspace/public/src/scripts/revalidation/build_android_acdb_ownprocess_get_exec_linked_v2512.py \
    --dry-run --build \
    --manifest-path workspace/private/builds/audio/v2512-acdb-ownprocess-exec-linked-host-only/manifest.json

PYTHONPATH=workspace/public/src/scripts/revalidation \
  python3 workspace/public/src/scripts/revalidation/native_audio_acdb_ownprocess_get_live_handoff_v2490.py \
    --dry-run \
    --helper-path workspace/private/builds/audio/v2512-acdb-ownprocess-exec-linked-host-only/bin/a90_acdb_ownprocess_get_exec_linked_v2512 \
    --helper-sha256 aab66000e12d6c976a96b3d73d603e6bb9c935dcd5dc801d3f25410f46887dc6
```

Result:

- Focused Python validation passed.
- Focused unittest validation passed: `14` tests.
- V2512 private build passed.
- V2490 dry-run with the V2512 helper passed.
- `git diff --check` passed for the V2512-scoped paths.

## Next Step

Next live unit should rerun the V2490 own-process Android handoff with the explicit V2512 helper path and SHA, not `--build-helper`:

```bash
ART=workspace/private/builds/audio/v2512-acdb-ownprocess-exec-linked-host-only/bin/a90_acdb_ownprocess_get_exec_linked_v2512
SHA=aab66000e12d6c976a96b3d73d603e6bb9c935dcd5dc801d3f25410f46887dc6
PYTHONPATH=workspace/public/src/scripts/revalidation \
  python3 workspace/public/src/scripts/revalidation/native_audio_acdb_ownprocess_get_live_handoff_v2490.py \
    --run-live \
    --from-native \
    --helper-path "$ART" \
    --helper-sha256 "$SHA"
```

Expected discriminator:

- `acdb_loader_init_v3` succeeds and at least one `acdb_ioctl` row is emitted: proceed to ordered pure-read GET result analysis.
- `acdb_loader_init_v3` still returns `-19`: use the newly expanded setup inventory and collected stderr/logs to distinguish ACDB directory load failure from ACPH initialization failure.
- Out-buffer set without 4916 bytes is still partial success and should be preserved privately for operator analysis.
