# A90 WLAN Vendor And Property Ablation Proposal

Date: 2026-08-15
Target: operator-owned Samsung Galaxy A90 5G only
Tier: H0, host-only design
Status: `H0_WP2_2_STATIC_POLICY_CORPUS_COMPLETE_NO_CANDIDATE_AUTHORITY`

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

This unit is not a candidate and not a rootfs change. `WP-H0-1` has frozen the
current source graph, and `WP-H0-2` now freezes the H0 one-factor state machine
and result vocabulary. The evidence program has four outputs:

1. one mechanically generated, duplicate-rejecting component manifest;
2. a static ban on global SELinux policy/load/enforce writes;
3. an exact property-observation contract with only two acceptable terminals;
4. a generated one-factor ablation and measurement specification reusable by
   both ownership topologies.

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
| `E13` | archived V241/V1692 public reports | One historical `cnss-daemon` byte identity, selected linker examples, and static control-flow/property observations exist; their exact H24 applicability remains unproved. |
| `E14` | archived V242/V249 public reports | The historical launcher/runtime inventory separates identity, linker/APEX, property, SELinux, QRTR, and diag gaps; it did not start the daemon. |
| `E15` | archived V2033 public report | Historical `tftp_server` evidence names a `wlanmdsp.mbn` read path and proves only request/open/OACK, not a complete transfer or current H24 dependency. |
| `E16` | archived V2117 public report | Android-observed `rmt_storage`/`tftp_server` identities differ from H24's selected root-mode path and therefore cannot be silently inherited by a capsule. |

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

For the frozen H24 selection, that topology owner is exactly
`/bin/a90_android_execns_probe`, launched directly (the supervisor wrapper is
compiled off) with the service-object-visible mode, result
`/cache/native-init-wifi-test-boot-v2812-helper.result`, timeout `120`, the SD
property root, `dev-null`, service-default SELinux contexts, copied real linker
and APEX configuration, the four selected allow flags, and persistent-handoff
ready path `/cache/native-init-wifi-test-boot-v2812.ready`. Its environment is
exactly the source-declared `PATH`, `HOME=/`, and `TERM=vt100`; the run contract
uses `setsid`, process-group cleanup, no runtime timeout, and a 1000 ms stop
timeout. The machine-readable inventory records the complete selected argv and
environment. The shim and holder have no external executable/argv: each is a
forked helper body whose exact selected boolean predicate is recorded instead.

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

### WP-H0-1 machine-readable boundary

The deterministic inventory is
[`a90-h24-wlan-capsule-dependency-inventory-v1.json`](../inventory/a90-h24-wlan-capsule-dependency-inventory-v1.json).
It is generated by
`workspace/public/src/scripts/revalidation/a90_h24_wlan_capsule_inventory_v1.py`
from nine exact public source/report inputs. Its narrow parser reads the
selected `composite_child_init` branches directly; it never treats the
published order string as construction authority. It binds:

- all thirteen selected composite instances, eleven unique roles, the property
  shim, modem holder, and topology-owning helper;
- launch predicates, argv, current source-derived identity/capability state,
  lifetime, cleanup, and ownership plane for each instance;
- the hidden duplicate pair and the exact 13/11/16 counts;
- historical public observations without promoting them to current H24 facts;
- ten explicit runtime closure gates `H0D01` through `H0D10`.

This closes only the **frozen H24 selected-path public-source snapshot** of
`WP-H0-1`; overall `WP-H0-1` remains
`PARTIAL_RUNTIME_CLOSURE_BLOCKED`. The H24 manifest does not bind
exact bytes or a complete transitive dependency graph for all eleven opaque
roles. Public history supplies one old `cnss-daemon` hash, a few linker
examples, two property keys, a WLFW/QMI control-flow map, and selected RFS
paths, but those records are historical and incomplete. Therefore the exact
ELF/dlopen/config/property/Binder/QRTR-QMI/device/firmware-RFS/output/SD-free
closure remains `BLOCKED_UNPROVED`.

