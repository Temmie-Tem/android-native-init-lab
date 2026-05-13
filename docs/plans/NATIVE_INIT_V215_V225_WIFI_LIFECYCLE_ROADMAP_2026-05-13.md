# v215-v225 Roadmap: ICNSS/CNSS Lifecycle to Controlled Wi-Fi Bring-Up

## Summary

v214 stopped at `icnss-rebind-failed`. The safe conclusion is that generic
platform-driver sysfs `unbind`/`bind` is not a valid ICNSS lifecycle control
method on this kernel. v215-v225 therefore shift from direct reprobe attempts to
evidence-driven lifecycle reconstruction.

For a shorter version-by-version execution view, see
`docs/plans/NATIVE_INIT_V215_V225_WIFI_VERSION_MASTER_PLAN_2026-05-13.md`.

The roadmap goal is to reach a first controlled Wi-Fi scan/connect without
guessing Android's hidden ICNSS/CNSS ordering. Until the lifecycle is understood,
native init must keep active Wi-Fi bring-up blocked.

- latest native runtime used for Wi-Fi evidence: `A90 Linux init 0.9.59 (v159)`
- blocking result: v214 `SAFETY STOP`, `icnss-rebind-failed`
- current known-good low-risk operation: read-only inventory, temporary vendor
  `ro,noload` mount, temporary `firmware_class.path` apply/readback/rollback
- forbidden until explicitly opened by later gate: Wi-Fi scan/connect, rfkill
  writes, WLAN link-up, generic ICNSS unbind/bind, daemon/HAL/supplicant start

## Reference Notes

- Linux firmware lookup can be redirected with the runtime
  `firmware_class.path` sysfs parameter, but this only solves file lookup. It
  does not solve ICNSS/CNSS power, QMI, PDR/SSR, or service ordering:
  <https://docs.kernel.org/driver-api/firmware/fw_search_path.html>
- The Linux driver model treats driver `probe()`/`remove()` as real lifecycle
  callbacks. v214 showed that forcing this path through sysfs can leave ICNSS
  unbound until reboot:
  <https://docs.kernel.org/6.7/driver-api/driver-model/driver.html>
- Android init starts services through service definitions, classes, property
  triggers, and `ctl.*` commands. Native bring-up must therefore model service
  environment and ordering, not just execute one binary:
  <https://chromium.googlesource.com/aosp/platform/system/core/+/master/init/README.md>
- Qualcomm ICNSS kernel sources show recovery, PDR/SSR, service-location,
  debugfs/sysfs, firmware service, and driver-registration concepts that need to
  be mapped before active Wi-Fi work:
  <https://android.googlesource.com/kernel/msm/+/c9760d512dc5a7d452676a4cc97cfcb683809c19/drivers/soc/qcom/icnss.c>
- Community bring-up notes for WCN399x/ICNSS devices often point at
  `cnss-daemon`, but that is only a lead. It must not be copied into native init
  as a blind start command:
  <https://gitlab.com/postmarketOS/pmaports/-/issues/494>

## Current Evidence Chain

- v203: native Wi-Fi baseline still blocked; no WLAN netdev/rfkill/wiphy.
- v204: Android/TWRP baseline confirms Android can expose WLAN/rfkill/sysfs.
- v205: native read-only ICNSS/nl80211 probe confirms ICNSS node exists but
  WLAN objects are absent.
- v206: Android ICNSS/CNSS map captured service/init/firmware/interface hints.
- v207: native preflight confirms active bring-up remains blocked.
- v208-v210: vendor block and Wi-Fi/CNSS assets can be mounted/read
  temporarily.
- v211-v212: `/mnt/vendor/firmware` is the preferred temporary firmware path
  and can be applied/read back/rolled back safely.
- v213: read-only ICNSS baseline and path-only firmware path flow passed.
- v214: ICNSS unbind passed, bind failed with `Driver is already initialized`
  and `probe ... failed with error -17`; reboot restored ICNSS bound state.
