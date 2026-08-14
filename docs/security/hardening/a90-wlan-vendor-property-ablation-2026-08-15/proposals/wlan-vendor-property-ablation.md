# A90 WLAN Vendor And Property Ablation Proposal

Date: 2026-08-15
Target: operator-owned Samsung Galaxy A90 5G only
Tier: H0, host-only design
Status: `H0_ABLATION_PROGRAM_SELECTED_NO_CANDIDATE_AUTHORITY`

## Decision

Run one topology-neutral vendor-service and property ablation program before
choosing between a reduced native supervisor and a Debian-supervised vendor
capsule.

Do not rehost the H24 helper unchanged. Its selected route contains an
executable 13-entry / documented 11-role mismatch, two duplicated Binder
service-manager instances, a whole SD property snapshot, root-capability
surfaces, global Binder devices, and a global SELinux policy/permissive write.
H24 never reached that route live.

Keep the reduced-native-supervisor design as the present reference boundary.
The Debian-supervised capsule becomes preferable only if a finite clean-exec
backend, property terminal, cold relaunch, Debian station ownership, cleanup,
and performance envelope are all proved.

## Executive Recommendation

The next unit is not a candidate and not a rootfs change. It is an H0 evidence
program with four immediate outputs:

1. one mechanically generated, duplicate-rejecting component manifest;
2. a static ban on global SELinux policy/load/enforce writes;
3. an exact property-observation contract with only two acceptable terminals;
4. a one-factor ablation and measurement specification reusable by both
   ownership topologies.

Current evidence supports neither “eleven services are required” nor “three
services are enough.” It supports only that some surviving vendor control plane
is required under the tested bring-up route.

## Evidence

| ID | Evidence | What it establishes |
| --- | --- | --- |
| `E01` | WSTA18 | Full removal of native/vendor userspace left WLAN objects but collapsed firmware, Root PD, WMI, and scan. It is an aggregate negative, not an individual ablation. |
| `E02` | WSTA19 | A surviving native control plane preserved scan while Debian Dropbear ran; association and DHCP were not tested in that unit. |
| `E03` | H24 manifest and v724 mode selection | H24 selects the service-object-visible route, persistent handoff, and an SD property snapshot. |
| `E04` | H24 helper composition | The selected control flow constructs thirteen entries representing eleven unique roles. |
| `E05` | H24 order and liveness code | The published order hides the duplicate pair while the liveness predicate requires every actual entry. |
| `E06` | H24 shim/holder code | Property shim and modem holder add two helper-managed children; the helper makes sixteen processes before station policy. |
| `E07` | H24 policy-load code | The selected route writes the global SELinux policy interface and best-effort sets permissive mode. |
| `E08` | historical bring-up plan | Vendor Binder/peripheral-manager visibility produced route progress, but never isolated the minimum causal set. |
| `E09` | H24 incident | H24 stopped before the Wi-Fi helper, so its exact route is not live-qualified. |
| `E10` | `/proc` incident | A shared PID/proc view makes vendor process/root/fd/ns capabilities reachable; either topology must close this. |
| `E11` | SD-free input design | Whole-snapshot relocation is rejected; property must be proved absent or reduced to a finite deterministic seed. |
| `E12` | A90 contract and goal | H24 remains installed, D1 is consumed, no successor identity exists, and this work grants no live authority. |

### Decisive source observations

- `with_service_manager` becomes true for the selected mode at
  `a90_android_execns_probe.c:1406-1411`.
- The first `servicemanager`/`hwservicemanager` pair is added at
  `:58654-58666`; the same two roles plus `vndservicemanager` are added again at
  `:58722-58735`.
- The selected list totals thirteen composite entries; `:59215-59231` spawns
  each one with no deduplication.
- The log order at `:58860-58862` lists eleven unique roles and therefore cannot
  prove the executable instance set.
- `persistent_handoff_child_required()` at `:58048-58074` treats every
  non-macloader entry as required.
- The selected mode calls `load_precompiled_policy_for_pm_observer()` at
  `:59150-59155`; the helper bind-mounts host SELinuxFS read-write at
  `:4580-4612`, writes `load`, and attempts `enforce=0` at `:63519-63605`.

## Current Design And Failure Mode

### Actual selected graph

