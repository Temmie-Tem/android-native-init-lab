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

### X - Forbidden

The existing forbidden partition and primitive list remains absolute. In
particular, no policy tier authorizes a partition image, raw block write, or
flashing operation to recovery, vendor_boot, DTBO, vbmeta, BL, CP, CSC, super,
userdata, persist, EFS, sec_efs, RPMB, keymaster, modem, bootloader, or any
partition other than an explicitly authorized boot payload. Normal Android
Package Manager and shared-user-storage writes are not partition operations
when they satisfy the exact reviewed D1 rules above. Raw host `dd`,
partition-table action, qdl/Sahara/Firehose, RAM dump, EUD/UART write, format,
fuse/QFPROM action, and unreviewed panic/RDX paths remain forbidden unless a
separate binding contract explicitly says otherwise.

## Escalation Rules

Escalate to F1 or a separately reviewed contract when any command hands a
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
