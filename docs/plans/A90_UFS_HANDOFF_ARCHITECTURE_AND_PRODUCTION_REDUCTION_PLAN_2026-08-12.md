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

2026-08-13 refinement deferred the next candidate until Wi-Fi ownership was
selected. The persistent native Wi-Fi companion keeps an old-root mount
namespace while the old in-place handoff moves shared procfs, so private
`CLONE_NEWNS` alone cannot support a minimal-exposure claim. The binding
follow-up is
`A90_HEADLESS_HANDOFF_MINIMUM_AND_WIFI_OWNERSHIP_DECISION_2026-08-13.md`.

2026-08-14 correction retires both attempted ownership diagnostics. H24 shell
inventory triggers PID 1's generic command-boundary reaper and separate
inventory/stop frames cannot close the device-side capability race. The later
atomic design would require a new Binder/AF_UNIX/process-broker runtime and
cannot reproduce H24's distinct post-fork Android UID/GID/capability roles
under its filter contract. It is preserved only as rejected design evidence.

The selected H0 direction is
`A90_HEADLESS_NATIVE_WIFI_ISOLATED_DEBIAN_DESIGN_2026-08-14.md`: native PID 1
keeps the exact native Wi-Fi owner and remains a small safety supervisor; one
child becomes Debian PID 1 in fresh PID, mount, IPC, UTS, and network namespaces, pivots
to read-only UFS, and receives only a reviewed veth/IP boundary. No ownership
stop, diagnostic resident, or shared-namespace fallback is part of the product.

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
14. in the historical H24 path, move `/proc` and `/sys`, create a fresh minimal
    tmpfs `/dev`, create exact core character nodes, and mount devpts without
    moving native devtmpfs or creating a userdata block node;
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
| `/root/.ssh` | Historical H24 boot-private tmpfs populated from reviewed observer input | Replace with read-only service-home authorization owned by the successor's fixed nonzero UID |
| Debian `/dev` | Historical H24 used core nodes plus devpts; successor freezes exactly null/zero/full/urandom and no PTY | Core safety boundary, reduced before successor |
| Native devtmpfs | Remains outside Debian | Core safety boundary |
| Native HUD card0 root | H24-only child namespace/private root | Remove from headless critical path |
| Wi-Fi handoff | Read-only, redacted input consumed by Debian | Core for cable-free server use |
| SD evidence bind | Proof sidecar under `/mnt/sdext` | Temporary hard dependency; replace before SD removal |
| UFS firstboot | Immutable demonstration script configures legacy NCM, smoke, HUD-intent, and Debian Wi-Fi and has no inherited-FD writer | Replace with separately versioned minimal content before the first candidate; installation also needs a reviewed higher-precedence boundary change |

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
that property root, so SD removal is unproved. The retired H24 shell W0 and
atomic diagnostic grant no exception. Before any fresh isolated-Debian
successor candidate is created, both production dependencies must be replaced
by a reviewed compact cache receipt/authenticated same-run observer and a
boot-private non-SD native-Wi-Fi input. HUD removal alone is not the SD-removal
gate.

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

The historical script is also not evidence for a new post-exec health/log
descriptor protocol. The exact audit in
`A90_H14_IMMUTABLE_FIRSTBOOT_ISOLATED_DEBIAN_MISMATCH_H0_2026-08-14.md`
shows that it configures legacy `ncm0`, smoke, HUD-intent, and Debian Wi-Fi
paths. The first isolated-Debian proof therefore uses separately versioned
minimal content, keeps exactly two bounded scalar bootstrap pipes created
close-on-exec -- one parent-to-child control pipe for fixed `N`/`R`/`X` tokens
and one child-to-parent receipt pipe for fixed stage frames -- with only the
two child ends temporarily cleared for one clean-bootstrap exec and re-armed
before `CHILD_READY`, and relies on
native parent observations plus an attended host SSH proof. The minimal content
Stage 2 precedes the candidate Stage 3; no overlay, undeclared FD writer, or
one-pipe shortcut is inserted.

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
bytes, about 20.1%. The exact firstboot audit proves that some are invoked, so
they are removed in the separately versioned minimal content completed before
the first headless candidate.

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
- bounded writable tmpfs set and boot-private authentication installed
  read-only in the manifest-fixed nonzero service UID's home, not `/root/.ssh`;
