# Security Hardening Review: A90 WLAN Vendor And Property Ablation

## Evidence Basis

This H0 review binds 24 public artifacts from the lineage anchored at baseline
revision `fda348a072eba8a53c2de7c9904c52429a7dddaf`. Their current collection
SHA256 is
`12e587805caa82beff7599a1be8130469929f30916d52d89bf039fc24a1e6d67`.

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

The 2026-08-16 `WP2-4` follow-up is a separately generated H0 extension. Its
JSON carries its own five exact public `sourcePins`; neither it nor the new
WP2-5b streaming-kmsg report is retroactively counted as source evidence in
the 24-artifact collection above. `GOAL_A90.md` is one of those 24 artifacts,
so recording the current WP2-4/WP2-5b state rotates the collection hash; that
rotation does not relabel either derived follow-up as original evidence.

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
- Namespace membership is never proof that a global or shared kernel object is
  contained. QRTR, SELinux policy state, and ancestor proc magic links each
  require their own proved deny/non-nameability/mediated-owner control.

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
- The generated
  [`WP2-3` inventory](inventory/a90-h24-wlan-dependency-surface-inventory-v1.json)
  now binds fourteen roles and all 140 `H0D01-H0D10` dependency-surface slots
  as exact selected-source facts, historical-only observations, explicit
  identity conflicts, or unproved requirements. Its ten mutation cases reject
  evidence promotion and schema drift. It deliberately binds zero current H24
  opaque-ELF hashes: the historical `cnss-daemon` artifact and linker/property/
  WLFW facts are not current H24 closure, while the historical `rmt_storage`
  and `tftp_server` identities remain conflicts with the selected root launch.
  `WP2-3` is complete only as an H0 requirement/evidence-state inventory; all
  ten gates, the byte-derived consumer, execution, and Option C remain blocked.
- The generated
  [`WP2-4` schema](schema/a90-h24-wlan-property-observation-schema-v1.json)
  fixes eight observation phases, exact retained-role/phase coverage, distinct
  READ/WRITE/ACK events, a separately qualified exact generation/role binding,
  two terminal validators, and a total same-run
  cnss_utils MAC-effect decision table. The false-value row additionally
  requires the exact type-0 absence signature from the bound driver-init epoch;
  a debugfs absence read alone is only corroboration. The source invariant is
  non-reversion, not set-once, because debugfs may overwrite existing bytes.
  Event loss, fabricated defaults,
  read-error-as-absence, mixed runs, writable/link/extra seed members, missing
  final `RESIDENT_HEALTHY`, and recovery uncertainty all fail closed as
  `NO_PROOF_OBSERVER` or a rejected terminal. It also makes the global-object
  rule explicit: the remote workload keeps the all-ABI `AF_QIPCRTR` deny,
  compat `socketcall` and namespace-escape/namespace-clone denies remain a
  non-relaxable coupled invariant,
  global SELinux load/enforce writes stay zero, and ancestor proc magic links
  require the selected fresh PID/proc boundary. This is H0 schema completion
  only: runtime observer and byte-derived consumer are absent, H0D04 and H0D10
  remain `UNPROVED`, and WP2-4 grants no D0 or live authority.
- `WP2-5b` remains absent and unauthorized. Its permanent
  `WP2_5B_KMSG_STREAM_COMPLETENESS` invariant now forbids post-result `dmesg`,
  `/proc/kmsg` fallback, pstore/last-kmsg absence, or a larger ring from proving
  a kernel-log-dependent terminal. A trusted exact `/dev/kmsg` reader must be
  armed before effect intent and driver init, continuously drain complete
  source-bounded records, preserve the bounded raw epoch, and reject every
  overrun (`EPIPE`/`POLLERR`), sequence, format, boundary, or cap defect as
  `NO_PROOF_OBSERVER`. The effective live ring size is unproved:
  `LOG_BUF_SHIFT=17` is only the 128-KiB minimum, while the eight-CPU
  source-default calculation is 1 MiB absent an early override. The temporary
  `WP2_5B_STREAMING_KMSG_OBSERVER_ABSENT` gate retires only with the exact
  implementation, consumer, qualification, hostile tests, and independent
  execution review; it grants no authority.

## Property Terminal

Do not select a seed format yet. Accept only:

1. `PROPERTY_ABSENT_PROVED`; or
2. `PROPERTY_FINITE_SEED_PROVED` with exact key, context, value, file, digest,
   read-only lifetime, and negative corpus.

The shim's narrow set-operation acknowledgements do not reveal the vendor
binaries' read set. Moving the complete SD snapshot to cache is rejected.
The WP2-4 validators make an ACK non-equivalent to a read or state change and
require complete same-run coverage before either terminal can be published.
The result cannot nominate its own role set: validation also requires the exact
separately qualified pre-effect component-generation binding,
cold/persistent lifecycle partition, candidate seed-contract digest, and exact
event/byte caps; the post-run
trace digest remains result evidence rather than a pre-effect input. READ `ERROR`
or `DENIED`, phase regression, or an ACK not returned to the same exact
writer process in the same phase rejects the terminal. An explicit `MISSING`
remains a recorded read result and is never silently replaced by a fabricated
default.

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
