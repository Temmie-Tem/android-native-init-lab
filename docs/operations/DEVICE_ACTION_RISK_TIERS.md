# Device Action Risk Tiers

This contract keeps validation effort proportional to the action. It is a
classification rule, not blanket device authorization. `AGENTS.md`, its
permanent boundaries, and the selected binding target contract always win.
Archived target-specific policies are evidence only and grant no authority.

## Threat Model

Protect the device and evidence against implementation mistakes, stale target
selection, ambiguous transports, unintended writes, hangs, and incomplete
recovery. Do not turn every attended local action into a defense against a
malicious same-UID host owner replacing the repository or state namespace
between individual syscalls. When that adversary is material, stop and define a
separate trust boundary instead of growing an ordinary recovery helper.

## Tiers

### H0 - Host Only

Examples: source review, artifact inspection, tests, build, image unpacking,
hashing, and dry-runs with device access hidden.

- No device approval or one-shot policy is required.
- Commands must not contact ADB, USB endpoints, Odin, serial bridges, or network
  services on the target.
- Generated payloads remain private and do not imply flash authorization.

### D0 - Connected Read Only

Examples: exact target identity, boot health, sysfs/procfs reads, USB inventory,
and `odin4 -l` when a target-specific rule permits it.

- Require an unambiguous target and bounded reads/timeouts.
- Do not reboot, change boot mode, create device files, alter settings, or send
  a payload.
- Record only the evidence needed for the decision. A bespoke one-shot policy,
  artifact hash graph, and independent-model review are not required unless an
  installed policy explicitly requires them.
- A selected target contract may activate one exact derived-artifact retrieval
  after independent review. It must use a closed filename grammar in one fixed
  normal shared-storage directory, accept exactly one regular-file match,
  enforce fixed size bounds, compare the device SHA-256 with the pulled host
  file, and publish only by no-clobber into `workspace/private/`. It may not
  enumerate unrelated filenames, read app data, use root, or access a
  partition/block path.

### D1 - Routine Attended Non-Partition Action

Examples: an attended reboot, request/exit Download mode, or exact Odin
`--reboot` with no AP or other payload option. A target contract may also bind
one exact Package Manager APK install or one inert shared-storage file stage as
defined by `docs/operations/ROUTINE_CONNECTED_ACTIONS.md`.

- Exact UI-only native-init `hide` may use the operator's standing direction
  while the operator is actively attending. Announce it, send it once to the
  exact target, and require a complete framed success response.
- Require one fresh explicit operator approval for every other bounded D1
  action.
- Pin the exact target/topology, use an argv allowlist, bound output and time,
  and verify the expected return state. A mode-entry dispatch remains
  `HEALTH_PENDING` until its endpoint or operator-visible state is confirmed;
  do not replay it merely because observation is absent.
- No partition payload, credential mutation, persistent system configuration,
  permission grant, or security/debug-state change is permitted.
- A binding target contract may activate the reviewed routine-setup subset:
  one exact non-privileged APK install through Package Manager or one exact
  inert regular-file stage to fixed shared user storage. The input path, size,
  SHA-256, package/destination, and argv must be closed; staging is no-clobber
  and device-hash verified. It never authorizes execution, patching, deletion,
  reboot, mode transition, or partition transfer.
- A binding target contract may define a separately reviewed exact
  storage-artifact cleanup as a narrow D1 sub-capability when the only
  persistent effect is unlinking named target-owned files, every selected byte
  identity has an exact host-preserved recovery copy, current and protected
  artifacts are excluded, the dispatch is one-shot with no replay, and final
  target health is re-established. After unlink dispatch, the target contract
  may authorize only exact restoration of an absent selected byte identity as
  a separate durable recovery transaction; it must be attended, no-clobber,
  nonautomatic, and never replay an uncertain transfer or publish. This does
  not authorize arbitrary file, directory, package, credential, configuration,
  security-state, or partition mutation.
- Default evidence is one result plus the canonical timeline. Do not create a
  new policy exception, one-shot authority graph, or multi-review ladder merely
  for ordinary D1 recovery.
- On ambiguity or the same failure twice, stop. Do not inflate D1 into a larger
  live policy while the underlying transport remains unresolved.

