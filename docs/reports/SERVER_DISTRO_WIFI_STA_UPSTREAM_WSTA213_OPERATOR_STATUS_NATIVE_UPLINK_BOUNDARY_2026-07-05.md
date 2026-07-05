# WSTA213 Operator Status Native Uplink Boundary

Date: 2026-07-05

## Verdict

PASS.  WSTA213 folds the WSTA212 native uplink boundary policy into the WSTA108
operator server status bundle.  The status now treats `wsta-native-uplink-helper`
as a defined native-owned boundary instead of a remaining Debian launcher gap.

Private evidence:

```text
workspace/private/runs/server-distro/wsta213-operator-status-native-uplink-boundary-20260705T2145KST/wsta108_operator_server_status.json
workspace/private/runs/server-distro/wsta213-operator-status-native-uplink-boundary-20260705T2145KST/wsta108_operator_server_status.md
```

Decision:

```text
wsta108-operator-server-status-source-pass
```

## Status State

The accepted status records:

```text
native_uplink_boundary_policy_defined=true
allowed_debian_ops=status,scan
denied_debian_ops=connect,associate,association,dhcp,ping,public-tunnel,tunnel
debian_service_launcher_allowed=false
debian_service_seccomp_target=false
remaining_launcher_profiles=
```

Operator next-actions now end with:

```text
continue-containment-hardening-with-nftables-or-apparmor
move-to-nftables-default-drop-or-apparmor-hardening
```

The stale action below is retired:

```text
continue-root-boundary-policy-for-wsta-native-uplink-helper
```

## Safety

This was host-only status aggregation.  No device action, boot flash, native
reboot, Wi-Fi connect/association, DHCP, ping, public tunnel, public smoke,
packet-filter mutation, rootfs mutation, userdata write, or switch-root
occurred.

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

- Added `--wsta212-native-uplink-boundary-policy-json` to WSTA108.
- Added native uplink boundary compaction and status checks.
- Removed `wsta-native-uplink-helper` from remaining launcher profiles when
  WSTA212 is supplied and valid.
- Updated operator next-actions to move directly to nftables/AppArmor once
  seccomp, non-root capability-drop, and native-uplink boundary policy are all
  proven.
- Added focused WSTA108 tests for WSTA213.

## Next

Continue D-harden with nftables/default-drop hardening or AppArmor feasibility.
Public exposure remains default-off unless an explicit live gate is supplied.