`WP-H0-2` **design** is now complete as H0 work in the generated
[`a90-h24-wlan-one-factor-ablation-design-v1.json`](../design/a90-h24-wlan-one-factor-ablation-design-v1.json).
It is not circularly gated on evidence that only its future observations and
ablations can produce. Before executing any observation or ablation, retire
that row's static prerequisites, prove the H0D10 public SD-free bootstrap
superset, independently review the instrumentation, and obtain separate live
authority. H0D10 has a second, later half: after the retained set is known,
freeze either property absence or the exact finite seed. Before any Option C
implementation, identity allocation, or promotion, retire all
`H0D01`-`H0D10` gates by their declared evidence classes. In particular,
property, Binder, QRTR/QMI, firmware/RFS, and output gates cannot be retired by
one offline generation. This unit neither reads private inputs nor authorizes
their collection or execution.

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
5. Namespace membership is never proof that a global or shared kernel object
   is contained. Each such object has one named scope and an independently
   proved deny, non-nameability rule, or sole mediated owner.
6. Property is either proved absent or one exact deterministic read-only seed;
   no third state exists.
7. The property write-ACK protocol is versioned separately from property read
   data, bounded, authenticated by local provenance, and not treated as a
   successful state mutation unless a consumer requires and verifies it.
8. One ablation changes one variable. Failure never becomes the baseline for
   the next removal.
9. A passing unit proves WCNSS/Root PD/WMI, bounded scan, association, DHCP,
   cleanup, recovery, and no forbidden capability exposure.
10. Remote SSH/workload code cannot name or control the privileged backend in
   either topology.
11. The same component/property contract can be launched by native PID 1 or a
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

### Global kernel-object containment rule

Namespace membership is never proof that a global or shared kernel object is
contained. The current evidence names three load-bearing examples rather than
treating them as exceptions:

- QRTR node, endpoint, and port registries are not keyed by the caller's
  network namespace on this tree. Remote service/workload code must retain the
  all-ABI `AF_QIPCRTR` deny, compat `socketcall` denial, and namespace-escape/
  namespace-clone denials as one non-relaxable invariant and receive no
  inherited QRTR FD; a separately trusted capsule QRTR role remains explicitly
  bounded.
- SELinux loaded policy and enforcing state are kernel-global here. A private
  mount namespace cannot make a read-write SELinuxFS bind or `load`/`enforce`
  write private, so those effects are zero.
- A mount namespace with shared PID visibility does not close ancestor
  `/proc/<pid>/{root,fd,ns}` magic links. The selected boundary requires a
  fresh nested PID namespace, its matching procfs, and proved ancestor-task
  non-nameability; path hiding is not a substitute.

An object whose actual scope or deny cannot be proved is `NO_GO`. This rule is
topology-neutral: it applies equally to the reduced native-supervisor path and
Option C. It neither grants a device read nor turns any namespace declaration
into H0D04/H0D10 retirement.

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
relaunch. A missing property access must be emitted as an explicit `MISSING`
event; READ `ERROR` or `DENIED` invalidates the terminal, and no missing/error
path may silently return a fabricated default.

`PROPERTY_FINITE_SEED_PROVED` requires one canonical finite set of key,
context, value, source, digest, lifetime, and reader. Unknown/duplicate keys,
extra files, wrong context, writable content, symlinks, hardlinks, truncated
records, wrong generation, and digest drift must fail closed.

The generated
[`WP2-4` schema](../schema/a90-h24-wlan-property-observation-schema-v1.json)
turns these requirements into two host-side terminal validators. It requires
the exact retained-role by phase Cartesian coverage, distinguishes READ,
WRITE, and ACK, rejects event loss/default fabrication/mixed runs, and requires
final `RESIDENT_HEALTHY` plus `PROVED` before either terminal can validate. The
result may not choose its own topology: the validator also consumes a
separately qualified exact generation binding, retained-role set, and
cold/persistent lifecycle partition, candidate seed-contract digest, plus the
exact event/byte caps. The
post-run trace digest is not misclassified as a pre-effect expectation. Phase
regression, an ACK from a different writer identity or phase, or a READ `ERROR`
or `DENIED` rejects the terminal. Observer failure is `NO_PROOF_OBSERVER`,
never property absence.

