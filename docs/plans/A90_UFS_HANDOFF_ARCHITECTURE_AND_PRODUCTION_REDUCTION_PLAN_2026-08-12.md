# A90 UFS handoff architecture and production reduction plan

Date: 2026-08-12
Target: operator-owned Samsung Galaxy A90 5G only
Tier: H0 architecture and documentation
Live authority: none

## Decision

The next A90 server successor should first prove a smaller **headless** Debian
handoff. Persistent native HUD, display ownership, boot-time HUD self-test,
firstboot overlay, and boot chime do not belong in that first critical path.
Display becomes a separately qualified optional capability after Debian PID 1,
authenticated SSH, final Wi-Fi, and the minimal Debian device tree are stable.

This is a reduction in the claim and attack surface, not a relaxation of the
permanent safety boundaries. Boot-only transfer, exact target selection,
rollback, recovery, read-only UFS, durable one-shot/no-replay state, minimal
Debian `/dev`, cleanup, and terminal health remain mandatory.

2026-08-13 refinement: the next candidate is deferred until Wi-Fi ownership is
decided. The persistent native Wi-Fi companion keeps an old-root mount
namespace while Debian receives shared procfs, so private `CLONE_NEWNS` alone
cannot support a minimal-exposure claim. The binding follow-up is
`A90_HEADLESS_HANDOFF_MINIMUM_AND_WIFI_OWNERSHIP_DECISION_2026-08-13.md`.
Prefer a bounded proof that all native Wi-Fi sidecars can be reaped and Debian
can take ownership. Consider a nested PID-namespace supervisor only if that
proof is refuted and after a separate hazard review.

The installed H24 resident is unchanged. Its consumed D1 effect is not retried.
H25 is `NO_GO_RETIRED`; this plan creates no H26 or other successor identity,
artifact, approval, or live authority.

## Frozen anchors

- Repository baseline at the start of this audit: `f2820159a5f4`.
- Installed resident: H24 `0.11.192`, build
  `phase3-minimal-h24-ufs-auth-native-hud-private-card-root-minimal-debian-dev`.
- H24 manifest SHA-256:
  `40c26c5878db21737600bc29864db9123cc4650ec39d7f0d7395209c2df70a8f`.
- H24 native closure:
  `3d1514e3f266e5b77886bf4511a396c9328b487b0c614c3c79fd3df16d26ca52`
  / 142 files.
- H24 boot-only resident:
  `d8c280e4acee5d17d13270fdf25535b4ce05304e786bc22efa84ab16f6b82782`
  / 58,372,096 bytes.
- H24 D1 terminal:
  `REFUTED_H24_POST_ROOT_FAILURE_ATTRIBUTED_NATIVE_FALLBACK_HEALTHY` with
  exact post-return native `RESIDENT_HEALTHY`.
- Rollback identity: exact V2321 as bound by the target contract and future
  fresh runner; no artifact bytes are recorded here.

These anchors describe evidence. They do not make H24 or any successor
live-eligible.

## Actual H24 automatic path

### 1. Arm and reboot

`a90_auto_handoff_arm_cmd()` validates the compiled binding and versioned state
paths, requires the enable and latch to be absent, performs a full read-only UFS
qualification, durably creates the enable marker, and dispatches the separately
approved reboot. The arm-time qualification is intentionally cross-boot
preparation; it cannot replace the armed-boot revalidation.

### 2. Armed native boot

`a90_auto_handoff_run_once()`:

1. validates the compiled binding, enable, and latch state;
2. repeats the full UFS qualification against current boot topology;
3. durably creates the latch before the handoff effect, making replay invalid;
4. publishes the on-device evidence-run identity under the SD evidence tree;
5. calls `a90_server_distro_switch_root_userdata_ro()` once.

### 3. Read-only UFS handoff

The active H24 `a90_server_distro_switch_root_userdata_ro()` sequence is:

