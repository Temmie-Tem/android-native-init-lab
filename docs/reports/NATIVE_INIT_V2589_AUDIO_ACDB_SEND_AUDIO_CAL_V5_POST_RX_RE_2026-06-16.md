# NATIVE_INIT V2589 — ACDB send_audio_cal_v5 post-RX RE

Date: 2026-06-16

## Scope

Host-only follow-up to the V2588 live result. No device action, Android handoff, ACDB command
execution, native replay SET, speaker write, or raw payload publication was performed. The private
input binary was `workspace/private/inputs/audio/acdb-deps-v2506/vendor-lib/libacdbloader.so`.

## Decision

- decision: `v2589-send-audio-cal-v5-pre-get-blocker-localized`
- live basis: V2588 `arg2=1` reached `before_send_audio_cal_v5`, then timed out with zero real
  armed `acdb_ioctl` call rows.
- host RE basis: Thumb disassembly of `acdb_loader_send_audio_cal_v5` at `0x9d30`.
- next action: do not rerun identical `arg2=1`; design a source/RE-backed pre-GET localization or
  direct lower-get route.

## Key Findings

1. **The arg2 gate is real, but no longer the active blocker.** The function maps the second
   argument as a two-bit capability/mode selector: bit0 produces mode `0`; bit1-only produces mode
   `1`; `(arg2 & 0x3)==0` bails. V2588 used `arg2=1`, so it exercised the non-bail RX/mode-0 path.
2. **A first direct dispatcher `acdb_ioctl` exists before the per-device subcalls.** After the
   sample-rate/list setup, the function builds a small request and calls ACDB command `0x1122e` with
   `out_len=4`. If execution reached this point while armed, the current `acdbtap` wrapper would have
   recorded a real `acdb_ioctl` call row.
3. **V2588 recorded no real armed `acdb_ioctl` rows.** It recorded only the arm/control marker. The
   live hang therefore occurs before the first direct `0x1122e` dispatcher call, not inside the later
   AFE/AUDPROC/VOL GET handlers.
4. **The 25 fake `AUDIO_ALLOCATE_CALIBRATION` records are not sufficient evidence of per-device GET
   progress.** They occur during the broader initialized ACDB path and include zero-size allocation
   headers for many cal types, including `11`, `12`, `15`, and `16`, but no corresponding GET payloads
   or `AUDIO_SET_CALIBRATION` calls.
5. **SELinux is not the current blocker.** The captured AVC lines are generic Android boot/property
   denials plus unrelated kernel audit lines. There is no `/dev/msm_audio_cal` open/ioctl denial and
   no ACDB-specific denial explaining the hang.

## Control-Flow Notes

The relevant top-level flow is:

```text
entry
  -> initialized/global flag check
  -> arg2 capability/mode gate
  -> sample-rate/list setup keyed by the stack arg5 value
  -> local constructor/register path
  -> direct acdb_ioctl command 0x1122e, out_len 4
  -> only then: local per-device subcalls for cal-type families 9/11-or-49/12/16/17/23/etc.
```

V2588 reached the wrapper's `before_send_audio_cal_v5` marker but did not produce the first
`0x1122e` ACDB row. That localizes the live failure to the pre-`0x1122e` setup path.

## Implications

- Repeating the same `arg2=1` run is low-information and should count against the fails-twice guard
  if done without new instrumentation.
- `arg2=3` is not meaningfully different for this binary because bit0 overrides mode to `0`; it is
  expected to behave like `arg2=1`.
- `arg2=2` selects mode `1` and is a different branch, but it is not the speaker RX route and should
  not be the next default unless the operator explicitly wants a TX/mode-1 discriminator.
- The direct `store_get` guesses from V2585 remain invalid; the lower-get route needs more request
  geometry, not more blind selector retries.

## Recommended Next Unit

Build a host-only V2590 plan that either:

1. adds finer pre-`0x1122e` localization around the `send_audio_cal_v5` setup path without issuing
   native SET or speaker writes, or
2. derives a lower-level pure-read GET request from the actual local subcall inputs instead of the
   five V2585 store-get guesses.

Do not run another live capture until that new instrumentation or request geometry exists.

## Validation

- `llvm-objdump` Thumb disassembly of `libacdbloader.so` around `0x9d30..0xa0b0` into private run
  scratch.
- `llvm-readelf -s` symbol inventory confirmed the public function address and exported lower-get
  symbols.
- V2588 private logs inspected: `acdbtap-events.jsonl`, `acdb-v2572-perdevice-indirect-events.jsonl`,
  `ioctl-trace-events.jsonl`, and filtered AVC/ACDB logs.
- `git diff --check` for this report.