The same schema records the optional same-run cnss_utils effect observation.
The false-value row requires exactly one
`WLAN MAC address is not set, type 0`, zero type-1 absence lines, and exact
attribution to the bound driver initialization that produces working `wlan0`;
a debugfs absence read is corroboration only. The true-value row retains the
source-unique `getting MAC address from platform driver failed` signature. A
present MAC with working `wlan0` remains unresolved, and a read error is never
normalized to absence. The within-boot source invariant is non-reversion, not
set-once: debugfs can overwrite an existing value. This is an observation
shape for a future separately reviewed run, not a current D0 action; WP2-4
grants no D0 or live authority.

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
| `A6c` | Remove `per_mgr` only | provider/readiness diff declared in advance | one-factor result, never chained |
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

## WP-H0-2 One-Factor Design Boundary

The canonical H0 design is generated by
`workspace/public/src/scripts/revalidation/a90_h24_wlan_ablation_design_v1.py`
from the exact WP-H0-1 inventory. The generated JSON is the design authority
for role coverage, baseline formation, terminal names, metrics, and promotion
semantics. The accompanying
[state-machine diagram](../diagrams/wlan-vendor-property-ablation-state-machine.mmd)
is explanatory and grants no live transition.

### Corrected baseline formation

H24 is **not** an ablation baseline. It did not execute this helper route, its
graph has two duplicate manager instances, it can mutate global SELinux state,
and it consumes the forbidden SD property snapshot. `A1`, `A2`, and the bounded
observer/SD-free bootstrap part of `A3` are baseline corrections, not evidence
that any named role is unnecessary.

The duplicate correction has two unproved, mutually exclusive placements:

1. retain the early `servicemanager#1`/`hwservicemanager#1` pair and remove the
   provider-adjacent duplicate pair; or
2. retain the provider-adjacent `#2` pair and remove the early pair.

Each placement is a separate future baseline unit. All non-placement
components and bindings stay exact, but the candidate/configuration/control-
flow bytes that select placement are separately bound and necessarily differ.
Both variants require zero global SELinux mutation. The design does not guess
which one is correct. The first independently qualified variant with
`experimentProof=PROVED`, `deviceSafetyState=RESIDENT_HEALTHY`, and complete
functional, metric, cleanup, recovery, and native-health evidence becomes
`G0`. `BASELINE_HEALTHY` records controlled pre-effect safety only and never
admits `G0`. `NO_GO_ABLATION_BASELINE` requires exact `REFUTED` proof for both
separately bound variants; unresolved proof, pending final health, or parked
recovery is non-admitting but is not silently collapsed into `NO_GO`.
The generated aggregate table binds the two fixed, distinct variant IDs and
all sixteen normalized result pairs. Exactly one pair emits `NO_GO`: both are
`BASELINE_REJECTED`. A duplicate/same ID, unknown result, invalid attempt
order, or any `NOT_RUN`/non-admitting member cannot satisfy that terminal.
This aggregate is proof-sequence state, not execution authority. One rejected
variant only names the other as the next possible proof subject. The other
variant cannot even enter fresh qualification until the rejected result's
independent safety axis is `RESIDENT_HEALTHY`; `BASELINE_HEALTHY` leaves final
health pending, and `RECOVERY_REQUIRED` remains `RECOVERY_PARKED`. After that
gate, independent review, fresh binding, and separate authority are still
required before any `UNIT_PREPARED` transition.

### SD-free bootstrap and final property terminal

Before any future baseline or ablation execution, H0D10 requires
`SD_FREE_PUBLIC_BOOTSTRAP_SUPERSET_PROVED`. The superset may be derived only
from exact public binaries, public defaults/configuration, and reviewed
deterministic generators. It may not read, copy, relocate, or bless the private
whole property snapshot. Every key, context, value source, generator byte,
file identity, digest, and read-only lifetime is bound. If a required input
cannot be obtained under this rule, baseline formation is `NO_GO`.

