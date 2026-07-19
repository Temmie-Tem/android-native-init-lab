# S22+ FYG8 R4W1-C Connected-To-Live Runbook

Date: 2026-07-20 KST

Target: `SM-S906N/g0q/S906NKSS7FYG8`

State: connected policy ACTIVE; connected PASS present; replacement live source
SOURCE GO; live policy retired/inactive; candidate unconsumed.

This runbook freezes the remaining promotion sequence. It grants no device
contact or live authorization. `AGENTS.md` remains the binding policy.

## Frozen Preconnected Packet

```text
connected source checkpoint  64d317ab
connected policy binding     686b57d7
live helper                   65c137586b2decf160800f841b7243f3332108332043dbcaa548d7698e080c99
live focused test             c5966fb411983bed5b72e39400e8c8d15304ec0257e34e435ad5aae075ca1fbb
live policy template          06f28538c4fa358dabd5e35c6bab5e0cd5a83c6e78c39d9ba1a6c1516ced5497
binding packet generator      1a7ab0cd1ef1883e4db7e676203155a2ee402510914e7ccba5b749ed040e62e3
binding packet test           8c8a4edc01fa1814946c2e1a424bef501cb87bad152e9a39084877011305ffbd
connected helper              fa4e9b0a77032fbb8b17affb2ae985b80c990b6e4b07c0ee095328cfd80516b9
connected focused test        98938da61fc6a3f95389a31f019950fa00b3e6575687aab8d1edf5d070240251
connected ACTIVE clause       35f1d2cf8b9a4b25bac108832fb3f9ec9fd37e05c1b03f9fa34eeb5367c17ffa
```

Do not modify the live helper/test/template, connected helper/test/core, or
connected evidence after qualification. Any such change invalidates the
promotion chain and requires host requalification; connected-source changes
also require a new connected qualification.

## Stage 0: Host-Only Precheck

The following command has returned
`PASS_R4W1C_PRECONNECTED_SOURCE_PACKET_HOST_ONLY`:

```bash
PYTHONDONTWRITEBYTECODE=1 \
python3 workspace/public/src/scripts/revalidation/s22plus_fyg8_r4w1c_live_binding_packet.py \
  --preconnected-check
```

It requires connected policy ACTIVE, live policy inactive, connected PASS
absent, candidate unconsumed, exact source/template pins, and full artifact
qualification. It performs no device contact.

## Stage 1: Connected Read-Only Qualification

Required fresh acknowledgement:

`S22PLUS-FYG8-R4W1C-CONNECTED-READ-ONLY-DRY-RUN`

Only after that exact token, run:

```bash
PYTHONDONTWRITEBYTECODE=1 \
python3 workspace/public/src/scripts/revalidation/s22plus_fyg8_r4w1c_connected_gate.py \
  --connected-read-only-dry-run \
  --ack S22PLUS-FYG8-R4W1C-CONNECTED-READ-ONLY-DRY-RUN
```

The sole PASS is `PASS_R4W1C_CONNECTED_BASELINE_READ_ONLY`. The run must remain
read-only and report `device_writes=false`, `reboot=false`,
`download_transition=false`, `odin_transfer=false`, and `flash=false`. Its
canonical state is:

`workspace/private/state/s22plus_fyg8_r4w1c_connected_read_only_pass.json`

A failed or consumed connected exception does not authorize retry or live
promotion.

## Stage 2: Deterministic Live Binding

After connected PASS, do not edit frozen source or evidence. Generate the
private review packet with:

```bash
PYTHONDONTWRITEBYTECODE=1 \
python3 workspace/public/src/scripts/revalidation/s22plus_fyg8_r4w1c_live_binding_packet.py \
  --emit-after-connected
```

It must return `PASS_R4W1C_LIVE_BINDING_PACKET_EMITTED_HOST_ONLY` and create an
exclusive private packet containing `packet.json`, the rendered policy, and
the exact `AGENTS.md` clause. The generator cannot contact a device or edit
policy.

Independently review the exact packet and clause. While the live policy is
still inactive, rerun the packet source gate, syntax checks, 181 relevant
regression tests, and the complete offline artifact gate. Then copy the exact
clause into `AGENTS.md` in a separate commit. After activation, rerun syntax
checks, the 181 tests, and the live helper's complete `--offline-check`; do not
rerun the packet generator because its source gate intentionally rejects an
already-active live policy. Required final state is connected PASS present,
candidate unconsumed, and both the connected and live policies ACTIVE.

## Stage 3: Attended One-Shot Live

Only after Stage 2 is committed and requalified, request the fresh live token:

`S22PLUS-FYG8-R4W1C-DIRECT-PID1-LIVE`

Command:

```bash
PYTHONDONTWRITEBYTECODE=1 \
python3 workspace/public/src/scripts/revalidation/s22plus_fyg8_r4w1c_live_gate.py \
  --live \
  --ack S22PLUS-FYG8-R4W1C-DIRECT-PID1-LIVE
```

The helper repeats the complete baseline, binds the exact ADB serial and USB
topology/serial digest, seals Odin for the whole invocation, consumes the
one-shot immediately before candidate transfer, flashes only the exact
boot-only candidate AP, and requires the complete 120-second observation.

After candidate observation, the operator physically enters normal Samsung
Download. Every actual rollback transfer requires the fresh temporal token:

`S22PLUS-FYG8-R4W1C-NORMAL-DOWNLOAD-CONFIRMED`

Exact Magisk boot-only rollback and final observer are mandatory. Stock boot is
cleanup-only after a definite Magisk Odin nonzero return and can never PASS.

## Stage 4: Interrupted Recovery

Use recovery only after a valid consumed state exists and the device is in
normal Samsung Download:

`S22PLUS-FYG8-R4W1C-MAGISK-ROLLBACK-FROM-DOWNLOAD`

```bash
PYTHONDONTWRITEBYTECODE=1 \
python3 workspace/public/src/scripts/revalidation/s22plus_fyg8_r4w1c_live_gate.py \
  --rollback-from-download \
  --ack S22PLUS-FYG8-R4W1C-MAGISK-ROLLBACK-FROM-DOWNLOAD
```

The temporal Download confirmation remains mandatory. If a prior Magisk
transfer intent has ambiguous completion, only one retransmission is possible
after exact Magisk Android is absent and the operator supplies:

`S22PLUS-FYG8-R4W1C-AMBIGUOUS-MAGISK-ROLLBACK-RETRY`

Recovery never retransfers candidate and stops after two numbered attempts.

## Stop Conditions

Stop without improvisation on a pin or evidence mismatch, unexpected state,
wrong ADB serial, changed USB topology or serial digest, ambiguous endpoint,
non-normal Download screen, incomplete 120-second observation, observer or
marker-integrity failure, noncanonical timeline, or rollback health failure.
Never broaden the boot-only partition envelope or substitute generic approval
for an exact acknowledgement.