- v215: ICNSS/CNSS lifecycle collector passed with `lifecycle-map-ready`.
- v216: Android service replay model passed with `replay-model-ready`.
- v217: ICNSS debug/recovery inventory passed with `state-only-inventory`.
- v218: CNSS daemon dry-run feasibility passed with `daemon-dryrun-partial`.
- v219: native Android-env shim planning passed with `shim-plan-partial`.
- v220: lifecycle-aware bring-up preflight gate v2 passed with `no-go`.

## Current Execution Status

This roadmap is now in the post-v220 phase.

- completed:
  - v215 `ICNSS/CNSS Lifecycle Research`
  - v216 `Android Service Replay Model`
  - v217 `ICNSS Debug / Recovery Inventory`
  - v218 `CNSS Daemon Dry-Run Feasibility`
  - v219 `Native Android-Env Shim Plan`
  - v220 `Wi-Fi Bring-Up Preflight Gate v2`
- next execution item:
  - v221 `Host Vendor ELF / Library Evidence Closure`
- still blocked:
  - `cnss-daemon` and `cnss_diag` execution
  - Wi-Fi HAL execution
  - supplicant/hostapd execution
  - rfkill writes, link-up, scan, connect
- current highest-risk unknown:
  - whether host ELF/library evidence plus reboot-only recovery/security policy
    can justify any later temporary-mutating CNSS experiment

## Safety Policy

Every version in this roadmap must state one of three modes:

1. `read-only`
   - no sysfs writes except harmless command output files on host
   - no daemon start
   - no rfkill/link/scan/connect
2. `temporary-mutating`
   - explicit opt-in
   - rollback evidence required
   - no persistence
   - no active Wi-Fi connection
3. `active-network`
   - only allowed after all prior gates pass
   - scoped to scan-only first, then controlled test AP
   - requires exposure/security review before use

v215-v220 should remain `read-only` or tightly bounded `temporary-mutating`.
`active-network` starts no earlier than v223.

## Phase Map

### Phase A. Lifecycle Evidence and Replay Model

Versions: v215-v217

Purpose: explain Android's ICNSS/CNSS service lifecycle and find read-only
driver-specific state/recovery evidence before starting any daemon.

- v215 collects lifecycle evidence and kernel/source hints.
- v216 converts Android init/service evidence into a replay model.
- v217 inventories ICNSS debug/recovery controls and classifies risk.

Exit gate:

- service graph exists
- ICNSS state/recovery surface is mapped
- dangerous controls are explicitly denied
- next step can reason about CNSS daemon dry-run without guessing

### Phase B. Native Replay Feasibility

Versions: v218-v220

Purpose: decide whether native init can safely emulate enough Android runtime
environment for CNSS/Wi-Fi experiments.

- v218 checks `cnss-daemon` dependency feasibility without executing it.
- v219 designs a minimal Android-env shim and rollback policy.
- v220 upgrades the Wi-Fi preflight gate with lifecycle/service evidence.

Exit gate:

- dry-run dependencies are known
- temporary mounts/properties/sockets are scoped
- `wififeas gate` can produce a defensible `go-scan-prep` or `no-go`

### Phase C. Controlled State Transition

Versions: v221-v223

Purpose: move from read-only evidence to the smallest reversible kernel state
change, then scan-only Wi-Fi if WLAN objects appear safely.

- v221 starts the smallest CNSS-related component under strict timeout.
- v222 inspects WLAN/rfkill/nl80211 state passively if objects appear.
- v223 performs first scan-only test only after prior gates pass.

Exit gate:

- serial/NCM fallback remains available
- health/thermal/longsoak monitoring is active
- scan-only succeeds or fails with enough evidence to stop safely

### Phase D. Pre-Connect Security and Test AP Connect

Versions: v224-v225

Purpose: avoid turning a local lab kernel experiment into an exposed root
network target.

- v224 reviews credential handling, listener binding, firewall/exposure, and
  evidence redaction.
- v225 attempts first controlled test-AP connect only if v224 approves it.