A selected target contract may define a separately reviewed, mechanically
activated pre-F1 catalog that replaces per-ordinal approval only for its exact
finite transient descriptors. The S22+ definition is
`docs/operations/targets/S22PLUS_FYG8_PREF1_AUTONOMOUS_RESEARCH_POLICY_V1.md`;
it remains `DEFINED_NOT_ACTIVE` until its listed gates pass and never covers
F1 or persistent mutation.

### F1 - Boot-Only Transfer

Examples: one checked candidate or rollback AP containing only `boot.img.lz4`.

- Use the reusable process in
  `docs/operations/DEVICE_ACTION_PROCESS_V2.md`: exact artifact
  SHA256 and membership checks, full target preflight, known rollback, one fresh
  approval, append-only journal, bounded observation, and verified
  rollback/health.
- The approval binds one candidate attempt and its mandatory rollback. Recovery
  must not wait for a second acknowledgement after candidate execution begins.
- Record pre-session host failures precisely; do not permanently consume a
  candidate merely because a dry-run or Odin local parser failed.
- Do not create a candidate-specific helper, policy activation commit, or
  repeated review ladder when the runner and hazard class are unchanged.
- Missing evidence is no-proof and never weakens rollback requirements.
- A90 alone has a target-specific resident-promotion terminal defined by
  `A90_RESIDENT_BOOT_PROMOTION_V1.md`. It remains F1 risk: the exact rollback
  is preauthorized and mandatory after any post-attempt failure. Rollback may
  be omitted only after the exact candidate passes two independent health
  closures across one separate resident reboot. This does not apply to S22+
  or authorize an untested candidate.

### F2 - Exact S20+ Recovery-Canary Bootstrap

F2 exists only for the one exact `SM-G986N` / `y2q` / `y2qksx` /
`G986NKSS8IYC2` T0 capability named by its binding target contract. It is not a
general recovery tier and does not apply to TWRP T1, S22+, A90, another build,
or another image.

- Preparation is attended and read-only. It requires healthy rooted Android,
  exact target/serial/topology/current-boot binding, an empty Download
  baseline, and the fixed no-input root profile proving the live recovery node
  is the expected size and exact stock SHA-256.
- One fresh approval binds the exact runner/source closure, current boot,
  candidate, stock rollback, Download/recovery handoffs, observations, and
  expiry. It authorizes at most one candidate and one stock rollback attempt.
- Each AP contains exactly one deterministic regular `recovery.img.lz4`
  member. The candidate transfer omits auto-reboot; only a previously intended
  attended direct-Recovery key action may follow a completed classification.
  The rollback is preauthorized before candidate intent and never waits for a
  second approval.
- Candidate and rollback intents precede their exact Odin processes. Each
  intent consumes its attempt. Timeout, partial output, local parse failure,
  missing receipt, endpoint drift, reporting cut, or ambiguous state never
  permits replay. The exact candidate SHA-256 is also globally consumed so a
  later run cannot resend it.
- Odin and each AP are held as direct regular files across dispatch and
  revalidated afterward. Endpoint identity is refreshed immediately before
  dispatch. Bounded raw output, process-cage entry, descendant quiescence, and
  private atomic no-replace journal publication are mandatory.
- Recovery observation is bounded to the exact prepared serial/topology and
  fixed marker/properties. Absence or malformed evidence is `NO_PROOF`, not
  permission to retry. Automatic or attended physical Download recovery may
  lead only to the fixed stock recovery rollback.
- Terminal closure requires a later healthy exact rooted Android boot and the
  same fixed privileged digest profile proving exact stock recovery bytes.
  Transfer attribution, candidate claim, rollback health, and terminal health
  remain separate. An unknown rollback result can close only with an explicit
  unproved-transfer verdict after exact stock bytes are independently read.

### F2-T1 - Exact S20+ TWRP Retained Recovery

Status: **BINDING OWNER ACTIVE - T1 CANDIDATE CONSUMED**

