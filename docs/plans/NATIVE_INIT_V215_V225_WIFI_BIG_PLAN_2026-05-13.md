# v215-v225 Big Plan: Wi-Fi Bring-Up Prerequisite Closure

## Summary

This document is the high-level version-by-version plan for the current Wi-Fi
bring-up track. It intentionally stays above the per-version implementation
plans and reports.

The current direction is conservative:

- v215-v219 established read-only evidence, lifecycle maps, service replay, and
  shim planning.
- v220 produced `no-go`, so active Wi-Fi bring-up is blocked.
- v221 narrowed the main daemon feasibility gap to missing host-visible vendor
  root evidence.
- v222-v225 should close vendor evidence, recovery, shim, and exposure blockers
  before any controlled CNSS/Wi-Fi start plan is allowed.

This plan does **not** approve Wi-Fi scan, connect, rfkill writes, link-up,
`cnss-daemon`, `cnss_diag`, Wi-Fi HAL, `wificond`, `wpa_supplicant`, or
`hostapd` execution.

## Planning Layers

| Layer | Document | Role |
| --- | --- | --- |
| Big plan | `docs/plans/NATIVE_INIT_V215_V225_WIFI_BIG_PLAN_2026-05-13.md` | Version-level intent and gate order |
| Master plan | `docs/plans/NATIVE_INIT_V215_V225_WIFI_VERSION_MASTER_PLAN_2026-05-13.md` | Detailed branch logic and references |
| Lifecycle roadmap | `docs/plans/NATIVE_INIT_V215_V225_WIFI_LIFECYCLE_ROADMAP_2026-05-13.md` | Technical evidence chain and longer rationale |
| Per-version plans | `docs/plans/NATIVE_INIT_V21*_*.md`, `docs/plans/NATIVE_INIT_V22*_*.md` | Concrete implementation scope |
| Reports | `docs/reports/NATIVE_INIT_V21*_*.md`, `docs/reports/NATIVE_INIT_V22*_*.md` | Executed result and acceptance evidence |

## Global Rules

- Default mode is `read-only`.
- Any `temporary-mutating` step requires explicit opt-in, bounded timeout,
  rollback evidence, and a working rescue path.
- Active Wi-Fi operations are blocked until a later gate says otherwise.
- Generic ICNSS `unbind`/`bind`, `driver_override`, rfkill write, `ip link up`,
  scan, connect, DHCP, and credential handling stay forbidden in this track.
- Host evidence outputs must use private directories/files and no-follow writes.
- Serial/NCM rescue control must be recoverable before attempting any risky
  experiment.

## Current Status Table

| Version | Status | Decision | Meaning |
| --- | --- | --- | --- |
| v215 | PASS | `lifecycle-map-ready` | ICNSS/CNSS lifecycle evidence and Android/native delta mapped |
| v216 | PASS | `replay-model-ready` | Android Wi-Fi service graph and replay model documented |
| v217 | PASS | `state-only-inventory` | ICNSS debug/recovery controls classified read-only |
| v218 | PASS | `daemon-dryrun-partial` | CNSS daemon dry-run evidence partial; ELF/library gap remains |
| v219 | PASS | `shim-plan-partial` | Native Android-env shim matrix exists; blocked items remain |
| v220 | PASS | `no-go` | Lifecycle-aware gate blocks active Wi-Fi work |
| v221 | PASS | `vendor-root-required` | Host-visible vendor root is required for ELF/library closure |
| v222 | PASS | `export-source-required` | Export helper ready; source vendor root still required |
| v223 | PASS | `reboot-recovery-accepted` | Reboot-only recovery policy accepted for later opt-in planning |
| v224 | PASS | `shim-source-required` | Host-side shim dry-run artifacts ready; source vendor root still required |
| v225 | PLANNED | TBD | Exposure/security gate and gate v3 integration |

## Version-Level Plan

### v215. ICNSS/CNSS Lifecycle Research

Purpose: explain how Android brings up ICNSS/CNSS compared with native init.

Outcome:

- mode: `read-only`
- decision: `lifecycle-map-ready`
- report: `docs/reports/NATIVE_INIT_V215_ICNSS_CNSS_LIFECYCLE_RESEARCH_2026-05-13.md`

Resulting rule: native Wi-Fi bring-up is a lifecycle problem, not just a
firmware path problem.

### v216. Android Service Replay Model

