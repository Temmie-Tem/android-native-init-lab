# NATIVE_INIT_V2384_AUD4_NATIVE_SPEAKER_PILOT_NUMERIC_ROUTE_LIVE_2026-06-15

## Scope

Live retry of the AUD-4 native speaker pilot after V2383 changed non-enum route values from `On`/`Off` strings to numeric `1`/`0`.

Exact gate used:

```text
AUD-4-native-speaker-pilot go: one-shot V2377 observed route apply, low-amplitude tinyplay, reverse reset, rollback to V2321
```

Private evidence:

```text
workspace/private/runs/audio/v2379-native-speaker-pilot-20260615-051444/
```

## Safety Result

The recoverable envelope held.

- Started from V2321 with `selftest fail=0`.
- Flashed V2334 through the checked helper only.
- ADSP/card and `/dev/snd` materialization reproduced.
- Route reset commands ran in the `finally` path after playback failure.
- Rollback to V2321 completed.
- Final V2321 `selftest verbose` reported `fail=0`.

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

V2384 passed both earlier blockers:

1. `cmdv1x` preserved space-containing mixer control names.
2. Numeric `BOOL` values fixed the V2382 `only enum types can be set with strings` blocker.

All 13 route apply commands returned `rc=0`, including the previous failing command:

```text
apply-453-SLIMBUS_0_RX Audio Mixer MultiMedia1 rc=0
cmd=['cmdv1', 'run', '/cache/a90-runtime/bin/v2379-speaker-pilot/tinymix', '-D', '0', 'SLIMBUS_0_RX Audio Mixer MultiMedia1', '1', '0']
```

All 12 reset commands also returned `rc=0`, including numeric bool reset values:

```text
reset-453-SLIMBUS_0_RX Audio Mixer MultiMedia1 rc=0
cmd=['cmdv1', 'run', '/cache/a90-runtime/bin/v2379-speaker-pilot/tinymix', '-D', '0', 'SLIMBUS_0_RX Audio Mixer MultiMedia1', '0', '0']
```

The run reached bounded `tinyplay`, but playback still failed:

```text
a90_tcpctl v1 ready
OK authenticated
[pid 691]
Error playing sample
Playing sample: 2 ch, 48000 hz, 16 bit 192000 bytes
Draining... Wait 85333 us
[exit 0]
OK
```

V2381 failure classification correctly treated `Error playing sample` as hard failure despite `[exit 0]`, then the runner reset the route and rolled back.

## Interpretation

The route-control layer is now proven executable under native init for this V2377-derived speaker route. The remaining blocker is PCM playback execution, not route command syntax.

The current evidence does not prove speaker sound. It proves only:

- ADSP and `/dev/snd` materialization work;
- pinned `tinymix` can apply and reset the observed speaker route;
- `tinyplay` reaches the PCM device but reports `Error playing sample`.

Because the live runner currently raises during `tinyplay`, partial `speaker_pilot` summary fields are not preserved in `result.json`; the per-step JSON evidence is intact. Preserve this as a V2385 runner/reporting fix candidate.

## Magisk Direction

No Magisk path was used. Magisk remains Android-side measurement fallback only and is not a solution for this native PCM playback blocker.

## Next

Host-only V2385 should classify the `tinyplay` failure before another live attempt:

1. Inspect the pinned tinyalsa `tinyplay` source at the staged commit to identify which code path prints `Error playing sample`.
2. Extend the runner to preserve partial `speaker_pilot` state on playback failure.
3. Add bounded diagnostics around playback: capture stderr/stdout, PCM open/write path details available from tinyalsa, and relevant dmesg/audio logs if safely observable.
4. Decide whether the next live run should change PCM params/device, add required stream controls, or only improve diagnostics.