1. validate the compiled UFS identity and expected content binding;
2. resolve exactly one `PARTNAME=userdata` candidate and verify expected
   `sda33`, sector count, runtime `dev_t`, private node identity, unmounted
   state, ext4 magic/journal-clean state, label, and UUID;
3. create the future root directory;
4. stop native display owners and release KMS/DRM strictly;
5. repeat target identity preflight after display cleanup;
6. make mount propagation private;
7. mount UFS `ro,noload,nosuid,nodev` and prove it is read-only;
8. validate the appliance marker and exact H14 content manifest;
9. create and probe four bounded writable tmpfs paths: `/run`, `/tmp`,
   `/etc/dropbear`, and `/var/log`;
10. mount the boot-private observer authorization overlay at `/root/.ssh`;
11. start H24's persistent native HUD private-root service;
12. bind the SD evidence directory and the redacted Wi-Fi handoff input;
13. validate `/sbin/init` and the display-release marker;
14. move `/proc` and `/sys`, create a fresh minimal tmpfs `/dev`, create exact
    core character nodes, and mount mandatory devpts without moving native
    devtmpfs or creating a userdata block node;
15. execute BusyBox `switch_root` into `/sbin/init`.

Every pre-exec failure records the exact stage/return/errno, stops transient
children, removes owned overlays and binds, restores core mounts, unmounts UFS,
and returns to native without replaying the consumed intent.

H24 reached step 11 and returned `persistent-hud rc=-22 errno=22`. Therefore
steps 12-15 were **not** live-proved by H24. Their reviewed source design remains
useful, but it is not same-run device evidence.

## Storage and ownership model

| Surface | Intended owner and lifetime | Production judgment |
|---|---|---|
| UFS appliance root | Debian root, mounted read-only with journal replay disabled | Core; retain |
| `/run`, `/tmp`, `/etc/dropbear`, `/var/log` | Fresh bounded tmpfs for one Debian boot | Core initially; revisit sizes later |
| `/root/.ssh` | Boot-private tmpfs populated from reviewed observer input | Keep until formal key provisioning replaces it |
| Debian `/dev` | Fresh bounded tmpfs plus exact core nodes and devpts | Core safety boundary |
| Native devtmpfs | Remains outside Debian | Core safety boundary |
| Native HUD card0 root | H24-only child namespace/private root | Remove from headless critical path |
| Wi-Fi handoff | Read-only, redacted input consumed by Debian | Core for cable-free server use |
| SD evidence bind | Proof sidecar under `/mnt/sdext` | Temporary hard dependency; replace before SD removal |
| UFS firstboot | Immutable script in the existing appliance image | Rebuild separately after headless success |

The physical storage device may contain several partitions, but the automatic
lane treats only the exact UFS appliance filesystem as Debian root and writes no
partition. UFS root content changes are a separate population/content-manifest
operation, not part of this documentation unit.

## Residual SD dependencies

The current lane is direct-UFS for the Debian root, but is not yet SD-free:

- `a90_auto_handoff.c` publishes the run identity beneath
  `/mnt/sdext/a90/runtime/evidence/a90-ondevice-evidence-run`;
- the switch-root path hard-gates `d3_bind_evidence_dir()` before proceeding;
- the H24 build embeds the Wi-Fi property root
  `/mnt/sdext/a90/private-property-v317/v726/dev/__properties__`.

The public closure does not prove whether every armed Wi-Fi path dereferences
that property root, so SD removal is unproved. The current H24 resident may use
its exact known SD only for the separately approved pre-candidate W0 ownership
test. Before any fresh A90 successor candidate is created, both dependencies
must be replaced by a reviewed compact cache receipt/authenticated same-run
observer and a boot-private non-SD Wi-Fi input. HUD removal alone is not the
SD-removal gate.

## Exact firstboot distinction

H24 compiles `A90_UFS_FIRSTBOOT_OVERLAY_V1=0`. The exact installed UFS
`/etc/a90-d3-firstboot` is therefore the 12,092-byte file with SHA-256
`fd8625402c76b2ee0cc4a2aff07eed3b182c6dd12eba1a022a445ea428c8c84a`
from commit `a4925b80eadf781cf524c7eaf6741bb940ce78d4`. It is 345 lines.

