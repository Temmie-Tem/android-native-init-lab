# V1186 Per_mgr SELinux Domain and Early Exit Classifier — Host-Only Plan

- **cycle**: V1186
- **date**: 2026-05-28
- **type**: host-only (no device contact)
- **prior**: V1185 live FAIL (gate timeout; per_mgr exits before registering with vndservicemanager)

## Objective

Classify why per_mgr (pm-service) exits with exit_code=0 before opening `/dev/vndbinder`
and registering with vndservicemanager, even when per_proxy is not spawned.

## V1185 Evidence Summary

| metric | value |
|---|---|
| `per_mgr_obs_at_probe` | 1 (observable at zero-delay probe) |
| `vndservice_gate.poll_count` | 22 |
| `vndservice_gate.elapsed_ms` | 5152ms |
| `per_mgr_vndbinder_count` (all polls) | -1 (never opened) |
| `pm_server_register_entry.count` | 0 |
| `pm_client_register_entry.count` | 0 |
| `per_mgr.exit_code` | 0 |
| `per_proxy_skipped` | 1 (gate correctly prevented spawn) |
| `preexec_context_suppressed_reason` | `pm-service-trigger-observer-ptrace-lite-output-budget` (helper's own preexec only — see below) |
| `pm_server_name_helper_entry` | 3 (pm-service processed 3 peripherals before exiting) |

Per_mgr starts and is observable, but exits clean (code 0) within the 5s gate window
without ever opening vndbinder or processing any pm_client_register calls.

**New finding (V1186 analysis)**: per_mgr IS executing application code —
`pm_server_name_helper_entry=3` means it ran the peripheral name-building loop for 3
items. This rules out a pure exec-time crash from domain transition failure. pm-service
progresses through internal init (mutex locks, peripheral list), then fails silently when
attempting to open `/dev/vndbinder` or connect to vndservicemanager.

## Candidate Causes

### Cause A — SELinux domain (most likely)

The helper process runs in `kernel` domain (or lacks a domain transition to `vendor_per_mgr`).
`setexeccon()` writes to `/proc/self/attr/exec`, but a domain transition at exec time requires
`allow <current_domain> vendor_per_mgr:process transition` in the loaded policy.

V490 policy load should enable this transition, but:
1. V490 loads the policy into the kernel (`/sys/fs/selinux/load`)
2. `execcon` is set to `u:r:vendor_per_mgr:s0` in the helper before `execve`
3. If the policy doesn't grant the transition from the helper's domain to `vendor_per_mgr`,
   the exec proceeds in the calling domain (`kernel`) instead

Running in `kernel` domain: pm-service tries to open a vendor socket
(`/dev/socket/vendor.per_mgr` or equivalent), connect to hwservicemanager/vndservicemanager,
or bind a vendor binder — all of which may fail or silently early-exit if the domain
doesn't have the expected capabilities.

**Correction re `preexec_context_suppressed_reason`**: This marker means the helper
suppressed its OWN preexec context (linker/target paths) in ptrace-lite + pm-observer mode.
It does NOT mean per_mgr's running domain was blocked — `composite_capture_observable_children`
reads `/proc/<pid>/attr/current` via procfs and is not ptrace-budget-limited. The actual
reason per_mgr's domain was absent from V1185 is that `drain_pm_service_trigger_observer_children`
reaped per_mgr (`child_done=true`) before `composite_capture_observable_children` ran.
**Fix in helper v223**: v222 used `append_proc_file_capture_named()` which emits
`A90_EXECNS_CNSS_PROC_*` markers. The child-script grep filter only passes
`pm_service_trigger_observer.*` and a few other prefixes — `A90_EXECNS_CNSS_PROC_*` is
filtered out, so the domain content never reaches the host. The `captured=1` flag
still passed through because it uses the `pm_service_trigger_observer.` prefix.
v223 replaces this with a direct open/read that writes the domain as
`pm_service_trigger_observer.child.per_mgr.pre_drain_domain_value=<value>`,
which passes the filter. V1187 also updates `_per_mgr_domain()` to read
from step files (not the truncated `payload` field).

### Cause B — Missing socket or environment

pm-service may require a socket at `/dev/socket/vendor.per_mgr` or similar that doesn't
exist in the native environment. Clean exit with code 0 is consistent with a "no socket,
bail cleanly" startup path.

### Cause C — Missing property or init lifecycle condition

Android `vendor.per_mgr` init service sets `ioprio rt 4` and depends on certain init
lifecycle conditions. Running pm-service directly may trigger a missing-dependency
early exit.

## Gaps to Close

1. **per_mgr running domain**: Capture actual `/proc/<pid>/attr/current` for per_mgr
   PID before it exits. Root cause of V1185 miss: drain reaped per_mgr before procfs
   read. Fix: helper v222 pre-drain read. Target: V1187 live.

2. **per_mgr dmesg output**: Any SELinux denial or early-exit log from pm-service
   within the gate window. Particularly `avc: denied { open }` for vndbinder or
   vendor sockets targeting `kernel` domain.

3. **per_mgr exec contract comparison**: Android pm-service runs as `u:r:vendor_per_mgr:s0`.
   Does native transition to that domain? The `setexeccon` path writes correctly but
   the transition depends on policy allowance. V867 showed runtime domains stayed
   `kernel` in the PM init-contract start-only experiment.

## Next Live Gate (V1187)

V1186 is host-only classification. V1187 uses helper v223 and should:
- Deploy helper v223 (SHA `52d32ff2e469b674dc7d424337176bae3f43e63b1135deecf77442d4ccf92266`)
- Capture per_mgr's `/proc/<pid>/attr/current` via pre-drain read (v223 corrected feature)
- Capture dmesg AVC denials around per_mgr exec time in the observer window
- Report `per_mgr_domain_value` in manifest

Scripts: `wifi_execns_helper_v223_deploy_preflight.py`, `native_wifi_pm_per_mgr_domain_capture_v1187.py`

**v222 failure note**: V1187 first ran with helper v222. The pre-drain probe code executed
(`pre_drain_probe=1`, `pre_drain_pid=2985`, `pre_drain_attr_current_captured=1`) but
`domain_value=""`. Root cause: v222 used `append_proc_file_capture_named()` whose
`A90_EXECNS_CNSS_PROC_*` output is stripped by the child-script grep filter. v223 fixes this.

Still below Wi-Fi HAL, scan/connect, credentials, DHCP/routes, external ping.

## Classification Sources

- V1183/V1185 tracefs: `per_mgr_vndbinder_count=-1` confirms pm-service never opened binder
- V490 policy load: stock Android policy loaded; `allow kernel vendor_per_mgr:process transition` TBD
- CLAUDE.md V862/V864: Android init contract for `vendor.per_mgr` documented
- CLAUDE.md V904: Android runs `vendor.mdm_helper` as `u:r:vendor_mdm_helper:s0` after `vendor.per_mgr=running`
- V867: live PM init-contract start-only — runtime domains stayed `kernel` (per_mgr, per_proxy)