Exit gate:

- test AP is isolated and disposable
- root control services remain bound to intended channels
- connect/disconnect produces clean rollback evidence

## Version Roadmap

### v215. ICNSS/CNSS Lifecycle Research

Mode: `read-only`

Goal: explain why generic ICNSS sysfs bind fails and identify the driver-specific
lifecycle path Android uses.

Planned work:

- collect Android, TWRP, and native dmesg around ICNSS/CNSS/WLAN boot
- parse vendor init `.rc` service ordering for `cnss-daemon`, `cnss_diag`,
  Wi-Fi HAL, `wificond`, supplicant, and related property triggers
- compare Android `init.svc.*` service state with native missing state
- inspect ICNSS sysfs/debugfs/ramdump/recovery nodes read-only
- search source references for `Driver is already initialized`, PDR/SSR,
  service-location, firmware service, and CNSS daemon interaction

Deliverables:

- `docs/plans/NATIVE_INIT_V215_ICNSS_CNSS_LIFECYCLE_RESEARCH_PLAN_2026-05-13.md`
- `docs/reports/NATIVE_INIT_V215_ICNSS_CNSS_LIFECYCLE_RESEARCH_2026-05-13.md`
- host collector candidate:
  `scripts/revalidation/wifi_icnss_lifecycle_collect.py`

Decision:

- `lifecycle-map-ready`: enough ordering/control evidence to model next step
- `android-only-required`: native cannot proceed without Android service layer
- `manual-review-required`: evidence conflicts or is insufficient

Status:

- done
- result: `lifecycle-map-ready`
- report:
  `docs/reports/NATIVE_INIT_V215_ICNSS_CNSS_LIFECYCLE_RESEARCH_2026-05-13.md`

### v216. Android Service Replay Model

Mode: `read-only`

Goal: convert Android service/init/property evidence into a native replay model
without starting services.

Planned work:

- build a dependency graph from vendor/system init rc files
- classify required mounts, binaries, users/groups, capabilities, sockets,
  properties, and libraries
- identify which parts native init already provides and which are missing
- model minimal service start order for CNSS/Wi-Fi without executing it

Deliverables:

- service graph JSON/Markdown under `tmp/wifi/v216-*`
- report with `required`, `available`, `missing`, and `unsafe` sections

Decision:

- `replay-model-ready`: enough dependencies are mapped for dry-run feasibility
- `missing-android-runtime`: property/socket/SELinux/framework dependency too
  large for native init

Status:

- done
- result: `replay-model-ready`
- report:
  `docs/reports/NATIVE_INIT_V216_ANDROID_SERVICE_REPLAY_MODEL_2026-05-13.md`
- important blockers preserved:
  - `cnss-daemon` and `cnss_diag` need ICNSS/CNSS recovery model first
  - Wi-Fi HAL services need capability/runtime policy review
  - `wpa_supplicant` and `hostapd` remain disabled until scan/connect gates

### v217. ICNSS Debug / Recovery Inventory

Mode: `read-only`

Goal: find driver-specific recovery controls that are safer than generic
sysfs unbind/bind.

Planned work:

- inventory ICNSS debugfs/sysfs files, permissions, and visible state names
- inspect ramdump, recovery, rejuvenate, PDR/SSR, firmware service, and test
  mode indicators without writing
- map which controls are read-only, write-only dangerous, or unknown
- correlate names with Android kernel ICNSS source references

Deliverables:

- `a90_icnssctl status --verbose` or host-side read-only collector extension
- risk matrix for every discovered ICNSS/CNSS control

Decision:

- `safe-control-candidate`: a non-destructive or documented recovery path exists
- `no-safe-control`: reboot remains the only known recovery from broken ICNSS
  state

Status:

- done
- result: `state-only-inventory`
- report:
  `docs/reports/NATIVE_INIT_V217_ICNSS_DEBUG_RECOVERY_INVENTORY_2026-05-13.md`