The current public `a90_dpublic_firstboot.sh` is a different later source:
13,515 bytes, 384 lines, SHA-256
`6ffba1fb45a98b6d9861d112caed3643bf062f6bea6ef9748fec489656008d86`.
It must not be cited as the exact H24 post-exec runtime. Its HUD, tunnel,
smoke-HTTP, and resolver-write logic is design input for a future rootfs rebuild
only. In particular, its `/etc/hosts` and `/etc/resolv.conf` writes conflict with
the current read-only-root writable set and should be redesigned, not inherited.

## Where the size came from

The handoff grew because product runtime, safety transaction machinery,
incident diagnostics, and historical experiments accumulated in the same
source and qualification surfaces.

### Target binary source

- `a90_server_distro.c`: 8,030 lines / 258,111 bytes.
- Defensible HUD-only source regions: about 1,940 lines, 24.2% of that file.
  They include presenter/parser, service/private-root, H23/H24 parent
  validation/start/stop, and the UFS shared-HUD-run bind.
- Generic native display-owner scanning/release adds about 589 lines, 7.3%.
  It is shared safety code and should remain through the first headless proof;
  it is not counted as immediate HUD-only deletion.
- `a90_auto_handoff.c`: 971 lines / 33,086 bytes.
- `a90_kms.c`: 1,850 lines / 60,175 bytes.

H24's persistent HUD also adds one surviving child, a private mount namespace,
card0 and public-run binds, bounded private tmpfs mounts, and a 100 ms poll loop
that may attempt work up to ten times per second.

### Host execution machinery

- H24 observer: 575 lines / 23,088 bytes.
- H24 D1 runner: 2,217 lines / 81,873 bytes.
- H24 F1 runner: 3,732 lines / 147,317 bytes.
- Total: 6,524 lines / 252,278 bytes.

These files are not shipped as target init. Much of their size implements exact
approval binding, crash-prefix reconstruction, no-replay, post-flash source
revalidation, rollback, attribution, and terminal evidence. They should be
modularized and archived by lineage, but not removed merely to make a line-count
metric smaller.

### Debian content

The H14 content manifest binds 19 objects totaling 4,247,011 declared bytes.
HUD intent/presenter, smoke HTTP, and service-launch objects account for 855,448
bytes, about 20.1%. They may remain inert for the first headless proof because
changing them mutates the rootfs content contract; remove them only in a
separately versioned UFS image/content-manifest change.

The later 384-line public firstboot source devotes inclusive source spans of
126 lines to HUD, 115 to tunnel handling, and 18 to smoke HTTP: 259 lines,
67.4%, including comments and glue. Again, this quantifies a future design, not
the exact H24 runtime file.

### Why compile flags alone do not shrink it

A public-only `/tmp` comparison rebuilt the exact H24 manifest and an in-memory
variant with persistent-HUD/private-root/delayed-DRM flags disabled. Both
stripped static init files were 1,723,376 bytes. Text was 1,564,354 bytes for
H24 and 1,567,594 bytes for the HUD-off variant; HUD-off was 3,240 text bytes
larger. The experiment changed no tracked or private file and its temporary
output was deleted.

This is not a performance result and the variant is not a candidate. It proves
only that the current monolithic link and conditional layout do not produce a
useful size reduction from those macro flips alone. Physical module separation
and init-specific section garbage collection must precede any size claim.

### Historical causes

1. The original SD image/work-copy path needed multi-gigabyte copying, hashing,
   cleanup, and automatic-return evidence.
2. Direct UFS removed the copy cost but retained older receipts and manual
   paths for recovery and comparison.
3. Read-only UFS required writable tmpfs overlays and boot-private SSH input.
4. Wi-Fi timing, dynamic `dev_t`, observer-key, mount, `/dev`, and display
   incidents each added a fail-closed layer while preserving older code.
