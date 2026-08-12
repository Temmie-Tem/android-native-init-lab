# A90 headless handoff minimum and Wi-Fi ownership decision

Date: 2026-08-13
Target: operator-owned Samsung Galaxy A90 5G only
Tier: H0 design
Live authority: none

## Outcome

The project does not need to rewrite the proven UFS handoff from zero. It needs
to freeze a smaller product contract around the existing transaction core and
resolve one ownership question before allocating another candidate: **who owns
Wi-Fi after Debian starts?**

The preferred final architecture has no long-lived native process visible in
Debian's PID namespace. Native init performs bounded hardware bring-up, proves
all temporary helpers gone, mounts the exact UFS appliance read-only, creates
the minimal Debian runtime, and executes `switch_root`. Debian then owns SSH,
Wi-Fi, logging, and any future display. A nested native supervisor is considered
only if a small Wi-Fi ownership-transfer experiment proves that the sidecars
cannot be retired.

No H26 ordinal, version, profile, state path, artifact, or live runner is
created by this design. Identity allocation follows the Wi-Fi decision so a
failed design does not leave another dead candidate lineage.

## Current implementation inventory

| Area | Current implementation | Evidence status | Product decision |
|---|---|---|---|
| Boot resident | Exact boot-only F1 install, post-tool artifact revalidation, rollback and final native health | H24 installed and healthy | Keep |
| One-shot dispatch | Versioned enable/latch, latch before handoff, consumed-effect no replay | Live-proved in prior lanes | Keep; add compact cache receipt later |
| UFS discovery | Runtime `sda33`/`dev_t`, sector, label, UUID, marker, unmounted and clean-ext4 checks | Reviewed; multiple earlier live boundaries | Keep |
| UFS root | `ro,noload,nosuid,nodev` mount and exact content validation | H24 reached and proved mount/content | Keep |
| Writable runtime | Bounded tmpfs for `/run`, `/tmp`, `/etc/dropbear`, `/var/log` | H24 live-proved | Keep initially |
| Authentication | Boot-private `/root/.ssh` tmpfs overlay | H24 live-proved mount stage | Keep; formalize provisioning later |
| Debian `/dev` | Fresh tmpfs, exact core character nodes, mandatory devpts, no userdata block node | Host-qualified H24 design; H24 stopped before live execution | Keep and live-prove |
| Display cleanup | Bounded scan/release of native DRM owners before mount transition | Earlier live use; shared safety function | Keep until headless proof; remove broad scan only after explicit ownership exists |
| Persistent HUD | Native presenter plus private card root after UFS mount | H24 failed at bootstrap; H25 alternatives retired | Remove from headless path |
| Wi-Fi | Persistent native helper, Android companions and native autoconnect in shared network/PID environment | Earlier functional evidence, but old-root isolation is unproved | Block final candidate pending ownership decision |
| USB/NCM | Kernel gadget prepared for Debian; native TCP control is not required in Debian | Earlier observation path | Keep as attended recovery/first-proof channel |
| Same-run evidence | SD evidence-run file bind plus host observer/journal | Works but hard-requires SD | Replace with cache receipt plus authenticated live observation |
| Failure fallback | Stage/rc/errno attribution, child cleanup, mount restoration, UFS unmount, native continuation | Repeatedly exercised | Keep |
| Persistent terminal | Debian service proof while live, attended return/recovery for final native health | Contracted; earlier lanes exercised variants | Keep states separate |
| Benchmark | `CLOCK_BOOTTIME` stage markers plus CPU/GPU/temp/memory/power and `mmcblk0` sectors | Implemented test instrumentation | Keep host/test-only; correct storage counter for UFS before comparison |
| Rootfs services | Exact immutable H14 UFS content including Dropbear and optional legacy firstboot functions | Installed/read-only | Keep unchanged for first mechanical proof; rebuild separately |

This table separates "implemented" from "proved in one current run". H24's
failure at persistent HUD means the post-HUD minimal `/dev`, core-mount move,
and `switch_root` steps are reviewed source, not H24 live evidence.

## Absolute production requirements

The following remain even in the smallest build:

1. exact A90 target, installed-resident, candidate, rollback, and recovery
   identity;
2. boot-only transfer and a durable launch journal with candidate no-replay;
3. versioned one-shot handoff intent consumed before the effect;
4. fresh same-boot UFS identity and clean read-only mount proof;
5. exact writable tmpfs set, boot-private SSH authorization, and minimal Debian
   `/dev` with mandatory devpts;
6. exact failure stage/rc/errno recorded before cleanup, followed by bounded
   child reap, mount restoration, UFS unmount, and unchanged-userdata proof;
7. an attended recovery channel independent of Wi-Fi;
8. same-run authenticated proof of Debian namespace PID 1, SSH, root mount,
   minimal `/dev`, and network state;
9. final cable-free Wi-Fi owned by a component whose root, descriptors,
   namespace, credentials, and lifetime are explicitly bounded;
10. `HEALTH_PENDING_PERSISTENT_DEBIAN` while Debian is live and exact
    `RESIDENT_HEALTHY` only after attended return or recovery.

Logging is part of the minimum, but verbose telemetry is not. The target needs
only a compact durable sequence containing intent identity, checkpoint,
boottime, failure stage, rc/errno, cleanup result, and zero-write result. Raw
logs and large observer transcripts stay private on the host.

## Wi-Fi ownership gate W0