F2-T1 is a separate, non-generalizing exception for the exact
`SM-G986N/y2q/y2qksx/G986NKSS8IYC2` TWRP T1 candidate. It receives no authority
from F2 T0. Its only candidate AP SHA-256 is
`3ed8498243ff09399ffd93fa3b0e90044a3cfe1709b7204dac53fe190647260f`;
its only recovery AP SHA-256 is the exact-stock
`ac9745b642c7fbd950d988671f707e47d58f8e2092464b27a37bede2267d7157`.
Each contains exactly one deterministic regular `recovery.img.lz4` member.

The completed T0 terminal may qualify only these predecessor facts: one exact
candidate transfer and one exact-stock rollback transfer were Odin-derived,
the physical Download recovery path worked, and a later root read proved the
stock recovery bytes. Its `NO_PROOF` candidate observation does not prove TWRP,
recovery ADB, display, touch, mounts, or retention. F2-T1 exists specifically
to test those still-unknown properties with a different SHA-pinned image.
Preparation must rederive those facts from the exact 2,188-byte private T0
terminal SHA-256
`94a7edbf5607f60cb19eeb3c7f09795682ccecb26a4dc807bed2485263b9e67a`,
pin its owner/base sources, and match its final serial binding to the current
healthy T1 target without publishing that identifier.

The one attended T1 preparation and exact returned approval consumed the T1
candidate once. It could retain the T1 recovery only
after a raw-derived completed transfer plus a fresh recovery boot whose same
prepared serial and topology answer the fixed root-ADB marker/version profile.
That terminal permits no TWRP UI action, mount, terminal command, format,
install, backup, restore, or another partition write. Visual UI is supportive
only; ADB marker proof is the retention gate.

Missing or malformed recovery ADB, Android arrival, transfer uncertainty, or
endpoint drift never retains by proof and never replays the candidate. Before
a retained terminal, the prebound exact-stock rollback remains reachable only
through the bounded attended physical Download path. Candidate/rollback intents,
global no-replay claim, cgroup quiescence, raw capture, exact endpoint binding,
and no-clobber journal rules remain at least as strict as F2 T0.

A clean retained terminal intentionally closes the run and its rollback
approval. Later stock restoration is possible only through separately reviewed
fresh exact-stock authority; it is not silently available from the closed run.

Activation required independent review of the common boundary, target section,
exact profile, connected owner, hostile tests, artifact closure, retained
terminal, and rollback branches, followed by a separately reviewed mechanical
activation commit. Every run still begins with a fresh attended preparation and
exact returned approval. The global T1 claim now prevents another preparation;
the owner remains only for closed-journal validation and terminal re-emission.
- Every other partition payload, format, mount, `dd`, direct block write,
  caller path/artifact/partition/command, security or Magisk mutation, and
  other-target command remains forbidden. T0 PASS supplies evidence for a
  later independently reviewed T1 proposal; it never authorizes T1.

F2 is available only while the target contract, exact connected owner, hostile
tests, permanent-boundary diff, and activation transition retain their
independently reviewed committed identities. An incident, source/artifact
drift, lost physical Download path, or the first global candidate claim retires
fresh candidate use.

### F2-T2 - Exact S20+ TWRP Corrected Retained Recovery

Status: **BINDING - ACTIVE ONLY THROUGH EXACT ATTENDED T2 OWNER**

F2-T2 is a new non-generalizing exception for only the exact
`SM-G986N/y2q/y2qksx/G986NKSS8IYC2` T2 candidate. Its sole candidate AP
SHA-256 is
`6d10b3154f2e899ee64305f3f3279d7d5243eb917f1fedb413b8f88d22ec88cb`;
its sole rollback is the demonstrated exact-stock recovery-only AP SHA-256
`ac9745b642c7fbd950d988671f707e47d58f8e2092464b27a37bede2267d7157`.
Each archive contains exactly one deterministic regular `recovery.img.lz4`.

T1 remains `NO_PROOF_T1_RETURNED_STOCK_RECOVERY_HEALTHY`. T2 may use that run
only as exact predecessor evidence: both T1 recovery transfers completed, the
final stock digest and rooted Android health passed, and its fixed root-ADB
observer matched every required field except that the effective property was
`sys.usb.config=mtp,adb` rather than the predeclared `adb`. The exact T1 owner,
terminal, observation, raw-capture receipt, raw stdout, and source closure must
all be mechanically revalidated. Documentation or semantic reconstruction of
those private bytes grants nothing.