- exact public-key-only Dropbear client authentication: one login-eligible
  fixed service account, one canonical boot-private key, one forced read-only
  probe, and no password/interactive/root/alternate-account/key/general-shell/
  subsystem/PTY/forwarding/agent/X11 path;
- one preinstalled dormant SSH-ingress handle plus durable
  `INGRESS_OPEN_INTENT`, one atomic activation, exact `INGRESS_OPEN` return/
  readback, no replay, and close-only exact cleanup before child termination;
- one distinct locked non-login SSH-key-daemon UID/GID owning the mode-0700/
  mode-0400 private-key tree and Dropbear engines; the service UID cannot read
  the file, inspect daemon proc/memory/FDs, inherit key material, or regain the
  daemon identity, and cleanup empties both dedicated-UID resource sets;
- exact consoleless Debian `/dev` with only null/zero/full/urandom, verified
  null stdio, a read-only root-device tmpfs, no devpts/ptmx/tty/console/
  `ttyGS0`/native PTY, and no native-devtmpfs move;
- strict pre-exec failure attribution, cleanup, mount restoration, and
  post-return native health;
- same-run Debian PID 1, authenticated SSH, Wi-Fi, and device-tree evidence.

### B. Keep through the first headless proof

- strict native display-owner release, because native boot UI can still own
  DRM even when no persistent HUD starts;
- detailed stage telemetry, benchmark, and failure attribution;
- current observer authorization overlay;
- host ACM/NCM observation plus bounded native-Wi-Fi and veth/netfilter health
  evidence, with native tasks absent from Debian's PID/proc/network view;
- compact cache receipt and authenticated same-run observer replacing the SD
  evidence bind before candidate creation;
- separately versioned minimal UFS content completed and reviewed before the
  candidate;
- bounded Wi-Fi watch/trace settings until repeatable final Wi-Fi is proved.

### C. Remove from the next critical path

- persistent native HUD presenter/service/private root;
- card0 and shared-run HUD binds;
- delayed HUD DRM acquisition and HUD success predicates;
- H25 `chroot` and boot-selftest designs;
- firstboot overlay;
- boot chime autoplay;
- hard SD evidence bind and compiled SD Wi-Fi property path;
- any display-success requirement in the headless terminal;
- historical smoke HTTP, tunnel, HUD-intent/presenter, and Debian-Wi-Fi
  services from the demonstration rootfs.

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
- debugfs/firmware trace and long Wi-Fi supervisor instrumentation after
  repeatable hardware bring-up proof;
- obsolete lineage adapters from the active distribution, while retaining
  their historical evidence in archive/Git.

Host approval, journaling, rollback, recovery, and final-health tooling remains.
It can be reorganized without weakening it.

## Staged production plan

### Stage 0: documentation boundary — complete

- retire H25 and record its host-only hazards;
- record the exact H24 path and failure boundary;
- freeze H16 as the first live direct-UFS mechanical-boundary baseline and compare its
  proved `switch_root_exec` boundary, missing server evidence, and inherited
  mechanisms against H24 and the selected isolated-Debian design in
  `A90_H16_H24_ISOLATED_DEBIAN_COMPARISON_BASELINE_2026-08-14.md`;
- make headless service health distinct from display health;
- identify SD evidence and Wi-Fi couplings;
- change no target, rootfs, artifact, or live state.

### Stage 1: isolated-Debian feasibility

- freeze the H24 shell-W0 and atomic-diagnostic `NO_GO_RETIRED` disposition;
- independently review
  `A90_HEADLESS_NATIVE_WIFI_ISOLATED_DEBIAN_DESIGN_2026-08-14.md`;
- use the frozen H16/H24 comparison to retain the proven UFS, rollback,
  fallback, and timing anchors while rejecting a simple H16 rebuild or a
  continuation of H24's HUD/display gate;
- prove host-side kernel/toolchain support for PID/mount/IPC/UTS/network
  namespaces, matching procfs, one exact cgroup backend with aggregate pids/
  memory+swap/CPU/UFS-I/O bounds, veth, exact rtnetlink/netfilter/sysctl
  operations, `pivot_root`, capability drops, pidfd/wait, empty child session
  keyring, one all-ABI inherited static deny for keyring, namespace creation,
  mount/root APIs, and device-node creation with exact fork compatibility,
  plus an AF_INET-TCP/UDP-only direct-socket allowlist that rejects QRTR,
  netlink, packet/raw, hardware/control families and compat `socketcall`, a
  normalized exec envelope, and
  complete cleanup/restoration;