The bootstrap superset is not production-minimality proof. One-factor evidence
must later close H0D10 with exactly one of `PROPERTY_ABSENT_PROVED` or
`PROPERTY_FINITE_SEED_PROVED` for the retained set. A temporary SD-backed
diagnostic is not selected here; it would require a separate design, identity,
review, and live authority.

### Generation and one-factor rule

Every role-removal unit derives from one exact healthy `G(n)` and changes
exactly one construction role. Executable/input generations, identity,
capability, FD, namespace, cgroup, scheduler, property/IPC, firmware/RFS,
observer, budget, target, candidate, rollback, and recovery bindings otherwise
remain exact. The topology-owning `wifi-helper` is not an ablation variable;
its replacement belongs to later Option B or C integration.

`REMOVAL_SUPPORTED_FOR_GENERATION` may propose `G(n+1)` only after a fresh full
baseline qualification of the exact new bytes. `BASELINE_REJECTED`,
`REMOVAL_REFUTED_FOR_GENERATION`, `NO_PROOF_OBSERVER`, and `RECOVERY_PARKED` never become
a baseline, never chain another removal, and never justify a global statement
that a role is hardware-essential or unnecessary. Multi-removal batch
promotion is forbidden.

### Future durable execution semantics

This H0 document has zero reachable live transitions. A future unit requires
row-specific static prerequisites, a measured baseline budget receipt, an
independent execution review, and separate current authority. Its future
sequence is `UNIT_PREPARED -> EFFECT_INTENT_DURABLE ->
EFFECT_DISPATCHED_ONCE -> OBSERVING -> TERMINAL`. After durable effect intent,
the removal is never resent. Reconciliation performs observation, cleanup,
rollback, recovery, and reporting only. Missing, malformed, mixed-run, stale,
or ambiguous observation sets experiment proof to `NO_PROOF_OBSERVER`; cleanup,
rollback, or final-health uncertainty independently sets device safety to
`RECOVERY_REQUIRED` and workflow to `RECOVERY_PARKED`. The result carries
separate proof-subject, observer, experiment-evidence, attribution, and safety-
closure inputs and emits independent `experimentProof`, `deviceSafetyState`,
`workflowState`, and generation outcome. An exact device contradiction
attributable to the proof subject maps to contract `REFUTED` and wins even when
an observer defect also exists; the observer defect never downgrades it.
`REFUTED` may coexist with `RECOVERY_REQUIRED`/`RECOVERY_PARKED`, so recovery
uncertainty never erases the causal result.

#### WP2-5b kernel-log streaming prerequisite

`WP2-5b` must permanently close
`A90_WP2_5B_POSTHOC_KMSG_RETENTION_GAP` before it can qualify any unit whose
proof uses a kernel-log record. The matching source does not prove a fixed
128-KiB live ring: `LOG_BUF_SHIFT=17` is the minimum, CPU scaling computes a
source-default 1 MiB for eight possible CPUs absent an early override, and the
effective live `log_buf_len` remains unproved. No finite size proves that an
earlier record survives until a post-result snapshot.

The future observer must therefore open and `SEEK_END` the exact `/dev/kmsg`
reader before durable effect intent and before the bound driver init can start,
then publish `OBSERVER_ARMED` before allowing the effect. It continuously
drains complete structured records with a buffer of at least the source-bound
8192-byte maximum, preserves every record in the bounded epoch, and proves
strict sequence continuity through the exact driver outcome. `EPIPE`,
`POLLERR`, `EINVAL`, `EFAULT`, any sequence/format/boundary error, or
byte/count cap exhaustion is `NO_PROOF_OBSERVER`. The selected reader advances
its cursor before returning `EINVAL` or `EFAULT`, so either is a terminal
consumed-record fault: record it once and never retry or issue another read.
`/proc/kmsg` is forbidden as an automatic fallback
because it advances the global legacy syslog cursor; `dmesg`, post-result
snapshots, pstore/last-kmsg absence, and a larger boot log are not substitutes.

