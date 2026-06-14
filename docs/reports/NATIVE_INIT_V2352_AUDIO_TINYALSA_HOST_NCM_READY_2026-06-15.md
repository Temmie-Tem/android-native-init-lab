# NATIVE_INIT V2352 — audio tinyalsa host NCM readiness restored

Date: 2026-06-15

## Scope

No flash, no ADSP command, no `/dev/snd` command, no tinyalsa execution.

Goal: verify and repair the host transport prerequisite for the next exact-gated AUD-3C tinyalsa inventory run after V2351 added transfer readiness and serial fallback logic.

## Finding

The resident V2321 device was healthy and reported native-side NCM/tcpctl readiness, but the host had not assigned `192.168.7.1/24` to the current A90 NCM interface.

Observed before repair:

```text
A90 NCM interface: enx6a745cf03a57
ID_VENDOR_ID=04e8
ID_MODEL_ID=6861
ID_SERIAL=A90-LNX_A90_Linux_ARM64_A90NATIVE001
host IPv4: none
ping 192.168.7.2: 100% packet loss
```

The host still had two stale `a90-v725-ncm-bench` NetworkManager profiles pinned to older ifnames:

```text
5dd11b05-eada-4b95-922d-0b5642e03aa5 -> enx4a99e758b508
0a80de46-1a66-402e-a0e8-a1cc3a3969ba -> enxda19f9d69997
```

## Action

Updated the existing non-autoconnect NetworkManager profile `5dd11b05-eada-4b95-922d-0b5642e03aa5` to the current A90 NCM ifname and activated it:

```text
connection.interface-name=enx6a745cf03a57
ipv4.method=manual
ipv4.addresses=192.168.7.1/24
ipv6.method=link-local
ipv6.addr-gen-mode=stable-privacy
connection.autoconnect=no
```

This is a host configuration repair only; no repository private artifact or device partition changed.

## Validation

After repair:

```text
a90_ncm_host_preflight.py run
# decision: a90-ncm-host-ready
# pass: True
# reason: A90 NCM candidate has expected CIDR and device ping passed

ip -br -4 addr show enx6a745cf03a57
# enx6a745cf03a57 UP 192.168.7.1/24

ping -c 2 -W 2 192.168.7.2
# 2 packets transmitted, 2 received, 0% packet loss

tcpctl_host.py ... ping
# a90_tcpctl v1 ready
# pong
# OK

a90ctl version
# A90 Linux init 0.9.285 (v2321-usb-clean-identity-rodata)

a90ctl selftest verbose
# selftest: pass=11 warn=1 fail=0

native_audio_tinyalsa_inventory_live_handoff_v2349.py --dry-run
# decision=v2349-audio-tinyalsa-inventory-live-dry-run ok=True
# remote_tools={'tinymix': '/cache/bin/tinymix', 'tinypcminfo': '/cache/bin/tinypcminfo'}
# readiness plan emits tcpctl-first / serial-fallback selection
```

## Next Gate

The next meaningful unit is the fresh exact-gated AUD-3C live inventory attempt using the V2351 runner.

Required phrase remains:

```text
AUD-3C-tinyalsa-inventory go: read-only tinyalsa mixer/PCM inventory on materialized V2334, no mixer set, no tinyplay/playback, rollback to V2321
```

Do not proceed to `tinyplay`, PCM playback/write, or mixer writes until read-only inventory succeeds and is reviewed.
