# Working Context: A90 WLAN Vendor And Property Ablation

Date: 2026-08-15
Repository: `android-native-init-lab` (all paths below are repository-relative)
Baseline revision: `dd8d0d8a59f84419ec830e0798718dc14edbd3b7`; the exact
collection below was refrozen after adding the public historical dependency
evidence and correcting the prior portfolio's `WP-H0-1` status
Target: operator-owned Samsung Galaxy A90 5G only
Tier: H0, host-only source investigation and design

## Question

What is the smallest vendor WLAN compatibility backend that must remain alive
after Debian starts, and does that backend need an Android property area at
all?

This question is shared by both viable ownership topologies:

1. a reduced native supervisor with isolated Debian; and
2. a clean Debian PID 1 supervising a separately contained vendor capsule.

The answer cannot be inferred from process names. It must distinguish the
current implementation's liveness predicate from causal hardware necessity.

## Method And Contact Boundary

The primary pass read the common/A90 contracts, current goal, public WSTA and
incident reports, current H16/H24 manifests, the exact selected H24 native
source, the historical bring-up plan, and the two preceding H0 hardening
portfolios. It did not inspect any private artifact or execute any device or
transport code.

Primary-pass contact counters are: physical device `0`, target-bearing `/dev`
`0`, USB `0`, device network `0`, `workspace/private` read/list/stat `0`, live
command `0`, payload `0`, reboot `0`, and flash `0`. One overly broad public
repository search displayed one S22+ report path before this unit was frozen;
that file was excluded from the evidence collection and no claim depends on
it. S20+ contact is `0`. The independent A90-only source reviewer reported
device, `/dev`, USB, network, private, S22+, S20+, live-command, and write
counters all `0`.

Repository writes are limited to this H0 portfolio, its focused host test, the
security index entry, and corrections to the prior portfolio's inaccurate
“eleven children / known-sufficient” wording.

## Evidence Collection Identity

The collection digest is computed over the following files in the listed
order as `relative_path NUL size NUL sha256 NUL`:

`adc7127d7a7fe7960d28e26267f096c30ec56ddc649a3b3ed961c8d3e4a05368`

Artifact count: `24`. Source drift at analysis time: `none`.