Open/identity/seek/parser/arm failure stops before intent and spends no ordinal.
Loss after intent never replays the effect and remains separate from cleanup,
recovery, and final resident health. The complete requirement and source
anchors are in
`docs/reports/A90_WLAN_WP2_5B_STREAMING_KMSG_OBSERVER_H0_2026-08-16.md`.
The permanent runtime invariant is `WP2_5B_KMSG_STREAM_COMPLETENESS`; the
temporary `WP2_5B_STREAMING_KMSG_OBSERVER_ABSENT` gate remains until the exact
runtime owner integration, durable final-name raw/journal publication writer,
integrated consumer,
qualification, hostile live execution tests, and independent execution review
exist. WP2-5b.1 H0 framing/consumer core alone does not retire it. WP2-5b.2 now fixes
the separate sole-reader, durable no-replace publication, receipt, and
crash-reconciliation design in
`docs/reports/A90_WLAN_WP2_5B_RUNTIME_OWNER_DURABLE_EVIDENCE_DESIGN_H0_2026-08-16.md`;
it remains H0 design. WP2-5b.3a separately implements only the effect-free
observer child source, generated scalar-pipe/header contract, exact-file exec
and exclusive-waiter cores, launch-readback validation core, dynamic-FD
post-open confinement, and injected host fault corpus at
`docs/reports/A90_WLAN_WP2_5B_OBSERVER_RUNTIME_COMPONENT_H0_2026-08-16.md`.
It exposes no effect/journal/receipt API, has no selected runtime profile or
parent integration, and does not retire the gate.

### Result and budget contract

Each result binds the exact target/resident/candidate/rollback/recovery,
generation and component-manifest digests, one removed role and delta digest,
boot/run nonce, durable journal chain, observer and budget receipt, original
stage/result/errno, separate cleanup result, terminal, and terminal scope.
Functional evidence covers firmware, Root PD, WMI, exact `wlan0` driver,
bounded scan, association, DHCP/route, and authenticated service when in scope.
Metrics cover latency, process/thread/FD/RSS/PSS, cgroup memory, CPU/wakeups,
I/O and cache publication, network quality/bounds, property/Binder/QRTR/QMI/
firmware-RFS use, residue, cleanup, and recovery.

No numeric pass threshold is invented here. Budgets must be measured from a
corrected `BASELINE_HEALTHY` result and independently bound before execution
qualification. Observer/parser failure and device functional failure remain
separate classifications; only complete same-run evidence can support a causal
removal terminal.

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

## WP2-2 Forbidden-Surface Policy And Execution Economy

`WP2-2` is complete only as a host-side static policy and negative corpus in
[`a90-h24-wlan-forbidden-surface-policy-v1.json`](../policy/a90-h24-wlan-forbidden-surface-policy-v1.json).
It is distinct from the already-complete `WP-H0-2` one-factor design. The
generator pins that design, the source-derived `WP-H0-1` inventory, the H24
manifest, the exact v724 launcher, and the exact helper source.

The policy rejects four H24-derived reintroduction classes before any future
corrected-baseline or Option C input can be considered:

1. more than one `servicemanager` or `hwservicemanager`, or different graph
   digests across construction, order, health, cleanup, and evidence;
2. a read-write bind of global SELinuxFS or a write to global `load` or
   `enforce`;
3. `/dev/binder`, `/dev/hwbinder`, `/dev/vndbinder`, their native-global
   backing, or the same global Binder rdevs hidden under a different path; and
4. `/mnt/sdext`, the historical cache relocation class, a whole property-area
   snapshot, or private-snapshot provenance renamed under another path.

