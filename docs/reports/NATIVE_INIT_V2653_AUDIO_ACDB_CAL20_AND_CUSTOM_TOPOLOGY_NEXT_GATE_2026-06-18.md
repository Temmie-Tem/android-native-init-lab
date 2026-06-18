# NATIVE_INIT V2653 — ACDB cal20 and custom-topology next gate

Date: 2026-06-18

## Scope

Host-only classification and next-step design after V2652 decoded existing real Android-good
`AUDIO_SET_CALIBRATION` arg bytes. No device action, flash, playback, mixer write,
calibration ioctl, or raw ACDB byte publication occurred.

## Decision

- `decision`: `v2653-cal20-real-but-not-the-v2648-topology-fix`
- `ok`: `True`
- next live/native replay action: **blocked until custom-topology SET records are captured**
- next implementation unit: extend the own-process fake-SET capture path to drive the
  custom-topology send path and capture cal_types `10`, `14`, and `24` byte-exact.

## Evidence

### V2652 real SET decode

Existing Android-good ptrace `bytes_hex` decoded 26 real kernel
`AUDIO_SET_CALIBRATION` calls:

| cal_type | count | decoded shape |
| ---: | ---: | --- |
| `39` | `12` | `data_size=32`, `cal_type_size=16`, `cal_size=4916`, `mem_handle=35/36/37` |
| `20` | `14` | `data_size=68`, `cal_type_size=52`, `cal_size=0`, `mem_handle=-1` |

The decoded real SET order appears in older trace windows as repeated `39` followed by
two `20` records. V2652 found no decoded cal_type `8`, no `AUDIO_PREPARE_CALIBRATION`,
and no `AUDIO_POST_CALIBRATION`.

### Operator enum correction

The current operator spec pins the relevant global cal_type enum:

- `10 = ADM_CUST_TOPOLOGY`
- `14 = ASM_CUST_TOPOLOGY`
- `20 = AFE_FB_SPKR_PROT`
- `24 = AFE_CUST_TOPOLOGY`
- `39 = CORE_CUSTOM_TOPOLOGIES`

Therefore V2652's cal_type `20` is a real Android-good SET edge, but it is **not**
one of the custom-topology definitions that explain the V2648 DSP rejections.

### V2648 failure mapping

V2648 already accepted the native replay order `39,13,9,11,12,15,23,16,21` at the
kernel SET layer, then failed inside the DSP:

- `adm_open topo_id 0x10004000 -> ADSP_EFAILED`
- `afe ... SET_PARAM_V2 -> ADSP_EBADPARAM`
- `q6asm_set_pp_params -> ADSP_ENEEDMORE`

The spec maps these to missing per-subsystem custom topology definitions:

- ADM needs `cal_type 10`
- ASM needs `cal_type 14`
- AFE needs `cal_type 24`

Adding cal_type `20` alone would not register those topology graphs.

## Replay Consequence

Do **not** run another native replay unchanged, and do **not** run a cal20-only replay.
The evidence supports three separate facts:

1. V2632/V2648 replay lacks a real Android-good cal_type `20` SET.
2. V2648's actual DSP failures are custom-topology failures, not speaker-protection
   feedback failures.
3. The required topology fix still needs byte-exact SET records for cal_types `10`,
   `14`, and `24`.

cal_type `20` should be retained as a real Android-good SET candidate for the eventual
full replay manifest, but it should not displace the custom-topology capture gate.

## Next Unit Design

The next meaningful unit should be a host/build unit, not native replay:

1. Reuse the V2630/V2632 own-process fake-SET mechanism.
2. Keep `AUDIO_SET_CALIBRATION` fake-successed; do not pass real SETs to the kernel.
3. After `acdb_loader_init_v3`, drive the vendor custom-topology send path in addition to
   `acdb_loader_send_audio_cal_v5`.
4. Capture every fake-successed SET arg byte range `arg[0:data_size]`.
5. For payload-backed records, capture the same-process dma-buf payload by `mem_handle`.
6. Accept only a manifest containing byte-exact records for cal_types `10`, `14`, and `24`.
7. Preserve the already found cal_type `20` evidence as a supplemental replay candidate,
   but do not mark the capture complete only because `20` appears.

The follow-on native replay should then replay, in order, the captured custom topology
SETs plus the prior accepted manifest. Its exact order must be derived from the captured
vendor call sequence, not guessed from the enum.

## Validation

- `GOAL.md`, `AGENTS.md`, `CLAUDE.md`, and
  `docs/OPERATOR_ACDB_IOCTL_INTERPOSE_CAPTURE_SPEC_2026-06-15.md` were reread.
- V2652 private manifest was inspected host-only.
- Local docs/source were searched for `AUDIO_SET_CALIBRATION`, `send_audio_cal_v5`,
  `AFE_FB_SPKR_PROT`, `ADM_CUST_TOPOLOGY`, `ASM_CUST_TOPOLOGY`, and
  `AFE_CUST_TOPOLOGY`.
- No raw ACDB bytes were copied into this report.