| SHA256 | Bytes | Repository-relative path |
| --- | ---: | --- |
| `a90560db2985b588a1aa53c0a2078bb6d930865895167a5b71e5bba2acec076b` | 11157 | `AGENTS.md` |
| `9cf34ea25062c6280254b67e0a62de48f6b477de1ce6ab779aa532d38d066d5e` | 24893 | `GOAL_A90.md` |
| `ed9f51212db33bd822dc96ecf12feeda05ce255d088c402c4742851d173fad51` | 89405 | `docs/operations/targets/A90_TARGET_CONTRACT.md` |
| `edd64a434330f79a3b1ec542c12822e5b201362c212484c7b67d67b4ffbb61a9` | 97237 | `docs/operations/CAMPAIGN_LEDGER_A90.md` |
| `1c7984a85af3cb059244d7f3e7ed5b21516a60657bd947a275a4ed7e4faa5b71` | 4991 | `docs/reports/SERVER_DISTRO_WIFI_STA_UPSTREAM_WSTA18_CONTROL_PLANE_BLOCKED_2026-07-04.md` |
| `055359850d4141f360b0bed0e5cffe2f2f27bb0be4bc9e8ca7c0cbafbe1c256d` | 6149 | `docs/reports/SERVER_DISTRO_WIFI_STA_UPSTREAM_WSTA19_NATIVE_OWNED_CHROOT_WIFI_PASS_2026-07-04.md` |
| `5c4c669f058bb003519dc04813158d2e408901c05eb9354a7a082d728a56a01b` | 12667 | `docs/reports/A90_NATIVE_WIFI_OWNERSHIP_PERMANENCE_EVIDENCE_H0_2026-08-15.md` |
| `2591fdc1adf180b11907944710c0ddd3d18d146a749c73f0d6750cbfe72afa27` | 6642 | `docs/reports/A90_NATIVE_WIFI_SIDECAR_PROC_ROOT_EXPOSURE_HOST_INCIDENT_2026-08-13.md` |
| `f676937b298c41670af04703d72edd698dbb0b89bff0b67e1ed6f4a2c5170d93` | 3095 | `docs/reports/A90_H24_PERSISTENT_HUD_BOOTSTRAP_EINVAL_INCIDENT_2026-08-12.md` |
| `87d3cda80ba0acddece4a8553a70de04451fd15ae03695fe46e150310b15cc74` | 2585 | `docs/reports/A90_H16_PERSISTENT_DEBIAN_RETURN_OBSERVER_INCIDENT_2026-08-10.md` |
| `5f67ed8a163e05abb91b5d0bf5d7f3699ca4d63578d8bf487a883b6fec29bf9b` | 1136979 | `docs/plans/NATIVE_INIT_NEXT_WORK_2026-04-25.md` |
| `9c48c21e813f27681d60cfd5e4881b73e8c4544abe2bca02b4a2f37dac0860c6` | 79078 | `docs/plans/A90_HEADLESS_NATIVE_WIFI_ISOLATED_DEBIAN_DESIGN_2026-08-14.md` |
| `f732b1ff9ff48dfd97383ad14c2c1e75f5eea227c3d80c85cddab68300099d73` | 36328 | `docs/security/hardening/a90-debian-supervised-wlan-2026-08-15/proposals/debian-supervised-wlan.md` |
| `47148cf7ef35331af47ef74ed07ff74075c2cec474062b7c0782d13890229ffd` | 37200 | `docs/security/hardening/a90-sd-free-input-evidence-2026-08-15/proposals/typed-sd-free-input-evidence.md` |
| `09e3731a575447305a5b1995ed827484cf65390d73fe3dfb4dbaacb9ff83ab7a` | 12790 | `workspace/public/src/scripts/revalidation/a90_flat_builder/versions/phase3-minimal-h16/manifest.toml` |
| `40c26c5878db21737600bc29864db9123cc4650ec39d7f0d7395209c2df70a8f` | 7801 | `workspace/public/src/scripts/revalidation/a90_flat_builder/versions/phase3-minimal-h24/manifest.toml` |
| `4e68735fa2acc06fa4c101d8dbab6380d7785c4d9c7edfe47448ab26031b57e2` | 3253399 | `workspace/public/src/native-init/helpers/a90_android_execns_probe.c` |
| `2a6863c0fd5f1dc2559ccee45031e389c956d6e094d8602364fd1875b919128f` | 277766 | `workspace/public/src/native-init/v724/90_main.inc.c` |
| `0212b18b2f76a88247300a55f9c670b18de15f69a488c62f1167304b3de1ebc2` | 5118 | `docs/archive/legacy/reports/NATIVE_INIT_V241_VNDK_APEX_ALIAS_PROBE_2026-05-18.md` |
| `b6a61a6b259b4dd29606bc29ed3f788c7479b0289a32f8b6e4252e2422aa2821` | 3867 | `docs/archive/legacy/reports/NATIVE_INIT_V242_CNSS_RUNTIME_REQUIREMENT_INVENTORY_2026-05-18.md` |
| `07dac305ae652c451135606d62f69479af756c3958e5e5798574dc6c426f71f3` | 4050 | `docs/archive/legacy/reports/NATIVE_INIT_V249_CNSS_RUNTIME_GAP_CLASSIFIER_2026-05-19.md` |
| `345428d2284919776b67a3a88c40f9a4986002956a2f9d5488efe2c48dd033e3` | 3629 | `docs/archive/legacy/reports/NATIVE_INIT_V1692_CNSS_NONLOG_CONTROL_FLOW_2026-06-02.md` |
| `caad3e832038f28de2febd4b2dd0742f093ab0b035d4b1d6db59032e595e20d2` | 4757 | `docs/archive/legacy/reports/NATIVE_INIT_V2033_WLANMDSP_TFTP_TRANSFER_COMPLETION_GAP_2026-06-04.md` |
| `a3f7b5b81c9cf9861c1e7a039d6f0f4102726c71cca8585e1228194ab6c59914` | 4291 | `docs/archive/legacy/reports/NATIVE_INIT_V2117_DUAL_RFS_LEAF_ANDROID_IDENTITY_HANDOFF_2026-06-05.md` |

