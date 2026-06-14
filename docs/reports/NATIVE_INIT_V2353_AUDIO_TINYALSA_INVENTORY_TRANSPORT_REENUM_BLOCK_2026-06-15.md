# NATIVE_INIT V2353 — AUD-3C tinyalsa inventory blocked by post-flash NCM host re-enumeration

Date: 2026-06-15

## Scope

Exact-gated live AUD-3C attempt using the V2351/V2349 tinyalsa inventory runner.

Approval phrase used:

```text
AUD-3C-tinyalsa-inventory go: read-only tinyalsa mixer/PCM inventory on materialized V2334, no mixer set, no tinyplay/playback, rollback to V2321
```

Hard boundaries preserved:

- no `tinyplay`
- no PCM playback/write
- no `tinymix` control/value operands
- no mixer writes
- no audio HAL
- no `adsprpc` invoke/ioctl
- rollback to V2321 after the run

## Preflight

Host and device preflight passed before live execution:

```text
rollback V2321 sha256 = ca978551aabe4b39563abaf529ccf2522054952d8b2ad852e632d26da88168cb
fallback V2237 sha256 = b2ea2d26d160b7702ce7d4438b84367788eea26c6a5bbe4ed93f3d270292ac7f
fallback V48 sha256   = 1c87fa59712395027c5c2e489b15c4f6ddefabc3c50f78d3c235c4508a63e042

resident version = A90 Linux init 0.9.285 (v2321-usb-clean-identity-rodata)
resident selftest = fail=0
host NCM preflight = a90-ncm-host-ready
host ping 192.168.7.2 = pass
tcpctl ping = pong / OK
runner dry-run = ok
```

## Live Result

Run artifact directory:

```text
workspace/private/runs/audio/v2349-tinyalsa-inventory-20260615-010427
```

Decision:

```text
v2349-tinyalsa-inventory-live-blocked-before-inventory
```

The V2334 candidate flashed and booted successfully. Candidate status reported native-side transport readiness before the audio window:

```text
A90 Linux init 0.9.292 (v2334-audio-snd-nodes-preflight)
transport.ncm=ready
transport.ncm.ifname=ncm0
transport.ncm.ipv4=192.168.7.2
transport.tcpctl=ready
transport.tcpctl.port=2325
transport.upload=tcpctl-ready
transport.preferred=tcpctl
```

ADSP boot was accepted once:

```text
audio.adsp_boot_once.write=accepted
audio.adsp_boot_once.retry=forbidden
```

`/dev/snd` materialization reproduced the V2348 result:

```text
audio.snd_materialize.entries=128 allowed=61 with_dev=61 listed=61 missing=61 already_ok=0 invalid=0 refused=67 created=61 failed=0
audio.snd_materialize.open_attempted=0
audio.snd_materialize.ioctl_attempted=0
audio.snd_materialize.playback_attempted=0
```

Post-materialization `audio snd-status` confirmed all 61 allowed ALSA nodes existed and no playback was attempted:

```text
audio.dev_snd.count=61 control_like=1 pcm_like=59
audio.snd_status.entries=128 allowed=61 with_dev=61 listed=61 missing=0 already_ok=61 invalid=0 refused=67 created=0 failed=0
audio.status.audio_playback_attempted=0
```

Tinyalsa inventory did not execute. The runner stopped before staging `tinymix`/`tinypcminfo` because both host-side transfer readiness probes failed after the V2334 flash/materialization window:

```text
ping -c 1 -W 2 192.168.7.2
# 1 packets transmitted, 0 received, 100% packet loss

tcpctl_host.py ... ping
# TimeoutError: timed out
```

Raised error:

```text
RuntimeError: neither tcpctl nor host NCM ping is ready; cannot stage tinyalsa tools
```

## Rollback / Health

Rollback to V2321 completed successfully:

```text
A90 Linux init 0.9.285 (v2321-usb-clean-identity-rodata)
selftest: pass=11 warn=1 fail=0
```

A follow-up serial health check on the resident rollback image also passed:

```text
version = 0.9.285 build=v2321-usb-clean-identity-rodata
status selftest fail=0
selftest verbose fail=0
```

## Interpretation

This was not an audio-materialization failure. The audio side reached the same safe pre-inventory point as V2348:

- ADSP boot accepted once.
- `/dev/snd` nodes materialized: 61 nodes, including `controlC0` and 59 PCM-like nodes.
- No ALSA open/ioctl, mixer write, tinyalsa command, PCM write, or playback occurred.

The blocker is host-side NCM/tcpctl reachability after USB re-enumeration for the flashed V2334 window. V2352 repaired the host NetworkManager profile for the then-current A90 NCM ifname, but the live flash/rollback cycle can enumerate a different host interface name/MAC. The current runner only probes ping/tcpctl after materialization; it does not repair or rebind the host NCM profile for the candidate-boot interface before staging tools.

## Next Unit

Do not retry AUD-3C unchanged.

Next host-only repair should make the inventory runner resilient to candidate-boot USB NCM re-enumeration before tool staging. The bounded fix is to run the existing host NCM preflight/setup logic after candidate boot or immediately before transfer selection, then verify:

```text
host has 192.168.7.1/24 on the current A90 NCM interface
ping 192.168.7.2 passes
tcpctl ping passes or serial fallback is explicitly selected
```

Only after that host-side repair should another exact-gated AUD-3C live attempt run. The same hard boundaries remain: no `tinyplay`, no PCM playback/write, no mixer writes, and rollback to V2321.
