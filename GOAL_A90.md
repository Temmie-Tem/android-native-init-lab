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
- H28 was written once but never received a boot opportunity: an uncertain
  TWRP System return caused the F1 owner to restore exact V2321 before the
  attended physical System return. H28 boot acceptance is therefore unproved,
  not failed. Candidate and rollback replay are forbidden.
- The first physical-return observer proved exact V2321 `version` and then
  failed by serial input truncation. Its separately reviewed slow-input
  reconciliation was consumed once on 2026-08-21. That session proved exact
  V2321, `selftest fail=0`, native status health, and pstore entries zero, but
  the final boot-ID producer returned `EBUSY` because the automatic menu was
  active. That consumed checkpoint was `NO_PROOF_OBSERVER / RECOVERY_PARKED`;
  see
  `docs/reports/A90_H28_SLOW_HEALTH_BOOT_ID_BUSY_NO_PROOF_2026-08-21.md`.
- A fresh independently reviewed menu-hide reconciliation then durably armed
  one exact session, sent `hide` once, waited the fixed settle, and proved two
  equal boot-ID receipts around exact V2321 `version`, `selftest fail=0`,
  healthy `status`, and zero pstore entries. It published
  `41-recovery-closed.json` at SHA-256
  `4ae580129004e3237889e886b4640dccc9efb8f194b74845357f70971c4795d7`,
  removed the active-run guard after exact readback, and retained the consumed
  H28 candidate guard. Candidate/rollback replay remains false and H28 boot
  acceptance remains unproved. See
  `docs/reports/A90_H28_MENU_HIDE_HEALTH_RECONCILIATION_PASS_2026-08-21.md`.
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

### WLAN backend minimization pre-candidate gate

The isolated-Debian topology remains the reference boundary, but it does not
make the accumulated H24 vendor backend minimal. The H0 portfolio at
`docs/security/hardening/a90-wlan-vendor-property-ablation-2026-08-15/`
therefore freezes a topology-neutral minimization gate before any successor
identity:

- `WP-H0-1` source-parses the exact H24-selected graph as thirteen composite
  instances / eleven unique roles plus property shim, modem holder, and helper.
  It proves no individual role necessary or unnecessary; `H0D01-H0D10` remain
  `UNPROVED`.
- `WP-H0-2` now fixes the H0-only corrected-baseline and one-factor state
  machine in
  `design/a90-h24-wlan-one-factor-ablation-design-v1.json`. H24 is not the
  baseline: its helper route was not reached live, it contains duplicate
  service-manager pairs and global SELinux mutation, and it consumes the
  forbidden SD property snapshot.
- Two mutually exclusive corrected service-manager placements remain
  unproved. Only the first separately qualified variant with `PROVED` baseline
  proof and final `RESIDENT_HEALTHY` may become `G0`; `BASELINE_HEALTHY` alone
  never admits it. Every later unit removes exactly one role from an exact
  healthy generation; failed, refuted, ambiguous, or recovery-parked units
  never chain or become a baseline.
- Before any future execution, H0D10 requires a public deterministic SD-free
  bootstrap superset. It may not copy or bless the private whole snapshot.
  After ablation, the retained set must close as `PROPERTY_ABSENT_PROVED` or
  `PROPERTY_FINITE_SEED_PROVED`.
- The distinct `WP2-2` work package is now complete only as a generated H0
  forbidden-surface policy and sixteen-case negative corpus at
  `policy/a90-h24-wlan-forbidden-surface-policy-v1.json`. It source-pins the
  current H24 evidence and rejects manager duplication/consumer drift, global
  SELinux mutation, native-global Binder endpoints even when renamed,
  SD/whole/relocated-private property inputs, and global/inherited property
  service endpoints. A fresh private binderfs or private property socket stays
  blocked on `H0D05`/`H0D04`; no future byte-derived consumer exists and no
  dependency gate is retired. Each B0 placement is bound to its complete
  ordered fourteen-instance graph; later G_N or topology inputs require an
  explicit parent digest and removal/integration lineage and remain H0-only.
