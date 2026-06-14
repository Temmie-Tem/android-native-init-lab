# Native Init V2340 Audio Runner Serial Transport Recovery

## Summary

- Cycle: `V2340`
- Track: audio AUD-3 preflight runner hardening, host-only.
- Decision: `v2340-audio-runner-serial-transport-recovery-pass`
- Result: PASS
- Device flash: `no`.
- Device action: `none`.
- Touched runner: `workspace/public/src/scripts/revalidation/native_audio_snd_nodes_preflight_handoff_v2335.py`.
- Touched tests: `tests/test_native_audio_snd_nodes_preflight_handoff_v2335.py`.

## Reason

V2336 showed a serial protocol desync before the audio window, and V2338 showed the
runner can still depend on clean command/response parsing across a long flash,
health-check, ADSP, and rollback sequence. V2339 fixed the card-wait parser, but
the runner still used direct `a90ctl.py` subprocess calls for live native-init
commands.

`tcpctl_host.py` was reviewed as an alternative transport. It is useful for
helper `ping`/`version`/`status`/`shutdown` and `run <absolute-path>`, but it does
not directly invoke PID-1 native-init builtins such as `audio adsp-status`,
`audio adsp-boot-once`, or `audio snd-materialize-once`. Therefore it is not a
drop-in replacement for this AUD-3 runner.

## Change

- Routed live serial native-init commands through shared
  `a90_transport.run_serial_command_recovered()`.
- Allowed recovery retries only for read-only observation commands:
  - `version`
  - `status`
  - `selftest verbose`
  - `audio adsp-status`
  - `audio snd-status`
- Kept token-gated commands one-shot and non-retried:
  - `audio adsp-boot-once AUD2_ONE_SHOT_ADSP_BOOT`
  - `audio snd-materialize-once AUD3_DEV_SND_MATERIALIZE_ONLY`
- Persisted `serial_recovery` metadata in per-step JSON/text artifacts so a future
  live run shows whether a command used busy/protocol-noise/bridge-missing
  recovery.
- Left `native_init_flash.py` as the only flash path.
- Left dry-run command output in the existing `a90ctl.py` form for operator
  readability.

## Safety Boundary

- Host-only harness change.
- No bridge command was executed during this iteration.
- No flash, ADSP write, `/dev/snd` materialization, ALSA open/ioctl, mixer,
  tinyalsa, PCM, HAL, playback, or `adsprpc` action.
- A fresh exact AUD-3-preflight operator gate is still required before any live
  retry:

```text
AUD-3-preflight go: materialize ALSA /dev/snd nodes only on V2334, no open/ioctl/mixer/playback, rollback to V2321
```

## Regression Coverage

- Observation calls now assert `retry_observation=True` through
  `run_serial_transport_step()`.
- Token-gated materialization calls assert `retry_observation=False`, proving the
  runner does not ask the shared transport to retry one-shot AUD commands.
- Recovery metadata recording is covered with a mocked
  `run_serial_command_recovered()` result.

## Validation

- `python3 -m py_compile workspace/public/src/scripts/revalidation/native_audio_snd_nodes_preflight_handoff_v2335.py tests/test_native_audio_snd_nodes_preflight_handoff_v2335.py`: PASS.
- `python3 workspace/public/src/scripts/revalidation/native_audio_snd_nodes_preflight_handoff_v2335.py --dry-run`: PASS.
- `python3 -m unittest discover -s tests -p 'test_native_audio_snd_nodes_preflight_handoff_v2335.py'`: PASS (`8` tests).
- `python3 -m unittest discover -s tests -p 'test_*.py'`: PASS (`1004` tests).
- `git diff --check`: PASS.

## Next Step

With V2339 parser fix plus V2340 serial recovery hardening in place, the next
substantive step is the exact-gated V2334 AUD-3 preflight live retry. The current
informal "pre-approval" wording is intentionally insufficient; the runner still
requires the exact phrase above.