One fresh attended preparation and exact returned approval may
consume the byte-distinct T2 candidate once. Retention requires a raw-derived
completed transfer and the same prepared serial/topology in ADB recovery state,
with a fresh boot ID, root UID, exact TWRP version/incremental, security fields,
running adbd, exact T2 marker, and exactly `mtp,adb`. Neither T1's supportive
observation nor T2 visual UI can substitute for that new T2 marker proof.

Every T1 no-replay, caged Odin, intent-before-effect, endpoint, physical
rollback, final stock-health, no-clobber journal, and other-target isolation
rule remains. A retained terminal closes the run and its rollback approval;
future stock restore requires separate fresh reviewed authority. No mount,
format, UI action, terminal command, install, backup, restore, caller path,
other partition, or security/Magisk mutation is introduced.

An expired or declined prepared-only run with no candidate or rollback intent
may close on the prepared Android boot only after a fresh exact-target/root
health check and exact-stock recovery digest. It records zero transfer attempts,
never consumes or replays a candidate unless a prior global claim already did,
and releases only its own guard. Same-boot closure is forbidden after any
transfer intent and grants no new approval or device effect.

Activation required independent review of the common boundary, target section,
exact builder/profile/owner, hostile tests, artifact and predecessor closures,
retained terminal, and rollback branches, followed by a separate mechanical
activation commit. Each run still requires a fresh attended preparation and its
exact returned approval before candidate transfer.

### R1 - Exact Privileged Root-Data Transaction

Examples: one independently reviewed, target-bound Magisk module experiment
whose exact persistent data mutation, ordinary reboots, disablement, cleanup,
and stock-boot recovery are one preauthorized attended transaction.

- R1 is not routine root maintenance. A binding target contract must activate
  the exact runner, artifact bytes, target/build, Magisk version, module ID,
  finite root-data surface set, fixed command literals, reboot budget, cleanup, and
  recovery owner after independent review. Otherwise the action is forbidden.
- Require one fresh attended approval after exact healthy rooted-Android
  preflight. Bind the complete pre-existing module inventory and reject any
  pending module update, target drift, stale namespace, staged-path collision,
  artifact drift, or unexpected root state before the first effect.
- The CLI exposes named state transitions only. It accepts no shell fragment,
  path, module/package ID, property, service, mount, credential, or executable
  from the caller. Every root command is a reviewed literal with bounded output
  and time.
- Durably record separate intent before staging, privileged install, each reboot, disablement,
  cleanup, or recovery. Each effect has one attempt. A missing receipt,
  transport uncertainty, malformed journal, or identity drift retains the
  shared guard and never permits replay. Strict typed JSON rejects duplicate
  keys and bool/integer substitution. Bounded partial command or read evidence
  after an intent is classified as consumed recovery-only evidence, never as
  success and never as permission to repeat the effect.
- Publish each final journal name only from a complete file-fsynced inode using
  an atomic no-replace operation, then fsync its directory. A pre-publication
  cut leaves no final name; a post-publication cut may expose only complete
  parseable bytes. Direct partial writes into final names are invalid.
- A staging-only cut has no root-data effect. Before the install intent, the
  operator may close an exact prepared-only run with zero writes; after
  staging starts, the only terminal continuation is exact-target health plus
  cleanup or read-only absence of the fixed staged bytes. After the install
  intent, recovery remains possible without
  requiring the candidate ZIP, builder source, or other candidate-only inputs;
  each recovery CLI must start and reach its scoped validator without importing
  those disposable inputs. It revalidates only the closure needed by that
  recovery branch. Rooted
  recovery rebinds the exact prepared Magisk version and helper bytes before
  any persistent recovery effect. A completed stock transfer may proceed to
  health-only finalization without reopening the already-consumed stock AP.