W0 is a separately reviewed D1, no-payload feasibility experiment. It does not
arm handoff, mount UFS, reboot, flash, or claim Debian health.

The exact experiment must:

1. start from the exact healthy installed resident and a USB recovery path;
2. identify the native Wi-Fi helper process group and every required child;
3. establish `wlan0` and record only redacted link state;
4. durably record stop intent, stop the group once, and prove every named PID
   and process-group member is reaped;
5. sample `wlan0` presence, carrier and driver state for a fixed short window;
6. make no association replay and send no external probe unless separately
   approved;
7. restore native service only through a predeclared bounded recovery branch;
8. publish `TRANSFER_FEASIBLE`, `TRANSFER_REFUTED`, or `NO_PROOF`, never a
   server PASS.

Decision:

- `TRANSFER_FEASIBLE` selects Debian-owned Wi-Fi. A fresh candidate gets a
  boot-private, non-SD configuration overlay and Debian performs association,
  DHCP, DNS, and final health. Every native helper must be gone before
  `switch_root`.
- `TRANSFER_REFUTED` selects an H0-only nested PID-namespace supervisor design.
  That design must keep native sidecars outside Debian's procfs and requalify
  cleanup, recovery, and health. It is not automatically authorized.
- `NO_PROOF` leaves the branch unresolved and authorizes no candidate.

## Minimal handoff state machine after W0

```text
native healthy
  -> fresh target/UFS/rollback preflight
  -> prepare recovery USB/NCM
  -> bounded vendor Wi-Fi bring-up
  -> W0-selected ownership boundary
  -> prove zero Debian-visible old-root sidecars
  -> durable one-shot intent and latch
  -> mount UFS read-only + tmpfs auth/runtime + minimal /dev
  -> durable pre-switch receipt
  -> switch_root once
  -> authenticated same-run Debian observation
  -> HEALTH_PENDING_PERSISTENT_DEBIAN
  -> attended return/recovery
  -> exact native RESIDENT_HEALTHY
```

Any failure before `switch_root` records the original failure first, cleans up,
and stays native. Any uncertain post-intent state parks; it does not resend arm,
reboot, candidate transfer, or handoff.

## Test and benchmark features

Test instrumentation is intentionally outside the production minimum:

- stage timestamps for native start, cache readiness, Wi-Fi boundary, UFS
  mount, writable-set ready, pre-switch, Debian SSH ready, and final network;
- CPU 0/4/7 clock, GPU clock, CPU/GPU/battery temperature, memory/load,
  battery current/voltage, and calculated power sampled at a small fixed set of
  stages rather than continuously;
- storage counters from exact UFS whole device `sda`, not the current
  `mmcblk0`-only counter;
- boot-to-handoff, handoff-to-SSH, handoff-to-Wi-Fi, and steady-state samples;
- target binary size and rootfs manifest size;
- a fixed workload after functional success, then section-GC and Full-LTO as
  separate build comparisons.

Benchmark collection never delays, retries, or changes a handoff decision.
Missing telemetry is `na`; it cannot turn an unsafe or unhealthy run into PASS.
Continuous polling, long trace windows, debugfs, firmware trace, display HUD,
CPU stress, and smoke/tunnel traffic are laboratory features and are absent
from the final production profile.

## Removal schedule

### Remove before the next candidate

- persistent native HUD and all display-success predicates;
- firstboot overlay and boot chime;
- SD evidence bind and compiled SD property-root dependency;
- any long-lived native process whose old root is visible in Debian `/proc`;
- continuous HUD polling and display presenter artifacts;
- candidate-specific legacy rootfs copy/hash work from the direct-UFS lane.

### Keep for first proof, then reduce

- strict display-owner release;
- detailed stage attribution and private raw logs;
- USB/NCM attended observation;
- existing immutable UFS root content;
- conservative Wi-Fi bring-up diagnostics selected by W0.

### Remove from the formal production image after repeated proof

- formatter/populator and experimental shell commands;
- debugfs and firmware trace;
- long Wi-Fi watcher/supervisor budgets;
- HUD, Doom, stress, smoke HTTP and tunnel binaries/content;
- benchmark emitters beyond a small optional diagnostics build;
- obsolete lineage adapters from the active package, while Git/archive retains
  their evidence.

Host approval, journaling, rollback, recovery, and final-health evaluation are
not target-image bloat and remain.

## Why the implementation became large

The growth was not caused by one slow function. Four concerns accumulated in
the same target and host surfaces:

1. product services: SSH, Wi-Fi, display, HUD, tunnel and smoke checks;
2. safety transaction: target identity, rollback, no-replay, mount restoration
   and terminal health;
3. experiment tooling: SD copying/hashing, UFS population, traces, benchmarks,
   stress and display tests;
4. incident compatibility: each failure added a new parser, marker, observer,
   version branch, and retained historical adapter.

Safety checks should be shared and retained. Product and experiment features
must become separate modules/profiles, and retired adapters should remain
historical rather than ship in init. Compiler optimization comes only after
this ownership and module split; LTO cannot correct an unsafe process model.

## Exit criteria

This design advances to candidate implementation only when W0 has one terminal
result and an independent review agrees with the selected ownership branch.
The final candidate then needs its own fresh identity, deterministic boot-only
artifacts, capability qualification, connected D0, attended F1 approval,
resident health, separate attended D1 approval, and same-run result. This H0
document grants none of those authorities.