## Evidence Registry

| ID | Type | Evidence | Establishes |
| --- | --- | --- | --- |
| `E01` | observed experiment | WSTA18 | Removing native/vendor userspace left WLAN objects visible but firmware, Root PD, WMI, and scan failed. It is aggregate evidence, not an individual-service ablation. |
| `E02` | observed experiment | WSTA19 | Keeping the native control plane alive preserved scan while Debian Dropbear ran; association and DHCP were not tested there. |
| `E03` | observed source | H24 manifest and v724 mode selection | H24 selects persistent handoff, an SD property snapshot, and the service-object-visible trigger. |
| `E04` | observed source | H24 helper composition | The selected path creates thirteen composite entries representing eleven unique roles; two service-manager roles are duplicated. |
| `E05` | observed source | H24 persistent predicate | Every non-macloader composite entry is treated as required, including the duplicated entries. This is implementation policy, not causal necessity. |
| `E06` | observed source | H24 shim and holder | A property-service shim and modem holder add two helper-managed children; the helper makes the backend sixteen processes before station policy starts. |
| `E07` | observed source | property-root and shim code | The full binary property area is read-only bound; the shim only acknowledges a narrow write protocol and does not prove the property read set. |
| `E08` | observed source hazard | selected policy-load path | The selected route bind-mounts host SELinuxFS read-write, loads vendor policy globally, and best-effort writes permissive mode. |
| `E09` | historical route evidence | bring-up plan | Correct vendor Binder/peripheral-manager visibility produced route progress, but did not prove those services universally necessary. |
| `E10` | incident boundary | H24 D1 incident | H24 stopped at persistent HUD before Wi-Fi helper execution, so its exact thirteen-entry branch has no H24 live proof. |
| `E11` | architecture boundary | `/proc` incident and selected design | Either topology must prevent Debian workload code from naming vendor-side process/root/fd/ns capabilities. |
| `E12` | input boundary | SD-free portfolio | Property must end as proved absent or an exact deterministic finite seed; wholesale snapshot transplantation is rejected. |
| `E13` | authority evidence | common/A90 contract and goal | This is H0 only. H24 is installed, its D1 is consumed, and no successor identity or live authority exists. |
| `E14` | historical observed linker evidence | archived V241 | One historical `cnss-daemon` linker-list completed with a private VNDK v30 alias and named six example libraries; it is not a complete current-H24 ELF closure. |
| `E15` | historical runtime classification | archived V242/V249 | Historical identity, property, SELinux, QRTR, diag, path, and linker gaps were classified without starting `cnss-daemon`. |
| `E16` | historical binary/control-flow evidence | archived V1692 | One historical `cnss-daemon` byte identity, two property keys, and its WLFW start control-flow were recorded; applicability to the H24 executable bytes is unproved. |
| `E17` | historical RFS evidence | archived V2033 | `tftp_server` named a read-only `wlanmdsp.mbn` RFS path and reached request/open/OACK, not a complete transfer or current dependency proof. |
| `E18` | historical identity evidence | archived V2117 | Android-observed non-root `rmt_storage`/`tftp_server` identities differ from H24's selected root-mode source path. |

## Direct Anchors