The sixteen-case corpus also rejects an inherited/global property-service
socket and an unknown exception field. A fresh capsule-private binderfs or a
fresh capsule-private filesystem property-service socket is not classified as
globally forbidden, but it remains blocked on an exact `H0D05` or `H0D04`
proof respectively. Passing these static guards is therefore
`STATIC_REINTRODUCTION_GUARDS_PASS_H0_ONLY`, never execution eligibility.
No qualified extractor yet derives the declaration from complete linked
candidate/config/input bytes, so a hand-authored declaration is not evidence.

Each B0 placement accepts only its complete source-derived ordered
fourteen-instance graph. Removing any non-placement role while calling the
result B0 is rejected. A later `G_N_ROLE_ABLATION` declaration must instead
name the exact WP-H0-2 unit, removed role and instance, plus its parent manifest
digest; topology-integration declarations carry their own parent digest. Those
lineage shapes remain H0-only and explicitly pending until a qualified
byte-derived lineage consumer exists.

### Execution economy before any ordinal

The current plan contains a worst-path projection of thirty **logical future
units** under a one-unit/one-session interpretation:

| Class | Maximum logical units |
| --- | ---: |
| corrected baseline placement variants | 2 |
| exact-one-role removal units | 13 |
| fresh `G_N_PLUS_1` baseline requalifications after every supported removal | 13 |
| mutually exclusive property-terminal attempts | 2 |
| **one-to-one serial projection** | **30** |

The projection formula is `2 + 13 + 13 + 2 = 30`.

This `WP2-2` unit is H0 and consumes zero device ordinals. The projection is
for a separately designed, reviewed, budgeted, and authorized future program.

They are serial: a supported removal changes the generation, and another
removal cannot start until those exact bytes and bindings become a fresh
healthy baseline. Thirty is not yet a proved attended-session count or an
ordinal budget. `WP2-5b` may require more than one attended session per logical
unit; it must derive the exact session/ordinal budget, and the operator must
accept it, before execution qualification. Performance pass budgets remain a
different unset quantity derived from measured corrected `G0`.

The program yields an `ORDER_CONDITIONED_REDUCED_GENERATION_ONLY`, not a
global minimum. Earlier refuted removals are not retested after later supported
removals, so non-monotonic interaction means even terminal one-minimality is
unproved without a separate retest sweep. Such a sweep is not included in the
thirty-unit projection. Stopping early preserves only scoped results already
closed for their exact generation: corrected-`G0` feasibility first,
`cnss_diag` next, then manager/provider, QRTR/PD/RFS, CNSS/holder/shim, and
finally one property terminal. It never grants a global necessity claim or
Option C eligibility.

## WP2-3 Dependency-Surface Inventory Boundary

`WP2-3` is complete only as the generated H0 requirement and evidence-state
inventory in
[`a90-h24-wlan-dependency-surface-inventory-v1.json`](../inventory/a90-h24-wlan-dependency-surface-inventory-v1.json).
Its generator pins the WP-H0-1 component inventory, WP-H0-2 design, WP2-2
policy, H24 manifest/helper/launcher, and six historical public reports. It
does not read a device, private input, or compiled payload.

The inventory contains fourteen role records: eleven opaque external ELF
roles, two in-process helper bodies, and the topology-owning helper ELF. Every
record contains all ten dependency surfaces mapped to `H0D01-H0D10`, for 140
explicit slots. Source-selected executable path, argv, predicate, ownership
plane, and selected launch identity are kept separate from complete dependency
proof.

The decisive result is negative: current H24 exact opaque-ELF bindings remain
**zero**. No current size, SHA-256, ELF class/interpreter, `DT_NEEDED`, or
recursive library closure is invented. The one historical `cnss-daemon`
95112-byte/SHA-256 observation, its historical linker list, two property keys,
and WLFW control-flow evidence remain
`HISTORICAL_ONLY_H24_APPLICABILITY_UNPROVED`; they do not fill the current H24
artifact slot. Historical Android identities for `rmt_storage` and
`tftp_server` conflict with the selected H24 root launch and remain explicit
unresolved conflicts.

