# NATIVE_INIT V2513 — ACDB audconf own-process live rerun still blocks at init_v3

## Summary

- **Decision:** `v2490-init-v3-block-before-rollback-rollback-pass`
- **Live helper:** V2512 private artifact, pushed through the V2490 own-process runner.
- **Private run:** `workspace/private/runs/audio/v2490-acdb-ownprocess-get-20260616-040203/`
- **Target helper SHA-256:** `aab66000e12d6c976a96b3d73d603e6bb9c935dcd5dc801d3f25410f46887dc6`
- **Device action:** checked Android handoff, own-process helper run, cleanup, rollback to V2321.
- **Rollback:** passed.
- **Final native selftest:** `fail=0`.

V2513 used the V2512 helper that initializes `acdb_loader_init_v3()` with `/vendor/etc/audconf/OPEN` instead of `/vendor/etc/acdbdata`. The run still returned `-19` from `acdb_loader_init_v3` before any `acdb_ioctl` row was emitted.

## Preflight

Before live execution, the device was already resident on V2321:

- `A90 Linux init 0.9.285 (v2321-usb-clean-identity-rodata)`
- `selftest fail=0`
- ADB device list was empty, consistent with native-init resident state.
- Rollback images existed and V2321 SHA matched `ca978551aabe4b39563abaf529ccf2522054952d8b2ad852e632d26da88168cb`.

## Live Execution

Command path:

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

The runner:

- sealed the Android boot image into the private run directory with mode `0600`;
- flashed Android through `native_init_flash.py --from-native`;
- waited for Android ADB, boot-complete, and Magisk root;
- staged the V2512 helper plus the V2506 ACDB dependency closure;
- ran the helper once under `su`;
- pulled the private `/data/local/tmp/a90-acdb-ownget` artifact directory;
- cleaned `/data/local/tmp/a90-acdb-ownget`;
- rebooted Android to recovery;
- flashed V2321 with the checked helper.

All transport, staging, cleanup, and rollback steps returned `ok=true`.

## Observed ACDB Inventory

The expanded setup inventory confirmed the expected carrier ACDB directory exists on stock Android:

- `/vendor/etc/acdbdata/adsp_avs_config.acdb` exists, size `240`.
- `/vendor/etc/audconf/OPEN` exists.
- `/vendor/etc/audconf/OPEN` contains:
  - `Bluetooth_cal.acdb`
  - `Headset_cal.acdb`
  - `Speaker_cal.acdb`
  - `Handset_cal.acdb`
  - `Global_cal.acdb`
  - `Codec_cal.acdb`
  - `Hdmi_cal.acdb`
  - `General_cal.acdb`

This confirms V2510's sparse `/vendor/etc/acdbdata` root was a real mismatch, but switching to `/vendor/etc/audconf/OPEN` is not sufficient by itself.

## Helper Result

Private events:

```json
{"event":"error","stage":"acdb_loader_init_v3","code":-19,"pid":3819,"tid":3819}
```

Summary:

- `classification=init-v3-block`
- `error_count=1`
- `row_count=0`
- `raw_file_count=0`
- `target_4916_count=0`
- `partial_success=false`
- `full_success=false`

No `acdb_ioctl` row was emitted, so the failure remains before the pure-read GET matrix.

## Final State

Rollback completed to:

- `A90 Linux init 0.9.285 (v2321-usb-clean-identity-rodata)`

Post-run verification:

- `version` passed after serial recovery with `--input-mode slow`.
- `selftest verbose` passed with `fail=0`.

One ordinary `a90ctl` read hit a serial framing/desync issue after rollback, but the control channel recovered with slow input and returned valid A90P1 end markers. This did not affect the runner's rollback result.

## Interpretation

The V2512 audconf root fix closed one plausible `-19` cause but did not unblock ACDB initialization. The remaining two likely branches match the operator spec:

1. ACDB loader still rejects the standalone process's DB-load environment despite the valid `/vendor/etc/audconf/OPEN` directory.
2. ACPH initialization fails in the standalone su-domain before the loader reaches any `acdb_ioctl` GET.

The current runner does not capture `logcat -s ACDB-LOADER` or AVC/dmesg around the helper execution, so this run cannot distinguish those branches. Repeating V2513 unchanged is low value.

## Next Unit

Next meaningful unit is host-only runner hardening:

- capture `logcat -c` before helper;
- run the helper;
- pull `logcat -d -s ACDB-LOADER` and relevant `avc:` / denial lines;
- preserve stdout/stderr/events as now;
- keep the same pure-read/no-playback/no-`/dev/msm_audio_cal` boundary.

Acceptance for the next live rerun should be branch classification, not merely retrying the same helper:

- `ACDB -> Could not load .acdb files!` branch;
- `Error initializing ACPH returned = ...` branch;
- SELinux/vendor-file denial branch;
- or first `acdb_ioctl` row emitted.