- prove the exact three-barrier bootstrap protocol: `CHILD_READY` then an empty
  control-pipe block plus parent pidfd stop, but only after one inherited-mm
  close/exec branch enters a manifest-bound static clean bootstrap and the
  parent proves exact `/proc/<pid>/{exe,maps,map_files,fd,fdinfo}` with no
  inherited native anonymous/shared/file/device mapping; resource/scheduler plus native-end
  network setup while stopped, with the peer moved only by one bound close-on-
  exec netns FD and no native `setns`; bind its number/flags/nsfs inode, prove
  no duplicate, close it immediately after the exact move acknowledgement, and
  enumerate zero parent child-namespace FDs before configuration/continuation;
  durable `NETWORK_PREP_INTENT`, one-byte `N` and first
  continuation; unique child-side `NETWORK_PREPARED` reread/zero-payload/
  `CAP_NET_ADMIN`-drop frame plus empty-pipe block and second parent stop;
  durable `ROOT_PREP_INTENT`, one-byte `R` and second continuation; unique
  `ROOT_PREPARED` frame plus empty-pipe block and third parent stop; durable
  `CHILD_RELEASE_INTENT`, and only then one-byte `X`/`RELEASE` and the third/
  final pidfd continuation for pivot/exec plus exact `CHILD_RELEASED` dispatch
  result; every stopped barrier independently enumerates the exact two-pipe
  child FD set, revalidates clean mapping provenance, and rejects a retained
  netlink socket; no token or signal replay;
- prove native Wi-Fi remains in its native namespaces while Debian receives
  only the isolated veth/IP boundary, never native procfs, AF_UNIX/Binder/
  property endpoints, native-local TCP/UDP listeners, `wlan0`, old root,
  devtmpfs, or block devices; bind native-veth INPUT/OUTPUT as well as
  forwarding/NAT and prove exact cleanup;
- prove the child procfs has fixed private options, exact child PID/net/IPC/
  mount views plus only a finite read-only scalar allowlist, immutable masks
  over every writable/sensitive global entry, and a final read-only remount;
- freeze parent-owned veth MTU/queue plus bidirectional packet/byte rate,
  burst, and depth limits and one dedicated conntrack zone with bounded
  new-flow rate/concurrent state; prove UDP/SYN/return floods cannot consume
  the native Wi-Fi/control reserve and cleanup changes no global/Wi-Fi state;
- prove the consoleless four-node allowlist, `/dev/null` fd 0/1/2, `tty_nr=0`,
  final read-only `/dev`, and absence of devpts, ptmx, tty, `/dev/random`,
  `ttyGS0`, `/dev/console`, every native/physical character node, every block
  node, and every submount;
- prove distinct manifest-fixed nonzero service and non-login SSH-key-daemon
  UID/GID boundaries, non-PTY Dropbear, a complete
  trace-derived all-ABI default-deny syscall policy, and global file-table,
  pipe/socket/epoll/timer/per-UID/kernel-memory reserves in addition to cgroups;
- prove exact child `SCHED_OTHER`/priority-0/nice-+10/reset-on-fork state,
  manifest-frozen CPU placement, `IOPRIO_CLASS_BE` 7, bounded uclamp, zero RT
  rlimits/capabilities, and denial of every later scheduler mutation;
- freeze and independently review the separately versioned minimal-content
  contract: only the manifest-pinned public-key-only Dropbear and selected
  workload, boot-private authorization in the fixed nonzero service UID's
  read-only manifest home on the isolated veth, exactly one login account/key
  and forced probe, zero alternate auth/session/forwarding features, and a
  distinct filtered non-dumpable key daemon that alone owns/loads the
  already-present trusted-bootstrap per-boot server key after one bounded
  clean-exec non-dumpable zero-core generator exception has exited, been reaped, and left
  no core/log/temp/private-output residue. PID 1/firstboot/probe/
  workload never create, rotate, read, or inherit that key or a post-exec
  private FD;
