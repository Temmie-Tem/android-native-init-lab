# A90 Goal

## Objective

Build the operator-owned Samsung Galaxy A90 5G into a Debian-oriented personal
server. Native init performs only the vendor-kernel and hardware bridge-up that
Debian cannot yet perform, then remains a minimal headless safety supervisor.
One isolated child becomes Debian PID 1 in fresh PID, mount, IPC, UTS, and network
namespaces, pivots to the existing read-only UFS appliance root, and receives
only a bounded IP path through native-owned Wi-Fi. The production steady state
is authenticated SSH, final Wi-Fi, and a minimal Debian `/dev`, with native
fallback and recovery still available outside Debian's namespaces.

`AGENTS.md` and `docs/operations/targets/A90_TARGET_CONTRACT.md` are binding.
This file records current state and the next bounded unit; it grants no device
authority. Historical detail lives in the A90 campaign ledger, incident and
review reports, and Git history. The pre-H2 snapshot remains archived at
`docs/archive/roadmaps/GOAL_A90_PRE_H2_2026-08-05.md`.

Target identities, artifacts, transports, evidence, recovery, and commands
never cross between the two goals. The same non-transfer rule also applies to
the separately registered S20+ goal and every future target row.

## Exact Current State

- H24 `0.11.192`, build
  `phase3-minimal-h24-ufs-auth-native-hud-private-card-root-minimal-debian-dev`,
  is the exact installed resident. Its attended F1 wrote and read back one
  deterministic boot-only candidate and closed
  `PASS_A90_H24_UFS_RESIDENT_INSTALLED` / `RESIDENT_HEALTHY`. Candidate replay
  is false, rollback transfer count is zero, and the host guard was released.
- The separately approved H24 D1 run consumed exactly one arm, reboot, and
  handoff. It verified and mounted the read-only UFS root and four writable
  tmpfs paths, then stopped at `persistent-hud rc=-22 errno=22` before evidence
  bind, Wi-Fi handoff bind, `switch_root`, or Debian PID 1.
- Same-intent cleanup proved the UFS root unmounted, userdata unchanged, zero
  userdata writes, and no recovery requirement. The device returned to exact
  native `RESIDENT_HEALTHY` with `binding=1 enable=1 latch=1`. The terminal is
  `REFUTED_H24_POST_ROOT_FAILURE_ATTRIBUTED_NATIVE_FALLBACK_HEALTHY`.
- The H24 D1 effect is consumed and is never replayed. Its live evidence proves
  only the outer HUD-stage `EINVAL`; the inner syscall remains unproved.
- V2321 remains the exact bound rollback for a future, freshly qualified
  successor. No successor candidate, approval, transfer, reboot, or D1 effect
  is authorized by this goal.
- S22+ and S20+ command counts for the H24 transaction are zero. Their profiles,
  approvals, evidence, and authority do not transfer to A90.

## Proven Product Mechanics

The following are established capabilities, not standing live authority:

- A boot-only native resident can be installed with exact rollback, durable
  intent, post-transfer source revalidation, candidate no-replay, and terminal
  resident health.
- Reviewed native source can resolve the UFS appliance partition at runtime,
  verify its identity and clean ext4 state, mount it
  `ro,noload,nosuid,nodev`, verify its content, prepare bounded writable tmpfs,
  and construct H24's historical minimal Debian `/dev` with devpts. Earlier
  live lanes reached `switch_root`; H24 stopped before that device-tree step,
  and the selected successor instead requires a smaller no-PTY four-node
  `/dev` that has not yet been implemented or live-proved.
- H10 proved the minimal automatic loop can reach `switch_root` in about one
  second after dispatch. H16 proved the direct UFS path avoids the former
  multi-gigabyte SD work-copy and reached the UFS `switch_root` boundary in
  about 11.8 seconds on its boundary-reaching mechanical run.
- H24's reviewed design proves that native devtmpfs need not be moved into
  Debian: Debian is intended to receive a bounded tmpfs `/dev`, while a native
  HUD card capability is isolated in a separate private root. The H24 D1 run
  stopped before those post-HUD steps, so their live execution remains unproved.
