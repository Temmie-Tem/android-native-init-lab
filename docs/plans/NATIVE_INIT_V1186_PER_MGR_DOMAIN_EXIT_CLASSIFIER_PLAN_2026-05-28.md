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
| `preexec_context_suppressed_reason` | `pm-service-trigger-observer-ptrace-lite-output-budget` |

Per_mgr starts and is observable, but exits clean (code 0) within the 5s gate window
without ever opening vndbinder or processing any pm_client_register calls.

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

Evidence: `preexec_context_suppressed_reason=pm-service-trigger-observer-ptrace-lite-output-budget`
means the helper did not log per_mgr's running domain due to ptrace budget limits.

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
   PID before it exits. The ptrace budget limit suppressed this in V1185 — need a
   dedicated domain probe before the main observer starts.

2. **per_mgr dmesg output**: Any SELinux denial or early-exit log from pm-service
   within the gate window.

3. **per_mgr exec contract comparison**: Android pm-service runs as `u:r:vendor_per_mgr:s0`.
   Does native transition to that domain? The `setexeccon` path writes correctly but
   the transition depends on policy allowance.

## Next Live Gate (V1187)

V1186 is host-only classification. V1187 should be a bounded live probe that:
- Captures per_mgr's `/proc/<pid>/attr/current` immediately after spawn (before exit)
- Uses a tighter post-spawn domain read (not ptrace, just procfs)
- Logs any SELinux denials around per_mgr exec time from dmesg
- Optionally runs per_mgr alone (without the full PM observer) to isolate the exit path

Still below Wi-Fi HAL, scan/connect, credentials, DHCP/routes, external ping.

## Classification Sources

- V1183/V1185 tracefs: `per_mgr_vndbinder_count=-1` confirms pm-service never opened binder
- V490 policy load: stock Android policy loaded; `allow kernel vendor_per_mgr:process transition` TBD
- CLAUDE.md V862/V864: Android init contract for `vendor.per_mgr` documented
- CLAUDE.md V904: Android runs `vendor.mdm_helper` as `u:r:vendor_mdm_helper:s0` after `vendor.per_mgr=running`
- V867: live PM init-contract start-only — runtime domains stayed `kernel` (per_mgr, per_proxy)