| Order | Role | Executable | Current identity/capability observation | Status before ablation |
| ---: | --- | --- | --- | --- |
| 1 | `servicemanager` #1 | `/system/bin/servicemanager` | system UID/GID path; post-exec caps require proof | duplicate correction first |
| 2 | `hwservicemanager` #1 | `/system/bin/hwservicemanager` | system UID/GID path; post-exec caps require proof | duplicate correction first |
| 3 | `qrtr_ns` | `/vendor/bin/qrtr-ns -f` | vendor QRTR UID/GID, `CAP_NET_BIND_SERVICE` | conditional retain |
| 4 | `pd_mapper` | `/vendor/bin/pd-mapper` | system UID/GID, `CAP_NET_BIND_SERVICE` | conditional retain |
| 5 | `rmt_storage` | `/vendor/bin/rmt_storage` | root under current H24 compile path | conditional retain, high privilege |
| 6 | `tftp_server` | `/vendor/bin/tftp_server` | root under current H24 compile path | conditional retain, high privilege |
| 7 | `servicemanager` #2 | `/system/bin/servicemanager` | duplicates order 1 | unproved/likely conflict |
| 8 | `hwservicemanager` #2 | `/system/bin/hwservicemanager` | duplicates order 2 | unproved/likely conflict |
| 9 | `vndservicemanager` | `/vendor/bin/vndservicemanager /dev/vndbinder` | system identity route | conditional retain for current provider gate |
| 10 | `pm_proxy_helper` | `/vendor/bin/pm_proxy_helper` | system UID/GID | conditional retain for current provider gate |
| 11 | `per_mgr` | `/vendor/bin/pm-service` | system UID/GID; RT I/O class configured | conditional retain; route progress evidence |
| 12 | `cnss_diag` | `/vendor/bin/cnss_diag -q -f -t HELIUM` | system plus diagnostic groups | first diagnostic ablation candidate |
| 13 | `cnss_daemon` | `/vendor/bin/cnss-daemon -n -l` | system identity plus `CAP_NET_ADMIN` | conditional retain |

The property shim and modem holder run outside that composite array. The shim
and holder inherit a root-helper origin; the holder keeps a subsystem FD open
indefinitely. Native autoconnect, `wpa_supplicant`, and DHCP are dispatched
after backend readiness and are not among the thirteen.

### Current-source launch inventory

This inventory describes what the H24-selected source would launch, not what
hardware causally needs. The selected mode makes
`wlan_pd_service_object_visible_trigger=true`, `with_service_manager=true`,
`with_vnd_service_manager=false`, `wlan_pd_firmware_serve_gate=true`, and
`post_sysmon_observer=false` (`a90_android_execns_probe.c:58460-58552`). The
common composite launcher forks each entry, gives it a new session/process
group, chroots and changes to `/`, applies the selected environment and
identity routine, then execs the listed argv (`:43627-43856`). Every selected
non-macloader entry is required to remain PID-alive and observable for the
persistent handoff (`:58048-58074`). Common cleanup sends process-group
`SIGTERM`, waits up to 1 second, sends `SIGKILL`, waits up to 1 second, reaps
the direct PID, and requires the PGID to be absent (`:45424-45555`). That is
the current cleanup contract; it is not a complete descendant/cgroup proof.

