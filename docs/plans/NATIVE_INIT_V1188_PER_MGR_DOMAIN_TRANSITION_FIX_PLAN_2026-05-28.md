# V1188 Per_mgr SELinux Domain Transition Fix Plan

- **cycle**: V1188
- **date**: 2026-05-28
- **type**: host-only (no device contact)
- **prior**: V1187 live PASS — `per_mgr_domain_value='kernel'` confirmed

## Objective

Determine why per_mgr stays in `kernel` SELinux domain after exec (despite
`write_selinux_attr("exec", "u:r:vendor_per_mgr:s0")` being called), then fix
it so per_mgr transitions to `u:r:vendor_per_mgr:s0` at exec time.

## V1187 Evidence Summary

| metric | value |
|---|---|
| `per_mgr_domain_value` | `kernel` |
| `per_drain_pid` | 2939 |
| `pre_drain_attr_current_captured` | 1 |
| `vndservice_gate.elapsed_ms` | 5180ms |
| `per_mgr.exit_code` | 0 |
| AVC denials in dmesg | 0 |

## Root Cause Analysis

### Mechanism confirmed

1. `composite_spawn_child` forks a child for pm-service.
2. In the child, `apply_peripheral_manager_identity_contract()` drops to uid/gid=1000
   and calls `restrict_to_capabilities(NULL, 0)` — all capabilities dropped.
3. `apply_android_exec_selinux_context_if_requested()` then calls
   `write_selinux_attr("exec", "u:r:vendor_per_mgr:s0")`.
4. The write to `/proc/self/attr/exec` succeeds — in permissive mode
   (`/sys/fs/selinux/enforce=0`), the kernel SELinux hook allows all
   `setexeccon` operations and only logs the AVC denial.
5. `execv("/vendor/bin/pm-service")` is called.
6. Kernel attempts domain transition from `u:r:kernel:s0` →
   `u:r:vendor_per_mgr:s0` at exec time.
7. **Policy check FAILS**: V490 policy has no
   `allow kernel vendor_per_mgr:process transition` rule — this rule is
   absent because the kernel domain should never spawn vendor service processes
   in a normal Android deployment (Android's init has domain `u:r:init:s0`
   and the policy has `allow init vendor_per_mgr:process transition`).
8. Permissive mode: exec proceeds, but the transition is NOT performed.
   Per_mgr starts in `kernel` domain.
9. AVC denial for `{ transition }` goes to Samsung's `sec_avc_log`
   (`allocating 262144 bytes at ... for avc log` at boot) — not the kernel
   ring buffer captured by dmesg. Confirmed: 0 `avc:` lines in V1187 dmesg.

### Why `write_selinux_attr("exec", ...)` alone is not enough

In SELinux, an exec-context write (`/proc/self/attr/exec`) requests a
transition at the NEXT execve. The kernel checks:
- `allow <source_domain> <target_domain>:process transition`
- `allow <target_domain> <exec_file_type>:file entrypoint`
- `allow <source_domain> <exec_file_type>:file execute`

In permissive mode, these checks produce AVC denials but do NOT enforce.
However, the transition is only PERFORMED if the policy has the rule — in
permissive mode the kernel still requires the policy to be present for the
transition to actually execute. Without the rule, the process stays in the
source domain (`kernel`).

### Why pm-service exits code 0

Running in `kernel` domain, pm-service cannot:
- Open `/dev/vndbinder` (vndbinder is restricted to vendor domains)
- Register with vndservicemanager
pm-service detects the missing registration path and exits cleanly (code 0).
`pm_server_name_helper_entry=3` proves pm-service entered application code
before exiting — this is consistent with an early-exit on binder open failure.

## Fix Candidates

### Candidate A — `setcurrent` dynamic relabeling (preferred)

In the child process (after fork, before exec), write
`u:r:vendor_per_mgr:s0` to `/proc/self/attr/current` to dynamically
relabel the running domain. Then call `execv()`.

**Why this works**:
- Writing to one's own `/proc/self/attr/current` has no POSIX-level
  uid/cap restriction — any uid can write their own attr.
- The kernel SELinux hook checks `allow kernel vendor_per_mgr:process dyntransition`
  in policy; this rule is absent, so an AVC denial is logged.
