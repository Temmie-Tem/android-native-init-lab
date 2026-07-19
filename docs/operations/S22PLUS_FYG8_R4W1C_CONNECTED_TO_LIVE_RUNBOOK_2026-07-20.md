# S22+ FYG8 R4W1-C Connected-To-Live Runbook

Date: 2026-07-20 KST

Target: `SM-S906N/g0q/S906NKSS7FYG8`

State: connected policy ACTIVE; connected PASS present; serial-bound live policy
RETIRED after one pre-consumption failure; candidate unconsumed; no-serial
physical-continuity source commit `841d046f` qualified `SOURCE_GO`; deterministic
packet and exact clause qualified `BINDING_GO`; separate policy activation next.

This runbook freezes the remaining promotion sequence. It grants no device
contact or live authorization. `AGENTS.md` remains the binding policy.

## Retired Serial-Bound Packet

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
source checkpoint commit      69b37554
binding packet                a2a4aa676af903f29f8ad43d05644efc3f4c3b461da9f6f9f171b59c055ea3c6
rendered ACTIVE clause        09a0388f533ffa9525d9d3b6264e5f53b377507aa00ec76b7e294b9596d90fe2
connected PASS record         4b8bd44ee171341592e987171137007376dec71432df05b39a29a083c0914f20
connected result              f954c9b7238932f97d0a51c85cd5623ae2deced5b6d4c443992fb73bb0906e3a
```

These live-source identities describe the retired serial-bound packet and must
not be used for a new live run. The connected helper/test/core and connected
evidence remain frozen and reusable by the separately qualified replacement.

## Current No-Serial Source Packet

```text
live helper                   ce39196e58c6e7be83e8e8bcf7b56cb46e0e4ef22c05c1251f58b3310aae57ff
live focused test             b0e8112ffb926505d625f1feb9d5343d316d9d158386bee98cba641dc5ef0987
live policy template          4bdba3b3cd2e08dd51f255c2a63bd6c160ee52235073686f150fdb375c47a3ca
binding packet generator      3d66c98423cbf5e3a7f5b6084a1f6c6f46d9f115e5692c57a935f16021e28381
binding packet test           8c8a4edc01fa1814946c2e1a424bef501cb87bad152e9a39084877011305ffbd
shared Odin core              ab418aac5ce4c854f433e2132bd9536a610991384ec82c50dc0ba063f1888a9b
shared live core              9bcade2532e77d538112836ebe9903bab832c1f2250151d3635260b6fd013725
focused live tests            57/57
exact six-file tests          189/189
full offline verdict          PASS_R4W1C_LIVE_GATE_OFFLINE_CHECK
source review                 SOURCE_GO
source checkpoint commit      841d046f
binding packet                3e9d5f1535be977a0e303898f1cf6f8f8272ecfea39b0831401198aad002af08
rendered ACTIVE clause        22255be65e282567827922acdc0b820d78f0fbf9f21b81425a40d6dfee384ba4
binding review                BINDING_GO
```

The replacement accepts Download serial absence only as an exact measured
property. It does not promote topology to a per-handset identity. The operator
must freshly attest uninterrupted physical continuity of the same handset,
cable, hub path, and host port through final rollback and Android return.

After the source checkpoint commit, do not modify the live helper, focused test,
template, binding generator, connected source, shared cores, or connected
evidence. Any such change invalidates the replacement promotion chain.

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
still inactive, rerun the packet source gate, syntax checks, 189 relevant
regression tests, and the complete offline artifact gate. Then copy the exact
clause into `AGENTS.md` in a separate commit. After activation, rerun syntax
checks, the 189 tests, and the live helper's complete `--offline-check`; do not
rerun the packet generator because its source gate intentionally rejects an
already-active live policy. Required final state is connected PASS present,
candidate unconsumed, and both the connected and live policies ACTIVE.

The retired serial-bound packet emitted at
`workspace/private/outputs/s22plus-r4w1c-live-binding-20260719T205737Z` is
historical and must not be installed.

Activation commit `38266106` changes only `AGENTS.md`. The installed fenced
block is byte-identical to the reviewed clause. Post-activation `py_compile`,
the exact 181-test set with ResourceWarning fatal, `git diff --check`, and the
complete 9.68 GB `--offline-check` pass. Independent read-only review returned
`POST_ACTIVATION_GO` with no HIGH, MEDIUM, or LOW blocker. Stage 2 is complete.

The later live attempt proved that normal FYG8 Download at exact topology
`2-1.3` exposes `04e8:685d` and a direct character node but no sysfs `serial`
attribute. It stopped before consumption and transfer. Commit `47fbbc35`
retires that ACTIVE clause; Stage 3 must not be invoked with its token. A future
replacement must be generated and reviewed from a helper that treats Download
serial absence as an exact measured target property while retaining topology,
arrival generation, node identity, hardened ticket, and final continuity gates.

The replacement packet emitted at
`workspace/private/outputs/s22plus-r4w1c-live-binding-20260719T215103Z` passed
independent review with no HIGH, MEDIUM, or LOW finding and verdict
`BINDING_GO`. Install only its exact 12,135-byte
`AGENTS_R4W1C_LIVE_CLAUSE.md`; do not regenerate or substitute it during
activation. Current `AGENTS.md` remains RETIRED until that separate commit.

## Stage 3: Replacement Not Yet Active

The serial-bound helper, its exact live token, and its rollback tokens are
retired and must not be invoked. The no-serial replacement source is qualified,
but there is still no executable Stage 3 because no new clause is ACTIVE.

Remaining promotion steps are deterministic packet generation, independent
binding review, a new separate ACTIVE policy commit, post-activation
requalification, and a fresh exact token supplied only after that checkpoint.

## Stage 4: Recovery Not Applicable

The failed run did not create a consumed state and did not attempt candidate
transfer. No rollback or interrupted-recovery action is authorized or needed.

## Stop Conditions

Stop without improvisation on a pin or evidence mismatch, unexpected state,
wrong ADB serial, changed USB topology or serial digest, ambiguous endpoint,
non-normal Download screen, incomplete 120-second observation, observer or
marker-integrity failure, noncanonical timeline, or rollback health failure.
Never broaden the boot-only partition envelope or substitute generic approval
for an exact acknowledgement.