- The current sequential plan projects `2 + 13 + 13 + 2 = 30` logical future
  units if each baseline variant, removal, successful-removal requalification,
  and property-terminal attempt maps one-to-one to an attended session. Exact
  sessions and the ordinal budget remain unset and block execution
  qualification until `WP2-5b` plus operator acceptance. The result is only an
  order-conditioned reduced generation; without a separate final retest sweep,
  even terminal one-minimality remains unproved.
- `WP2-2` itself is host-only and consumes zero device ordinals. The thirty-unit
  figure applies only to a separately designed and authorized future program.
- `WP2-3` now generates
  `inventory/a90-h24-wlan-dependency-surface-inventory-v1.json`: fourteen
  roles with every `H0D01-H0D10` dependency surface represented, for 140
  exact known-fact/historical/conflict/unproved slots and ten fail-closed
  mutation cases. It records zero current H24 opaque-ELF bindings; the old
  `cnss-daemon` bytes/linker/property/WLFW evidence stays historical-only, and
  the Android `rmt_storage`/`tftp_server` identities remain unresolved
  conflicts with the selected root launch. This completes only the H0
  requirement/evidence-state inventory, not dependency closure: all ten gates,
  the future byte-derived consumer, execution implementation, and Option C
  remain blocked.
- `WP2-4` now freezes the H0 property observation/result schema, including the
  lookup-time type-0 MAC signature and strict fail-closed validators. Its
  runtime producer and byte-derived consumer remain absent; it retires no gate
  and grants no live authority.
- Before `WP2-5b` implementation, the permanent
  `WP2_5B_KMSG_STREAM_COMPLETENESS` invariant requires a trusted exact
  `/dev/kmsg` reader armed before effect intent and driver init, continuous
  sequence-complete bounded raw capture, and fail-closed overrun/boundary
  handling. `LOG_BUF_SHIFT=17` is only the 128-KiB minimum; the eight-CPU
  source-default calculation is 1 MiB absent an early override, while the
  effective live size remains unproved. Post-result snapshots and
  `/proc/kmsg` fallback cannot prove a log-dependent terminal. The
  `WP2_5B_STREAMING_KMSG_OBSERVER_ABSENT` implementation gate remains open.
- `WP2-5b.1` provides the generated trace framing/consumer core. `WP2-5b.2`
  now fixes the H0 runtime-owner/durable-evidence design: one sole reader with
  no effect authority, consumed-record `EINVAL`/`EFAULT` terminal faults with
  no retry, atomic no-replace trace/journal publication, separate
  driver/interface receipts, and observation-only crash reconciliation.
- `WP2-5b.3a` now implements the effect-free observer component and generated
  pipe/header contract at
  `docs/reports/A90_WLAN_WP2_5B_OBSERVER_RUNTIME_COMPONENT_H0_2026-08-16.md`.
  The source covers the exact-file clean-exec transition, null/fixed-FD
  bootstrap, exclusive waiter core, launch-readback validation core, dynamic-FD
  post-open confinement, sole `/dev/kmsg` state machine, and injected host
  fault corpus. It has no effect/journal/receipt API, no selected numeric
  runtime profile, and no parent integration. The durable final-name
  publication/storage writer and parser, receipt producers, qualified static
  target binary, and live execution review remain absent; the observer gate
  remains open.
- Numeric budgets remain unset until measured from a corrected healthy
  baseline. The design has no complete execution integration, qualification,
  independent execution review, identity, candidate, D0, D1, F1, handoff,
  UFS mutation, property provisioning, or live authority. Option C remains
  research-only until all ten dependency gates and its containment/switch
  conditions close. The exact next unit is H0 WP2-5b.3b: strict raw canonical
  writer/parser, selected storage-reservation backend, and crash-prefix fixture.
- The sealed-package boot-only F1 owner was retired before activation. Its
  7,313-file host-Python qualification and multi-module runtime made the simple
  A90 transaction harder to review without improving target, artifact,
  one-shot, rollback, or final-health proof. It remains historical evidence.
