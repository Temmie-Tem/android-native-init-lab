# NATIVE_INIT V2645 — ACDB SET-cal replay header-only policy fix

Date: 2026-06-18

## Scope

Host-only fix for the V2644 live blocker. The V2639 live replay reached the
V2635 native helper, but the helper stopped before issuing all SET ioctls because
it treated any exact SET arg with non-zero `cal_size` and no separate payload path
as invalid.

V2634/V2636 already classify cal_type `21` as `SPEAKER_VI_HEADER` with
`dmabuf_expected=False`. Its captured SET arg has `cal_size=28` but is still a
header/no-payload record in the ordered HAL SET manifest. Therefore the helper
must preserve and replay that exact arg instead of requiring a dma-buf payload.

No device action, flash, `/dev/msm_audio_cal` ioctl, PCM probe, or raw payload
publication occurred in this unit.

## Change

- Removed the helper-side rule `cal_size > 0 => external payload required` for
  header-only `--exact-set ARG` entries.
- Added the marker `A90_ACDB_SETCAL_HEADER_ONLY_EXACT_ARG` so future live logs
  distinguish preserved exact header/no-payload records from payload-backed SETs.
- Kept the stricter path for payload-backed entries: `--exact-set ARG:PAYLOAD`
  still requires positive `cal_size`, allocates a fresh ION dma-buf, patches
  `mem_handle`, and deallocates in reverse order.
- Rebuilt the private AArch64 helper and refreshed the V2635/V2636 public
  metadata with the new helper SHA.

## Result

- decision: `v2645-header-only-policy-fixed-host-only`
- helper_source: `workspace/public/src/native-init/helpers/a90_acdb_setcal_replay_scaffold_v2635.c`
- private_helper: `workspace/private/builds/audio/v2635-audio-acdb-setcal-replay-helper-gate/bin/a90_acdb_setcal_replay_execute_v2635`
- private_helper_sha256: `438cc0a118b2c09f1e6da58394ef7f142d389862dccda09db343c598ae045ad7`
- private_helper_file: `ELF 64-bit LSB executable, ARM aarch64, statically linked, stripped`
- deploy_manifest_refreshed: `workspace/private/builds/audio/v2636-audio-acdb-setcal-replay-deploy-plan/deploy-plan.json`
- V2636 helper entry verifies the same SHA and `all_inputs_ok=True`.

## Why This Is Safe

- Header-only exact SET entries are replayed from already captured SET arg bytes;
  no new ACDB data is synthesized.
- The change does not add any new ioctl class or route write.
- Payload-backed entries remain the only entries that allocate ION/dma-buf and
  receive patched `mem_handle` / reverse deallocate cleanup.
- The next live attempt remains the same bounded V2639 flow: one-shot SET replay,
  low-amplitude PCM probe only after successful SET sequence, dmesg capture,
  cleanup, and rollback to V2321.

## Validation

- `python3 -m py_compile workspace/public/src/scripts/revalidation/native_audio_acdb_setcal_replay_helper_gate_v2635.py tests/test_native_audio_acdb_setcal_replay_helper_gate_v2635.py`
- `PYTHONPATH=tests:workspace/public/src/scripts/revalidation python3 -m unittest tests.test_native_audio_acdb_setcal_replay_helper_gate_v2635 -v`
- `PYTHONPATH=workspace/public/src/scripts/revalidation python3 workspace/public/src/scripts/revalidation/native_audio_acdb_setcal_replay_helper_gate_v2635.py --build-helper --write-report --manifest-path workspace/private/builds/audio/v2635-audio-acdb-setcal-replay-helper-gate/manifest.json`
- `PYTHONPATH=workspace/public/src/scripts/revalidation python3 workspace/public/src/scripts/revalidation/native_audio_acdb_setcal_replay_deploy_plan_v2636.py --private-manifest workspace/private/builds/audio/v2636-audio-acdb-setcal-replay-deploy-plan/deploy-plan.json --write-report`
- `file workspace/private/builds/audio/v2635-audio-acdb-setcal-replay-helper-gate/bin/a90_acdb_setcal_replay_execute_v2635`
- `sha256sum workspace/private/builds/audio/v2635-audio-acdb-setcal-replay-helper-gate/bin/a90_acdb_setcal_replay_execute_v2635`

## Next Unit

A single V2639 live rerun is now meaningful. Expected discriminator:

- If all `A90_ACDB_SETCAL_SET_OK` markers appear, proceed to the bounded PCM
  prepare/play probe and inspect dmesg for the next audio gate.
- If another helper-side policy failure appears before the SET sequence completes,
  stop and fix host-only; do not retry-loop live.
- If SET sequence completes but PCM still fails, classify from post-prepare dmesg
  rather than reworking capture/replay inputs blindly.
