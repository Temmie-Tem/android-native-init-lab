# Security Hardening Review: A90 WLAN Vendor And Property Ablation

## Evidence Basis

This H0 review binds 18 public artifacts from baseline revision
`cddd986c561aa3211638e107ac9164ccec994da6` with collection SHA256
`e169452d657fe5c1cff34263db9e169e522fc35c45f178543eeec357d7e8940c`.

The strongest result is not a successful ablation. It is a correction to the
baseline: H24's selected helper builds thirteen composite children representing
eleven unique roles because `servicemanager` and `hwservicemanager` are each
enqueued twice. The published order string hides the duplicate pair. A
property shim and modem holder bring helper-managed children to fifteen; the
helper itself makes sixteen processes before native station policy starts.
H24 never reached this branch live, so it is neither live-qualified nor
known-minimal.

The same selected path also bind-mounts host SELinuxFS read-write, loads a
vendor policy into the global kernel policy interface, and best-effort writes
permissive mode. That makes the current helper unsuitable as a production
capsule baseline even before topology is chosen.

See [`context.md`](context.md) for exact anchors and the observed/inferred split.

## Constraints

- A90 only; H24 remains installed and its D1 remains consumed.
- H0 only. No device, private artifact, credential, property snapshot, or
  target transport was read or executed.
- WSTA18 proves only aggregate backend necessity. No named role is individually
  proved required or unrelated.
- Property remains `UNPROVED`: neither absence nor a particular finite seed is
  established.
- No successor may inherit the SD snapshot, global SELinux writes, duplicate
  service-manager instances, or a hand-maintained process/order mismatch.
- The `/proc` incident's containment closure remains mandatory under either
  ownership topology.

## Opportunity Portfolio

| Opportunity | Options | Recommendation | Proposal |
| --- | --- | --- | --- |
| Minimize the vendor backend once for both ownership topologies | Rehost H24 unchanged; immediately choose a reduced native supervisor; immediately choose a Debian capsule; run a topology-neutral ablation program first | Select topology-neutral ablation first. Keep reduced native supervision as the present safety baseline; promote the Debian capsule only after it satisfies explicit switch conditions. | [Detailed proposal](proposals/wlan-vendor-property-ablation.md) |

## Current Classification

- Individually proved hardware-essential roles: **zero**.
- Individually proved unrelated roles: **zero**.
- Current implementation-required composite children: **thirteen**.
- Unique named roles: **eleven**.
- Highest-priority corrections: remove the duplicate pair, reject global
  SELinux mutation, generate the component manifest mechanically, and bind
  exact property reads.
- First diagnostic ablation candidate: `cnss_diag`, still `unproved` rather
  than “unrelated.”
- Last removals to attempt: QRTR/PD/RFS/CNSS and the modem holder, because a
  failure there can collapse the entire hardware control plane.
- The proposal now freezes the selected launch predicate, argv, exact
  UID/GID/groups/caps or `UNPROVED`, lifetime, cleanup, and direct source
  anchors for every composite entry, the property shim, and the modem holder.
- The selected set contains `rmt_storage` but no separately selected `rmtfs`
  role. Their relationship and the exact QMI producer/consumer graph remain
  `UNPROVED` rather than inferred from names.

## Property Terminal

Do not select a seed format yet. Accept only:

1. `PROPERTY_ABSENT_PROVED`; or
2. `PROPERTY_FINITE_SEED_PROVED` with exact key, context, value, file, digest,
   read-only lifetime, and negative corpus.

The shim's narrow set-operation acknowledgements do not reveal the vendor
binaries' read set. Moving the complete SD snapshot to cache is rejected.

## Exact Sequence

1. Correct the executable graph: one generated manifest, no duplicate role,
   exact child count, exact identity/capability/FD/readiness/cleanup contract.
2. Remove all global SELinux load/enforce writes and reject them statically.
3. Build a host-only dependency inventory from exact binaries and public
   configuration without treating inferred edges as facts.
4. Define one-factor ablation candidates and instrumentation, then obtain an
   independent capability review before any candidate identity or live action.
5. For each separately qualified future candidate, measure backend readiness,
   scan, association, DHCP, process/FD/memory/CPU/wakeup, property/Binder/QRTR
   use, cache write rate, cleanup, cold relaunch, and recovery. Never chain a
   failed removal into the next candidate.
6. Freeze either property absence or one finite deterministic seed.
7. Apply the resulting component contract to both topology models and select
   the smaller proved boundary. Until the capsule passes every switch gate,
   reduced native supervision remains the reference design.

## Deliverables Before A Topology Change

- exact component manifest and generated order/health policy;
- zero global SELinux policy/enforce writes;
- exact Binder/QRTR/device/property surface;
- one of the two property terminals;
- cold launch, shutdown, descendant cleanup, and no-old-root proof;
- Debian-owned scan/association/DHCP proof while the backend survives;
- boot latency, WLAN-ready latency, RSS/PSS, process/thread/FD count, CPU
  wakeups, cache write/fsync rate, throughput, and recovery budgets;
- independent security and execution review.

This review creates no identity, artifact, qualification, approval, or live
authority. It grants no device, D0, D1, F1, candidate, handoff, UFS mutation,
property provisioning, credential provisioning, or SD-removal authority.