| Order / role | Selected launch predicate | Exact executable and argv | Selected pre-exec identity | Current lifetime and cleanup | Direct source anchors |
| --- | --- | --- | --- | --- | --- |
| 1 `servicemanager` #1 | `!android_order_pre_cnss_provider_observer && with_service_manager && !qrtr_first_service_manager && !cnss_first_delayed_service_manager && !service74_gated_any` | `/system/bin/servicemanager` | UID/GID `1000:1000`; groups `1000,3009`; source prints expected cap `none` but does not call an empty `capset`, so exact post-exec caps are **UNPROVED** | required alive/observable; common composite cleanup | construction `:58654-58666`; identity `:7139-7175`; spawn/argv `:43627-43856` |
| 2 `hwservicemanager` #1 | same first-pair predicate | `/system/bin/hwservicemanager` | UID/GID `1000:1000`; groups `1000,3009`; exact post-exec caps **UNPROVED** for the same reason | required alive/observable; common composite cleanup | construction `:58654-58666`; identity `:7139-7175`; spawn/argv `:43627-43856` |
| 3 `qrtr_ns` | `!android_order_pre_cnss_provider_observer && !peripheral_manager_node_parity` | `/vendor/bin/qrtr-ns -f` | UID/GID `2906:2906`; no supplementary groups; `CAP_NET_BIND_SERVICE` retained and raised ambient | required alive/observable; common composite cleanup | construction `:58674-58679`; identity `:6834-6845`; argv `:43679-43682` |
| 4 `pd_mapper` | same outer predicate and selected `wlan_pd_firmware_serve_gate` ordering | `/vendor/bin/pd-mapper` | UID/GID `1000:1000`; no supplementary groups; `CAP_NET_BIND_SERVICE` retained and raised ambient | required alive/observable; common composite cleanup | construction `:58680-58693`; identity `:6929-6940`; default argv `:43655-43659` |
| 5 `rmt_storage` | same outer predicate and selected firmware-serve ordering | `/vendor/bin/rmt_storage` | H24 does not select the alternate Android identity macro: UID/GID `0:0`, no supplementary groups, `android-init-root` capability mode; exact cap reduction is **UNPROVED** | required alive/observable; common composite cleanup | construction `:58680-58693`; identity branches `:6848-6902`; default argv `:43655-43659` |
| 6 `tftp_server` | same outer predicate and selected firmware-serve ordering | `/vendor/bin/tftp_server` | H24 does not select the alternate Android identity macro: UID/GID `0:0`, no supplementary groups, `android-init-root` capability mode; exact cap reduction is **UNPROVED** | required alive/observable; common composite cleanup | construction `:58680-58693`; identity branches `:6905-6926`; default argv `:43655-43659` |
| 7 `servicemanager` #2 | `wlan_pd_service_window_trigger || wlan_pd_service_object_visible_trigger` | `/system/bin/servicemanager` | same `1000:1000`, groups `1000,3009`, exact post-exec caps **UNPROVED** | required alive/observable; common composite cleanup | construction `:58722-58735`; identity `:7139-7175`; spawn/argv `:43627-43856` |
| 8 `hwservicemanager` #2 | same service-object predicate | `/system/bin/hwservicemanager` | same `1000:1000`, groups `1000,3009`, exact post-exec caps **UNPROVED** | required alive/observable; common composite cleanup | construction `:58722-58735`; identity `:7139-7175`; spawn/argv `:43627-43856` |
| 9 `vndservicemanager` | same service-object predicate | `/vendor/bin/vndservicemanager /dev/vndbinder` | UID/GID `1000:1000`; groups `1000,3009`; exact post-exec caps **UNPROVED** | required alive/observable and provider gate input; common composite cleanup | construction `:58722-58735`; identity `:7139-7175`; argv `:43674-43677` |
| 10 `pm_proxy_helper` | `wlan_pd_pm_service_window_trigger || wlan_pd_service_object_visible_trigger` | `/vendor/bin/pm_proxy_helper` | UID/GID `1000:1000`; no supplementary groups; explicit empty cap set, no ambient caps | required alive/observable and provider gate input; common composite cleanup | construction `:58737-58745`; identity `:6972-6981`; dispatch `:43790-43800` |
| 11 `per_mgr` | same PM/service-object predicate | `/vendor/bin/pm-service` | UID/GID `1000:1000`; no supplementary groups; explicit empty cap set; requests I/O priority `RT/4` | required alive/observable and provider gate input; common composite cleanup | construction `:58737-58745`; identity/ioprio `:6972-7005`; dispatch `:43790-43800` |
| 12 `cnss_diag` | `!post_sysmon_observer` | `/vendor/bin/cnss_diag -q -f -t HELIUM` | UID/GID `1000:1000`; groups `1000,1010,3003,1015,1023,2002`; explicit empty cap set | required alive/observable despite diagnostic name; common composite cleanup | construction `:58753-58757`; identity `:6699-6753`; argv `:43666-43672` |
| 13 `cnss_daemon` | `!post_sysmon_observer && !service74_gated_peripheral_manager_provider_first_cnss`; selected route has no macloader insertion | `/vendor/bin/cnss-daemon -n -l` | UID/GID `1000:1000`; groups `3003,3005,1010`; only `CAP_NET_ADMIN`, raised ambient | required alive/observable; common composite cleanup | construction `:58753-58769`; identity `:6630-6697`; argv `:43660-43664` |

Two helper-managed children sit outside the composite table:

