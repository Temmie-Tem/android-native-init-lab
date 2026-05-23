# Native Init V689 Peripheral Property Shim Classifier Report

## Result

- decision: `v689-peripheral-property-shim-candidate`
- pass: `true`
- evidence: `tmp/wifi/v689-peripheral-property-shim-classifier-rerun/`
- device commands: `false`
- device mutations: `false`
- Wi-Fi bring-up: `false`
- external ping: `false`

## Inputs

| input | decision | use |
| --- | --- | --- |
| V688 orchestrated live | `v688-provider-start-gap-classified` | provider property blocker source |
| V688 arm | `v688-provider-start-gap-classified` | helper transcript and context repair flag |
| V685 provider contract | `v685-peripheral-manager-provider-plan-ready` | `vendor.per_mgr`/`vendor.per_proxy` init contract |
| V676 property baseline | `v676-property-gap-persists-classified` | prior Android userspace property-denial comparison |

## Classification

V688 proved the invalid `u:r:per_mgr:s0` context was removed. The remaining
private property-service shim denials were exact and repeated:

| name | value | result | count |
| --- | --- | --- | ---: |
| `vendor.peripheral.SDX50M.state` | `OFFLINE` | `0x00000018` | `3` |
| `vendor.peripheral.modem.state` | `OFFLINE` | `0x00000018` | `3` |

No broader `vendor.peripheral.*` write set was observed. The accepted shim
request remained the existing service-manager readiness write:

| name | value | result | count |
| --- | --- | --- | ---: |
| `hwservicemanager.ready` | `true` | `0x00000000` | `1` |

Provider child state after those denials:

| child | observable | exited | exit_code | signal | context |
| --- | ---: | ---: | ---: | ---: | --- |
| `per_mgr` | `1` | `1` | `0` | `0` | no default context; skipped |
| `per_proxy` | `1` | `1` | `1` | `0` | no default context; skipped |
| `cnss_daemon_retry` | `1` | `1` | `-1` | `9` | bounded cleanup |

## Decision

The next helper change should acknowledge only the exact private shim writes:

```text
vendor.peripheral.SDX50M.state=OFFLINE
vendor.peripheral.modem.state=OFFLINE
```

This is not a global Android property mutation. It is a response from the
helper-owned private `/dev/socket/property_service` inside the helper namespace,
used only during the bounded provider/CNSS retry window.

## Guardrails

- no bridge or device command;
- no helper deploy;
- no daemon or service start;
- no Wi-Fi HAL, wificond, supplicant, or hostapd start;
- no scan/connect/link-up;
- no credential, DHCP, route change, or external ping;
- no boot image or partition write.

## Next Gate

V690 should build helper v115 with an exact allowlist for the two private
PeripheralManager state writes above, then run the same bounded provider/CNSS
retry. V690 must still block Wi-Fi HAL, credentials, scan/connect, DHCP, route
changes, and external ping.
