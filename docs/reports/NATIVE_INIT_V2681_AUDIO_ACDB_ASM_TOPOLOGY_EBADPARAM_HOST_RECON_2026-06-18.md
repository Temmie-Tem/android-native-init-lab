# NATIVE_INIT V2681 — ACDB ASM topology `ADSP_EBADPARAM` host recon

Date: 2026-06-18

## Scope

Host-only analysis after the V2680 native ACDB replay live run.  No device
action, flash, `/dev/msm_audio_cal` ioctl, PCM probe, or raw private payload
copy occurred in this unit.

## Result

- decision: `v2681-acdb-asm-custom-topology-dsp-ebadparam-host-recon`
- V2680 run: `workspace/private/runs/audio/v2639-acdb-setcal-replay-20260618-152256`
- V2679 manifest:
  `workspace/private/builds/audio/v2679-acdb-custom-topology-replay-deploy-plan/deploy-plan.json`
- kernel source:
  `tmp/wifi/v766-icnss-qcacld-patch-apply-build/source/techpack/audio/4.0/`

V2680 closed the replay-plumbing blocker.  The helper accepted all 11 replay
entries, `/dev/msm_audio_cal` accepted every `AUDIO_SET_CALIBRATION`, and
cleanup/rollback succeeded.  The remaining blocker is now DSP-side validation of
the ASM custom topology payload: `ASM_CMD_ADD_TOPOLOGIES` (`0x10dbe`) returned
`ADSP_EBADPARAM`, which makes `q6asm_audio_client_alloc()` fail and surfaces to
userspace as PCM open `-ENOMEM`.

## V2680 live evidence

Replay entries were staged from the V2679 manifest in this order:

| index | cal_type | role |
| ---: | ---: | --- |
| 0 | 39 | `CORE_CUSTOM_TOPOLOGIES` |
| 1 | 24 | `AFE_CUSTOM_TOPOLOGY_PAYLOAD` |
| 2 | 14 | `ASM_CUSTOM_TOPOLOGY_PAYLOAD` |
| 3 | 13 | app metadata header |
| 4 | 9 | AFE topology header |
| 5 | 11 | AUDPROC payload |
| 6 | 12 | VOL header |
| 7 | 15 | ASM stream payload |
| 8 | 23 | AFE topology-id header |
| 9 | 16 | AFE common payload |
| 10 | 21 | speaker VI header |

The V2680 helper output reached:

```text
A90_SETCAL_REPLAY_ALL_SET_OK pid=862 final_index=10
```

The deallocation check then observed:

```text
A90_SETCAL_REPLAY_DONE_OK
A90_SETCAL_REPLAY_DEALLOCATE_SEEN index=0
A90_SETCAL_REPLAY_DEALLOCATE_SEEN index=1
A90_SETCAL_REPLAY_DEALLOCATE_SEEN index=2
A90_SETCAL_REPLAY_DEALLOCATE_SEEN index=5
A90_SETCAL_REPLAY_DEALLOCATE_SEEN index=7
A90_SETCAL_REPLAY_DEALLOCATE_SEEN index=9
A90_SETCAL_REPLAY_FINAL_SET_SEEN
```

The PCM probe failed later, at playback open:

```text
q6asm_callback: cmd = 0x10dbe returned error = 0x2
send_asm_custom_topology: DSP returned error[ADSP_EBADPARAM]
msm_pcm_open: Could not allocate memory
SM8150 Media1: ASoC: failed to start FE -12
```

Rollback completed to V2321 and final selftest was `fail=0`.

## Kernel path

`apr_audio-v2.h` defines `ASM_CMD_ADD_TOPOLOGIES` as `0x00010DBE` and uses
`struct cmd_set_topologies` with payload physical address, mem-map handle, and
payload size.

`q6asm.c` does the following in `send_asm_custom_topology()`:

1. requires `cal_data[ASM_CUSTOM_TOP_CAL]`;
2. requires `set_custom_topology`;
3. obtains the only ASM custom topology cal block;
4. remaps the cal block with `ASM_CUST_TOPOLOGY_CAL_TYPE`;
5. sends `ASM_CMD_ADD_TOPOLOGIES`;
6. waits for `ac->mem_state`;
7. converts any positive DSP error state to a Linux error.

