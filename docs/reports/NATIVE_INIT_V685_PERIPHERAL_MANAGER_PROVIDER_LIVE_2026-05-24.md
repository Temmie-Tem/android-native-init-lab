# Native Init V685 PeripheralManager Provider Live Report

## Result

- decision: `v685-peripheral-manager-provider-start-order-gap`
- pass: `true`
- evidence: `tmp/wifi/v685-peripheral-manager-provider-live-verify/`
- device commands: `true`, read-only only
- daemon start: `false`
- Wi-Fi bring-up: `false`

## Interpretation

V685 confirms the provider side of the V684 Binder target:

```text
cnss-daemon
  -> libperipheral_client.so
    -> vendor.qcom.PeripheralManager
      <- vendor.per_mgr /vendor/bin/pm-service
      <- vendor.per_proxy /vendor/bin/pm-proxy
```

The current native global namespace does not expose `/vendor/bin/pm-service`,
`/vendor/bin/pm-proxy`, `/dev/vndbinder`, or the vendor init block by default.
That is expected for this native init environment and means the next fix belongs
inside the helper's private Android namespace, not in the global native root.

## Evidence Summary

| Check | Status |
| --- | --- |
| V684 target candidate ready | pass |
| A90 vendor init defines provider | finding |
| mounted vendor contained provider binaries | finding |
| current helper lacks provider start mode | finding |
| live global provider materialized | review |
| live global provider not materialized | finding |
| live provider not running by default | finding |

Vendor init evidence from V210:

```text
service vendor.per_mgr /vendor/bin/pm-service
    class core
    user system
    group system
    ioprio rt 4

service vendor.per_proxy /vendor/bin/pm-proxy
    class core
    user system
    group system
    disabled

on property:init.svc.vendor.per_mgr=running
    start vendor.per_proxy
```

Live read-only surface from V685:

| Item | Value |
| --- | --- |
| `pm_service_exists` | `false` |
| `pm_proxy_exists` | `false` |
| `vndbinder_exists` | `false` |
| `init_per_mgr_seen` | `false` |
| `init_per_proxy_seen` | `false` |
| `pm_service_running` | `false` |
| `pm_proxy_running` | `false` |
| `vndservicemanager_running` | `false` |
| `cnss_daemon_running` | `false` |

## Guardrails Verified

- no daemon start;
- no service-manager start;
- no Wi-Fi HAL start;
- no scan/connect/link-up;
- no credentials, DHCP, routing, or external ping;
- no sysfs/debugfs write;
- no boot image or partition write.

## Decision

V685 moves the next actionable blocker from "unknown vndbinder target" to
"helper lacks the provider/start-order surface for `vendor.per_mgr` and
`vendor.per_proxy`." The next unit should implement helper support for a
bounded provider start-only proof.

## Next Gate

V686:

1. add `pm-service`/`pm-proxy` target identities using Android init's
   `user system`, `group system` contract;
2. materialize the private Android namespace with `/dev/vndbinder`;
3. start `vendor.per_mgr` first;
4. start `vendor.per_proxy` only after `vendor.per_mgr` is observable;
5. run a fresh `cnss-daemon` retry only after provider availability is proven;
6. keep Wi-Fi HAL, scan/connect, DHCP, routes, and external ping blocked.
