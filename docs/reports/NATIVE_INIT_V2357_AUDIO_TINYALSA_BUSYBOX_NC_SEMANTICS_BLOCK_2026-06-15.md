# NATIVE_INIT V2357 — AUD-3C blocked by BusyBox netcat semantics

Date: 2026-06-15

## Scope

- Unit: exact-gated AUD-3C live retry after V2356.
- Approval phrase used: `AUD-3C-tinyalsa-inventory go: read-only tinyalsa mixer/PCM inventory on materialized V2334, no mixer set, no tinyplay/playback, rollback to V2321`.
- Candidate image: V2334 `0.9.292` (`v2334-audio-snd-nodes-preflight`).
- Rollback target: V2321 `0.9.285` (`v2321-usb-clean-identity-rodata`).
- Raw private run evidence: `workspace/private/runs/audio/v2349-tinyalsa-inventory-20260615-013451/`.

## Result

Decision: `v2349-tinyalsa-inventory-live-blocked-before-inventory`.

The run again reached post-materialization `tinymix` staging and then stopped before any tinyalsa inventory command ran.

## Positive evidence

- Candidate V2334 booted and passed the health gate.
- The token-gated ADSP boot command was accepted once.
- `/dev/snd` materialization reproduced successfully:
  - before materialization: `audio.dev_snd.count=0`
  - after materialization: `audio.dev_snd.count=61 control_like=1 pcm_like=59`
- The V2354 NCM repair again restored post-reenumeration transfer reachability:
  - `ncm_host_setup.py setup` selected the current host NCM interface,
  - host ping to `192.168.7.2` succeeded,
  - tcpctl ping returned `pong` and `OK`.
- Rollback to V2321 completed and final `selftest verbose` reported `fail=0`.

## Blocker

V2356 changed the AUD-3C runner from the missing `/cache/bin/toybox` path to `/cache/bin/busybox`. That fixed the path, but exposed a netcat semantic mismatch.

`tcpctl_host.py install` generates a toybox-style receive command:

```text
run /cache/bin/busybox netcat -l -p 18149 /cache/bin/busybox dd of=/cache/bin/.tinymix.tmp... bs=4096
```

With BusyBox `nc`, trailing command arguments do not execute unless the `-e PROG` form is used. The command therefore exited immediately with status 0, leaving no listener for the host transfer socket:

```text
[pid 656]
[exit 0]
OK
ConnectionRefusedError: [Errno 111] Connection refused
```

A post-rollback read-only help check confirmed the difference:

- `/bin/toybox netcat --help` supports listening with `COMMAND...` as the child process for an incoming connection.
- `/cache/bin/busybox nc --help` requires `-e PROG` for command execution after connect.

The lowest-risk follow-up is to keep the existing `tcpctl_host.py` command generator unchanged and set the AUD-3C runner toolbox path to `/bin/toybox`, which exists on the native-init runtime and matches the expected netcat semantics. This should avoid changing the shared installer globally.

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

V2358 should be host-only: change the AUD-3C runner default `--device-toolbox` from `/cache/bin/busybox` to `/bin/toybox`, update regressions to require `/bin/toybox` and absence of `/cache/bin/toybox`, run static validation, and require a fresh exact AUD-3C approval before any live retry.
