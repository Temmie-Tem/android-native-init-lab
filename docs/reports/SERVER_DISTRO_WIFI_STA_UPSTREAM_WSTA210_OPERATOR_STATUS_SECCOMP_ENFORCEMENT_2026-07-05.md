# WSTA210 Operator Status Seccomp Enforcement

Date: 2026-07-05

## Verdict

PASS.  WSTA210 updates the operator server status bundle so it accepts the
WSTA208 and WSTA209 real-service seccomp enforcement proofs.  The resulting
status now records seccomp as live-proven for both `dpublic-smoke-httpd` and
`dropbear-admin-usb`, and shifts the next hardening actions away from seccomp
scaffolding toward capability-drop, nftables, or AppArmor work.

Private evidence:

```text
workspace/private/runs/server-distro/wsta210-operator-status-seccomp-enforcement-full-20260705T2048KST/wsta108_operator_server_status.json
workspace/private/runs/server-distro/wsta210-operator-status-seccomp-enforcement-full-20260705T2048KST/wsta108_operator_server_status.md
```

Decision:

```text
wsta108-operator-server-status-source-pass
```

## Seccomp State

The accepted status contains:

```text
seccomp_state=REAL_SERVICE_SECCOMP_SMOKE_AND_DROPBEAR_LIVE_PROVEN
seccomp_real_services_live_proven=true
seccomp_smoke_service_live_proven=true
seccomp_dropbear_admin_live_proven=true
seccomp_all_supplied_proofs_live_proven=true
proven_services=dpublic-smoke-httpd,dropbear-admin-usb
```

The status also preserved the earlier server-distro proofs for packet filter,
service launcher, Cloudflared runtime, Dropbear admin, Dropbear syscall trace,
HUD presenter/handoff/restart, and HUD intent syscall trace.

## Next Actions

The generated operator next-action list now ends with:

```text
continue-containment-hardening-with-capability-drop-nftables-or-apparmor
move-to-capability-drop-nftables-or-apparmor-hardening
```

This is the intended transition after WSTA208/WSTA209: do not add more seccomp
scaffolding unless a profile changes.

## Safety

This was host-only status aggregation.  No device action, boot flash, native
reboot, Wi-Fi connect, DHCP, public tunnel, public smoke, packet-filter
mutation, userdata write, or switch-root occurred.

Safety fields from the accepted result:

```text
device_action=false
boot_flash=false
native_reboot=false
wifi_connect=false
dhcp=false
public_tunnel=false
public_smoke=false
packet_filter_mutation=false
userdata_touch=false
switch_root=false
public_url_value_logged=false
secret_values_logged=0
```

## Code Changes

- Added WSTA208/WSTA209 inputs to `run_wsta108_operator_server_status.py`.
- Added `seccomp_enforcement_proof` compaction with marker/check/safety
  validation for both real-service seccomp live runs.
- Added markdown/check output for real-service seccomp state.
- Added focused WSTA108 tests for seccomp proof acceptance, fail-closed
  incomplete proof handling, and non-pass WSTA209 rejection.