| Role | Selected predicate / interface | Identity and lifetime | Current cleanup | Direct source anchors |
| --- | --- | --- | --- | --- |
| property-service shim | `property_root != NULL` plus the selected start-only/allow path; AF_UNIX `/dev/socket/property_service`; attempts `chmod(..., 0666)` but does not check its result; `PROP_MSG_SETPROP`/`SETPROP2` and a fixed acknowledgement allowlist | forked from the root helper with no identity/capability normalization, so inherited exact caps are **UNPROVED**; persistent loop polls until stop or 4096 requests; start is mandatory but later liveness is not checked like a composite child | drain records, direct-PID `SIGTERM`/500 ms, `SIGKILL`/500 ms, wait, close record FD, unlink socket | selection `:60957-60986`; allowlist/protocol `:61126-61262`; start `:61264-61390`; cleanup `:61426-61500` |
| modem holder | selected firmware-serve gate, and for the service-object route only after provider visibility; opens `/dev/subsys_modem` | forked from the root helper with no identity/capability normalization, so inherited exact caps are **UNPROVED**; new session/chroot, holds the FD and pauses indefinitely; persistent readiness requires PID alive | process-group `SIGTERM`/3 s, `SIGKILL`/10 s, direct wait/reap, close record FD, unlink projected node | start/FD loop `:29011-29164`; cleanup `:29166-29266`; selected call `:59754-59767`; readiness `:58077-58099` |

The long-lived helper/supervisor itself is the sixteenth process in the source
accounting: 13 composite children + shim + holder + helper. It is a topology
owner, not an ablation role. Native autoconnect/station policy is separate and
must not be counted as evidence that this backend alone can associate or run
DHCP.

### Why the graph cannot be treated as a baseline proof

1. The executable graph and emitted order disagree.
2. The liveness predicate blesses construction choices as “required” without
   causal evidence.
3. The duplicate context-manager pair may be unable to coexist, but H24 never
   ran far enough to settle that.
4. H24's exact source route has no successful readiness, scan, association, or
   DHCP result; it is neither live-qualified nor known-minimal.
5. Selected global SELinux writes change the whole native kernel policy rather
   than create capsule-local compatibility.
6. Cleanup is based on direct children/process groups, not a proved cgroup and
   descendant closure.
7. Health publication performs recurring cache write/fsync/rename work, which
   must be measured rather than inherited.

### Dependency classification: established versus unproved

The shorthand sequence `property/Binder compatibility -> vendor provider
visibility -> QRTR/PD/RFS -> WCNSS/WMI -> wlan0 -> station policy -> DHCP` is
only a hypothesis map. Most arrows cross opaque binaries. The exact current
classification is:

| Surface or role | Producer / consumer classification | What direct source establishes | What remains **UNPROVED** |
| --- | --- | --- | --- |
| binary property area | compatibility input; producer is the external whole property snapshot; consumers are opaque vendor readers | H24 read-only binds the whole area into the private root | every actual reader, key, context, value, default, and lifetime |
| property-service shim | write-compatibility shim; vendor callers produce bounded set requests and the shim produces ACK/error records | exact AF_UNIX protocol and write allowlist | whether ACKs correspond to required state, whether any retained role needs writes, and which caller emitted each request |
| `servicemanager` / `hwservicemanager` / `vndservicemanager` | compatibility registry/context-manager route | selected construction and provider-readiness observations | which retained producer/consumer requires each manager and whether private Binder suffices |
| `pm_proxy_helper` / `pm-service` | provider-visibility compatibility route | selected service-object gate observes VSM, helper, PM, and provider states | exact hardware dependency, transaction edges, and whether direct readiness can replace the route |
| `qrtr-ns` | QRTR name-service compatibility candidate | selected route launches it before other PD/RFS roles | exact clients, service registrations, and individual necessity |
| `pd-mapper` | PD mapping/provider candidate | selected firmware-serve route launches it | exact producer/consumer edges and individual necessity |
| `rmt_storage` | selected RFS/storage-named producer candidate | selected route launches the binary as root | exact files/devices/QMI dependencies; the selected set contains no separately named `rmtfs` daemon, and the relationship between `rmt_storage` and `rmtfs` is **UNPROVED** |
| `tftp_server` | selected RFS/firmware-serving candidate | firmware-serve gate launches and observes it | exact requests, consumers, served objects, and individual necessity |
| QMI | protocol/transport observation surface, not a separately selected child role | helper instrumentation observes QMI-labelled events and v724 classifies `wlfw-or-icnss-qmi` | exact QMI producer/consumer graph for the selected 13 entries, including any relation to `rmt_storage`/`rmtfs` |
| `cnss-daemon` | WCNSS/WMI-facing control-plane candidate | selected route launches it with `CAP_NET_ADMIN`; aggregate WSTA evidence requires some surviving backend | which QMI/WMI/device operations it alone supplies and whether it can cold relaunch |
| `cnss_diag` | diagnostic candidate | selected route launches it and requires it alive | whether any readiness edge depends on it; it is not yet proved unrelated |
| modem holder | device-lifetime compatibility holder | opens and retains `/dev/subsys_modem`; selected route gates start on provider visibility | minimum lifetime and whether another retained component can own the requirement |
| WCNSS/Root PD/WMI | hardware/control-plane terminal | WSTA18 establishes aggregate collapse when the prior userspace backend disappears | the minimum upstream process/property/IPC set |
| native autoconnect | station-policy consumer, separate from the backend | runs after backend readiness | whether Debian can replace it for scan, association, and DHCP |

