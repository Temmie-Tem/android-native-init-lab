# Device Action Risk Tiers

This contract keeps validation effort proportional to the action. It is a
classification rule, not blanket device authorization. `AGENTS.md` and its
permanent boundaries always win. Archived target-specific policies are evidence
only and grant no authority.

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

### D1 - Transient No-Payload Control

Examples: an attended reboot, request/exit Download mode, or exact Odin
`--reboot` with no AP or other payload option.

- Require one fresh explicit operator approval for the bounded action.
- Pin the exact target/topology, use an argv allowlist, bound output and time,
  and verify the expected healthy return state.
- No partition payload, persistent configuration change, or security-state
  change is permitted.
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

### X - Forbidden

The existing forbidden partition and primitive list remains absolute. In
particular, no policy tier authorizes writes to recovery, vendor_boot, DTBO,
vbmeta, BL, CP, CSC, super, userdata, persist, EFS, sec_efs, RPMB, keymaster,
modem, bootloader, or any partition other than an explicitly authorized boot
payload. Raw host `dd`, partition-table action, qdl/Sahara/Firehose, RAM dump,
EUD/UART write, format, fuse/QFPROM action, and unreviewed panic/RDX paths remain
forbidden unless a separate binding contract explicitly says otherwise.

## Escalation Rules

Escalate to F1 or a separately reviewed contract when any command includes a
payload, can write a partition, persists across reboot, changes a security or
debug state, introduces a new low-level transport primitive, or cannot bind one
unambiguous target. A lower tier must never be used to split a higher-risk action
into apparently harmless steps.

Historical consumed policies remain evidence only. `ACTIVE`, `RETIRED`, or
never-installed text under `docs/archive/` grants no current authority and
cannot be reactivated by these tiers.