| Claim | Frozen source anchor |
| --- | --- |
| Selected mode and SD property root | `workspace/public/src/scripts/revalidation/a90_flat_builder/versions/phase3-minimal-h24/manifest.toml:34`, `:64`, `:72`; `workspace/public/src/native-init/v724/90_main.inc.c:350-359` |
| First duplicated service-manager pair | `workspace/public/src/native-init/helpers/a90_android_execns_probe.c:58654-58666` |
| QRTR/PD/RFS entries and second service-manager trio | `workspace/public/src/native-init/helpers/a90_android_execns_probe.c:58674-58745` |
| Historical linker examples and VNDK alias | `docs/archive/legacy/reports/NATIVE_INIT_V241_VNDK_APEX_ALIAS_PROBE_2026-05-18.md` |
| Historical `cnss-daemon` hash, property keys, and WLFW flow | `docs/archive/legacy/reports/NATIVE_INIT_V1692_CNSS_NONLOG_CONTROL_FLOW_2026-06-02.md` |
| Historical RFS path and identity mismatch | `docs/archive/legacy/reports/NATIVE_INIT_V2033_WLANMDSP_TFTP_TRANSFER_COMPLETION_GAP_2026-06-04.md`; `docs/archive/legacy/reports/NATIVE_INIT_V2117_DUAL_RFS_LEAF_ANDROID_IDENTITY_HANDOFF_2026-06-05.md` |
| CNSS entries and actual spawn loop | `workspace/public/src/native-init/helpers/a90_android_execns_probe.c:58753-58769`, `:59215-59231` |
| Published order hides the duplicate pair | `workspace/public/src/native-init/helpers/a90_android_execns_probe.c:58857-58868` |
| All selected entries become liveness requirements | `workspace/public/src/native-init/helpers/a90_android_execns_probe.c:58048-58074` |
| Property shim selection | `workspace/public/src/native-init/helpers/a90_android_execns_probe.c:60957-60986` |
| Common composite fork/session/chroot/identity/exec path | `workspace/public/src/native-init/helpers/a90_android_execns_probe.c:43627-43856` |
| Exact UID/GID/group/capability routines | `workspace/public/src/native-init/helpers/a90_android_execns_probe.c:6630-7005`, `:7139-7175` |
| Composite process-group cleanup and postflight check | `workspace/public/src/native-init/helpers/a90_android_execns_probe.c:45424-45555` |
| Modem-holder start, readiness, and cleanup | `workspace/public/src/native-init/helpers/a90_android_execns_probe.c:29011-29266`, `:58077-58099`, `:59754-59767` |
| Property-shim protocol, lifetime, and cleanup | `workspace/public/src/native-init/helpers/a90_android_execns_probe.c:61126-61500` |
| Global SELinux bind/load/permissive attempt | `workspace/public/src/native-init/helpers/a90_android_execns_probe.c:4580-4612`, `:59150-59155`, `:63519-63605` |
| H24 stopped before Wi-Fi handoff | `docs/reports/A90_H24_PERSISTENT_HUD_BOOTSTRAP_EINVAL_INCIDENT_2026-08-12.md:10-26` |

## Observed, Inferred, Proposed

### Observed

- H24's selected source path has thirteen composite entries but eleven unique
  roles. `servicemanager` and `hwservicemanager` are each enqueued twice.
- The helper's published order lists only the unique roles, so logs can hide
  the difference between intended topology and executable topology.
- The persistent predicate requires every one of the thirteen entries to stay
  alive. The property shim and modem holder bring helper-managed children to
  fifteen; the helper makes sixteen processes before native autoconnect.
- H24 never executed that path live. Its consumed D1 stopped at the preceding
  HUD bootstrap.
- WSTA18 removed the backend as a group. It proves aggregate control-plane
  necessity but does not prove any named member individually required.
- The selected property shim acknowledges only a narrow set operation
  protocol. That protocol is not the property read dependency of the opaque
  vendor binaries.
- The selected route attempts global SELinux policy replacement and a
  permissive write. It is not a capsule-private security policy.

### Inferred

- Duplicate Binder context-manager instances are likely to conflict, but an
  actual conflict or exit is unproved because H24 did not reach the branch.
- `qrtr-ns`, `pd-mapper`, RFS services, `cnss-daemon`, and the current
  peripheral-manager route are plausible core/conditional components, but
  none has individual causal proof.
- `cnss_diag` is the highest-confidence diagnostic ablation candidate, but it
  is not yet proved unrelated.
