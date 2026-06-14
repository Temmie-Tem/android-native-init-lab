# NATIVE_INIT_V2391_AUD4_DMESG_CAPTURE_TRUNCATED_2026-06-15

## Scope

V2391 reran the pre-authorized AUD-4 native speaker pilot after V2390 added a read-only post-failure dmesg capture. This was a device run inside the existing recoverable envelope: V2334 candidate boot, observed V2377 route apply, low-amplitude PCM probe playback, route reset, and rollback to V2321.

Private evidence directory:

- `workspace/private/runs/audio/v2379-native-speaker-pilot-20260615-060536/`

## Result

Decision:

- `v2379-native-speaker-pilot-live-blocked`

Recovered state:

- Rolled back to V2321: `True`
- Rollback version OK: `True`
- Rollback selftest `fail=0`: `True`
- Manual post-run check also showed V2321 and `selftest fail=0`.

Functional path reached:

- ADSP boot: `accepted-protocol-ok`
- Route apply: `13/13` OK
- PCM probe open: OK
- PCM write path: failed at first write chunk with the same V2389 prepare error
- Route reset: `12/12` OK
- Reset verification: OK

Probe output:

```text
A90_PCM_PROBE_START version=V2386 card=0 device=0 channels=2 rate=48000 bits=16 data_bytes=192000 period_size=1024 period_count=4
A90_PCM_PROBE_PCM_OPEN_OK buffer_frames=4096 buffer_bytes=16384
A90_PCM_PROBE_WRITE_ERROR chunk=0 rc=-1 errno=22 strerror="Invalid argument" pcm_error="cannot prepare channel: Invalid argument" bytes=16384 frames=4096
```

## V2390 Observability Outcome

The new dmesg step ran and produced an artifact:

- Step: `dmesg-after-playback-failure-before-reset`
- Path: `workspace/private/runs/audio/v2379-native-speaker-pilot-20260615-060536/43_dmesg-after-playback-failure-before-reset.txt`
- Remote result: OK
- Size: 131151 bytes / 1356 lines

However, the capture is not diagnostic for the PCM prepare failure. Because the step used the selected tcpctl path, the remote output hit the transport output cap and ended with `[output truncated]` while still in early boot logs around `0.834s`. Searches inside the captured artifact found no useful playback-time terms:

- `A90_PCM`: 0
- `cannot prepare`: 0
- `pcm`: 0
- `q6asm`: 0
- `msm_pcm`: 0
- `snd_pcm`: 0
- `tiny`: 0

So V2391 confirms both facts:

1. The `SNDRV_PCM_IOCTL_PREPARE` `EINVAL` is reproducible with the V2386 probe and V2377-observed route.
2. Unbounded `/bin/toybox dmesg` over tcpctl is the wrong capture transport/shape for this failure because it truncates before the relevant playback-time tail.

## Safety

- No new route controls were introduced.
- No PCM geometry, sample rate, card/device, or amplitude changes were made.
- No smart-amp gain/boost poking.
- No Magisk/native dependency.
- No Wi-Fi/modem/eSoC/PCIe/GDSC/PMIC/GPIO/partition action outside the checked boot rollback path.
- Final state is V2321 with `selftest fail=0`.

## Next

V2392 should be host-only: change the failure capture to a bounded tail form that cannot be consumed by early boot logs. Preferred shape:

- Use serial transport, not tcpctl, for the failure-log step.
- Use `/bin/busybox sh -c 'dmesg | tail -n 240'` or an equivalent bounded helper if verified by dry-run/tests.
- Keep it read-only and still run before route reset.

Only after that should AUD-4 be rerun again to collect the actual driver log around `SNDRV_PCM_IOCTL_PREPARE`.