`q6asm_set_cal()` sets `set_custom_topology = 1` when the SET cal index is
`ASM_CUSTOM_TOP_CAL`, so V2680's accepted cal_type `14` SET is what made the
later PCM open attempt push the custom topology to the DSP.

`q6asm_audio_client_alloc()` calls `send_asm_custom_topology()` before returning
an audio client.  If that returns an error, allocation fails.  `msm_pcm_open()`
then logs `client alloc failed` and returns `-ENOMEM`.  This matches V2680
exactly.

## Payload geometry

The V2679 manifest intentionally used only the captured custom-topology
payloads for cal_types `24` and `14`; cal_type `10` is absent under the V2676
policy `absent-not-capture-gap-per-v2676`.

Private payload metadata used by V2680:

| cal_type | arg_len | payload_len | payload_sha256 | first u32 |
| ---: | ---: | ---: | --- | --- |
| 39 | n/a | 4916 | `7c5d45efa40944bc23dcc83af9f0046249499bb13d1a03c3470c287127992b89` | `0x45` |
| 24 | 32 | 1180 | `53307305946f1a39e1d57de10c5bb7d65d120ea8f1c90725d0432b684c8e92c4` | `0x3` |
| 14 | 32 | 2356 | `bc03e4be2dc4667ebfaf14b27ecc088f28fb23f784b352c14f0524963f7b7c98` | `0x6` |

The cal_type `14` payload is non-zero and outer-header plausible: 2356 bytes,
first u32 `0x6`, followed by topology-like IDs such as `0x1000ffff`, module
count `0x9`, and module IDs including `0x10719`, `0x10bfe`, `0x108ba`, and
`0x108a5`.  The failure is therefore not "empty payload" or helper cap.  The
DSP accepted the packet path far enough to return an explicit `ADSP_EBADPARAM`.

## Interpretation

V2680 moves the frontier from AP-side replay mechanics to DSP-side topology
validity.  The important distinction is:

- `/dev/msm_audio_cal` accepted the SET args and dma-buf-backed payloads;
- q6asm later remapped cal_type `14` and issued `ASM_CMD_ADD_TOPOLOGIES`;
- the ADSP rejected that topology payload with `ADSP_EBADPARAM`.

The strongest current candidates are:

1. **cal_type 14 is not the exact ASM custom-topology blob required by this
   native playback route/state.**  V2675 captured a real non-zero block, but
   V2680 proves the ADSP does not accept it in the current native stream-open
   context.
2. **The missing cal_type 10 / ADM custom topology assumption needs a narrow
   revisit.**  V2676 correctly showed Android-good did not emit a cal_type 10
   SET and V2675's ADM GET returned `-12`.  However, V2680 shows the 24+14
   overlay alone is insufficient and the first fatal error is now ASM-side.
   That does not prove cal_type 10 is required, but it means "cal10 absence is
   harmless" is no longer a safe blanket assumption for replay.
3. **Route or stream context mismatch.**  The kernel sends the ASM custom
   topology during `q6asm_audio_client_alloc()` for the native PCM open.  If
   the native route opens a different topology/app/session context than the
   Android-good capture that produced the cal_type `14` blob, the payload can
   be structurally real but semantically rejected.

The evidence does **not** point to the old V2678 helper entry cap, SET ioctl
plumbing, dma-buf lifetime, rollback, or cleanup path.  Those passed in V2680.

## Next unit

Do **not** blindly rerun the same V2679/V2680 manifest.  It would replay the
same accepted SET sequence and hit the same `ASM_CMD_ADD_TOPOLOGIES`
`ADSP_EBADPARAM`.

Recommended next unit:

1. host-only parse the cal_type `14` payload with the Qualcomm custom topology
   grammar, enough to list topology IDs and module IDs;
2. compare those IDs against the native stream's requested topology/app route
   and the Android-good route evidence;
3. only if that comparison identifies a concrete mismatch or missing companion,
   build the next replay manifest.

Secondary parked branch:

- revisit cal_type `10` only with a concrete new hypothesis, for example a
  different ACDB input tuple or lower-node selector than V2675/V2676 used.  Do
  not restart generic cal10 capture variants.

## Validation

- Reread `GOAL.md`, `CLAUDE.md`, and the ACDB operator spec.
- Inspected V2680 private run metadata and dmesg.
- Inspected V2679 private deploy manifest metadata.
- Inspected q6asm/q6afe/q6adm source under the stock 4.14 audio techpack drop.
- `git diff --check`
