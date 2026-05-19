# v372 Report: Service-Manager Start-Only Approval Packet

- date: `2026-05-20`
- scope: approval packet for future bounded service-manager start-only smoke
- boot image change: none
- native baseline: `A90 Linux init 0.9.61 (v319)`
- plan: `docs/plans/NATIVE_INIT_V372_SERVICE_MANAGER_START_ONLY_APPROVAL_PACKET_PLAN_2026-05-20.md`
- result: `PASS`

## Summary

V372 adds a non-mutating approval packet generator for the next step after V371.
It verifies that V371 and V366 passed, refreshes current read-only native state,
and emits the exact V373 approval phrase. It does not start service-manager or
any Wi-Fi component.

## Evidence

| item | path | decision |
| --- | --- | --- |
| plan | `tmp/wifi/v372-service-manager-start-only-approval-packet-plan-20260520-013401/` | `service-manager-start-only-approval-packet-plan-ready` |
| live read-only packet | `tmp/wifi/v372-service-manager-start-only-approval-packet-live-20260520-013344/` | `service-manager-start-only-approval-packet-ready` |

Live read-only packet summary:

```text
decision: service-manager-start-only-approval-packet-ready
pass: True
reason: approval packet ready; live start-only still requires separate exact approval
next: implement V373 service-manager start-only smoke runner
live_execution_approved: False
device_mutations: False
```

Checks:

```text
v371-live-executor-pass: pass
v371-router-next-ready: pass
v366-smoke-pass: pass
native-version: pass
status-selftest-clean: pass
core-service-manager-binaries-visible: pass (servicemanager/hwservicemanager visible; vndservicemanager absent)
service-manager-processes-clean: pass
wifi-link-surface-clean: pass
temporary-binder-nodes-cleaned: pass
```

Required future approval phrase:

```text
approve v373 service-manager start-only smoke only; no Wi-Fi HAL start and no Wi-Fi bring-up
```

## Guardrails Kept

- V372 has `live_execution_approved=false`.
- V372 has `device_mutations=false`.
- V372 did not create `/dev` nodes.
- V372 did not start service-manager, HAL, `wificond`, supplicant, hostapd,
  CNSS, or diagnostic daemons.
- V372 did not perform Wi-Fi scan/connect/link-up/credential/DHCP/routing.
- V372 did not write rfkill, ICNSS bind/unbind, module state, firmware paths, or
  Android partitions.

## Next Step

Implement V373 as a separate fail-closed service-manager start-only smoke runner.
The V373 runner must still require the exact phrase above plus `--apply
--assume-yes`, and it must remain start-only with cleanup and postflight checks.
