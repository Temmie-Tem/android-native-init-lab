# Security Hardening Review: A90 WLAN Vendor And Property Ablation

## Evidence Basis

This H0 review binds 24 public artifacts from baseline revision
`fda348a072eba8a53c2de7c9904c52429a7dddaf` with collection SHA256
`8b00d72b2ff1621351374dda081fbd4e9c3c376a5687a6bf8d04b32e67cde691`.

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
- The generated
  [`WP-H0-1` inventory](inventory/a90-h24-wlan-capsule-dependency-inventory-v1.json)
  now source-parses the frozen H24 selected composite graph and binds exact
  selected-path helper/shim/holder launch contracts. This selected-path
  snapshot is complete, but overall `WP-H0-1` is
  `PARTIAL_RUNTIME_CLOSURE_BLOCKED`. Its ten opaque runtime gates remain
  `UNPROVED`, so Option C is still research-only. `WP-H0-2` design may proceed
  in H0; execution and Option C implementation may not.
- The generated
  [`WP-H0-2` design](design/a90-h24-wlan-one-factor-ablation-design-v1.json)
  now fixes the corrected-baseline variants, exact-one-role generation model,
  scoped terminals, result/metric vocabulary, measured-budget rule, SD-free
  public bootstrap prerequisite, no-replay boundary, and promotion/stop rules.
  Its state is `COMPLETE_H0_DESIGN_ONLY`: no corrected healthy baseline,
  execution implementation, qualification, independent execution review, or
  live authority exists.
- The generated
  [`WP2-2` policy](policy/a90-h24-wlan-forbidden-surface-policy-v1.json)
  now rejects duplicate manager construction/consumer drift, global SELinux
  mutation, native-global Binder endpoints even when renamed, SD or relocated
  whole-property inputs, private-snapshot provenance, and global/inherited
  property-service endpoints. Its sixteen negative cases pass only a static
  H0 boundary. Private binderfs and a private property socket remain
  `H0D05`/`H0D04` proof obligations, and no future byte-derived consumer or
  execution implementation exists. B0 accepts only one exact ordered
  fourteen-instance graph per placement; non-B0 declarations require explicit
  parent/removal or integration lineage and still remain non-executable.
- The same policy records a thirty-logical-unit one-to-one serial projection
  (`2 + 13 + 13 + 2`). Exact attended sessions and the ordinal budget remain
  unset until `WP2-5b`; operator acceptance is an execution-qualification
  prerequisite. The output is an order-conditioned reduced generation, not a
  global or terminal one-minimal set.
  `WP2-2` itself is H0 and consumes zero device ordinals.

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
2. Apply the generated WP2-2 policy to reject global SELinux mutation,
   native-global Binder, SD/whole/private-snapshot inputs, manager duplicates,
   and graph-consumer drift. This static pass retires no `H0D` gate.
3. Use the frozen source-derived graph and `H0D01-H0D10` registry to generate
   the one-factor `WP-H0-2` design. This H0 design is complete; do not treat
   historical observations or inferred edges as current H24 facts.
4. Before executing a row, prove the H0D10 public deterministic SD-free
   bootstrap superset, retire its offline/static prerequisites, review the
   exact bounded instrumentation independently, and obtain separate live
   authority. Runtime gates retire only from their declared observations or
   ablations; one offline generation cannot retire them.
5. For each separately qualified future candidate, measure backend readiness,
   scan, association, DHCP, process/FD/memory/CPU/wakeup, property/Binder/QRTR
   use, cache write rate, cleanup, cold relaunch, and recovery. Never chain a
   failed removal into the next candidate.
6. Freeze either property absence or one finite deterministic seed.
7. Retire all ten gates, then apply the resulting component contract to both
   topology models and select the smaller proved boundary. Until the capsule
   passes every switch gate, reduced native supervision remains the reference
   design.

Before any live qualification, derive and obtain operator acceptance of the
exact attended-session and ordinal budget. The current H0 projection is thirty
serial logical units if each maps one-to-one to a session, excludes any final
retest sweep, and must not be represented as a live cap or authority.

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