- Debian display, SSH, and Wi-Fi have each been observed in earlier bounded
  experiments, but H24 did not prove them in one terminal persistent-server
  run. Do not combine evidence from different ordinals into a new PASS.

The formal historical/design delta is frozen in
`docs/plans/A90_H16_H24_ISOLATED_DEBIAN_COMPARISON_BASELINE_2026-08-14.md`.
H16 is the direct-UFS mechanical reference, not a production image to rebuild:
the successor preserves its UFS identity/mount/fallback mechanics and
comparable stage anchors, incorporates later authorization and minimal-`/dev`
safety, and replaces its in-place/shared-namespace structure rather than
reviving it.

## Retired Successor Experiments

- H19-H23 were host-only successors retired before live use as their display
  ownership or device-isolation assumptions failed review.
- H25 `0.11.193` was also host-only and is `NO_GO_RETIRED`. Its `chroot` design
  left the old mount graph reachable as a namespace capability; its boot
  self-test could leave parent mounts, touch an unowned fixed path, be rerun or
  overwrite boot evidence, and did not close every reap/parser/receipt failure
  path. No H25 runner, approval, connected D0, flash, reboot, or handoff ever
  existed. Its draft source and manifest were removed and its untracked build
  output was moved to trash.
- Retired identities, paths, artifacts, reviews, and evidence are never
  reinterpreted as a fresh successor.

## Selected Bounded Unit: Retire Ownership Diagnostics and Bound Isolated Debian

The current unit remains H0 architecture and contract work only. A fresh
static audit found that
the existing persistent native Wi-Fi companion cannot simply be carried into a
headless successor: it retains the old Android root in a private mount
namespace while Debian receives the shared PID namespace and `/proc`. A private
mount namespace alone does not prevent Debian root from reaching a surviving
process through `/proc/<pid>/root`, `fd`, or `ns/mnt`.

The binding plan is
`docs/plans/A90_UFS_HANDOFF_ARCHITECTURE_AND_PRODUCTION_REDUCTION_PLAN_2026-08-12.md`.
Its ownership decision is refined by
`docs/plans/A90_HEADLESS_HANDOFF_MINIMUM_AND_WIFI_OWNERSHIP_DECISION_2026-08-13.md`
and the host incident report
`docs/reports/A90_NATIVE_WIFI_SIDECAR_PROC_ROOT_EXPOSURE_HOST_INCIDENT_2026-08-13.md`.
This unit does not build a successor and does not touch the device, UFS root,
boot partition, private evidence, or another target. No H26 identity or path is
allocated.

The attempted H24 shell-based W0 implementation is retired before review or
live use. Every H24 `cat` or `run` command reaches the generic command-boundary
orphan reaper, so a `run`-based inventory is not connected read-only D0.
Furthermore, inventory and stop were separate frames: the approved
process/group/session/mount-namespace set could change before `SIGTERM`. A host
journal cannot make that device-side gap atomic. The unqualified runner and
tests were removed; no W0 qualification, connected read, approval, durable
intent, signal, reboot, transfer, or recovery exists to resume.

The replacement atomic diagnostic is also `NO_GO_RETIRED`. Successive reviews
showed that safely reproducing H24's Binder/property/service tree would require
new process brokers, AF_UNIX mediation, and multiple Android UID/GID/capability
launch contracts. The final frozen H24 source proves those identities differ
after fork and before exec, contradicting the diagnostic filter model. No
diagnostic identity, qualification, connected read, approval, signal, reboot,
transfer, or recovery exists; the long design is historical evidence only.

The selected direction is now
`docs/plans/A90_HEADLESS_NATIVE_WIFI_ISOLATED_DEBIAN_DESIGN_2026-08-14.md`:

- native PID 1 remains a small headless supervisor and keeps the existing
  native Wi-Fi owner;
- one direct child becomes Debian PID 1 in separate PID, mount, IPC, UTS, and network
  namespaces, mounts a matching private read-only procfs with all writable and
  sensitive global entries masked, pivots to read-only UFS, removes
  the complete old root, and constructs an exact consoleless `/dev`: reviewed
  null/zero/full/urandom nodes and null stdio only, a final read-only tree, and
  no devpts, ptmx, tty, console, `ttyGS0`, native/physical character node,
  block node, or submount;
