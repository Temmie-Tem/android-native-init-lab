# NATIVE_INIT_V2382_AUD4_NATIVE_SPEAKER_PILOT_RETRY_2026-06-15

## Scope

Live retry of the exact-gated AUD-4 native speaker pilot after the V2381 transport hardening.

Exact gate used:

```text
AUD-4-native-speaker-pilot go: one-shot V2377 observed route apply, low-amplitude tinyplay, reverse reset, rollback to V2321
```

Private evidence:

```text
workspace/private/runs/audio/v2379-native-speaker-pilot-20260615-050456/
```

## Safety Result

The recoverable envelope held.

- started from V2321 with `selftest fail=0`;
- flashed V2334 through the checked helper only;
- ADSP/card and `/dev/snd` materialization reproduced;
- rollback to V2321 ran after the blocked route step;
- final rollback version check passed;
- final rollback `selftest verbose` reported `fail=0`.

Summary from `result.json`:

```json
{
  "decision": "v2379-native-speaker-pilot-live-blocked",
  "rolled_back": true,
  "rollback_version_ok": true,
  "rollback_selftest_fail0": true
}
```

## Functional Result

Speaker playback was not attempted. The run stopped at the first route control that failed after the stream config controls:

```text
apply-453-SLIMBUS_0_RX Audio Mixer MultiMedia1
```

The new serial `cmdv1x` route transport worked as intended: the mixer control name arrived intact as one argv entry, and there was no `Invalid mixer control` split-name failure.

Device-side failure:

```text
cmdv1x ... 36:534c494d4255535f305f525820417564696f204d69786572204d756c74694d6564696131 2:4f6e 3:4f6666
A90P1 BEGIN seq=27 cmd=run argc=7 flags=0x2
run: pid=679, q/Ctrl-C cancels
Error: only enum types can be set with strings
[exit 22]
[err] run rc=22 (101ms)
A90P1 END seq=27 cmd=run rc=22 errno=0 duration_ms=101 flags=0x2 status=error
```

Runner behavior was correct: V2381 classified `[exit 22]` as hard failure and aborted before playback.

## Interpretation

V2380's transport blocker is fixed. The next blocker is value encoding, not argv transport:

- Android/V2377 route-delta recorded human-readable values such as `On Off`.
- The native `tinymix` build rejects string values for this control with `Error: only enum types can be set with strings`.
- That implies at least some route controls are not enum controls and must be set with numeric values, likely `1`/`0` for boolean controls.

The first two stream config controls completed before this blocker, so the failure point is specifically the first route switch using string values.

## Magisk Direction

No Magisk path was used or needed in V2382. This remains consistent with the current policy:

- Magisk is an Android-side measurement fallback only;
- native AUD-4 playback must not depend on Android services, Magisk, `su`, or framework playback;
- if a future Android route-delta delivery wall appears, a private temporary Magisk module can be designed separately, as in earlier Wi-Fi-style handoffs.

## Next

Run a host-only V2383 route-value encoding fix before any further AUD-4 live attempt:

1. Re-parse V2377/V2382 `tinymix --all-values` with control types/counts.
2. Convert non-enum `On`/`Off` route values to numeric `1`/`0` where appropriate.
3. Preserve enum strings only for enum controls such as mux selectors.
4. Add tests proving the first route switch becomes numeric while enum mux values remain strings.
5. Dry-run the pilot plan and only then retry AUD-4 once.
