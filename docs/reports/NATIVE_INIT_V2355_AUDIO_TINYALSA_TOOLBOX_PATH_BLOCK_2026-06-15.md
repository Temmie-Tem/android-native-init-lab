# NATIVE_INIT V2355 — AUD-3C tinyalsa inventory blocked by tcpctl toolbox path

Date: 2026-06-15

## Scope

- Unit: exact-gated AUD-3C live retry using the V2354 NCM re-enumeration repair runner.
- Approval phrase used: `AUD-3C-tinyalsa-inventory go: read-only tinyalsa mixer/PCM inventory on materialized V2334, no mixer set, no tinyplay/playback, rollback to V2321`.
- Candidate image: V2334 `0.9.292` (`v2334-audio-snd-nodes-preflight`).
- Rollback target: V2321 `0.9.285` (`v2321-usb-clean-identity-rodata`).
- Raw private run evidence: `workspace/private/runs/audio/v2349-tinyalsa-inventory-20260615-012014/`.

## Result

Decision: `v2349-tinyalsa-inventory-live-blocked-before-inventory`.

The run reached the post-materialization tinyalsa staging phase, but `tinymix` installation failed before any tinyalsa inventory command ran.

## Positive evidence

- Candidate V2334 booted and passed the pre-audio health gate.
- The token-gated ADSP boot command was accepted once:
  - `audio.adsp_boot_once.write=accepted`
  - `audio.status.audio_playback_attempted=0`
- `/dev/snd` materialization reproduced successfully:
  - before materialization: `audio.dev_snd.count=0`
  - materialization: `entries=128 allowed=61 with_dev=61 listed=61 missing=61 already_ok=0 invalid=0 refused=67 created=61 failed=0`
  - after materialization: `audio.dev_snd.count=61 control_like=1 pcm_like=59`
  - `audio.snd_status` after materialization reported the nodes as `already_ok=61`.
- The V2354 NCM re-enumeration repair worked:
  - initial host ping and tcpctl probes failed after candidate USB re-enumeration,
  - one `ncm_host_setup.py setup` repair reconfigured the host NCM interface,
  - post-repair host ping succeeded,
  - post-repair tcpctl ping returned `pong` and `OK`.

## Blocker

`install-tinymix` invoked `tcpctl_host.py install --install-control-channel tcpctl` with the default helper path from `tcpctl_host.py`:

```text
run /cache/bin/toybox netcat -l -p 18149 /cache/bin/toybox dd of=/cache/bin/.tinymix.tmp... bs=4096
```

On the current native-init baseline, `/cache/bin/toybox` is absent, so the receive command failed before opening the transfer socket:

```text
execve(/cache/bin/toybox): No such file or directory
ERR exit=127
ConnectionRefusedError: [Errno 111] Connection refused
```

A post-rollback read-only path check on V2321 showed:

- `/cache/bin/busybox` exists and runs,
- `/bin/busybox` exists and runs,
- `/bin/toybox` exists,
- `/cache/bin/toybox` is missing.

The next host-only repair is therefore to make the AUD-3C runner pass the existing `tcpctl_host.py --toybox` option explicitly as `/cache/bin/busybox` for tool staging and tcpctl-run checks, instead of relying on the stale `/cache/bin/toybox` default.

## Safety outcome

- No `tinymix` or `tinypcminfo` inventory command executed.
- No `tinyplay` path executed.
- No mixer set/write command executed.
- No PCM playback/write command executed.
- No audio HAL path executed.
- No `adsprpc` path executed.
- Rollback to V2321 completed.
- Final V2321 health check: `selftest fail=0`.

## Next step

V2356 should be host-only: patch the AUD-3C inventory runner to pass `/cache/bin/busybox` through `tcpctl_host.py --toybox`, add a regression that dry-run install commands include that path, run static validation, and require a fresh exact AUD-3C approval before any live retry.