Purpose: convert Android init service evidence into a replay model without
starting any daemon.

Outcome:

- mode: `read-only`
- decision: `replay-model-ready`
- report: `docs/reports/NATIVE_INIT_V216_ANDROID_SERVICE_REPLAY_MODEL_2026-05-13.md`

Resulting rule: `cnss-daemon`, `cnss_diag`, Wi-Fi HAL, `wificond`, supplicant,
and hostapd need ordered environment modeling before execution.

### v217. ICNSS Debug / Recovery Inventory

Purpose: classify ICNSS state and recovery controls after v214 generic rebind
failed.

Outcome:

- mode: `read-only`
- decision: `state-only-inventory`
- report: `docs/reports/NATIVE_INIT_V217_ICNSS_DEBUG_RECOVERY_INVENTORY_2026-05-13.md`

Resulting rule: reboot is the only proven recovery path; generic unbind/bind is
not accepted as a routine recovery primitive.

### v218. CNSS Daemon Dry-Run Feasibility

Purpose: evaluate daemon execution requirements without executing the daemons.

Outcome:

- mode: `read-only`
- decision: `daemon-dryrun-partial`
- report: `docs/reports/NATIVE_INIT_V218_CNSS_DAEMON_DRYRUN_FEASIBILITY_2026-05-13.md`

Remaining blocker: ELF interpreter and shared library closure needs a
host-visible vendor root.

### v219. Native Android-Env Shim Plan

Purpose: define the smallest native shim that could support CNSS/Wi-Fi services
without recreating Android broadly.

Outcome:

- mode: `read-only planning`
- decision: `shim-plan-partial`
- report: `docs/reports/NATIVE_INIT_V219_NATIVE_ANDROID_ENV_SHIM_2026-05-13.md`

Remaining blockers: property service, QMI/PDR/SSR writes, binder/HAL surfaces,
and credential/data paths remain denied or out of scope.

### v220. Wi-Fi Preflight Gate v2

Purpose: combine v215-v219 evidence and decide whether active Wi-Fi work can
start.

Outcome:

- mode: `read-only`
- decision: `no-go`
- report: `docs/reports/NATIVE_INIT_V220_WIFI_PREFLIGHT_GATE_V2_2026-05-13.md`
- blocked items: `icnss_recovery`, `shim_policy`, `security_exposure`

Resulting rule: v221-v225 must be blocker closure, not active daemon or network
bring-up.

### v221. Host Vendor ELF / Library Evidence Closure

Purpose: inspect `cnss-daemon` and `cnss_diag` binaries when a host-visible
vendor root exists.

Outcome:

- mode: `read-only`
- decision: `vendor-root-required`
- plan: `docs/plans/NATIVE_INIT_V221_HOST_VENDOR_ELF_LIBRARY_EVIDENCE_PLAN_2026-05-13.md`
- report: `docs/reports/NATIVE_INIT_V221_HOST_VENDOR_ELF_LIBRARY_EVIDENCE_2026-05-13.md`

Required next evidence:

- `<vendor-root>/bin/cnss-daemon`
- `<vendor-root>/bin/cnss_diag`
- related vendor `lib`/`lib64` dependencies

### v222. Vendor Root Evidence Export / Extraction

Purpose: produce a private host-visible vendor evidence root that v221 can
inspect.

Mode: `read-only`

Plan:

- `docs/plans/NATIVE_INIT_V222_VENDOR_ROOT_EVIDENCE_EXPORT_PLAN_2026-05-13.md`

Status:

- done
- report: `docs/reports/NATIVE_INIT_V222_VENDOR_ROOT_EVIDENCE_EXPORT_2026-05-13.md`
- tool: `scripts/revalidation/wifi_vendor_root_evidence_export.py`
- result: `export-source-required` because no source vendor root was provided

Implementation:

- supports plan-only `export-source-required` when no source vendor root is
  provided
- supports `--source-vendor-root <path>` to copy an allowlisted minimal vendor
  root with private/no-follow host writes
- outputs `tmp/wifi/v222-vendor-root-evidence-export/manifest.json`,
  `export-plan.json`, `summary.md`, and optional `vendor-root/`

Decision model:

- `vendor-root-ready`: evidence root is ready for v221 rerun
- `export-source-required`: safe PASS planning result; operator must provide a
  vendor root source
- `vendor-export-blocked`: unsafe/incomplete source
- `manual-review-required`: manifest/source conflict