- A full property snapshot is accumulated compatibility state. Neither
  `PROPERTY_ABSENT` nor a particular minimal seed is established by current
  evidence.

### Proposed

- Replace the hand-maintained child/order split with one generated, duplicate-
  rejecting component manifest that binds target, argv, UID/GID/groups,
  capabilities, SELinux expectation, FDs, cgroup, readiness, and cleanup.
- Reject every successor that can write SELinux policy/load/enforce, exposes
  global Binder devices, or depends on the SD property tree.
- Perform topology-neutral one-factor ablation. The exact same component and
  property contract must feed both a reduced native supervisor and a
  Debian-supervised capsule.
- Accept only one of two property terminals: proved zero property reads, or an
  exact finite deterministic read seed. The current write-ACK shim is a
  separate interface and cannot substitute for either proof.

## Current Component Classification

No individual role is proved hardware-essential, and no role is proved
unrelated. “Conditional retain” means only that the current route has positive
or plausible dependency evidence and should be removed later in the matrix.

| Role or surface | Actual H24 instances | Current implementation policy | Causal classification |
| --- | ---: | --- | --- |
| `servicemanager` | 2 | both required alive | unproved; duplicate pair is first correction |
| `hwservicemanager` | 2 | both required alive | unproved; duplicate pair is first correction |
| `vndservicemanager` | 1 | required alive/provider gate | conditional retain for current Binder route |
| `qrtr-ns` | 1 | required alive | conditional retain; individual necessity unproved |
| `pd-mapper` | 1 | required alive | conditional retain; individual necessity unproved |
| `rmt_storage` | 1 | required alive | conditional retain; root execution surface |
| `tftp_server` | 1 | required alive | conditional retain; root execution surface |
| `pm_proxy_helper` | 1 | required alive/provider gate | conditional retain for current provider route |
| `pm-service` / `per_mgr` | 1 | required alive/provider gate | conditional retain; historical route progress |
| `cnss_diag` | 1 | required alive | unproved; highest-priority diagnostic ablation |
| `cnss-daemon` | 1 | required alive | conditional retain; individual necessity unproved |
| property-service shim | 1 | required to start, later liveness weakly observed | write-compatibility surface; read-seed necessity unproved |
| modem holder | 1 | required alive and FD held | current-route dependency; minimum need unproved |
| native autoconnect | separate | dispatched after backend readiness | known station-policy path; Debian replacement unproved |

The exact launch predicate, argv, UID/GID/groups/caps (or explicit
`UNPROVED`), lifetime, cleanup, and row-specific anchors for all thirteen
composite entries plus the shim and holder are frozen in the proposal's
“Current-source launch inventory.” The selected source contains
`rmt_storage`, not a separately selected `rmtfs` process. Any relationship
between those names, and the exact QMI producer/consumer edges, remains
`UNPROVED`; it is not inferred from names or diagnostic strings.
The machine-readable snapshot additionally binds the topology owner's exact
H24 executable, selected argv/environment/run contract, and the shim/holder
selected boolean predicates. Those source contracts do not prove opaque
runtime necessity.

## Property Decision

Current verdict: `UNPROVED`.

The next design must not guess. It must end in exactly one state:

- `PROPERTY_ABSENT_PROVED`: every surviving binary runs under a trace-derived
  deny-by-default property boundary with zero successful property reads; or
- `PROPERTY_FINITE_SEED_PROVED`: every successful read maps to one canonical
  key/context/value in a deterministic, read-only, manifest-bound seed, with
  unknown, duplicate, writable, symlink, hardlink, and extra-file cases
  rejected.

The current whole snapshot, cache relocation of that snapshot, and the shim's
write acknowledgements are not acceptable substitutes.

## Authority Result

This investigation grants no candidate, artifact, qualification, D0, D1, F1,
handoff, reboot, flash, UFS mutation, property provisioning, credential
provisioning, or SD-removal authority. H24 remains installed and its consumed
D1 remains unreplayable.
