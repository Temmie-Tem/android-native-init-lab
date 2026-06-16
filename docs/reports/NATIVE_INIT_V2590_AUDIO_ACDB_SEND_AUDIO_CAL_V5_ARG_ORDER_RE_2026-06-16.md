# NATIVE_INIT V2590 — ACDB send_audio_cal_v5 stack-arg order RE

Date: 2026-06-16

## Scope

Host-only follow-up to V2588/V2589. No device action, Android handoff, ACDB command execution,
native replay `SET`, speaker write, or raw payload publication was performed. The private input
binary was `workspace/private/inputs/audio/acdb-deps-v2506/vendor-lib/libacdbloader.so`.

## Decision

- decision: `v2590-send-audio-cal-v5-stack-arg-order-corrected`
- V2588 used the fixed `arg2=1` RX/capability path, but still produced zero real armed
  `acdb_ioctl` rows.
- Host RE of the thin `send_audio_cal_v2/v3/v4` wrappers shows the V2586/V2588 helper used the
  wrong order for the two trailing semantic arguments.
- Do not rerun the V2586/V2588 artifacts. The next unit should build corrected-order artifacts that
  call `send_audio_cal_v5(15, 1, 0x11135, 48000, 0, 48000, 1)`.

## Evidence

### Wrapper-derived argument growth

Thumb disassembly of `libacdbloader.so` thin wrappers:

```text
acdb_loader_send_audio_cal_v4 @ 0xb550:
  [sp+0] = caller stack arg5
  [sp+4] = caller stack arg6
  [sp+8] = 1
  call send_audio_cal_v5

acdb_loader_send_audio_cal_v3 @ 0xb574:
  [sp+0] = caller stack arg5
  [sp+4] = caller r3
  [sp+8] = 1
  call send_audio_cal_v5

acdb_loader_send_audio_cal_v2 @ 0xb590:
  [sp+0] = 0
  [sp+4] = caller r3
  [sp+8] = 1
  call send_audio_cal_v5
```

This proves `send_audio_cal_v5` has three stack arguments and that the final one is the wrapper
hardcoded `1` instance/use-case flag. It also proves the middle stack argument is the older-wrapper
`r3` value, while the first stack argument is a newer/defaultable selector that v2 sets to `0`.

### v5 prologue stack loads

`send_audio_cal_v5 @ 0x9d30` loads its stack arguments as:

```text
9d88  ldr  r0, [sp, #168]      ; v5 arg7 -> local [sp+20]
9d8c  ldrd r11, r0, [sp,#160] ; v5 arg5 -> r11, v5 arg6 -> r0
9d94  str  r0, [sp, #32]
9d96  str  r0, [sp, #12]
```

Later use shows the first loaded stack arg (`r11`) is used as a key/list selector before the first
`0x1122e` dispatcher query, while the second loaded stack arg is forwarded into the later AFE path:

```text
9fa8  str.w r11, [sp]
9fb2  ldr   r2, [sp, #32]
9fb4  bl    <cal_type_16 helper>
```

This makes the previous call order suspect: V2588 passed `48000` as v5 arg5 and `0` as v5 arg6.
That likely keyed the pre-`0x1122e` setup on `48000` and forwarded `0` as the AFE sample-rate-like
value, matching the observed hang before any real armed `acdb_ioctl` row.

## Corrected Working Prototype

The source-level call should use:

```c
acdb_loader_send_audio_cal_v5(
    15,       // acdb_id, speaker RX device
    1,        // RX capability/path mask; nonzero so the arg2 gate does not bail
    0x11135,  // media app type 69941
    48000,    // sample rate
    0,        // session/internal selector, defaulted by v2
    48000,    // AFE sample rate / older-wrapper r3 value
    1);       // instance/use-case flag, hardcoded by v2/v3/v4 wrappers
```

The current public source calls the last three arguments as `(48000, 0, 1)`. That was adequate for
V2586's arg2 experiment but is not a valid final replay/capture call shape.

## Implications

- The V2538 post-init-arm fix is already implemented in the V2576/V2577 family; this unit does not
  revisit it.
- The V2588 no-record timeout is now better explained by `send_audio_cal_v5` stack-arg order than by
  an unknown loader state.
- A corrected-order build is a meaningful new measurement and should not count as a blind retry of
  the V2588 route.
- Native ACDB replay remains blocked until per-device payload bytes are captured and operator-verified.

## Recommended Next Unit

Build V2591 corrected-order artifacts:

1. preserve historical V2572/V2586 behavior by using a compile-time switch or a new source variant;
2. set RX/capability arg2 to `1`;
3. pass v5 stack args as `(session/default=0, afe_sample_rate=48000, instance=1)`;
4. keep `A90_ACDB_FAKE_ALLOCATE=1`, armed-only capture, zero-buffer discriminator, and no native
   `AUDIO_SET_CALIBRATION` replay;
5. statically validate the private helper/preload artifacts before any live handoff.

## Validation

- `llvm-objdump` Thumb disassembly generated under private scratch
  `workspace/private/runs/audio/v2590-send_audio_cal_recon/`:
  - `send_audio_cal_v5_9d30_a0c0.disasm`
  - `send_audio_cal_wrappers_b550_b5b0.disasm`
- Prior live basis: V2588 reached `before_send_audio_cal_v5`, then timed out with zero real armed
  `acdb_ioctl` rows and final V2321 rollback selftest `fail=0`.
- `git diff --check` for this report.