5. “Debian server is healthy” and “native display remains visible” became one
   terminal claim, pulling a long-lived native HUD into the handoff.
6. No-replay and crash recovery correctly expanded host evidence machinery,
   but lineage-specific adapters accumulated beside the current one.
7. Experimental SD, UFS formatting, HUD, product services, and recovery were
   compile-hidden in places rather than separated into non-shipped modules.
8. The 900-line goal file mixed current frontier and historical ledger. It is
   now reduced to a current-state document; history remains in canonical logs.

Most growth was rational response to observed hazards. The error was not
having safety checks; it was allowing safety, diagnostics, experiments, and
product features to share one critical path and one compilation unit.

## Reduction classification

### A. Irreducible safety core

Retain:

- exact target/profile and compiled artifact binding;
- fresh dynamic UFS identity, unmounted/size checks, and clean ext4 proof;
- marker and exact content-manifest verification;
- versioned durable enable/latch and one-shot/no-replay journal;
- exact boot-only candidate, rollback, and physical recovery;
- `ro,noload,nosuid,nodev` root mount;
- bounded writable tmpfs set and boot-private authentication;
- fresh minimal Debian `/dev`, mandatory devpts, and no native-devtmpfs move;
- strict pre-exec failure attribution, cleanup, mount restoration, and
  post-return native health;
- same-run Debian PID 1, authenticated SSH, Wi-Fi, and device-tree evidence.

### B. Keep through the first headless proof

- strict native display-owner release, because native boot UI can still own
  DRM even when no persistent HUD starts;
- detailed stage telemetry, benchmark, and failure attribution;
- current observer authorization overlay;
- host ACM/NCM observation and W0-selected bounded Wi-Fi diagnostics, with no
  native Wi-Fi companion surviving into `switch_root`;
- compact cache receipt and authenticated same-run observer replacing the SD
  evidence bind before candidate creation;
- current immutable UFS content, even where optional services remain inert;
- bounded Wi-Fi watch/trace settings until repeatable final Wi-Fi is proved.

### C. Remove from the next critical path

- persistent native HUD presenter/service/private root;
- card0 and shared-run HUD binds;
- delayed HUD DRM acquisition and HUD success predicates;
- H25 `chroot` and boot-selftest designs;
- firstboot overlay;
- boot chime autoplay;
- hard SD evidence bind and compiled SD Wi-Fi property path;
- any display-success requirement in the headless terminal.

### D. Retire or replace after stable headless proof

- SD image/work-copy/loop/hash paths;
- UFS formatter/populator and manual experiment commands in resident init;
- manual HUD/display surfaces;
- proof-only display markers and verbose benchmark telemetry;
- global `sync()` and fixed waits once exact durability dependencies replace
  them;
- broad `/proc` display-owner scans once explicit service ownership is proved;
- experiment enable/latch names once a reviewed production boot policy and
  rescue selector exist;
- smoke HTTP, tunnel/cloudflared, HUD intent/presenter, and ineffective resolver
  writes in a separately rebuilt minimal Debian firstboot;
- debugfs/firmware trace and long Wi-Fi supervisor instrumentation after
  repeatable hardware bring-up proof;
- obsolete lineage adapters from the active distribution, while retaining
  their historical evidence in archive/Git.

Host approval, journaling, rollback, recovery, and final-health tooling remains.
It can be reorganized without weakening it.

## Staged production plan

### Stage 0: documentation boundary — this commit

- retire H25 and record its host-only hazards;
- record the exact H24 path and failure boundary;
- make headless service health distinct from display health;
- identify SD evidence and Wi-Fi couplings;
- change no target, rootfs, artifact, or live state.

### Stage 1: Wi-Fi ownership decision

- qualify one attended no-payload test against the exact healthy resident;
- start from a known Wi-Fi state, durably record one stop intent, stop and reap
  the exact native helper group once, and observe bounded redacted `wlan0`
  state;
