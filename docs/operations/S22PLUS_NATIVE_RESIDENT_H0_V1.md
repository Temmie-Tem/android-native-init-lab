# S22+ native resident runtime H0 V1

Status: **H0 IMPLEMENTED AND QUALIFIED; no live activation or device grant.**
Target: **SM-S906N / g0q / S906NKSS7FYG8**.

Results and limitations: [2026-09-11 H0 report](../reports/S22PLUS_NATIVE_RESIDENT_H0_V1_2026-09-11.md).

The operator selected implementation and host qualification of a resident
runtime on 2026-09-11. This bounded unit implements normal long-running local
services, CPU temperature reporting and bounded resource use. It does not
change the active [native baseline V1](S22PLUS_NATIVE_BASELINE_V1.md), its
900-second/eight-authentication profile, the consumed P385 grant or its admission.
Prospective resident code remains outside the active live owner and needs a
separate reviewed adoption before a device proposal.

## Implemented behavior

Native PID1 supervises local services from boot until explicit shutdown or
recovery. Host disconnect after clean DETACH does not stop normal telemetry or
HUD updates. A finite command session and a finite host F1 grant retain their
own deadlines; neither determines the normal service lifetime or renews device
authority. A service's failure and command admission are separate states.

The existing display continues for 900 seconds while its collector and fuel
gauge stop at 601 samples. A reproduced EOF then clears all metrics. Resident
operation must replace the producer, consumer and gauge limits together, retain
per-source freshness/status, and avoid the same mismatch in its log/frame bounds.

| Component | Resident behavior |
| --- | --- |
| PID1 | Cooperative nonblocking supervision; exact owned-child tracking and reaping; no DRM/I2C waits in the command loop |
| Command admission | Versioned boot-bound monotonic session counter, unique nonce construction, finite per-session commands/time; clean DETACH is the only normal reentry |
| System metrics | Periodic bounded procfs reads, independent from slow hardware reads; no session-count or 601-sample expiry |
| Hardware metrics | Exact existing gauge identity/register surface and verified CPU temperature types; a stalled worker retains its slot and cannot cause replacement process accumulation |
| HUD | Freshness and producer-state indication, continued idle updates, bounded current/next GEM ownership and matched-event retirement |
| Diagnostics | 64 retained complete records of at most 768 bytes, record/eviction/parser-drop counters, producer-drop observations and a bounded export footer; saturation cannot stop service |

## Fault and identity boundaries

- An uncertain consumed command/session latches command admission stopped for
  that boot. Local services may continue or report degraded status; their health
  cannot clear the command stop or replay any request or CONTROL.
- No automatic module reload, DRM reinitialization, USB reset or image transfer
  is part of this unit. Signalling a child does not prove it was reaped. A hung
  child retains its owned slot and there is no replacement-spawn loop.
- Every queue, child set, retained record window and sample structure has a
  fixed bound. Wide counters stop or saturate explicitly before wrap; nonce
  uniqueness never depends on evicting a previous-nonce history.
- CPU temperature is distinct from battery temperature. Selection uses the
  CPU type names in the exact Waipio source, not thermal-zone numbering. Missing,
  duplicate, malformed or unexposed sensors remain unavailable. Any maximum is
  labelled with its available-sensor coverage; incomplete coverage does not
  establish the hottest CPU sensor.
- Samples carry source sequence, collection time, units and validity. Retained
  values are visibly stale/stopped when freshness is lost. An old sample is
  never relabelled current after reconnect or worker failure.
- CPU temperature uses 13 source-named sensors (`cpu-1-0` through `cpu-1-8`,
  `cpu-0-0` through `cpu-0-3`). The hardware worker discovers their sysfs
  indices once, rejects duplicate names and verifies each retained name around
  every temperature read. It reports the maximum available reading in milli-C
  and its coverage. A source name does not prove native exposure.
- PID1, collectors, renderer and gauge timestamps use BOOTTIME. Validation after
  receipt allows a sample collected after the earlier supervisor tick instant.
  A nonzero owned-child exit upgrades prior socket EOF to a known worker fault.
- A complete export proves the bounded retained window was captured. It does
  not prove a lossless runtime history: eviction, parser drops, an unfinished
  line or renderer-pipe loss may precede it. No export renews command admission.
- Existing P385 source bytes and generated image identities remain unchanged.
  New composition uses separate resident sources and explicit shared inputs.
  Host qualification opens no current live lane and grants no unattended F1,
  automatic recovery, persistent data or other-target authority.

## Completed H0 checks

1. Execute the actual generated resident C with real framing, authenticated
   host replay, PTY detach/reopen and real service IPC. Hardware and clocks may
   be explicit fixtures; do not replace the affected producer/consumer logic.
2. Cross the old 601-sample and 900-second boundaries, then accelerated hour/day
   intervals. Verify fresh samples, bounded resources and retained-log semantics
   instead of merely counting rendered frames. Exercise counter exhaustion,
   corrupt frames, EOF, stale sensors, blocked/unreaped workers, log eviction,
   clean detach and uncertain command admission independently.
3. Verify CPU sensor matching, units, range, coverage and unavailable paths from
   fixed fixtures and the source mapping. This does not prove native sensor
   exposure or real thermal accuracy.
4. Build the actual runtime/renderer and changed gauge provider for AArch64 with
   the repository toolchain. Audit exact source inputs, target UAPI operands,
   applicable target-architecture behavior, ABI and output identities.
5. Complete one independent review of the changed runtime, protocol and service
   closure. Record functional results separately from live soak, target sensor
   exposure, physical display and recovery claims, which remain unproved here.

Later device qualification should increase observation duration in useful steps
after the H0 unit passes. Its duration, attendance, recovery and admission rules
belong to that separately reviewed adoption; these proposed stages confer no
standing device authority or live approval.