- a reviewed veth plus default-drop forwarding/NAT boundary exposes only the
  selected IP service; its SSH path is preinstalled dormant and opens only
  after `LOCAL_PERSISTENT` through durable `INGRESS_OPEN_INTENT`, one atomic
  activation, exact `INGRESS_OPEN` return/readback, and no replay; the parent
  closes the sole peer-move nsfs FD and proves zero retained child-namespace
  handle before any continuation and at cleanup; Debian cannot name native tasks, AF_UNIX/Binder/property
  endpoints, keyrings, `wlan0`, native devtmpfs, userdata, DRM, or network
  control; trusted bootstrap replaces the session with a proved-empty child
  keyring and one inherited all-ABI static filter denies keyring calls,
  namespace creation/entry, post-bootstrap mount/root APIs, and device-node
  creation while preserving only the exact service fork flags; the same filter
  allows direct sockets only for traced AF_INET TCP/UDP forms and rejects QRTR,
  netlink, packet/raw, hardware/control families, and compat `socketcall`;
- the final boundary uses two non-aliasing manifest-fixed nonzero identities:
  a service UID/GID for PID 1/login/probe/workload and a locked non-login
  SSH-key-daemon UID/GID for the private key and Dropbear engines; the service
  cannot traverse the key tree, inspect daemon proc/memory/FDs, inherit key
  material, or regain the key identity; both use exact all-ABI trace-derived
  static default-deny policies; PTYs,
  `/dev/random`/`GRND_RANDOM`, queued real-time signals, and unneeded global
  allocators such as perf/BPF/io_uring/AIO/inotify/mqueue/SysV IPC are absent;
- before release, one exact child cgroup bounds aggregate pids, memory+swap,
  CPU, and UFS I/O while reserving native Wi-Fi/recovery capacity; native
  forwarding sysctls are compatible preconditions and never changed, while
  only the nonce-created veth/child-netns fields are written; parent-owned
  veth rate/burst/queue limits and a dedicated bounded conntrack zone close
  softirq, skb, flow-state, and Wi-Fi-airtime exhaustion outside cgroup charge;
- cgroup bounds are supplemented by exact global file-table, FD, pipe/socket/
  epoll/timer, dedicated-UID, queued-signal, and charged or conservatively
  bounded kernel-memory reserves with empty-cleanup proof;
- before release the child is normalized to exact `SCHED_OTHER`, priority 0,
  nice +10, reset-on-fork, a manifest-frozen CPU subset, low best-effort I/O,
  and bounded uclamp with no later scheduler/priority mutation authority;
- native PID 1 keeps one-shot/no-replay journal, SD-free bounded logs, exact
  fallback, power/recovery control, and final native-health responsibility;
- the only child receipt pipe is bootstrap-only and closes on exec; native
  parent facts and a separate attended host SSH observer provide post-exec
  evidence; before SSH the host retrieves the same-run per-boot Ed25519 server
  public key/fingerprint from the target-bound native receipt and performs
  strict host-key checking, so neither TOFU nor an immutable-firstboot writer
  is assumed; the exact server build then accepts only one public key for one
  fixed nonzero service account and forces one read-only probe, with password,
  interactive, root/alternate-account, shell/subsystem, PTY, forwarding,
  agent, and X11 paths disabled;
- HUD, firstboot overlay, chime, W0/ownership brokers, general shell health,
  SD evidence/property roots, and benchmark safety predicates leave the formal
  path.

The exact H14/H24 firstboot audit is now closed: although the 12,092-byte
script can start Dropbear, it also configures legacy `ncm0`, smoke, HUD-intent,
and Debian Wi-Fi paths. It is not the first isolated-Debian rootfs. A separately
versioned minimal content manifest must be built and independently reviewed
before any candidate; installing that content remains a separate future
attended capability and also needs a separately reviewed higher-precedence
boundary change. It is not authorized here.

