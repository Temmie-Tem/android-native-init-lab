# WSTA215 Operator Status AppArmor Feasibility

Date: 2026-07-05

## Verdict

PASS.  WSTA215 folds the WSTA214 AppArmor feasibility audit into the WSTA108
operator server status bundle.  AppArmor is now explicitly parked as unavailable
under current evidence, and operator next-actions are narrowed to the proven
legacy-iptables loopback/default-drop hardening path.

Private evidence:

```text
workspace/private/runs/server-distro/wsta215-operator-status-apparmor-feasibility-20260705T2220KST/wsta108_operator_server_status.json
workspace/private/runs/server-distro/wsta215-operator-status-apparmor-feasibility-20260705T2220KST/wsta108_operator_server_status.md
```

Decision:

```text
wsta108-operator-server-status-source-pass
```

## Status State

The accepted status records:

```text
apparmor_state=APPARMOR_NOT_AVAILABLE_UNDER_CURRENT_EVIDENCE
apparmor_unavailable_under_current_evidence=true
apparmor_immediate_lever_available=false
preferred_current_hardening_lever=legacy-iptables-loopback-default-drop
profile_load_allowed=false
```

Operator next-actions now end with:

```text
continue-containment-hardening-with-legacy-iptables-default-drop
move-to-legacy-iptables-default-drop-hardening
```

The ambiguous actions below are retired:

```text
continue-containment-hardening-with-nftables-or-apparmor
move-to-nftables-default-drop-or-apparmor-hardening
```

## Safety

This was host-only status aggregation.  No device action, boot flash, native
reboot, Wi-Fi connect/association, DHCP, ping, public tunnel, public smoke,
packet-filter mutation, rootfs mutation, userdata write, LSM profile load, or
switch-root occurred.

Safety fields remained:

```text
device_action=false
boot_flash=false
native_reboot=false
wifi_connect=false
dhcp=false
public_tunnel=false
packet_filter_mutation=false
userdata_touch=false
switch_root=false
public_url_value_logged=false
secret_values_logged=0
```

## Code Changes

- Added `--wsta214-apparmor-feasibility-json` to WSTA108.
- Added AppArmor feasibility compaction and status checks.
- Updated operator next-actions to prefer
  `legacy-iptables-loopback-default-drop` once WSTA214 proves AppArmor is not an
  immediate lever.
- Added focused WSTA108 tests for WSTA215.

## Next

Continue D-harden by turning the proven legacy-iptables loopback/default-drop
path into the next explicit/default-off server hardening policy step.
