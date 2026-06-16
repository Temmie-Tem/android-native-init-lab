# NATIVE_INIT V2571 — ACDB per-device GET strategy after V2570

Date: 2026-06-16

## Scope

Host-only analysis/design after the V2570 pre-init per-device live run. No device action, no Android
handoff, no native replay, and no private raw ACDB bytes are committed.

## Inputs Re-checked

- V2570 live report and private metadata-only summaries.
- `docs/OPERATOR_ACDB_IOCTL_INTERPOSE_CAPTURE_SPEC_2026-06-15.md`, including the 2026-06-16 updates.
- `libacdbloader.so` exported symbols and disassembly around:
  - `acdb_loader_send_common_custom_topology` at `0x8cf1`;
  - `acdb_loader_send_audio_cal_v5` at `0x9d31`;
  - exported lower-level helpers such as `acdb_loader_get_audio_cal_v2` and
    `acdb_loader_get_calibration`.
- Current source for `libacdbtap_v2475.c` and `libacdb_preinit_perdevice_v2568.c`.

## Current Facts

1. **Topology is no longer the primary capture problem.** Operator verification in the spec records
   a real topology capture from V2547: command `0x13296`, indirect output, 4916 bytes, SHA-256
   `7c5d45efa40944bc23dcc83af9f0046249499bb13d1a03c3470c287127992b89`. The old criterion
   "`out_len==4916`" is obsolete for this function because the 4916-byte topology is behind an
   indirect pointer in `in_buf`, while the direct `out_buf` is only metadata.
2. **V2570 did not reach useful per-device GETs.** The V2568 hook entered
   `acdb_loader_send_common_custom_topology`, patched the initialized flag, and reached
   `before_send_audio_cal_v5`, but no AFE/AUDPROC/VOL payloads were captured and no
   `send_audio_cal_v5_return` marker appeared before timeout.
3. **The fake-allocation path is effective.** V2570 faked 25 `AUDIO_ALLOCATE_CALIBRATION` calls,
   including calibration types `11`, `12`, `15`, `16`, and `39`, without passing a real
   `AUDIO_SET_CALIBRATION` to the kernel.
4. **The current V2568 public-send path is not worth rerunning unchanged.** It calls the real
   common-topology function from inside an interposed common-topology hook, then calls the public
   `send_audio_cal_v5` API while `init_v3` is still inside its own initialization flow. The observed
   `real_common_topology_return=-92` and no-return `send_audio_cal_v5` behavior localize the blocker
   to this strategy, not to transport or rollback.

## Rejected Next Moves

- Do not rerun V2570 unchanged.
- Do not re-open HAL `LD_PRELOAD`/wrapper-exec injection; that path already hit higher-risk boot and
  service-environment walls.
- Do not chase another topology-only capture as the main win; topology bytes are already pinned once.
- Do not issue native `/dev/msm_audio_cal` replay or real `AUDIO_SET_CALIBRATION` until per-device
  payload bytes/order and cleanup policy are pinned.

## V2572 Recommended Implementation

Build a new host-only helper/preload revision with the following changes, then validate by private
build before any live handoff:

1. **Stop calling the real common-topology public function from inside its own interposed hook.**
   Either skip that call entirely or guard it behind a disabled-by-default diagnostic flag. The
   topology is already available from V2547, and the recursive/interposed context is a poor place to
   discover per-device payloads.
2. **Generalize indirect-output capture in `libacdbtap`.** Today it special-cases only topology
   command `0x13296`. Add a bounded generic path: for any armed `acdb_ioctl` with `ret==0`,
   `in_len>=8`, `in_word0` in `(0, A90_MAX_CAPTURE_LEN]`, and `in_word1` a non-null user pointer,
   hash and privately dump `*(uint8_t *)in_word1` for `in_word0` bytes. Keep the existing zero-buffer
   rejection. This catches topology-style and potential per-device indirect outputs without needing
   each command ID upfront.
3. **Increase metadata observability, not mutation.** Enable `A90_ACDBTAP_LOG_ENTER` for the next
   private build so every armed `acdb_ioctl` records `cmd`, `in_len`, `out_len`, and first input
   words before and after the real call. This is still read-only capture; no SET reaches the kernel.
4. **Drive per-device only after the initialization state is stable enough to produce GETs.** First
   build should keep V2568's current `send_audio_cal_v5(15,0,0x11135,48000,48000,0,1)` call but skip
   the real common-topology call and exit on a bounded timeout if no `acdb_ioctl` appears. If it still
   times out before the first per-device `acdb_ioctl`, stop live retries and move to static ABI RE of
   the lower-level exported getter structs.
5. **Classify success by payload semantics.** Full per-device capture requires `ret==0`, non-zero
   indirect or direct buffers, and a manifest containing the cal families expected from V2393/V2407:
   AFE (`16`), AUDPROC (`11`), VOL (`12`), and any ASM/ADM-relevant payloads that appear in order.

## Expected Outcomes

- `per-device-indirect-captured`: at least one non-zero indirect payload is captured after
  `send_audio_cal_v5` entry. Preserve ordered records and hand off for manifest mapping.
- `send-audio-cal-no-acdb-ioctl`: no armed `acdb_ioctl` occurs after `send_audio_cal_v5` entry. This
  closes the public-send strategy and forces lower-level ABI RE before another live run.
- `boundary-violation`: any real `AUDIO_SET_CALIBRATION` pass-through, native replay, or speaker
  write. Abort and rollback; do not use the run as positive evidence.

## Validation

Host-only design unit. No code or device state changed in this iteration. `git diff --check`
passed before committing this report.