This table deliberately does not rename `rmt_storage` as `rmtfs`, infer a QMI
edge from a diagnostic string, or promote a compatibility route to hardware
necessity. Binder provider visibility and the holder gate are visible in
source; every other per-binary causal edge requires one-factor evidence.

## Desired Invariants

1. Exactly one generated component manifest determines construction, logging,
   health, cleanup, and evidence; duplicate role/target/identity is rejected.
2. Every component binds executable digest, argv, UID/GID/groups,
   capabilities, SELinux expectation, namespace, cgroup, rlimits, scheduler,
   inherited FDs, readiness, and cleanup identity.
3. The successor performs zero writes to SELinux policy `load`, `enforce`, or
   any equivalent global policy interface.
4. No SD path, old root, global devtmpfs, global Binder endpoint, or unbounded
   property namespace is reachable.
5. Property is either proved absent or one exact deterministic read-only seed;
   no third state exists.
6. The property write-ACK protocol is versioned separately from property read
   data, bounded, authenticated by local provenance, and not treated as a
   successful state mutation unless a consumer requires and verifies it.
7. One ablation changes one variable. Failure never becomes the baseline for
   the next removal.
8. A passing unit proves WCNSS/Root PD/WMI, bounded scan, association, DHCP,
   cleanup, recovery, and no forbidden capability exposure.
9. Remote SSH/workload code cannot name or control the privileged backend in
   either topology.
10. The same component/property contract can be launched by native PID 1 or a
    Debian-owned clean launcher without semantic drift.

## Constraints And Non-Goals

- This proposal does not assert that a Debian-supervised capsule is feasible.
- It does not assert that native PID 1 must be the permanent owner.
- It does not identify any individual component as definitely removable.
- It does not read the private property snapshot or credentials.
- It does not authorize UFS content mutation or cache provisioning.
- It does not revive H24, reuse its identity, or replay its D1.
- It does not relax boot-only payload, rollback, recovery, durable no-replay,
  target isolation, or final-health requirements.
- It does not make a host fixture substitute for hardware ablation evidence.

## Before Architecture

See [current accumulated route](../diagrams/wlan-vendor-property-ablation-before.mmd).

The key defects are visible in one picture: SD input, global Binder, a
hand-built multi-process graph, hidden duplicates, global SELinux mutation,
and a separate station-policy path.

## Property And IPC Boundary

### What is observed

- The whole H24 property tree is bound read-only into the helper's private root.
- The set-operation shim accepts a small compatibility vocabulary, including
  `hwservicemanager.ready`, `ctl.stop=vendor.rmt_storage`, and two peripheral
  `OFFLINE` values.
- The shim returns acknowledgements; it does not demonstrate that a binary
  property value changed.
- A broad source-level property lookup allowlist belongs to diagnostic tooling.
  It is not the selected binaries' observed read set.
- The current Binder path reconstructs global Binder device nodes and uses
  service/provider visibility as a readiness gate.

### What remains unproved

- exact property files, keys, contexts, and values read by each surviving
  binary;
- whether any successful property read is needed after component ablation;
- whether a private Binder context works for the surviving provider graph;
- whether the set-operation shim is needed once diagnostic/service-manager
  components are removed;
- whether Root PD can cold relaunch after every backend process exits.

### Two acceptable property terminals

`PROPERTY_ABSENT_PROVED` requires zero successful property reads across clean
launch, readiness, scan, association, DHCP, steady state, shutdown, and cold
relaunch. Missing property access must fail the trace rather than silently
return a fabricated default.

`PROPERTY_FINITE_SEED_PROVED` requires one canonical finite set of key,
context, value, source, digest, lifetime, and reader. Unknown/duplicate keys,
extra files, wrong context, writable content, symlinks, hardlinks, truncated
records, wrong generation, and digest drift must fail closed.

## Options

### Option A: Rehost the H24 graph unchanged

Move the current helper and compatibility tree under the selected supervisor.

Tradeoffs:

- Security: worst option; preserves root processes, global Binder, SD property
  assumptions, hidden duplicates, and global SELinux mutation.