- The active replacement is the host-only minimal state machine at
  `workspace/public/src/scripts/server-distro/a90_boot_only_f1_minimal_v1.py`
  and its concise design
  `docs/plans/A90_BOOT_ONLY_F1_MINIMAL_V1_DESIGN_2026-08-20.md`. It fixes one
  A90, one `boot` candidate, one `boot` rollback, intent-before-effect,
  no-candidate-replay, and fresh final health in two allowlisted journal paths.
  It now has the small fixed production adapter and derived prepare/approved-
  execute CLI; the activated closure itself is awaiting fresh review and still
  grants no run authority.
  ADB remains recovery-scoped; ordinary resident observation is Native serial.
- At that checkpoint no H27 manifest, approval, ordinal, D0, D1, or F1
  authority existed. The small H0 adapter for the existing Native serial and
  `native_init_flash.py` mechanisms is now present. Its
  recovery mode binds the stable pre-effect non-recovery ADB baseline and one
  newly arrived recovery endpoint whose serial SHA-256 matches the private A90
  qualification, without a caller-selected serial. A first Luna MAX full review
  returned NO_GO because physical recovery was only a caller boolean. That
  boolean is now removed: the canonical candidate qualification binds and the
  owner rehashes exact recovery evidence/review bytes, its digest flows through
  preflight and terminal receipts, hazard acceptance is manifest-bound, and
  fresh enable/latch absence is observed directly. The exact next unit is one
  fresh independent full review of this repaired reduced execution closure.
  A second Luna MAX review rejected raw-hash-only review inputs; the owner now
  parses one canonical independent-review JSON and requires its `PASS_GO`,
  current ten-file closure, exact A90/candidate/rollback/recovery/hazard
  bindings, empty findings, and zero-contact disposition before PREPARED.
  A third review found that execute did not repeat that validation after fresh
  Native preflight. The owner now hashes and parses the same single read and
  repeats it immediately before approval and candidate intent.
  A fourth review found that special review paths were opened before the
  regular-file check. The owner now rejects them by `lstat` first, then opens
  nonblocking and rechecks the same inode before any bounded read.
  A fifth review found that generic `stat -ENOENT` was not tied to the marker
  argument. Adapter evidence now pairs every response with the exact request
  vector and requires `stat` plus the exact manifest path.
  A sixth review found enable/done roles and generations could be swapped. The
  manifest and independent review now require one shared generation stem and
  the exact `.enable`/`.done` suffix for their named roles.
  A seventh review rejected the constant other-target assertion. Live
  preflight now hashes complete `lsusb` output, requires exactly one Native A90
  endpoint (`04e8:6861`), and separately binds the fixed A90 Native serial;
  other Samsung endpoints may remain present but are never selected, and ADB
  remains recovery-only.
  An eighth review found rollback was still manifest-selected. The A90 owner
  now hardcodes the sole V2321 rollback path, size, SHA-256, version, and build;
  only the candidate varies by manifest.
  A ninth review found per-run journals permitted a second run ID to replay the
  same candidate. One fixed private run root now holds a permanent O_EXCL
  candidate-SHA guard, and approval also binds the run ID.
  A tenth review found artifact special files were opened before type checks.
  Candidate and V2321 rollback now pass pre-open `lstat`, nonblocking open, and
  same-inode revalidation before any read.
  An eleventh review found post-bind size growth was hashed before rejection.
  Checkpoints now reject declared-size drift and the 128 MiB cap before hash.
  A twelfth review found journal lstat/read reopen growth. Manifest and journal
  reads now use one bounded direct-regular descriptor with same-inode/size and
  trailing-growth rejection.
  A thirteenth review found dangling allowlisted symlinks were treated absent.
  Journal presence now comes from directory-entry names and every present name
  must pass the bounded direct-regular reader.
  A fourteenth review found different candidates could overlap. One durable
  capability-wide active-run guard now serializes all A90 F1 candidates and is
  removed only after an exact terminal; crashes keep it blocking.
  A fifteenth review found recovery-required terminals also removed that guard.
  Release is now limited to exact healthy candidate or healthy V2321 rollback;
  uncertainty remains globally blocking.
  A sixteenth review found another active run could burn a new candidate guard.
  PREPARED now acquires active first and only consumes candidate after; ordinary
  pre-effect candidate-guard rejection releases the new active reservation.
  A seventeenth review found the flash helper internally retried Native
  `recovery` and TWRP `reboot`. Minimal stable-baseline mode now sends each
  state-changing command once; response loss, busy, or no disconnect is
  uncertainty and never a resend.
  An eighteenth review found failed or malformed `adb devices` output could
  look empty. Minimal mode now requires successful strict inventory with exact
  header, empty stderr, and no malformed/duplicate endpoint row.
  A nineteenth review found TWRP disconnect still used the legacy parser. The
  same strict inventory now governs disconnect; inventory failure is
  uncertainty, never proof that recovery ADB disappeared.
  The first activated-closure review found fixed execute logs stranded a
  PREPARED candidate after wrong approval or pre-effect loss. Logs now use a
  derived monotonic per-run/per-phase ordinal and are never overwritten.
  The second activated review found ambient-`sys.path` import dependence and a
  log `exists`/`mkdir` race. Adapter loading now uses the exact sibling path and
  log reservation is atomic with collision normalization/retry.
  The third activated review found stale/foreign `sys.modules` aliases could
  still be reused. A per-load sentinel and exact path/class identity now reject
  mixed module instances.
  Luna MAX then issued `PASS_GO` for the activated ten-file closure
  `1a21cf7369d400ba01259e9d20cd73fe915b0597315b7bbd5843fa775a4c664b`.
  The H27 private manifest is canonical and host-validated at SHA-256
  `d97b8f45a8a43ce292fe9602b0154608ec2344a59f2ffbfcd4dbe5815e1c9b44`;
  it grants no effect until fresh preflight produces and the operator repeats
  its exact attended approval token.
  The first real prepare stopped before serial access because two Samsung
  `04e8:6860` endpoints were present instead of one Native A90 `04e8:6861`.
  No candidate/active guard or intent exists. The observed empty journal-dir
  residue prompted one final host repair: prepare now creates that directory
  only after target preflight and removes it on pre-effect guard contention.
  That historical preflight was followed by one separately approved attended
  H27 attempt. H27 was written once, boot-looped, and was never replayed; exact
  V2321 was then written once and returned healthy, while the owner retained a
  blocking `RECOVERY_REQUIRED` active guard because the rollback continuation
  occurred outside its missing resume surface. Before another F1, an exact
  terminal-only V2321 recovery receipt must close that run and the owner must
  be reviewed with an already-present bound recovery-ADB continuation.
  Host-only follow-up then located exact published Snapdragon LLVM 10.0.7,
  rebuilt the unchanged RKP CFP/JOPP/ROPP configuration, and materialized
  deterministic H28 `0.11.195 / phase3-minimal-h28-stock-rebuild-1007-cfp`
  A/B boot artifacts at SHA-256
  `aea34a96464affd2f7e6c30d237e2175940eef511e69c1452c9deab4833a521b`; see
  `docs/reports/A90_EXACT_SNAPDRAGON_LLVM_1007_STOCK_REBUILD_H28_H0_2026-08-21.md`.
  H28 remains H0-only: no D0, approval, ordinal, F1, or live authority exists.
  The two H27 follow-up gaps are now implemented and independently reviewed:
  the 13-file execution closure
  `e58746ea93270c43a28db5df20695a61a687eec942a5a665f562f4fe5173f077`
  received `PASS_GO` with HIGH/MEDIUM/LOW `0/0/0`. One exact
  terminal-only postrollback reconciler can close the fixed 2026-08-21 run
  after fresh V2321 health while preserving the manual rollback outcome as
  unproved and retaining the consumed candidate guard; the future rollback
  helper can reuse one already-present manifest-bound recovery ADB endpoint
  without issuing another Native recovery command. One separately authorized
  connected read-only D0 then ran that reconciler exactly once. Fresh Native
  V2321 `0.9.285 / v2321-usb-clean-identity-rodata` health passed; canonical
  journal record 41 was published at SHA-256
  `4d1da970b34d2a3cc9c6cce20858b0d8971a13a6ec057b5615fb1646a0b18930`;
  the active H27 guard was released while the consumed candidate guard stayed
  exact. Candidate and rollback replay remained false, the external rollback
  outcome remained unproved, and no ADB, reboot, payload, partition transfer,
  or F1 action occurred. The other Samsung endpoint received no command. H28
  still requires its own qualification, manifest, connected D0, and fresh
  attended approval; this terminal closure grants none of them.
  H28 qualification preparation now uses the candidate-neutral review scope
  `A90_MINIMAL_BOOT_ONLY_F1_EXECUTION_AND_CANDIDATE_HAZARD`; the retired
  H27-named scope is accepted only for the exact H27 candidate, hazard, and
  marker tuple. The resulting 13-file execution closure is
  `0dca4f3ddc98eb4625411c93ad7c1748f3c016aab0075a570652ca946fc4eb1f`.
  The public H28 review input and independent-review handoff bind the exact
  candidate, V2321 start/rollback, H28 state paths, and narrowed new-build-
  certificate hazard. At that preparation checkpoint, independent `PASS_GO`
  and the private manifest were absent. Luna MAX then issued
  `PASS_GO`, HIGH/MEDIUM/LOW `0/0/0`, for that exact closure and H28 input.
  The canonical public review is 1,189 bytes at SHA-256
  `51474c2d323971c07ca1425be613ea48cdd6c13f870606b166fba76835e6a9b2`.
  One canonical private H28 manifest was then host-validated at SHA-256
  `e708e45e9cd925229682c76ad3b6359426f2e636eb26eb111ea54e9843e8d1c2`;
  its runtime candidate/rollback/review rehash passed. At that checkpoint no
  journal, guard, connected D0, approval, ordinal, or F1 existed. One directly
  requested connected D0 then re-proved exact healthy V2321, recovery
  availability, the H28 enable/latch paths absent, and the other Samsung
  endpoint untouched. It published only canonical `00-prepared.json` at
  SHA-256
  `68b97cac14118ee4f3533a4b9760af10011efcc897332bad25fec585a5a0e7f3`,
  acquired the exact active and H28 candidate guards, and derived one fresh
  attended approval token. Candidate intent, transfer, reboot, ADB, rollback,
  and F1 effects remained zero pending the operator's exact token repetition.
  The operator then repeated that exact token and the attended H28 F1 consumed
  one candidate and one rollback attempt. Both boot writes and prefix readbacks
  matched their exact images, but each sole TWRP System-return request ended
  uncertain and was not resent. No H28 Native observation occurred, so kernel
  acceptance is unproved rather than refuted. The last proved boot bytes are
  exact V2321, but V2321 health is unproved; terminal record 40 is
  `RECOVERY_REQUIRED / ROLLBACK_HEALTH_UNPROVED` at SHA-256
  `400a6fe75ea54a738777092f828dede4d7b801bd3fbd8db29baddf26878c4f01`.
  Both guards remain, candidate/rollback replay is forbidden, and the next
  unit is a separately reviewed no-replay recovery continuation—not F1.
  That H28-only continuation is now specified in
  `docs/plans/A90_H28_PHYSICAL_SYSTEM_RETURN_RECOVERY_DESIGN_2026-08-21.md`
  and implemented by
  `a90_h28_physical_system_return_reconcile_v1.py`. It adds no host ADB,
  TWRP, reboot, flash, or partition path: one reviewed approval may durably
  arm one operator physical `Reboot -> System` press, after which only fresh
  read-only Native/ACM V2321 health can publish recovery closure and release
  the active guard. The candidate guard remains consumed and the original
  TWRP return remains unproved. The implementation and 21-case focused corpus
  are H0-only pending an independent full review; no physical action, D0, D1,
  F1, recovery, or guard-removal authority is active.
  The capability subsequently received independent `PASS_GO`, was committed at
  `96a187b2b1`, and one fresh exact approval durably armed the physical return.
  The operator selected TWRP `Reboot -> System` once and exact V2321 Native
  became visible. The finalizer consumed its one observation, proved the A90
  USB/bridge and complete exact V2321 version receipt, but the next read-only
  `selftest` command was truncated to `cmdv1 selft` before any A90P1 frame.
  It closed `NO_PROOF_OBSERVER` without retry: no recovery record was written
  and both guards remain. See
  `docs/reports/A90_H28_PHYSICAL_RETURN_SELFTEST_TRANSPORT_NO_PROOF_2026-08-21.md`.
  The next unit is a separately reviewed terminal-only slow-input observer
  repair; it grants no image, reboot, physical-action, or current live authority.
  That unit is now specified by
  `docs/plans/A90_H28_SLOW_HEALTH_RECONCILIATION_DESIGN_2026-08-21.md`.
  It permits one fixed `a90ctl --input-mode slow` read-only health session only
  after a new review and exact approval, then may remove only the active guard
  after durable exact V2321 health. No implementation, review, approval,
  observation, or guard authority exists at this design checkpoint. That slow
  session then ran once and reached the exact V2321 resident: `version`,
  `selftest fail=0`, and `status pstore entries=0` were observed, but the
  first boot-ID request returned `EBUSY` because the native automatic menu was
  still active. The slow-health intent is consumed and the run remains parked;
  no recovery record was written and both guards remain. This is observer
  no-proof, not an H28 kernel failure. See
  `docs/reports/A90_H28_SLOW_HEALTH_BOOT_ID_BUSY_NO_PROOF_2026-08-21.md`.
  The next H0 unit is the separately reviewed menu-hide observer repair,
  specified in
  `docs/plans/A90_H28_MENU_HIDE_HEALTH_RECONCILIATION_DESIGN_2026-08-21.md`
  and implemented by
  `workspace/public/src/scripts/server-distro/a90_h28_menu_hide_health_reconcile_v1.py`.
  It binds the consumed slow-health intent
  `63c26238f332a7bc1bad37a3950d5dc05f383c50a4a09ecfe57e2a119a390ac4`, sends
  one raw `hide` line only after its new durable intent, requires the explicit
  `hide requested` receipt, waits the fixed 3.0-second asynchronous-menu
  settle, then reads boot ID first followed by exact V2321/version, selftest,
  status, and a final boot-ID receipt. Exactly two boot-ID reads are required;
  `sameBoot` derives from equality, and a changed or failed final read parks.
  A settle interruption parks without a boot-ID request. It has no
  candidate, rollback, reboot, image, partition, or physical-action path and
  currently has no review, approval, observation, or guard-removal authority.
  H29 `0.11.196` was the first identity-only exact-toolchain candidate, with
  boot SHA `c3d1b84e…`; its materialization and qualification remain historical
  at their named reports. After its consumed uncertain run was recovered,
  host-only H30 was materialized from the same functional configuration as
  `0.11.197 / phase3-minimal-h30-stock-rebuild-1007-cfp`. A/B are byte-identical
  at SHA-256 `d28bd41434d252619dd95ecb352f55140d93889fd599784c0a7dbf491959c5fe`;
  the exact kernel remains `59f79b8f…`, and only identity/state paths changed.
  See `docs/reports/A90_EXACT_SNAPDRAGON_LLVM_1007_STOCK_REBUILD_H30_H0_2026-08-21.md`.
  H30 is H0-only. Current owner closure is `e0a1fa5d…` and current
  candidate-return continuation closure is `a396a744…`; the old `9b17904d…`
  dated continuation review is stale after the receipt/observer repair. Fresh
  independent review must bind both current closures before H30 qualification,
  private manifest, D0, approval, or F1 can exist.
  One later attended H29 F1 wrote and prefix-read back the exact H29 candidate
  once, but its sole TWRP System-return request was uncertain. The old owner
  then wrote and prefix-read back exact V2321 once with the same uncertain
  return; both attempts are consumed and neither may be replayed. No H29 Native
  observation occurred, so H29 remains unproved rather than refuted. After the
  operator manually selected System, a candidate-neutral terminal finalizer
  re-observed exact healthy V2321 over ACM only. It stopped before publication
  for a noncanonical bridge launch and then a second Samsung endpoint. Once the
  other Samsung was disconnected, the no-effect finalizer published canonical
  `41-recovery-closed.json` at SHA-256
  `d6f012df46645cb2b27a6d3a549c6b971eef0018e14a4d11e02b55bfb6667845`.
  The active guard is released, the H29 candidate guard remains consumed, and
  the rollback outcome remains `UNPROVED_EXTERNAL_CONTINUATION`. No image,
  reboot, ADB, recovery transition, or partition command was issued by the
  finalizer. See
  `docs/reports/A90_H29_UNCERTAIN_SYSTEM_RETURN_POSTROLLBACK_RECOVERY_2026-08-21.md`.
  This recovery closure grants no new candidate, D0, D1, F1, manifest, or
  approval authority.
  Separately, the ordinary F1 owner now has a host-only machine receipt for
  the exact `boot write + prefix readback + uncertain TWRP System return`
  case. It durably parks that case as `CANDIDATE_RETURN_PENDING` before any
  rollback; generic rc/prose/missing receipts never enter the park. The
  candidate-neutral physical/observation continuation remains a separate H0
  design with no live authority:
  `docs/plans/A90_F1_CANDIDATE_RETURN_CONTINUATION_DESIGN_2026-08-21.md`.
  The receipt/park implementation is recorded in
  `docs/reports/A90_F1_CANDIDATE_RETURN_MACHINE_RECEIPT_H0_2026-08-21.md`;
  its execution-closure change requires fresh independent review before F1.
  New candidate or rollback success also requires the exact confirmed-return
  receipt; a healthy snapshot with an unclassified, missing, or legacy effect
  result is not a new success terminal. A crash between exact uncertain
  `22-candidate-result.json` and `23-candidate-return-pending.json` now parks
  as `CANDIDATE_RETURN_PENDING_RECORD_MISSING_NO_ROLLBACK`; historical H28
  records without the new outcome are not reclassified. The `23` receipt
  digest must equal the durable `22` receipt digest exactly.
  The separate candidate-neutral continuation state machine is implemented at
  `workspace/public/src/scripts/server-distro/a90_f1_candidate_return_continuation_v1.py`,
  with the exact fixed backend at
  `workspace/public/src/scripts/server-distro/a90_f1_candidate_return_backend_v1.py`.
  `prepare` remains host-only. `resume`/`finalize` and any physical
  continuation remain H0/non-authoritative until a fresh independent review
  binds the current closure, qualification and manifest are current, and an
  attended token activates the exact run. The backend's fixed single-Samsung
  inventory, TWRP identity, intent ordering, and rollback attribution are part
  of that review.
  No static live-enable value remains. `review_gate_present()` reports only
  direct-regular canonical current `PASS_GO` availability; absent, symlink,
  malformed, wrong, or stale-closure review stops before backend creation.
  PASS alone grants no token, attendance, intent, or device authority.
  The backend factory requires a continuation-issued activation lease created
  only after the phase intent and both guards are durable; it binds the exact
  manifest/run/pending receipt/approval/phase and review/closure callbacks.
  Every subprocess is bracketed by lease revalidation, and stale or restored
  inputs fail before the next call. This is a fail-closed workflow API, not a
  same-UID Python isolation boundary. Each activation intent check rereads the
  strict current journal prefix, binds every envelope to the current manifest,
  and re-joins 22/23 to the activation-bound pending receipt before contact.
  The operational F1 precondition is intentionally simple: exactly one
  Samsung USB endpoint (`04e8`) may be connected. Non-Samsung host USB
  devices may remain, but every other Samsung device must be disconnected
  before the attended run. This is an A90 speed/safety precondition, not a
  permanent common boundary; multi-device coexistence is out of scope for
  this unit and would require a new design and review. Native is exactly one
  `04e8:6861` endpoint with the fixed ACM/managed bridge and zero ADB rows.
  Recovery is exactly one `04e8:6860` endpoint with exactly one total ADB row
  in `recovery` whose serial hash equals the manifest binding. Extra Samsung
  or ADB rows, a wrong product/state, or ambiguity parks before per-device
  contact. Owner mode persists only digest/status inventory markers and
  redacts bound serials as `<A90-ADB-SERIAL-SHA256:...>`.
  Its only effect entry is rollback: exact boolean `rollback: true` and the
  strict five-field manifest rollback artifact are required. Candidate,
  alternate-path, equal-SHA, schema/type, and symlink variants are rejected
  before any runner call, with direct regular-file identity/hash checkpoints
