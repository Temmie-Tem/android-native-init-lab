# NATIVE_INIT_V2438_AUDIO_ACDB_M1_MAGISK_STAGING_TRANSFER_FIX_2026-06-15

## Summary

V2438 is a host-only fix for the V2437 M1 Magisk-module retry wall. V2437 did
not prove a Magisk module namespace blocker; it proved the runner tried to
`adb push` as Android `shell` into a root-created `0700` staging directory.

This iteration adds a new V2438 runner rather than mutating the V2436 artifact.
The new runner keeps the V2436/V2429 Android-good measurement semantics, but
splits file transfer by privilege:

1. Magisk root creates an incoming directory under `/data/local/tmp` and makes
   only that directory shell-owned.
2. Host `adb push` writes the exact module payload files into that shell-owned
   incoming directory.
3. Magisk root validates exact SHA-256 values and file count.
4. Magisk root copies only the validated files into
   `/data/adb/modules/a90_audio_acdb_m1_v2429`.
5. The final module path is tightened to root-owned restrictive permissions.
6. Cleanup remains exact and removes both the module path and run directory.

No Android boot, Magisk module activation, speaker route write, mixer write,
PCM playback, `/dev/msm_audio_cal` ioctl, Wi-Fi action, DHCP, route, or ping was
run in V2438.

## Touched Public Artifacts

- `workspace/public/src/scripts/revalidation/native_audio_acdb_m1_magisk_module_retry_live_handoff_v2438.py`
- `tests/test_native_audio_acdb_m1_magisk_module_retry_live_handoff_v2438.py`

## Runner Changes

The V2438 runner adds:

- `RUN_ID=V2438`
- build tag `v2438-audio-acdb-m1-magisk-module-retry`
- shell-owned incoming directory:
  `/data/local/tmp/a90-audio-acdb-m1-v2429/incoming`
- incoming owner `2000:2000` for Android `shell`
- parent run directory mode `0711` so `shell` can traverse to the exact
  incoming path without listing root-owned run contents
- incoming directory mode `0700`
- root-side SHA-256 validator:
  - requires exactly four files under incoming
  - validates `module.prop`
  - validates `service.sh`
  - validates `README.md`
  - validates `bin/a90_acdb_ioctl_capture_threadset_v2423`
- `A90_M1_INCOMING_READY` and `A90_M1_INCOMING_HASH_OK` markers
- materialized dry-run manifest with local paths, remote incoming paths, sizes,
  and SHA-256 hashes

The runner still rejects:

- `magisk --install-module`
- `post-fs-data.sh`
- native `tinyplay`
- native `tinymix set`
- native calibration ioctl symbols
- broad `/data/adb/modules` removal
- raw partition/fastboot paths

## Dry-Run Evidence

Materialized dry-run summary:

```json
{
  "command_safety_ok": true,
  "decision": "v2438-acdb-m1-magisk-module-retry-live-dry-run",
  "future_live_blockers": [],
  "future_live_ready": true,
  "manifest_labels": [
    "README.md",
    "a90_acdb_ioctl_capture_threadset_v2423",
    "module.prop",
    "service.sh"
  ],
  "ok": true,
  "remote_incoming_dir": "/data/local/tmp/a90-audio-acdb-m1-v2429/incoming",
  "run_id": "V2438"
}
```

## Validation

```text
python3 -m py_compile \
  workspace/public/src/scripts/revalidation/native_audio_acdb_m1_magisk_module_retry_live_handoff_v2438.py \
  tests/test_native_audio_acdb_m1_magisk_module_retry_live_handoff_v2438.py

PYTHONPATH=tests python3 -m unittest \
  tests/test_native_audio_acdb_m1_magisk_module_retry_live_handoff_v2438.py -v

PYTHONPATH=tests python3 -m unittest discover -s tests

git diff --check
```

Focused tests: `6` passed. Full discovery: `1191` tests passed.

The focused tests prove:

- wrong live approval exits before device action;
- dry-run emits V2438 metadata;
- materialized dry-run is future-live-ready;
- command safety remains clean;
- pushes target only `/incoming/` paths, not `module-stage`;
- incoming setup includes `chown 2000:2000` and `chmod 711`;
- install path contains exact file count and SHA-256 validation;
- `magisk --install-module`, `post-fs-data.sh`, playback, native mixer writes,
  and broad module removal remain absent.

## Next Unit

V2439 should be the exact-gated live rerun of the V2438 runner. It should use the
same M1 measurement boundary as V2437:

- Android-good measurement only;
- temporary Magisk `service.sh` module only;
- no native speaker/mixer/PCM writes;
- no native `/dev/msm_audio_cal` ioctl;
- no native ACDB replay;
- exact cleanup before checked rollback to V2321.

If V2439 reaches module activation and captures payload events, the next unit
should be host-only payload analysis: command order, decoded headers, private
payload hashes, mem-handle policy, and cleanup behavior. If V2439 activates the
module but still captures zero events, classify the Android-good measurement wall
before changing the hook strategy.