- In permissive mode, the write is ALLOWED despite the missing rule.
- After the write, the child process domain is `u:r:vendor_per_mgr:s0`.
- `execv("/vendor/bin/pm-service")` is called from `vendor_per_mgr` domain.
- Kernel does type_transition lookup for
  `vendor_per_mgr <pm_service_exec_type>:process` — this rule IS present in
  the Android stock policy (`allow init vendor_per_mgr:process transition`
  implies the entrypoint is established; Android runs pm-service via this path).
  Actually the needed rule is
  `type_transition vendor_per_mgr vendor_per_mgr_exec:process vendor_per_mgr`
  which IS in the stock policy.
- pm-service runs in `vendor_per_mgr` domain. ✓

**Implementation**: change `apply_android_exec_selinux_context_if_requested`
to write `/proc/self/attr/current` instead of (or before) `exec`, OR add a
dedicated `apply_android_current_selinux_context()` call before exec in
`composite_spawn_child` for per_mgr/per_proxy/per_proxy_helper children.

Note: only safe in permissive mode. Native init ensures permissive mode via
the V490 policy load. Do not use this approach without permissive mode active.

### Candidate B — V490 CIL injection (alternative)

Modify the V490 helper to accept an extra CIL file that is appended to the
compile step. The CIL would add:
```cil
(allow kernel vendor_per_mgr (process (transition)))
(allow kernel vendor_per_mgr_exec (file (execute)))
```
(assumes file type is `vendor_per_mgr_exec`; needs live verification).

**Tradeoff**: requires knowing the exact file type of `/vendor/bin/pm-service`
(likely `vendor_per_mgr_exec` by Android convention, but unverified), plus
modifying the V490 compile flow. The `setcurrent` approach (A) avoids this.

## Selected Fix: Candidate A — `setcurrent`

Candidate A requires no policy modification and works in permissive mode.
The file type of pm-service does not need to be confirmed in advance.

## Change Plan for Helper v224

**Target**: `a90_android_execns_probe.c`, in `composite_spawn_child`, for
`COMPOSITE_ID_PER_MGR`, `COMPOSITE_ID_PER_PROXY`, `COMPOSITE_ID_PER_PROXY_HELPER`:

After `apply_peripheral_manager_identity_contract()` and before `execv()`:
1. Keep the existing `apply_android_exec_selinux_context_if_requested()` call
   (writes to `exec` attr — retains existing observable output).
2. ADD a new call: `apply_android_current_selinux_context_if_needed()` that:
   - Reads the desired context (same lookup as `exec` path)
   - Writes to `/proc/self/attr/current`
   - Emits result as `wifi_hal_composite_child.<identity>.selinux_current.ok=<0|1>`

The pre-drain probe in `drain_pm_service_trigger_observer_children()` (v223
code) will then capture `vendor_per_mgr` instead of `kernel`.

**Output observable via grep filter**: the existing v223 pre-drain block
emits `pm_service_trigger_observer.child.per_mgr.pre_drain_domain_value=<value>`,
which passes through. If the fix works, this will show `vendor_per_mgr`.

## V1189 Next Live Gate

- Deploy helper v224 (SHA `5c2af22eb0a331e9b12470a5ae77e3be2c8d6a1809e48092b412ff9f82005a5d`)
- Run V1189 live — same setup as V1187 (vndservice gate + pre-drain probe)
- Validate: `per_mgr_domain_value='u:r:vendor_per_mgr:s0'`
- If domain is now `vendor_per_mgr`: check whether per_mgr opens `/dev/vndbinder`
  (vndservice gate should no longer time out) and whether gate passes
- Gate still below Wi-Fi HAL, scan/connect, credentials, DHCP/routes, external ping

Scripts: `wifi_execns_helper_v224_deploy_preflight.py`, `native_wifi_pm_per_mgr_domain_fix_v1189.py`

## Classification Sources

- V1187: `per_mgr_domain_value='kernel'`, zero AVC in dmesg
- V490: SELinux permissive (`enforce=0`)
- V861: `attr/current` stayed `kernel` in earlier per_mgr runs
- Android 4.14 kernel `fs/proc/base.c`: `/proc/self/attr` write does not require
  uid=0 when writing own attribute; SELinux `setexeccon`/`dyntransition` AVC
  is logged but not enforced in permissive mode
- Samsung `sec_avc_log`: boot message confirms AVC log lives in a separate
  RAM buffer (262144 bytes), not in the main kernel ring buffer
