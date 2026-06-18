# NATIVE_INIT V2650 — ACDB SET-cal DSP blocker host analysis

Date: 2026-06-18

## Scope

Host-only analysis after V2648/V2649. No device action, flash, playback,
calibration ioctl, mixer write, or raw payload publication occurred.

This unit answers the immediate post-V2648 question: after native replay accepts
the full captured SET sequence, is the next gate still the old cal_type `8/9`
missing-topology problem, or did the blocker move?

## Inputs

- V2632/V2633 SET-layer capture and Gate-2 handoff metadata.
- V2634/V2636 replay manifests.
- V2648 live run dmesg and result metadata.
- V2393 baseline dmesg from the pre-ACDB-replay speaker pilot.
- `GOAL.md` operator steering, including the statement that cal_type `8` absence
  is faithful HAL behavior, not a capture gap.

Private raw SET args/payloads were read only for scalar field inspection; no raw
bytes are copied into this report.

## Baseline vs Current Failure

### V2393 before ACDB replay

The old blocker was host-side missing calibration lookup:

```text
afe_get_cal_topology_id: cal_type 8 not initialized for this port 16384
afe_get_cal_topology_id: cal_type 9 not initialized for this port 16384
send_afe_cal_type cal_block not found!!
q6asm_send_cal: cal_block is NULL
adm_open:topo_id 0x10312
adm_open: DSP returned error[ADSP_EFAILED]
```

### V2648 after full native SET replay

The new blocker is different:

```text
afe_callback: cmd = 0x100ef returned error = 0x2
afe_apr_send_pkt: DSP returned error[ADSP_EBADPARAM]
afe_send_cal_block: AFE cal for port 0x4000 failed -22
q6asm_callback: cmd = 0x10da1 returned error = 0x12
q6asm_set_pp_params: DSP returned error[ADSP_ENEEDMORE]
q6asm_send_cal: audio audstrm cal send failed
adm_open:port 0x4000 path:1 rate:48000 mode:1 perf_mode:0,topo_id 0x10004000
adm_open:bit_width:0 app_type:0x11135 acdb_id:15
adm_open: DSP returned error[ADSP_EFAILED]
```

Notably absent in V2648: the `cal type 8/9 not initialized` and `cal_block not
found` text. The native SET replay has moved the system from "kernel has no cal
block" to "kernel sends a cal block, DSP rejects it".

## SET Manifest State

The V2633 expected SET order is exact for the captured `send_audio_cal_v5` layer:

```text
[13, 9, 11, 12, 15, 23, 16, 21]
```

V2636 adds the already-pinned common topology payload as the first native replay
record, so V2648 actually SETs:

```text
[39, 13, 9, 11, 12, 15, 23, 16, 21]
```

All records were accepted by `/dev/msm_audio_cal` in V2648.

Scalar inspection of the header records shows the topology/app identifiers now
visible in dmesg:

| cal_type | role | selected scalar fields |
| ---: | --- | --- |
| 13 | `APP_META_HEADER` | includes `0x10005000`, app_type `0x11135` |
| 9 | `AFE_TOPOLOGY_HEADER` | includes topology `0x10004000`, acdb_id `15`, app_type `0x11135` |
| 23 | `AFE_TOPOLOGY_ID_HEADER` | includes `0x1001025d`, acdb_id `15` |
| 16 | `AFE_COMMON_PAYLOAD` | acdb_id `15`, sample rate `48000`, payload size `1560` |
| 15 | `ASM_STREAM_PAYLOAD` | app_type `0x11135`, payload size `28` |
| 21 | `SPEAKER_VI_HEADER` | sample/rate scalar fields plus inline `cal_size=28` |

The V2648 dmesg `adm_open ... topo_id 0x10004000` matches the cal_type `9`
header scalar, so the replayed header is not ignored. It changes the downstream
DSP request.

## Conclusion

The next gate is **not** simply "find cal_type 8".

Reasons:

1. `GOAL.md` now records that cal_type `8` absence is faithful HAL behavior, not
   a capture gap.
2. V2648 no longer reports cal_type `8/9` as uninitialized.
3. V2648 proves cal_type `9`/`23` headers and cal_type `16` AFE payload are at
   least accepted by the kernel and affect the topology used for prepare.
4. The failure has moved to DSP-side validation: `ADSP_EBADPARAM` for AFE cal and
   `ADSP_ENEEDMORE` for ASM stream cal.

The highest-value hypothesis is now: **the captured SET-layer manifest is
necessary but not sufficient to reproduce the full Android-good HAL/kernel audio
calibration state.** The missing piece is likely one of:

- an ioctl/order edge around the real HAL path outside the fake own-process SET
  layer, such as `AUDIO_PREPARE_CALIBRATION` / `AUDIO_POST_CALIBRATION` or another
  `/dev/msm_audio_cal` call whose payload was not part of the V2632 fake-SET
  manifest;
- a route/stream geometry mismatch that makes the captured cal blocks valid as
  SET arguments but invalid for the native PCM stream state that reaches DSP;
- an ordering or lifetime condition where the kernel accepts all SETs, but the
  DSP requires a different sequencing relative to stream open, AFE port start,
  or ADM/ASM setup;
- a header-only field normalization issue beyond cal_type `12` where a captured
  scalar is accepted by the kernel but semantically wrong under native replay.

## What Not To Do

- Do not rerun V2639 unchanged. It will likely reproduce the same DSP-side
  prepare rejection.
- Do not chase cal_type `8` as a capture-gap assumption unless new Android-good
  real-kernel ioctl evidence shows a real cal_type `8` SET or another AFE
  startup ioctl outside `send_audio_cal_v5`.
- Do not change PCM geometry, route controls, WSA gain, or speaker path as a
  first reaction. The failure is now calibration-state semantic validation.

## Next Unit

V2651 should be host-only and should build an **audio-cal ioctl order analyzer**
for existing private Android-good and native replay evidence:

1. Parse existing private `setcal-events.jsonl`, M1/M0 `/dev/msm_audio_cal` ioctl
   traces, and V2639 replay stderr into a redacted request-order table.
2. Compare real Android-good `/dev/msm_audio_cal` request order against the
   V2632 fake-SET manifest and V2648 native replay order.
3. Explicitly classify whether `AUDIO_PREPARE_CALIBRATION`,
   `AUDIO_POST_CALIBRATION`, or any real cal_type `8`/extra AFE call appears in
   Android-good traces.
4. If existing traces are insufficient, design one bounded Android-good capture
   for ioctl order only; do not do another native speaker replay first.

Only after that order/context gap is resolved should another live native SET
replay be considered.

## Validation

- `GOAL.md` reread for current operator steering.
- V2633/V2634/V2636 private manifests inspected for metadata only.
- V2648 private dmesg/result inspected for exact DSP error text.
- V2393 baseline report inspected for the previous missing-cal-block failure.
- No raw payload bytes committed.