Known selected-route facts are equally narrow. The property shim names the
bounded `/dev/socket/property_service` ACK surface but proves no read seed; the
modem holder names `/dev/subsys_modem`; selected manager roles identify the
native-global Binder class already rejected by WP2-2; and the helper still
names the forbidden private SD property root. Historical `/dev/diag`, QRTR/QMI,
and WLANMDSP/RFS observations remain historical or incomplete rather than
causal current-H24 edges.

Ten negative mutations reject missing/duplicate roles, a missing dependency
slot, promotion of historical bytes into current H24, gate retirement,
authority enablement, erased identity conflict, false completion, unknown fact
state, and an extra top-level field. Passing this validator grants no
dependency-retirement credit. `H0D01-H0D10` all remain `UNPROVED`; the future
byte-derived consumer and execution implementation are absent.

`WP2-4` has now generated a property observation schema from the explicit
unproved property slots in H0. It may not treat this inventory or that schema
as a property read set, exact ELF closure, SD-free bootstrap, candidate,
runtime observation, or live authority.

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

- `WP2-1`: source-parsed component graph, exact frozen-path auxiliary launch
  contracts, and 13/11 mutation regression fixture — selected-path snapshot
  complete; overall runtime closure blocked by `H0D01-H0D10`;
- `WP2-2`: generated global SELinux/Binder/SD-path rejection policy,
  sixteen-case negative corpus, and serial execution-economy projection —
  complete as H0 static preparation only; no byte-derived future consumer,
  dependency-gate retirement, or execution authority;
- `WP2-3`: generated fourteen-role/140-slot binary, dynamic-dispatch,
  config, property, Binder, QRTR/QMI, device, firmware/RFS, output, SD-free,
  and identity evidence-state inventory with ten negative mutations — complete
  only as H0 requirements/known-facts/conflicts; current exact opaque-ELF
  bindings remain zero and every dependency gate remains unproved;
- `WP2-4`: generated property read/write observation schema, externally
  qualified exact-generation/role binding, two terminal validators, total
  same-run cnss_utils MAC-effect decision table with a proof-bearing type-0
  getter signature for the false row, and
  global-kernel-object containment rule — complete as H0 contract only at
  `schema/a90-h24-wlan-property-observation-schema-v1.json`; runtime observer,
  byte-derived consumer, qualification, H0D04/H0D10 retirement, and live
  authority remain absent;
- `WP2-5a`: H0 one-factor ablation design generator, baseline state machine,
  terminal vocabulary, and conceptual durable result schema — complete;
- `WP2-5b.1`: generated raw-trace contract/header, C framing encoder core,
  strict sequence/signature consumer, WP2-4 result binder, and H0 no-replay
  journal-prefix validator — complete only as host code; it opens no device,
  writes no durable journal, returns no dispatch permission, and grants no
  authority;
- `WP2-5b.3a`: effect-free observer source and generated pipe/header contract,
  exact-file exec and waiter cores, launch-readback validation core, dynamic-FD post-open
  confinement, and syscall-injected host corpus — complete only as an H0
  component; durable final-name publication/storage writer and parser, receipts,
  parent integration, measured profile,
  target qualification, and authority remain absent;
- `WP2-5b`: runtime execution implementation, journal/observer encoders with
  durable publication, receipts, parent integration, qualification, and live
  result validator — incomplete and unauthorized; any future version must
  satisfy `WP2_5B_KMSG_STREAM_COMPLETENESS` and may not use a post-result log
  snapshot or `/proc/kmsg` fallback for proof;
- `WP2-6`: common metric/benchmark collector and failure attribution;
- `WP2-7`: reduced-native launch/cleanup integration;
- `WP2-8`: clean Debian capsule feasibility implementation;
- `WP2-9`: independent security/execution review and topology decision.

`WP2-1`, `WP2-2`, `WP2-3`, `WP2-4`, `WP2-5a`, `WP2-5b.1`, and WP2-5b.3a are complete only
at their stated H0 boundaries. `WP2-4`, WP2-5b.1, and WP2-5b.3a remain host preparation.
Runtime `WP2-5b` and every later live package require their own implementation,
review, and authority and must not be inferred from this proposal.

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