immediately before and after the existing helper.
For a Native rollback branch, the fixed backend binds two matching managed
bridge preflights (ACM realpath/PID/listener inode/process argv) and the owner
helper repeats the same preflight immediately before its one Native recovery
frame. An already-bound recovery endpoint skips the Native bridge command;
stale listener, foreign ACM, or generation drift performs no recovery/effect.
Before either rollback helper launch, the backend binds the complete raw
`/usr/bin/lsusb` byte-stream SHA-256 (including non-Samsung rows and ordering)
into owner-only argv. `native_init_flash` repeats the fixed producer and
requires an exact match before ADB binding, bridge recovery, push, or boot
write; producer failure, malformed/missing/surviving output, digest/role/
foreign drift, or recovery ambiguity stops with zero effect. Legacy helper
invocations do not receive or interpret this binding.
Before a Native recovery frame, the owner repeats the bound initial raw
  USB/ADB digests and the strict Native role immediately before bridge
  preflight; an owner inventory binding without the fixed bridge-preflight flag
  is rejected, and the later Recovery gate is separate. After Native becomes
  Recovery, the post-transition gate requires exactly one Samsung `04e8:6860`
  endpoint and exactly one bound recovery ADB row. Native-to-Recovery may
  legitimately change product, bus/device numbers, and raw bytes, so the
  post-transition raw digest is evidence only; the simplified role gate is
  authoritative. Already-Recovery branches still require the same-epoch raw
  digest before effect. Multi-device coexistence is deliberately not attempted.