This is H0 architecture only. Kernel/toolchain support for nested namespaces,
veth/netfilter, `pivot_root`, capability drops, exact cleanup, and performance
must be independently proved before any successor identity. Missing support is
`NO_GO`; shared PID/proc/network namespaces, `chroot`, or a userspace proxy are
not fallbacks. While Debian is live the state remains
`HEALTH_PENDING_PERSISTENT_DEBIAN`; attended return/recovery is required for
`RESIDENT_HEALTHY`.

## What Stays in the Critical Path

- exact A90 target/profile and compiled binding;
- fresh dynamic UFS identity, size, unmounted, clean-ext4, marker, and content
  verification;
- versioned enable and latch with one-shot/no-replay journal semantics;
- exact boot-only candidate and rollback recovery;
- read-only `ro,noload,nosuid,nodev` root mount;
- bounded tmpfs writable paths and boot-private SSH authorization installed
  read-only in the manifest-fixed nonzero service UID's home, not `/root/.ssh`;
- one bootstrap-generated per-boot Dropbear server key whose public receipt is
  retrieved before SSH, whose exact `/etc/dropbear` tmpfs is remounted
  read-only before release, whose sole transient generator is non-dumpable,
  zero-core, output-closed, fully reaped with no residue, whose mode-0400 bytes are owned only by a distinct
  non-dumpable non-login key daemon, and whose private file/memory/FD state is
  unreachable from PID 1, the forced probe, and workload;
- one manifest-pinned public-key-only Dropbear/account contract: exactly one
  login-eligible fixed service account/key, one forced read-only probe, and no
  password/interactive/root/alternate-key/shell/subsystem/PTY/forwarding/
  agent/X11 acceptance;
- exact consoleless Debian `/dev`, verified null stdio, a read-only four-node
  null/zero/full/urandom tree, and no devpts/ptmx/tty/console/`ttyGS0`/native
  PTY/native-devtmpfs move;
- final Wi-Fi with an explicit owner and no Debian-visible old-root sidecar;
- a compact durable cache receipt plus authenticated same-run observation,
  replacing the SD evidence sidecar before the next candidate;
- strict pre-exec failure attribution, mount restoration, and final native
  health;
- final Debian PID 1, authenticated SSH, final Wi-Fi, minimal-device-tree, and
  same-run evidence.

## What Leaves or Moves Out

Remove from the next headless critical path now:

- persistent native HUD bootstrap and display-health predicates;
- H25 HUD self-test and all H25 design artifacts;
- firstboot overlay injection;
- boot chime autoplay;
- the hard SD evidence bind and compiled SD Wi-Fi property-root dependency.

Move out of the eventual production init after the headless lane is stable:

- legacy SD image/work-copy and hashing machinery;
- UFS formatter/populator commands;
- manual HUD and experimental display commands;
- benchmark and verbose qualification telemetry not needed for field recovery;
- smoke HTTP, optional tunnel, and HUD-intent logic in the installed Debian
  firstboot script;
- obsolete candidate-specific adapters and reports from the shipped image.

Keep host-side approval, durable journal, exact rollback, and recovery tooling.
Those are safety machinery, not target runtime bloat.

## Product Sequence

1. Freeze the H24 shell-W0 and atomic-diagnostic retirement; neither is resumed.
2. Freeze and independently check the H16-to-H24 comparison baseline so the
   first direct-UFS boundary reach is retained as a mechanical/timing reference
   without overclaiming it as server success or authorizing its reuse.
3. Independently review the selected native-Wi-Fi/isolated-Debian H0 boundary,
   then commit only the accepted A90 documentation and tests.
4. Prove host-side kernel/toolchain feasibility for nested PID/mount/IPC/UTS/
   network namespaces, one exact aggregate pids/memory+swap/CPU/UFS-I/O cgroup
   backend, the consoleless no-PTY four-node device tree, veth/netfilter/
   read-only-native-sysctl preconditions, a bounded read-only/masked child procfs,
   parent-owned rate/queue limits, a bounded
   dedicated conntrack zone, `pivot_root`,
   capability drops,
   child-keyring isolation plus static keyring/userns/mount/device syscall
   denial with exact fork compatibility, an AF_INET-only direct-socket corpus,
   a trace-derived all-ABI default-deny policy, distinct manifest-fixed
   service and non-login SSH-key-daemon UID/GID boundaries with proc/key-FD/
   memory isolation and one exact child identity drop, global-object reserve
   accounting, exact scheduler/CPU/
   ioprio/uclamp normalization, normalized exec state, and exact cleanup.