- never arm handoff, mount UFS, reboot, flash, or call the result a server PASS;
- select Debian-owned Wi-Fi only on `TRANSFER_FEASIBLE`;
- on `TRANSFER_REFUTED` or `NO_PROOF`, stop for a separately reviewed nested
  PID-namespace design.

No successor identity is allocated in this stage.

### Stage 2: fresh headless successor

- allocate a fresh post-H25 version/build, profile, random seed, enable path,
  latch path, A/B receipt, qualification, and execution closure;
- compile-disable persistent HUD, private-card-root, delayed HUD DRM,
  firstboot overlay, and boot chime;
- define a distinct headless persistent-result model with display explicitly
  not required and terminal native health deferred until attended return;
- replace the SD evidence bind with a compact durable cache receipt and use a
  boot-private non-SD Wi-Fi input selected by Stage 1; do not create a new
  candidate that still requires SD;
- require independent capability review, fresh connected D0, exact attended F1
  approval, resident health, separate attended D1 approval, and no replay.

While Debian stays live, report exact server observations and
`HEALTH_PENDING_PERSISTENT_DEBIAN`. Only an attended return/recovery and exact
native checks can close `RESIDENT_HEALTHY`.

### Stage 3: prove and exercise SD independence

- verify the installed artifact and runtime binding contain neither the SD
  evidence path nor the compiled SD Wi-Fi property root;
- after the SD-free resident is installed and healthy, remove the card while
  attended, perform an explicit no-SD D0 inventory, and only then approve the
  headless D1 handoff;
- move the card to S20+ only after A90's no-SD resident and recovery path are
  exact.

This stage is not a license to transfer A90 evidence, profiles, or approvals to
S20+.

### Stage 4: split production source

Separate modules/interfaces for:

- read-only UFS qualification and mount;
- switch-root transaction and restoration;
- minimal Debian `/dev` construction;
- optional Wi-Fi bridge;
- experimental SD/formatter/populator commands;
- optional HUD/display support;
- host approval/journal/observer logic.

Build production init without the experimental modules. Then evaluate
`-ffunction-sections -fdata-sections` and `--gc-sections` for init, with exact
artifact and behavior comparison. This is a fresh build change and requires
the usual closure review.

### Stage 5: minimal Debian content

Create a separately versioned UFS image/content manifest containing only the
chosen control channel, Dropbear/authentication, Wi-Fi configuration, logging,
and required recovery support. Remove HUD, smoke HTTP, tunnel, and obsolete
test services. Do not mutate the installed read-only appliance opportunistically.

### Stage 6: optional display

After repeated headless success, design display as an independent capability,
preferably Debian-owned. It must have its own target/device exposure claim,
failure isolation, qualification, and terminal; display failure must not prevent
an otherwise healthy headless server from booting.

### Stage 7: compiler optimization

Only after the functional split and comparable benchmark are stable:

1. record baseline size, boot-to-handoff, CPU, temperature, and clock evidence;
2. add section garbage collection and compare;
3. consider Full-LTO as a separate fresh artifact capability;
4. compare the same workload and rollback on any regression.

Compiler optimization is last because it cannot repair an oversized execution
model or an incorrect ownership boundary.

## Acceptance and retirement criteria

The reduction plan is complete only when:

- a fresh headless candidate reaches same-run Debian PID 1, authenticated SSH,
  final Wi-Fi, and exact minimal `/dev` without HUD/display dependencies;
- persistent live state and post-return native resident health remain distinct;
- the consumed H24 effect and retired H25 identity are never replayed or reused;
- SD removal has an explicit proof that both evidence and Wi-Fi couplings are
  gone;
- optional features are absent from the production target binary/rootfs rather
  than merely unused at runtime;
- rollback, recovery, no-replay, exact target isolation, and evidence durability
  remain independently reviewed.

Any ambiguity in target, resident, UFS identity, rollback, recovery, mount
restoration, no-replay journal, or cross-target scope stops live progress and
returns the work to H0.