The owner also binds the complete raw `/usr/bin/adb devices -l` SHA-256 and
the exact parsed role `NATIVE_NO_RECOVERY` or `BOUND_RECOVERY_PRESENT`.
`native_init_flash` verifies both before bridge recovery or any per-serial ADB,
push, or boot-write operation; ADB state/duplicate/extra-endpoint/initial raw-digest
drift stops with zero effect. Legacy helper invocations remain unbound.
  A continuation PASS releases only the active-run guard; the candidate-SHA
  guard remains consumed so the same candidate can never be prepared again.
  Candidate and rollback health snapshots must carry the exact manifest-bound
  qualification-review digest as recovery evidence; a mismatched valid digest
  parks rather than producing a new terminal success.
  The H28 qualification review/manifest/journal bytes remain frozen historical
  evidence at their original closure
  `0dca4f3ddc98eb4625411c93ad7c1748f3c016aab0075a570652ca946fc4eb1f`; the current owner
  intentionally rejects that stale review for new execution. Closed-H28
  reconciliation readers pin those historical bytes instead of promoting them
  to current authority. H29 must receive a fresh qualification, review,
  manifest, and owner-closure binding.
  TWRP identity is exact-key/exact-type validated before comparison, including
  rejection of bool, float, and string substitutions in numeric fields.
  Qualification review recovery/hazard joins now use recursive strict JSON
  equality, including scalar types and exact nested key sets; review `true`,
  `1`, and `1.0` cannot be treated as equivalent. This owner repair changed
  the dependent continuation closure and invalidated the prior continuation
  PASS_GO until a fresh review is issued.
  Rollback rechecks both guards after durable `31` and before flash; guard
  loss parks the consumed prefix without recreating or replaying it.
  Terminal `40` is now reopened and strictly read back before active-guard
  release; byte, schema, review, closure, or readback drift retains guards
  and raises without republishing or retrying the effect.
  The continuation and manifest qualification reviews now have identity/SHA
  leases (with continuation closure) checked around contacts, journal writes,
  rollback, and terminal release; same-byte swaps are rejected.
  Qualification-review SHA is explicit in approval/intents without adding its
  private path or bytes to the continuation closure.

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
- `docs/reports/A90_NATIVE_WIFI_OWNERSHIP_PERMANENCE_EVIDENCE_H0_2026-08-15.md`
  recovers the WSTA18/WSTA19 live evidence that native Wi-Fi ownership is a
  structural requirement of this device, not the residue of a retired
  experiment. Read it before reopening the isolated-Debian premise.
- `docs/reports/A90_WLAN_WP2_5B_OBSERVER_RUNTIME_COMPONENT_H0_2026-08-16.md`
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
The owner first-inventory path is fail-closed two-pass: endpoint tokens are
registered before persistence, and every valid/malformed/nonzero/timeout stdout
and stderr stream persists only digest/length/status markers.
