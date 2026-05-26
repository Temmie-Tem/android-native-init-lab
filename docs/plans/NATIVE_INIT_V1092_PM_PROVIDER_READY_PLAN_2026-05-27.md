# Native Init V1092 PM Provider Ready Plan

## Goal

Reproduce the V694 PeripheralManager-positive preconditions in the current PM
observer path and prove whether `/vendor/bin/pm-service` can register
`vendor.qcom.PeripheralManager` after the V490 SELinux policy-load proof.

## Scope

- Deploy `a90_android_execns_probe v202`.
- Start only the service-manager trio, `pm_proxy_helper`, and `pm-service`.
- Wait for explicit `vndservicemanager` readiness before starting `pm-service`.
- Query `/vendor/bin/vndservice list` immediately after `pm-service` readiness.
- Stop after provider registration is observed; do not continue to Wi-Fi actors.

## Guardrails

- No `mdm_helper`.
- No CNSS daemon.
- No Wi-Fi HAL, supplicant, hostapd, scan, connect, DHCP, route, or external ping.
- No `/dev/subsys_esoc0` open, eSoC ioctl, GPIO write, partition write, flash, or reboot.
- SELinux policy load is handled only by the separately gated V490 proof.

## Implementation

1. Add PM-observer `vndservicemanager` readiness wait and status fields.
2. Add compact `vndservice list` query after `pm-service` startup.
3. Suppress inherited stdio/context noise in the query child.
4. Stop the observer as soon as `vendor.qcom.PeripheralManager` is found.
5. Add deploy and live wrappers for the v202 helper and V1092 gate.

## Success Criteria

- Helper v202 deploy/preflight passes.
- V490 policy-load proof passes before the live gate.
- `vndservicemanager_readiness.ready=1`.
- `wifi_vndservice_query.*.vendor_qcom_peripheral_manager_seen=1`.
- Wi-Fi HAL/start/connect/link-up/external ping remain `False`.