- Performance: highest known process count and recurring health-write cost.
- Memory: retains sixteen-process backend before station policy.
- Reliability: executable graph may not reach readiness because duplicated
  context managers are unproved.
- Operability: shortest apparent port but hardest evidence attribution.
- Migration: low code movement, high hidden dependency and recovery risk.

Disposition: rejected.

### Option B: Reduced native supervisor plus isolated Debian

Apply the ablated component/property manifest under the existing selected
native-supervisor security model.

See [reduced-native diagram](../diagrams/wlan-vendor-property-ablation-native-after.mmd).

Tradeoffs:

- Security: keeps a privileged native boundary but places remote Debian behind
  the already selected PID/mount/IPC/UTS/network containment.
- Performance: one extra administrative plane, but the vendor set can shrink.
- Memory: native supervisor plus capsule and Debian; bounded by measured
  cgroups/resources rather than process-name assumptions.
- Reliability: closest to the only live-supported WLAN lineage and recovery
  model.
- Operability: two administrative worlds and more explicit cross-boundary
  logging/recovery.
- Migration: lowest-risk place to validate component ablation first.

Disposition: current reference, conditional on completing ablation and all
selected-design gates.

### Option C: Debian PID 1 supervises the reduced capsule

Clean-exec Debian first, then launch the exact ablated backend as a contained
hardware compatibility capsule.

See [Debian-capsule diagram](../diagrams/wlan-vendor-property-ablation-capsule-after.mmd).

Tradeoffs:

- Security: one lifecycle/policy owner, but only if rootless remote workloads
  cannot name capsule proc/fd/ns/device/IPC state.
- Performance: can remove the permanent native supervisor path; capsule launch
  and mediation overhead remain.
- Memory: potentially smallest administrative footprint after a real service
  reduction; no benefit if most Android compatibility must remain.
- Reliability: cold relaunch, Root PD recovery, and Debian station ownership
  are currently unproved.
- Operability: simpler ownership after success, more demanding bootstrap and
  failure attribution before success.
- Migration: highest up-front work because clean exec, private IPC, capsule
  security envelope, recovery, and adoption all need new proof.

Disposition: H0 research target, not selected for implementation.

### Option D: Topology-neutral ablation first

Freeze one component/property contract and one validation vocabulary before
running either topology as a candidate.

Tradeoffs:

- Security: avoids blessing accumulated Android compatibility as permanent and
  prevents topology choice from weakening the component boundary.
- Performance: produces comparable process, memory, wakeup, and latency data.
- Memory: lets measured service removal determine the actual footprint.
- Reliability: separates hardware necessity failures from supervisor/topology
  failures.
- Operability: more H0 preparation, substantially clearer future attribution.
- Migration: adds an explicit evidence phase but all results are reusable by
  Options B and C.

Disposition: recommended now.

## Comparison

| Criterion | Rehost H24 | Reduced native | Debian capsule | Ablation first |
| --- | --- | --- | --- | --- |
| Exact current feasibility | unproved | design-selected, not implemented | unproved | host-design feasible |
| Hidden duplicate removed | no | required | required | first gate |
| Global SELinux write removed | no | required | required | first gate |
| Property minimum | whole snapshot | unproved | unproved | explicit terminal |
| Remote workload separation | not inherent | selected isolated boundary | must be newly proved | validation contract shared |
| WLAN live lineage proximity | medium | highest | lowest | neutral |
| Expected security review surface | largest inherited | bounded but dual-world | potentially smallest after proof | reduces both |
| Recommendation | reject | reference | conditional research | select now |

## Recommendation

Select Option D immediately and retain Option B as the reference architecture.
Do not allocate a successor identity merely to test the current thirteen-entry
graph. First correct the graph and static hazards in host-only design/code, bind
one manifest and negative corpus, and obtain independent capability review.

Switch the architectural recommendation from Option B to Option C only when
all of the following are true:

1. the surviving component set is finite and every retained role has positive
   necessity evidence;
2. property is absent or a finite seed is proved;
3. global Binder/property/SELinux dependencies are removed or replaced by
   capsule-private equivalents;
4. the backend cold-launches after complete shutdown without reboot;
5. Debian owns scan, association, and DHCP over the surviving backend;
6. clean exec, old-root/FD/VMA/capability/cgroup/descendant cleanup are proved;
7. rootless SSH/workload code cannot name or control the capsule;
8. boot, memory, CPU wakeup, throughput, write amplification, cleanup, and
   recovery remain within predeclared budgets.

