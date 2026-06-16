# NATIVE_INIT V2556 — ACDB post-initialize auto-arm fix

Date: 2026-06-16

## Scope

Host/build-only correction after V2555 proved that
`acdb_loader_init_v3()` internally reaches `send_common_custom_topology()` before
returning to the helper. The previous V2554 manual-arm-after-init policy was too
late for this device path.

## Change

`libacdbtap_v2475.c` now keeps the first initialization call silent and arms only
after it completes successfully:

1. while `a90_armed == 0`, the wrapper calls the real `acdb_ioctl` directly;
2. no dump, file I/O, hash, or JSON event is produced on the unarmed path;
3. if that silent call is `ACDB_CMD_INITIALIZE_V2` and returns `0`, the wrapper
   sets `a90_armed = 1`;
4. subsequent `acdb_ioctl` calls are captured, including the topology/per-device
   GET calls that occur inside the remainder of `acdb_loader_init_v3()`;
5. the helper-side `a90_arm_capture()` call remains as a fallback, and
   `A90_ACDBTAP_EXIT_ON_TARGET=0` remains the full-manifest policy.

This is a measured correction to the prior operator-spec assumption: V2555 live
logs showed the topology GET occurs inside init, not after init returns.

## Artifacts

Private rebuilt artifacts under
`workspace/private/builds/audio/v2553-acdb-full-manifest-capture-host-only/`:

- helper_sha256: `d93bbeb645dbb48f34f50451338058ce5c8b5648ee707aea889fcd03cd795406`
- preload_sha256: `98d684f8af27c1bbd17325f2acfe6120ee4886c0a5a4246431a4eefa5edd14ac`

Raw payload bytes and private build binaries are not committed.

## Validation

Commands run:

```bash
python3 -m py_compile \
  workspace/public/src/scripts/revalidation/build_android_acdb_full_manifest_v2553.py \
  workspace/public/src/scripts/revalidation/native_audio_acdb_full_manifest_live_handoff_v2555.py
PYTHONPATH=tests python3 -m unittest \
  tests.test_build_android_acdb_full_manifest_v2553 \
  tests.test_native_audio_acdb_full_manifest_live_handoff_v2555
python3 workspace/public/src/scripts/revalidation/build_android_acdb_full_manifest_v2553.py --build
python3 workspace/public/src/scripts/revalidation/native_audio_acdb_full_manifest_live_handoff_v2555.py --dry-run
```

Observed validation result:

- focused unittest count: `6`, result `OK`.
- build manifest: `ok=True`.
- source gates:
  - `tap_post_initialize_auto_arm=True`.
  - `tap_unarmed_path_has_no_dump_before_real=True`.
  - `tap_has_no_exit_macro=True`.
  - `tap_all_zero_guard=True`.
- dry-run decision: `v2555-acdb-full-manifest-live-runner-dry-run`.
- dry-run: `ok=True`, `live_ready=True`, `blockers=[]`.
- dry-run capture contract:
  - `post_initialize_auto_arm=True`.
  - `manual_arm_after_init_v3=False`.
  - `fake_audio_cal_allocate=True`.
  - success still requires `ret==0` and non-all-zero raw data.

## Next Unit

Run the same checked Android handoff with the rebuilt post-initialize auto-arm
preload. Acceptance is the full ordered `acdb_ioctl` out-buffer set, not only a
requested `out_len==4916`; success requires real `ret==0` and non-all-zero
buffers. Roll back to V2321 and verify final native `selftest fail=0`.