- important blockers preserved:
  - generic ICNSS `bind`/`unbind` remains denied
  - `driver_override` remains denied
  - reboot remains the only proven recovery from broken ICNSS state

### v218. CNSS Daemon Dry-Run Feasibility

Mode: `read-only`

Goal: determine whether `/vendor/bin/cnss-daemon` can even start in native init
without actually starting it.

Planned work:

- inspect ELF interpreter, shared libraries, config files, firmware paths, and
  device nodes required by CNSS daemon
- compare Android environment variables, mounts, permissions, properties, and
  sockets with native init
- capture linker dependency output from host-side tools when possible
- forbid real daemon execution in this version

Deliverables:

- dry-run feasibility report
- dependency list for a minimal native Android-env shim

Decision:

- `daemon-dryrun-ready`: enough dependencies are present or shim-able
- `daemon-native-blocked`: missing Android runtime pieces block safe execution

Status:

- done
- result: `daemon-dryrun-partial`
- report:
  `docs/reports/NATIVE_INIT_V218_CNSS_DAEMON_DRYRUN_FEASIBILITY_2026-05-13.md`
- important blockers preserved:
  - daemon execution remains denied
  - ELF/library inspection is incomplete without a host-visible vendor root
  - reboot remains the only proven ICNSS recovery path

### v219. Native Android-Env Shim Plan

Mode: `read-only` planning plus optional harmless file/mount checks

Goal: design the minimum native environment needed for CNSS/Wi-Fi service
experiments.

Planned work:

- specify temporary `/vendor`, `/system`, `/odm`, `/product` visibility
- define property stub policy, log output policy, and socket/device-node policy
- define rollback for any temporary mount or helper state
- define host evidence bundle requirements before and after service experiments

Deliverables:

- shim design document
- explicit allow/deny list for environment emulation

Decision:

- `shim-plan-ready`
- `shim-too-wide`: required Android compatibility layer is too large or risky

Status:

- done
- result: `shim-plan-partial`
- report:
  `docs/reports/NATIVE_INIT_V219_NATIVE_ANDROID_ENV_SHIM_2026-05-13.md`
- important blockers preserved:
  - daemon execution remains denied
  - Android property service recreation remains denied
  - QMI/PDR/SSR writes remain denied
  - host ELF/library evidence is still incomplete

### v220. Wi-Fi Bring-Up Preflight Gate v2

Mode: `read-only`

Goal: update `wififeas`/host gate so it blocks or allows active work based on
the new lifecycle evidence, not only static inventory.

Gate requirements:

- ICNSS bound and healthy
- firmware path policy available and rollback-tested
- vendor firmware assets visible
- lifecycle model available
- no unresolved dangerous write-only recovery dependency
- controlled recovery path known or reboot recovery accepted explicitly
- security exposure policy reviewed

Deliverables:

- `wififeas gate` output extended with lifecycle fields
- host summary including `go/no-go` and missing prerequisites

Decision:

- `go-scan-prep`: scan-only experiment can be planned
- `no-go`: active Wi-Fi remains blocked

Status:

- done
- result: `no-go`
- report:
  `docs/reports/NATIVE_INIT_V220_WIFI_PREFLIGHT_GATE_V2_2026-05-13.md`
- gate counts: `pass=3`, `warn=1`, `fail=0`, `blocked=3`
- blocked: `icnss_recovery`, `shim_policy`, `security_exposure`
- warning: `daemon_dryrun`

Interpretation:

- active Wi-Fi remains blocked
- v221 must be prerequisite closure, not controlled CNSS start
- required v221 focus: host vendor ELF/library evidence for `cnss-daemon` and
  `cnss_diag`

### v221. Host Vendor ELF / Library Evidence Closure

Mode: `read-only`

Goal: close the v218 evidence gap by inspecting `cnss-daemon` and `cnss_diag`
ELF/interpreter/DT_NEEDED/config/library path requirements from host-visible
vendor evidence.

Reason:

- v220 returned `no-go`
- controlled CNSS start is not approved
- daemon execution requires better binary/library evidence before any opt-in
  mutating plan

Planned work:

- locate or reconstruct a host-visible vendor root from existing v209-v210
  evidence
- inspect `cnss-daemon` and `cnss_diag` ELF interpreter and `DT_NEEDED`
  libraries
- map required config, firmware, device node, group, and capability
  dependencies
- keep all daemon execution blocked

Forbidden:

- daemon execution
- Wi-Fi scan/connect
- rfkill write or link-up
- persistent service enablement

Decision:

- `elf-evidence-ready`: enough ELF/library evidence exists for later recovery
  and shim policy review
- `daemon-native-blocked`: binary/library/runtime dependency remains too wide
  or incomplete

### v222. Recovery / Rollback Policy Hardening

Mode: `read-only`

Goal: decide whether reboot-only ICNSS recovery can be accepted for any later
temporary-mutating CNSS experiment.

Planned work:

- define ICNSS broken-state detection checklist
- define stop/reboot handoff policy
- define required pre/post evidence bundle
- keep generic ICNSS bind/unbind denied

Decision:

- `reboot-recovery-accepted`
- `active-mutation-blocked`

### v223. Android-Env Shim Dry-Run Materialization

Mode: `temporary-mutating`, no daemon start

Goal: materialize only the reversible shim-required pieces from v219 and prove
cleanup/rollback without executing CNSS services.

Allowed:

- temporary read-only vendor/system path aliases
- private evidence/log output directories
- static property evidence files, not a real property service

Forbidden:

- daemon execution
- Android property mutation service
- QMI/PDR/SSR writes
- Wi-Fi scan/connect

Decision:

- `shim-materialized`
- `shim-too-wide`

### v224. Wi-Fi Exposure / Credential Security Gate

Mode: `read-only`

Goal: review exposure and credential handling before any scan or connect
experiment can be approved.

Planned work:

- decide whether native Wi-Fi uses isolated test AP only
- define credential storage policy; no persistent plaintext secrets by default
- review NCM/tcpctl/rshell coexistence with Wi-Fi
- define firewall/bind/listener policy before Wi-Fi gives wider reachability
- define logging redaction for SSID/BSSID/PSK-sensitive artifacts

Decision:

- `connect-approved-test-only`
- `connect-blocked-security`

### v225. Preflight Gate v3 / Controlled CNSS Start Plan

Mode: `read-only`

Goal: re-run an integrated gate after v221-v224 prerequisite closure and decide
whether controlled CNSS start can be planned after v225.

Required preconditions:

- v221 ELF/library evidence is complete
- v222 recovery policy is accepted or blocks mutation
- v223 shim materialization is bounded and reversible
- v224 exposure/security gate passes

Planned work:

- integrate v221-v224 results into gate v3
- keep daemon start outside v225 unless a later explicit plan approves it
- produce go/no-go for controlled CNSS start

Decision:

- `cnss-start-plan-approved`
- `still-no-go`

## Cross-Version Acceptance

- No version may silently progress from read-only to mutating behavior.
- Every mutating version must have:
  - explicit opt-in flag
  - rollback evidence
  - post-run device health evidence
  - report with manifest/hash references
- Active Wi-Fi versions must additionally have:
  - security/exposure gate
  - credential policy
  - NCM/serial fallback validation
  - thermal/power monitoring

## Recommended Immediate Next Step

Start v221 as prerequisite closure. Do not execute `cnss-daemon`, `cnss_diag`,
Wi-Fi HAL, supplicant, or hostapd yet.

The next concrete deliverable should close the v218/v220 evidence gap by
inspecting host-visible vendor ELF/library requirements for:

- `cnss-daemon`
- `cnss_diag`
- their interpreter and `DT_NEEDED` library graph
- related config, firmware, device-node, group, and capability requirements

Only after v221-v224 close the remaining evidence, recovery, shim, and exposure
gaps can v225 decide whether controlled CNSS start is eligible for planning.