- replace SD evidence and property-root dependencies with cache-backed bounded
  evidence and boot-private native-Wi-Fi inputs before candidate allocation;
- implement and independently qualify only after the H0 feasibility boundary
  passes; no diagnostic identity, ownership signal, or shared-namespace
  fallback exists.

### Stage 2: minimal Debian content prerequisite

Create a separately versioned UFS image/content manifest containing only one
independently reviewed nonprivileged consoleless PID 1, non-PTY
Dropbear/authentication on a non-privileged port, isolated-veth consumption,
the chosen workload, bounded logging, and required recovery support. Do not
assume the historical sysvinit binary or its root identity is compatible; the
chosen PID 1 must have an exact trace under the fixed UID/device/filter
envelope. Remove HUD, smoke
HTTP, tunnel, Debian Wi-Fi, and obsolete test services. Do not mutate the
installed read-only appliance opportunistically.

The manifest binds the exact Dropbear binary hash, source/configuration
provenance, feature matrix, argv, account database, fixed service and distinct
non-login key-daemon identities/homes, forced read-only probe dispatcher, and
canonical one-line `authorized_keys` grammar.
Only one nonzero service account is login-eligible and only one run-bound
boot-private public key is accepted. Password, empty-password, `none`,
keyboard-interactive/PAM, root or alternate accounts, alternate key sources,
general shell, arbitrary command/subsystem, PTY, local/remote forwarding,
agent forwarding, and X11 forwarding are disabled and negatively tested.
Missing exact two-identity non-root Dropbear support makes Stage 2 `NO_GO`; it
never selects a permissive runtime fallback.

Trusted bootstrap alone launches the static Dropbear listener under the
distinct key-daemon UID/GID. From the proved-clean bootstrap mm, one child
first exact-execs the manifest-bound static daemon before reading the key or
binding the listener. It becomes non-dumpable, installs the exact filter,
emits `KEY_DAEMON_CLEAN_READY` on its sole transient internal status pipe before
key load/listener bind, and may load/bind only while ingress remains blocked.
It emits `KEY_DAEMON_LISTEN_READY` and closes that pipe before any accept. The
clean bootstrap validates both frames and EOF and alone forwards a canonical
summary; Native PID 1 proves exact `maps`/`map_files`, IDs, capabilities and FDs
before `LOCAL_PERSISTENT`; that verification never opens ingress or permits an
accepted connection. The service
UID cannot traverse the private tree or
use proc/ptrace/process-vm/pidfd-getfd to inspect it. Before the forced
dispatcher exec, every child key copy is zeroed, key/config/listener FDs are
absent or close-on-exec, an explicit zero-`capset` and ambient clear are
performed after the nonzero-to-nonzero service-ID transition, all capability
sets/saved IDs are reread empty/exact, and
the new address space receives only bounded non-PTY channels. Missing exact
source/zeroization/FD/proc/capability proof is `NO_GO`.

The minimal content never touches the exact per-boot Ed25519 server key created
in private tmpfs by trusted bootstrap. It never generates, replaces, rotates,
reads, or inherits that key. The one manifest-pinned transient generator is
non-dumpable with `RLIMIT_CORE=0`, closed stdio/FD/output sinks, and exact
exit/reap; any crash, private output, core/log/temp artifact, or residual PID/
FD is `NO_GO`. Trusted bootstrap binds the file, remounts the
exact `/etc/dropbear` tmpfs read-only, and launches the filtered key daemon
before the service PID-1 exec. Only the algorithm, public key, and SHA-256
fingerprint are exported in the target/resident/boot/run-bound native receipt;
during generation private bytes are limited to the file and sole generator
address space; after proven generator reap they remain inside the mode-0400
file or key-daemon signing memory and disappear when exact child cleanup reaps
the daemon and destroys the tmpfs.

