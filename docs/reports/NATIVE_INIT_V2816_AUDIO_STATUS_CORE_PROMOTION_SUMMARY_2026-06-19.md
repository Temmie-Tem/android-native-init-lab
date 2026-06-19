# Native Init V2816 Audio Status Core Promotion Summary

## Summary

- Run ID: `V2816`
- Track: post-promotion audio Tier C observability.
- Device flash: no.
- Scope: make `audio status` report the promoted `0.10.0` audio-core state and safety envelope directly.

## Change

- `audio status` now emits a read-only promoted-core block:
  - `audio.status.core.promoted=1`
  - `audio.status.core.promotion_run=V2815`
  - `audio.status.core.version=0.10.0`
  - `audio.status.core.build_tag=v2812-audio-core-promotion-candidate`
  - `audio.status.core.validation_run=V2814`
  - `audio.status.core.native_play_gate=closed`
- `audio status` also emits the default profile endpoint, speaker map, app type, ACDB ID, sample format, route-control count, speaker count, amplitude cap, duration cap, and the explicit `wsa_speaker_protection_verified=0` safety boundary.

## Validation

- Host-only source contract update; no boot image was built or flashed.
- Focused validation: `tests/test_native_audio_command_profile_contract_v2751.py`.
- The change is read-only output only: no route write, ACDB SET, PCM playback, or device runtime action is added.

## Next

- A future flashed artifact can pick up this status surface; if that artifact changes the device-visible image, assign a new run/build identity and validate through the checked flash gate.