Gate to v223:

- If v222 returns only `export-source-required`, do not treat the vendor evidence
  blocker as closed. Collect vendor root evidence first or explicitly document
  why recovery/security work can continue independently.

### v223. Recovery / Rollback Policy Hardening

Purpose: decide whether reboot-only recovery is acceptable for later controlled
mutation.

Mode: `read-only` plus policy documentation

Plan:

- `docs/plans/NATIVE_INIT_V223_RECOVERY_ROLLBACK_POLICY_PLAN_2026-05-13.md`

Status:

- done
- report: `docs/reports/NATIVE_INIT_V223_RECOVERY_ROLLBACK_POLICY_2026-05-13.md`
- tool: `scripts/revalidation/wifi_recovery_rollback_policy.py`
- result: `reboot-recovery-accepted`

Completed deliverables:

- broken-state detection checklist
- pre/post evidence capture checklist
- stop condition matrix
- reboot handoff policy
- post-reboot verification steps

Decision model:

- `reboot-recovery-accepted`: later temporary mutation may be planned with
  strict stop/reboot policy
- `active-mutation-blocked`: recovery risk remains too high

Gate to v224:

- v224 may proceed as dry-run-only even if active mutation remains blocked, but
  no daemon execution is allowed.

### v224. Android-Env Shim Dry-Run Materialization

Purpose: materialize only reversible shim pieces from v219 and prove their
filesystem/runtime shape without daemon execution.

Mode: host-side dry-run by default; no live device mutation

Plan:

- `docs/plans/NATIVE_INIT_V224_ANDROID_ENV_SHIM_DRYRUN_MATERIALIZATION_PLAN_2026-05-13.md`

Status:

- done
- report: `docs/reports/NATIVE_INIT_V224_ANDROID_ENV_SHIM_MATERIALIZE_2026-05-13.md`
- tool: `scripts/revalidation/wifi_android_env_shim_materialize.py`
- result: `shim-source-required`

Completed examples:

- host-side path alias dry-run artifact
- static property evidence artifact
- group/capability dry-run artifact
- private log policy artifact
- health capture plan artifact using v223 policy

Forbidden:

- `cnss-daemon`, `cnss_diag`, Wi-Fi HAL, `wificond`, supplicant, hostapd
  execution
- Android property mutation
- QMI/PDR/SSR writes
- rfkill/link-up/scan/connect

Decision model:

- `shim-source-required`: dry-run artifacts exist but source vendor root remains missing
- `shim-dryrun-ready`: reversible shim shape is ready for later gated planning
- `shim-too-wide`: required shim recreates too much Android runtime and remains
  blocked

### v225. Wi-Fi Exposure / Credential Security Gate + Gate v3

Purpose: combine v221-v224 prerequisite results and decide whether a later
controlled CNSS start plan is eligible.

Mode: `read-only`

Planned deliverables:

- ACM/NCM/tcpctl/broker/listener exposure matrix
- auth token and binding policy review
- credential storage and redaction policy
- test AP isolation requirements
- gate v3 manifest integrating vendor evidence, recovery, shim, and security

Decision model:

- `cnss-start-plan-approved`: only approves writing the next controlled CNSS
  start plan; it does not itself start Wi-Fi
- `still-no-go`: active Wi-Fi remains blocked

## Execution Order

1. Provide a source vendor root and rerun v222, or keep the vendor-root blocker open.
2. Rerun v221 with v222 `vendor-root/` if `vendor-root-ready` is achieved.
3. Write v224 shim materialization dry-run plan using v223 policy as a hard dependency.
4. Write v225 security/exposure gate and gate v3 after v221-v224 results are
   available.

## Stop Conditions

Stop this Wi-Fi track and return to planning if any of these occur:

- serial/NCM rescue control becomes unreliable;
- vendor evidence cannot be acquired privately and safely;
- recovery remains reboot-only with no accepted policy;
- shim scope requires broad Android property/binder/HAL recreation;
- security exposure review shows root-control channels can leave the trusted
  USB-local boundary;
- any plan requires credentials or active network association before v225.

## Acceptance

This big plan is acceptable when:

- each version has a clear mode, purpose, output, and decision;
- active Wi-Fi work is clearly blocked until gate v3;
- v222-v225 are ordered around blocker closure rather than feature pressure;
- existing per-version plan/report documents remain the source of detailed
  commands and validation evidence.