If most of Binder/property/global policy or the H24-scale process tree remains
necessary, Option B is the smaller security boundary despite having two PID 1
roles.

## Ablation Matrix

| Stage | Single change | Host-only gate | Future hardware terminal |
| --- | --- | --- | --- |
| `A0` | Parse exact current bytes | derive 13 entries/11 roles; reject order drift | never execute as a candidate |
| `A1` | Correct the duplicated SM/HSM construction bug | generated graph/order/health all equal; duplicates impossible | later baseline only; this is not a necessity ablation |
| `A2` | Eliminate global SELinux mutation | zero load/enforce write symbol/path reachability | exact domain/cap behavior without global change |
| `A3` | Add bounded dependency/property/IPC observation | observer cannot mutate or fabricate success | exact read/IPC baseline, no component removed |
| `A4` | Remove `cnss_diag` only | no static hard dependency; health schema updated | WMI, scan, association, DHCP unchanged |
| `A5a` | Remove `servicemanager` only | exact private IPC diff and predicted stage | one-factor result, never chained |
| `A5b` | Remove `hwservicemanager` only | exact private IPC diff and predicted stage | one-factor result, never chained |
| `A6a` | Remove `vndservicemanager` only | provider/readiness diff declared in advance | one-factor result, never chained |
| `A6b` | Remove `pm_proxy_helper` only | provider/readiness diff declared in advance | one-factor result, never chained |
| `A6c` | Remove `pm-service` only | provider/readiness diff declared in advance | one-factor result, never chained |
| `A7a` | Remove `qrtr-ns` only | ELF/config/device/QRTR diff and exact expected failure stage | one-factor result, never chained |
| `A7b` | Remove `pd-mapper` only | ELF/config/device/PD diff and exact expected failure stage | one-factor result, never chained |
| `A7c` | Remove `rmt_storage` only | file/device/QMI observation and exact expected failure stage | one-factor result, never chained |
| `A7d` | Remove `tftp_server` only | served-object/RFS observation and exact expected failure stage | one-factor result, never chained |
| `A8` | Remove `cnss-daemon` only, late | exact QMI/WMI/device observation predicts terminal loss | one-factor result or proved hard requirement; never chained |
| `A9` | Remove modem holder only, late | exact `/dev/subsys_modem` FD/lifetime diff | one-factor result or proved hard requirement; never chained |
| `A10` | Remove property-service shim only | observed write callers and ACK semantics are complete | no required writes/ACKs across full lifecycle |
| `A11a` | Property area absent | trace/filter makes any read explicit | zero reads through full lifecycle |
| `A11b` | Finite property seed | canonical schema and negative corpus | every read belongs to exact seed |
| `A12` | Clean capsule envelope | old-root/FD/VMA/ns/cgroup escape negatives | cold start/restart/cleanup pass |
| `A13` | Debian station ownership | bounded client and ownership receipt | Debian scan/association/DHCP, no native autoconnect |

`A11a` and `A11b` are alternative property-read terminals, not sequential
requirements. `A10` is a separate property-write compatibility decision and
does not follow automatically from either read terminal. `A1` is one
construction-defect correction, not evidence that either manager is
unnecessary. Every suffixed `A5`, `A6`, `A7`, or `A11` row is a separate unit
with a fresh unchanged baseline; no grouped route removal counts as one-factor
evidence. `A4` through `A13` may begin only after `A1` through `A3` pass.

## Evidence Coverage And Residual Risk

| Claim | Coverage | Residual risk |
| --- | --- | --- |
| Some vendor backend must survive under the tested route | live WSTA18/WSTA19 evidence | another clean bring-up implementation could differ |
| H24 selected graph is 13 entries / 11 roles | direct source control flow | actual runtime conflict not observed |
| All 13 are implementation-required | direct persistent predicate | says nothing about causal necessity |
| Property read minimum | none | opaque binaries may read undocumented keys/defaults |
| Binder/PM individual necessity | historical route progress only | route-specific scaffolding may be removable |
| Global SELinux mutation is reachable in selected source | direct source path | H24 did not execute it live |
| Debian capsule can cold relaunch backend | none | Root PD may require native lifetime/reboot |
| Debian can own station policy | none under preserved minimal backend | native autoconnect may still be required |

The largest residual risk is opaque vendor behavior. Host source review can
define safe experiments and reject structural hazards; it cannot prove a
binary unnecessary on the physical SoC.

## Migration And Rollout

1. Keep H24 installed and do not replay its consumed D1.
2. Make host-only graph generation and negative tests independent of a
   successor identity.
