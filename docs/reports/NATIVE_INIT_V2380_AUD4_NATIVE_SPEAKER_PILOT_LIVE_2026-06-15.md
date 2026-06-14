# NATIVE_INIT V2380 — AUD-4 Native Speaker Pilot Live Attempt

## Scope

V2380 ran the V2379 exact-gated AUD-4 native speaker pilot under the recoverable boot-only envelope.

Command:

```text
python3 workspace/public/src/scripts/revalidation/native_audio_speaker_pilot_live_handoff_v2379.py --run-live --approval 'AUD-4-native-speaker-pilot go: one-shot V2377 observed route apply, low-amplitude tinyplay, reverse reset, rollback to V2321'
```

Private evidence:

- `workspace/private/runs/audio/v2379-native-speaker-pilot-20260615-045042/`

## Safety Result

The safety envelope held:

- V2321 resident preflight: `selftest fail=0`.
- V2334 candidate flash: checked helper path only.
- ADSP/card appeared and `/dev/snd` materialization reproduced the known state:
  - `audio.sound_class.count=128`
  - `audio.sound_class.card_like=1`
  - `audio.sound_class.control_like=1`
  - `audio.dev_snd.count=61`
  - `audio.dev_snd.control_like=1`
  - `audio.dev_snd.pcm_like=59`
- Candidate post-pilot selftest: `fail=0`.
- Rollback to V2321 succeeded:
  - `rolled_back=True`
  - `rollback_version_ok=True`
  - `rollback_selftest_fail0=True`

No forbidden partition write or raw flash path was used.

## Functional Result

Do **not** classify V2380 as speaker-playback success.

The runner selected `tcpctl` for command execution. That transport does not preserve the V2377 mixer control names containing spaces when forwarding argv to the device-side command parser. Every route apply command reached `tinymix` with only the first word of the control name.

Observed examples:

```text
apply-3345-Audio Stream 0 App Type Cfg -> Invalid mixer control: 'Audio
apply-3344-Playback Channel Map0 -> Invalid mixer control: 'Playback
apply-453-SLIMBUS_0_RX Audio Mixer MultiMedia1 -> Invalid mixer control: 'SLIMBUS_0_RX
apply-346-SLIM RX0 MUX -> Invalid mixer control: 'SLIM
apply-188-RX INT7_1 MIX1 INP0 -> Invalid mixer control: 'RX
```

Summary:

```text
install_transport: tcpctl
route_apply_commands: 13
route_apply_invalid_mixer_control: 13
route_reset_commands: 12
route_reset_invalid_mixer_control: 12
tinyplay_attempted: True
tinyplay_host_step_ok: True
rollback_ok: True
```

`tinyplay` output contained:

```text
Error playing sample
Playing sample: 2 ch, 48000 hz, 16 bit 192000 bytes
Draining... Wait 85333 us
[exit 0]
OK
```

Because no route control was actually set, this does not prove speaker output or a valid route. The `Error playing sample` line is consistent with trying playback without the intended mixer route, but V2380 cannot distinguish PCM open success from audible output.

## Runner Bug

The V2379 live runner treated the host `tcpctl_host.py run` return code as sufficient. In this run, `tcpctl_host.py` returned host rc `0` while the device-side command body reported `ERR exit=2`. Therefore the V2379 runner incorrectly advanced and reported `v2379-native-speaker-pilot-live-pass-before-rollback`.

Two fixes are required before retrying AUD-4:

1. Route `tinymix` apply/reset commands through serial `cmdv1x` (or another transport that preserves argv with spaces), not tcpctl.
2. Treat `ERR exit=...` in tcpctl stdout as command failure even when the host process exits `0`.

`tinyplay` can remain on tcpctl because its argv has no space-containing control names, but the runner should still parse `ERR exit=` and the `Error playing sample` line explicitly.

## Decision

`aud4-live-attempt-safe-but-functionally-invalid`

V2380 proves the live safety envelope and rollback path for AUD-4, but it does not prove native speaker playback. The next unit should patch the runner transport/result parsing host-only, add regression tests for space-containing mixer controls and tcpctl `ERR exit=2`, then retry AUD-4 once.
