# NATIVE_INIT V2735 — Atomic App Type Config success-dmesg live replay

Date: 2026-06-18

## Scope

One recoverable live replay cycle to preserve post-PCM success dmesg for the
V2734 route: V2334 audio candidate boot, ADSP + `/dev/snd` setup, V2725 corrected
ACDB SET-cal replay manifest, V2733 atomic `App Type Config` writer, bounded
low-amplitude PCM write probe, cleanup, route reset, and checked rollback to
V2321.

This unit does not claim human-audible speaker output. It verifies the kernel /
ALSA / ADSP PCM write path and records the post-write dmesg focus that V2734 was
missing.

## Result

- Decision: `v2735-atomic-app-type-config-success-dmesg-live-pass-rollback-pass`.
- Candidate flash: `ok=True`, `rc=0`, step `02_flash-v2334-candidate.txt`.
- V2733 global App Type Config: `A90_APP_TYPE_CFG_WRITE_OK num_entries=1`.
- ACDB SET replay: `A90_SETCAL_REPLAY_ALL_SET_OK pid=857 final_index=10`.
- PCM probe: `A90_PCM_PROBE_DONE chunks=12 bytes=192000 drain_us=85333`.
- Post-playback dmesg capture: `67_dmesg-after-setcal-playback-before-reset.txt` and `68_dmesg-focus-after-setcal-playback-before-reset.txt` captured before helper deallocate / route reset.
- Helper cleanup: `ok=True`, reverse deallocate script completed.
- Rollback: V2321 flashed back via checked helper; rollback `version` reports `0.9.285`; rollback `selftest verbose` reports `fail=0`.

## Evidence

Private run directory, not committed:

`workspace/private/runs/audio/v2639-acdb-setcal-replay-20260618-225912`

Key metadata-only evidence:

- `48_v2733-atomic-app-type-config.txt`: resolved control `App Type Config`, `numid=3123`, `count=128`, payload `69941:48000:16`, write OK.
- `63_acdb-setcal-replay-start-wait-all-set.txt`: all staged ACDB files SHA-verified, final SET index 10 reached.
- `66_tinyplay-low-amplitude-speaker-pilot.txt`: PCM open succeeded and all 192000 bytes were written.
- `68_dmesg-focus-after-setcal-playback-before-reset.txt`: post-write focused dmesg shows `__afe_port_start: port id: 0x4000`, `adm_open:bit_width:16 app_type:0x11135 acdb_id:15`.
- `85_rollback-v2321.txt`: rollback image SHA/readback verified and system rebooted to V2321.
- `87_rollback-selftest-content-attempt-1-attempt-1.txt`: rollback selftest `fail=0`.

## Interpretation

V2735 confirms the V2733 atomic global App Type Config write is sufficient to
avoid the previous `adm_open` bit-width/app-type mismatch: the playback-time
focus dmesg reports `bit_width:16 app_type:0x11135 acdb_id:15`, while the PCM
probe writes the full low-amplitude 48 kHz S16LE stereo pilot without a
userspace or ALSA write failure.

The same post-write focus also shows a remaining calibration-side issue:
`q6asm_send_cal: audio audstrm cal send failed` after `DSP returned
ADSP_ENEEDMORE`. Therefore the next audio frontier is not the ALSA PCM write
path; it is the missing or incomplete ASM/audstrm calibration payload/sequence.
This unit intentionally does not chase unrelated eSoC warnings seen in the broad
dmesg tail; rollback health passed.

## Validation

Static validation before live:

- `python3 -m py_compile workspace/public/src/scripts/revalidation/native_audio_acdb_setcal_replay_live_handoff_v2639.py tests/test_native_audio_acdb_setcal_replay_live_handoff_v2639.py`
- `PYTHONPATH=tests:workspace/public/src/scripts/revalidation python3 -m unittest tests.test_native_audio_acdb_setcal_replay_live_handoff_v2639 -v` — 10 tests passed.
- `git diff --check`

Live command:

```bash
PYTHONPATH=workspace/public/src/scripts/revalidation \
python3 workspace/public/src/scripts/revalidation/native_audio_acdb_setcal_replay_live_handoff_v2639.py \
  --run-live \
  --v2636-manifest workspace/private/builds/audio/v2725-audio-acdb-corrected-core39-ioctl-result-deploy-plan/deploy-plan.json \
  --manifest-path workspace/private/builds/audio/v2735-atomic-appcfg-success-dmesg-live/live-manifest.json \
  --report docs/reports/NATIVE_INIT_V2735_AUDIO_ATOMIC_APP_TYPE_SUCCESS_DMESG_LIVE_2026-06-18.md \
  --write-report
```

Post-live verification:

- `python3 workspace/public/src/scripts/revalidation/a90ctl.py --retry-unsafe version` — V2321 / `0.9.285`.
- `python3 workspace/public/src/scripts/revalidation/a90ctl.py --retry-unsafe selftest verbose` — `fail=0`.

## Next Unit

Host-side compare the captured V2735 dmesg against Android/HAL calibration order
for the ASM/audstrm path. The concrete discriminator is why native still reaches
`q6asm_send_cal` with `ADSP_ENEEDMORE` while `adm_open` now has the correct
`bit_width:16 app_type:0x11135 acdb_id:15` tuple.
