# WSTA212 Native Uplink Boundary Policy

Date: 2026-07-05

## Verdict

PASS.  WSTA212 defines the `wsta-native-uplink-helper` as a native-owned
root-boundary policy, using only existing evidence.  Debian remains limited to
the redacted native Wi-Fi service client `status` and `scan` surface.  Connect,
association, DHCP, ping, routing, credential access, and public tunnel start
remain native-owned boundary operations.

Private evidence:

```text
workspace/private/runs/server-distro/wsta212-native-uplink-boundary-policy-20260705T2130KST/wsta212_result.json
workspace/private/runs/server-distro/wsta212-native-uplink-boundary-policy-20260705T2130KST/wsta212_native_uplink_boundary_policy.json
workspace/private/runs/server-distro/wsta212-native-uplink-boundary-policy-20260705T2130KST/wsta212_native_uplink_boundary_policy.md
```

Decision:

```text
wsta212-native-uplink-boundary-policy-source-pass
```

## Policy State

The accepted policy records:

```text
state=NATIVE_UPLINK_ROOT_BOUNDARY_POLICY_SOURCE_DEFINED
service=wsta-native-uplink-helper
classification=native-owned-root-boundary
allowed_debian_ops=status,scan
denied_debian_ops=connect,associate,association,dhcp,ping,public-tunnel,tunnel
debian_service_launcher_allowed=false
debian_service_seccomp_target=false
```

The policy is derived from:

```text
workspace/private/runs/server-distro/wsta90-service-hardening-manifest-20260704T131000Z/wsta90_service_hardening_manifest.json
workspace/private/runs/server-distro/wsta22-native-wifi-service-client-20260704T011641Z/wsta22_result.json
workspace/private/runs/server-distro/wsta154-seccomp-launcher-gate-model-20260705T1210KST/wsta154_seccomp_launcher_gate_model.json
workspace/public/src/scripts/server-distro/a90_native_wifi_service_client.sh
```

## Checks

WSTA212 fail-closes unless:

- the WSTA90 manifest marks `wsta-native-uplink-helper` as a native boundary.
- WSTA22 proves Debian `status` and `scan` through the native-owned service.
- WSTA22 proves the response owner is `native-init`.
- WSTA22 proves no credential, connect, DHCP, or public tunnel action is exposed
  through the Debian helper.
- WSTA22 proves scan output is redacted.
- WSTA154 keeps `wsta-native-uplink-helper` excluded from Debian service seccomp.
- the Debian helper source denies connectivity operations before request write.
- the generated policy keeps future connect/public rungs operator-gated.

All checks passed; there were no false checks in the accepted result.

## Safety

This was host-only policy aggregation.  No device action, boot flash, native
reboot, Wi-Fi connect/association, DHCP, ping, public tunnel, public smoke,
packet-filter mutation, rootfs mutation, userdata write, or switch-root
occurred.

Safety fields from the accepted result:

```text
device_action=false
boot_flash=false
native_reboot=false
wifi_connect=false
wifi_association=false
dhcp=false
ping=false
public_tunnel=false
packet_filter_mutation=false
rootfs_mutation=false
userdata_touch=false
switch_root=false
public_url_value_logged=false
secret_values_logged=0
```

## Code Changes

- Added `run_wsta212_native_uplink_boundary_policy.py`.
- Added focused WSTA212 tests.
- Updated `GOAL.md` with the WSTA212 result and next action.

## Next

Fold WSTA212 into the WSTA108 operator status bundle so the
`continue-root-boundary-policy-for-wsta-native-uplink-helper` next action can
retire.  Then continue D-harden with nftables/default-drop or AppArmor
feasibility.