5. Carry forward the exact immutable-firstboot mismatch audit and build a
   separately versioned minimal UFS content manifest with one independently
   reviewed nonprivileged consoleless PID 1, non-PTY Dropbear/authentication on
   a non-privileged port, veth consumption, and the chosen workload. Do not
   assume the historical sysvinit binary or root identity is compatible; the
   chosen PID 1 must pass the exact UID/device/filter trace. Bind the exact
   Dropbear binary/config/argv and account database, one distinct non-dumpable
   key-daemon identity, one canonical boot-private client key, one login
   account, and one forced read-only probe; reject service access to key
   file/memory/FDs and every
   password/interactive/root/alternate-account/key/command/subsystem/PTY/
   forwarding/agent/X11 path. Trusted bootstrap alone launches the key daemon;
   it must clean-exec and pass exact maps/map_files/FD proof before key load or
   listener bind, and the transient generator likewise clean-execs before key
   material exists.
   PID 1, firstboot, the probe, and workload never generate, rotate, read, or
   inherit the server key. Review
   both the content and the required higher-precedence boundary plus future
   installation process before any candidate identity; no UFS write is
   authorized by this goal.
6. Replace the hard SD evidence bind and compiled Wi-Fi property-root path
   with the reviewed cache/boot-private inputs before any headless identity.
7. Implement the minimal native supervisor, exact `CHILD_READY`/empty-control-
   pipe barrier only after one manifest-bound static clean-bootstrap exec and
   parent verification of exact `exe/maps/map_files/fd/fdinfo` with no inherited
   native mapping, plus parent pidfd stop, parent-only netns-FD peer move without
   `setns` followed immediately by exact close/no-duplicate/zero-parent-nsfs-FD
   proof before any continuation, durable `NETWORK_PREP_INTENT`, one-byte `N` plus the first pidfd
   continuation, verified child-side `NETWORK_PREPARED` reread/zero-payload/
   `CAP_NET_ADMIN`-drop frame and second parent stop, durable
   `ROOT_PREP_INTENT`, one-byte `R` plus the second continuation, verified
   `ROOT_PREPARED` frame and third parent stop, durable
   `CHILD_RELEASE_INTENT`, one-byte `X`/`RELEASE` plus the third/final pidfd
   continuation and exact `CHILD_RELEASED` dispatch result without retry, two
   bootstrap control/receipt pipes created close-on-exec, temporarily cleared
   only for that one clean exec and re-armed before `CHILD_READY`, with parent-
   side exact FD/mapping-set enumeration at every stop; keep clean bootstrap as
   the sole native-receipt writer and give the clean-exec generator and key
   daemon only separate, non-overlapping transient internal status pipes with
   exact `GENERATOR_CLEAN_READY`/`GENERATOR_PUBLIC_COMPLETE` and
   `KEY_DAEMON_CLEAN_READY`/`KEY_DAEMON_LISTEN_READY` frame order, FD sets, EOF,
   helper identity, and no-residue proof,
   one preinstalled dormant SSH-ingress set/handle followed only after
   `LOCAL_PERSISTENT` by durable `INGRESS_OPEN_INTENT`, one atomic activation,
   exact `INGRESS_OPEN` return/readback, no resend, and close-only cleanup,
   dedicated read-only native evidence retrieval including the
   same-run public server-key receipt, and attended strict-host-key SSH observer
   without live authority;
   independently qualify their exact execution-critical closure.
8. Only then allocate one fresh headless successor identity and deterministic
   boot-only candidate/rollback artifacts; never patch/reuse H25 or the retired
   diagnostic.
9. Build and host-validate it, including negative namespace/device/network
   tests and before/after size, boot, forwarding, and handoff measurements.
10. Prepare from the exact durable H24 terminal and passive target/recovery
   evidence. Any unavoidable H24 command is reviewed post-approval F1 control,
   never relabelled D0.