- The privileged installer must not reopen a payload from normal shared user
  storage. Stage it only in one fixed, exclusively claimed non-shared
  directory inaccessible to untrusted app UIDs; bind the direct non-symlink
  directory by owner, mode, and exact child set, and bind each direct regular
  payload by owner, mode, link count, exact size, and SHA-256 immediately before
  the sink. Directory link counts are filesystem-dependent and are not authority
  receipts. Concurrent independently authorized writers
  with the same staging UID are outside the lane and are a stop. Ordinary,
  stock/root-absent, and abrupt-cut cleanup must remain available to the
  non-root staging owner and remove only bounded regular remnants at the fixed
  names without replaying install.
- Normal success requires the exact observation contract, immutable replay
  proof when claimed, exact disable marker, healthy exact-target rooted
  Android, unchanged unrelated module inventory, and exact staged-input
  cleanup. Each reboot must freshly rebind its exact source boot before intent,
  and every returned boot ID must be distinct from the prepared and all earlier
  durable observations. It does not silently remove or alter any unrelated module.
- A durable terminal input must precede cleanup. A reviewed finalizer may
  resume only from exact journal state, never replay a consumed cleanup, and
  may release a post-terminal guard without a device command. Every other
  terminal attempt rechecks current exact target/root and terminal module
  state; a prior health receipt alone is insufficient.
- Device-generated evidence must match the reviewed writer/parser canonical
  byte grammar, not merely decode to an equivalent JSON object. Cleanup of a
  consumed partial stage write is limited to bounded regular non-hardlinked
  bytes at the two fixed names inside the exclusively claimed namespace.
- Recovery is included in the original approval. Exact Android-root recovery
  may create only the named disable marker. Physical Magisk Safe Mode is not an
  ordinary R1 recovery because its implementation can also mutate persistent
  Magisk database/configuration state; it requires a separate target-specific
  surface binding and review before use. When rooted Android recovery is
  unavailable, a stock fallback requires a distinct reviewed recovery owner
  and durable handoff, and can send only one prebound stock boot-only artifact.
  It has no candidate path and cannot inherit an adjacent F1 approval.
- The stock owner couples an empty Download baseline, a durable attended
  physical-action intent, and one exact endpoint arrival. The initial wait is
  finite; an intent-only reporting cut may perform one current exact endpoint
  observation but cannot repeat the baseline or physical action. It rejects
  legacy baseline-only state, malformed arm/arrival, and any endpoint-session
  change before dispatch. After
  rollback intent, a missing or partial local result is observation-only and
  can never cause another Odin call; later exact stock health may close with an
  explicit unproved transfer state but never as proved transfer completion or
  as stock-boot provenance.
- R1 never authorizes a partition payload itself. Its separately owned stock
  fallback remains subject to every ordinary boot-only transport, endpoint,
  artifact, no-replay, and final-stock-health boundary.

### X - Forbidden

The existing forbidden partition and primitive list remains absolute except
for the exact contract-bound S20+ T0/T1 recovery-only AP pairs and a separately
activated exact T2 pair. In particular, no policy tier authorizes a raw block
write or a flashing operation to vendor_boot, DTBO,
vbmeta, BL, CP, CSC, super, userdata, persist, EFS, sec_efs, RPMB, keymaster,
modem, bootloader, or any partition other than an explicitly authorized boot
payload or one mechanically active exact S20+ recovery-only pair. Normal Android
Package Manager and shared-user-storage writes are not partition operations
when they satisfy the exact reviewed D1 rules above. Raw host `dd`,
partition-table action, qdl/Sahara/Firehose, RAM dump, EUD/UART write, format,
fuse/QFPROM action, and unreviewed panic/RDX paths remain forbidden unless a
separate binding contract explicitly says otherwise.

## Escalation Rules

Escalate to F1, F2, R1, or a separately reviewed contract when any command hands a
payload to a bootloader, recovery, partition writer, or other executable
runtime; can write a partition; changes a credential, security, debug, or
persistent system configuration state; introduces a new low-level transport
primitive; or cannot bind one unambiguous target. The only persistent D1
exceptions are the exact Package Manager APK install, inert shared-storage
stage, and reviewed storage-artifact cleanup defined above. A lower tier must
never be used to split a higher-risk action into apparently harmless steps.

Historical consumed policies remain evidence only. `ACTIVE`, `RETIRED`, or
never-installed text under `docs/archive/` grants no current authority and
cannot be reactivated by these tiers.