The two bootstrap control/receipt pipes remain the only native-facing pipes,
and the clean bootstrap is the sole native-receipt writer. Generator and
key-daemon helper forks may only close both main-pipe ends before clean exec and
never carry or write them across that exec. One helper at a time receives one
transient internal `pipe2(O_CLOEXEC)` status writer plus its exact manifest-
bound object FDs for one static exec, then re-arms and rereads that FD set. The
generator emits exactly `GENERATOR_CLEAN_READY` then public-only
`GENERATOR_PUBLIC_COMPLETE`, closes before exact exit/reap, and reaches EOF.
The daemon emits exactly `KEY_DAEMON_CLEAN_READY` then
`KEY_DAEMON_LISTEN_READY`, closes before any accept, and reaches EOF while it
remains live. Bootstrap binds helper pid/start/pidfd, frame order, byte cap, FD
set and EOF and forwards only the canonical scalar summary. Wrong writer,
inherited main-pipe end, extra FD, interleaved/partial/duplicate/extra frame,
premature or late EOF, helper crash, or residue is `RECOVERY_PARKED`.

The immutable H14/H24 service-start path is audited incompatible with the
selected minimum. This stage therefore completes before any headless candidate
identity. Building content is host-only; installing it on UFS requires a
separately reviewed higher-precedence boundary change, a future exact
target-contract capability, an exact rollback/recovery model, and attended
approval. Until then installation is `NO_GO`; a raw partition image is never
permitted.

### Stage 3: fresh headless successor

- allocate a fresh post-H25 version/build, profile, random seed, enable path,
  latch path, A/B receipt, qualification, and execution closure;
- compile-disable persistent HUD, private-card-root, delayed HUD DRM,
  firstboot overlay, and boot chime;
- compile in only the minimal native supervisor, isolated Debian bootstrap,
  manifest-frozen cgroup resource boundary verified without runtime selection,
  consoleless no-PTY minimal-dev boundary, positive default-deny syscall and
  global-kernel-object resource boundary, exact scheduler/CPU/ioprio/uclamp
  normalization, UTS/veth/netfilter/traffic-rate/
  queue/conntrack/read-only-native-sysctl policy, exactly two bounded
  scalar bootstrap pipes created close-on-exec; only their child ends may be
  temporarily cleared for one exact clean-bootstrap exec and are re-armed
  before `CHILD_READY` (parent-to-child `N`/`R`/`X` control and child-to-parent
  fixed-frame receipt); helper clean execs use only the one-at-a-time transient
  internal status channels above and bootstrap alone forwards their summaries;
  preinstall and bind one dormant SSH-ingress set/handle, then after
  `LOCAL_PERSISTENT` require durable `INGRESS_OPEN_INTENT`, one atomic
  element activation and exact `INGRESS_OPEN` return/readback with no resend;
  close and prove absent every scoped parent child-namespace FD before any
  continuation, published observation, or cleanup namespace-disappearance claim;
  dedicated read-only native evidence
  retrieval, and exact cleanup/restoration;
- require the attended host observer to connect only after exact current
  `INGRESS_OPEN`, retrieve the same-run host-key receipt before SSH, build a
  no-clobber private `known_hosts`, and use strict host-key
  checking; then require the exact public-key method, accepted client-key
  fingerprint, fixed service account, and forced read-only probe with zero
  alternate authentication/session/forwarding feature; TOFU, a stale receipt,
  or any permissive client-auth path is `NO_PROOF`/security failure;
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

### Stage 4: prove and exercise SD independence

- verify the installed artifact and runtime binding contain neither the SD
  evidence path nor the compiled SD Wi-Fi property root;
- after the SD-free resident is installed and healthy, remove the card while
  attended, perform an explicit no-SD D0 inventory, and only then approve the
  headless D1 handoff;
- move the card to S20+ only after A90's no-SD resident and recovery path are
  exact.

This stage is not a license to transfer A90 evidence, profiles, or approvals to
S20+.

### Stage 5: split production source

Separate modules/interfaces for:

- read-only UFS qualification and mount;
- isolated child pivot-root transaction and parent fallback;
- minimal Debian `/dev` construction;
- native-Wi-Fi veth/netfilter boundary;
- experimental SD/formatter/populator commands;
- optional HUD/display support;
- host approval/journal/observer logic.

Build production init without the experimental modules. Then evaluate
`-ffunction-sections -fdata-sections` and `--gc-sections` for init, with exact
artifact and behavior comparison. This is a fresh build change and requires
the usual closure review.

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

- a fresh headless candidate reaches same-run Debian PID 1, exact one-shot
  `INGRESS_OPEN`, authenticated SSH, final Wi-Fi, and exact minimal `/dev`
  without HUD/display dependencies;
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