11. Require fresh connected D0 and exact attended F1 approval before one
   boot-only resident install. After the SD-free resident is healthy, remove
   the card while attended and prove exact no-SD D0 before handoff approval.
12. Require exact resident health, then a separate attended D1 approval before
   one arm/reboot/isolated-Debian launch.
13. While Debian remains the persistent live runtime, publish only its exact
   service evidence and `HEALTH_PENDING_PERSISTENT_DEBIAN`; do not call the
   native resident healthy. After an attended return or recovery, require exact
   native `RESIDENT_HEALTHY`. Missing display is expected in the headless lane,
   not a failure.
14. After repeatable headless success, split remaining experimental native and
   host source modules. The minimal rootfs was already completed before the
   candidate and is not rebuilt or mutated as part of this source-only step.
15. Add display later as a separate optional capability, preferably owned by
   Debian. Any persistent native HUD needs a fresh hazard design and review.
16. Consider section garbage collection and then Full-LTO only after functional
   boundaries and comparable benchmarks are stable.

## Evidence

Canonical public records include:

- `docs/operations/CAMPAIGN_LEDGER_A90.md`
- `docs/reports/A90_H24_MINIMAL_DEBIAN_DEV_INDEPENDENT_REVIEW_2026-08-12.json`
- `docs/reports/A90_H24_UFS_F1_D1_EXECUTION_INDEPENDENT_REVIEW_2026-08-12.json`
- `docs/reports/A90_H24_PERSISTENT_HUD_BOOTSTRAP_EINVAL_INCIDENT_2026-08-12.md`
- `docs/reports/A90_H25_HUD_CHROOT_AND_SELFTEST_REPLAY_HOST_INCIDENT_2026-08-12.md`
- `docs/reports/A90_NATIVE_WIFI_SIDECAR_PROC_ROOT_EXPOSURE_HOST_INCIDENT_2026-08-13.md`
- `docs/reports/A90_H14_IMMUTABLE_FIRSTBOOT_ISOLATED_DEBIAN_MISMATCH_H0_2026-08-14.md`
- `docs/plans/A90_H16_H24_ISOLATED_DEBIAN_COMPARISON_BASELINE_2026-08-14.md`
- `docs/plans/A90_UFS_HANDOFF_ARCHITECTURE_AND_PRODUCTION_REDUCTION_PLAN_2026-08-12.md`
- `docs/plans/A90_HEADLESS_HANDOFF_MINIMUM_AND_WIFI_OWNERSHIP_DECISION_2026-08-13.md`
- `docs/plans/A90_ATOMIC_WIFI_OWNERSHIP_DIAGNOSTIC_RESIDENT_DESIGN_2026-08-14.md`
- `docs/plans/A90_HEADLESS_NATIVE_WIFI_ISOLATED_DEBIAN_DESIGN_2026-08-14.md`

Private manifests, journals, raw logs, artifacts, device identifiers, network
identifiers, and credentials remain under `workspace/private/` and are never
committed.

## Success Conditions

- Current documentation names H24, its consumed D1 refutation, and the exact
  no-replay/native-health boundary without overclaiming the failing syscall.
- H25 is unambiguously retired before qualification or live use.
- The Wi-Fi owner is decided before a successor identity is allocated, and a
  private mount namespace alone never proves old-root isolation.
- The critical-path inventory distinguishes device safety from experiment
  convenience and from later product cleanup.
- H16 is used as a mechanical and comparable-timing baseline without
  reclassifying its missing SSH/PID1/Wi-Fi/display evidence as success.
- Any future headless successor keeps the permanent boot-only, rollback,
  recovery, isolation, evidence, and target-selection boundaries.
- GOAL remains a current-state document rather than another historical ledger.

## Stop Conditions

Stop and remain H0 if exact target, resident, UFS identity, rollback, recovery,
source/artifact binding, or terminal health is ambiguous; if any previous effect
is not durably terminal; if a candidate would reuse a retired identity; if a
forbidden partition or native devtmpfs exposure appears; if evidence would need
to combine different runs; or if another target's profile, command, approval,
or evidence enters the A90 scope.