3. Freeze the property observation schema and metric vocabulary.
4. Independently review the resulting execution-critical source closure.
5. Only after current Goal/contract pre-candidate gates permit it, allocate a
   fresh identity for one exact baseline correction. A replacement candidate
   never reuses H24 identity, enable path, latch, artifacts, or approval.
6. Each live ablation is one separately bound boot-only candidate or another
   contract-approved mechanism. A failure is terminal evidence for that unit;
   do not remove another component on top of it.
7. Return/recover to exact native health after every persistent experiment.
8. Compare Options B and C only on the same proved component/property set.

## Validation Plan

### Host-only static fixtures

- evaluate the H24 manifest flags and derive the selected mode;
- derive the actual component array and compare it to generated order, health,
  cleanup, and report schemas;
- reject duplicate name, executable, role, identity, or readiness key;
- reject any successor reference to SD property/evidence/profile roots;
- reject SELinux policy/load/enforce writes and global Binder reconstruction;
- require exact UID/GID/groups/caps/scheduler/rlimit/cgroup/FD/namespace fields;
- reject shim EOF, request-budget exhaustion, or holder death as healthy;
- reject descendants escaping a bound cgroup/session/namespace cleanup set;
- reject full snapshot, unknown/duplicate property key/context/value, extra
  file, writable seed, symlink, hardlink, truncation, or digest drift;
- require diagrams, observed/inferred/proposed labels, authority denials, and
  exact evidence collection digest.

### Future live metrics

| Category | Required measurement |
| --- | --- |
| functional | firmware, Root PD, WMI, `wlan0`, bounded scan, association, DHCP, route, authenticated service |
| latency | component ready, backend ready, first scan, association, DHCP, SSH, cold relaunch, cleanup, recovery |
| footprint | process/thread/FD count, RSS/PSS, cgroup memory, Binder objects, QRTR endpoints |
| runtime cost | CPU time, wakeups, context switches, cache write/fsync/rename rate, I/O bytes |
| network | throughput, latency, loss, retransmit, packet/flow bounds, final Wi-Fi state |
| property/IPC | exact reads/writes, keys/contexts, Binder transactions/context managers, QRTR service events |
| cleanup | lingering PID/PGID/cgroup/nsfd/device FD/socket/property/Binder/QRTR state |
| recovery | exact rollback/return time, native schedulability, no replay, final health |

Budgets must be derived from a measured healthy reference before implementation
qualification; this document does not invent pass numbers.

## Implementation Work Packages

- `WP2-1`: generated component manifest and 13/11 regression fixture;
- `WP2-2`: global SELinux/Binder/SD-path rejection corpus;
- `WP2-3`: exact binary/config/device/identity dependency inventory;
- `WP2-4`: property read/write observation schema and two terminal validators;
- `WP2-5`: one-factor ablation manifest generator and durable result schema;
- `WP2-6`: common metric/benchmark collector and failure attribution;
- `WP2-7`: reduced-native launch/cleanup integration;
- `WP2-8`: clean Debian capsule feasibility implementation;
- `WP2-9`: independent security/execution review and topology decision.

Only `WP2-1` through `WP2-4` are immediate H0 work. Later packages require
their own authority and must not be inferred from this proposal.

## Open Questions

1. Which role first establishes the minimum WCNSS/WMI-ready state?
2. Can both duplicated service-manager instances ever remain healthy, or is the
   current selected graph deterministically unready?
3. Is `cnss_diag` causally required or purely diagnostic?
4. Can VSM/PM provider visibility be replaced by a direct hardware readiness
   signal without weakening proof?
5. Which property keys/contexts are actually read by each retained binary?
6. Does any retained binary require property writes, or only acknowledged
   lifecycle notifications?
7. Can private binderfs replace global Binder devices for the reduced set?
8. Can Root PD and WMI cold relaunch after every backend process and holder are
   gone, without reboot?
9. Can Debian `wpa_supplicant` own scan, association, and DHCP after the backend
   is ready?
10. What exact firmware/RFS paths and writes remain after ablation?
11. Can `rmt_storage`, `tftp_server`, shim, and holder lose root and all
    unnecessary capabilities?
12. What measured process, memory, wakeup, write-amplification, and recovery
    budgets make Option C smaller than Option B in practice?

## Authority

This proposal is an H0 architecture and experiment specification only. It
creates no candidate identity, manifest, artifact, qualification, approval,
provisioning capability, or live authority. It grants no device contact, D0,
D1, F1, handoff, reboot, flash, UFS mutation, property/credential write,
SD removal, or cross-target authority.
