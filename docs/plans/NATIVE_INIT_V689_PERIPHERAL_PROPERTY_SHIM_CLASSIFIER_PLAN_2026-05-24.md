# Native Init V689 Peripheral Property Shim Classifier Plan

## Objective

V689 classifies the V688 provider property-service blocker without running any
new device commands. V688 proved that helper v114 removed the invalid
`u:r:per_mgr:s0` context failure, then stopped at private property-service
responses:

```text
vendor.peripheral.SDX50M.state=OFFLINE -> 0x18
vendor.peripheral.modem.state=OFFLINE -> 0x18
```

V689 decides whether the next helper should safely acknowledge those exact
private property-service writes before another bounded provider/CNSS retry.

## Scope

- Use existing host evidence only:
  - V688 orchestrated live manifest and companion transcript;
  - V685 provider init contract;
  - V676 Android userspace/property-denial baseline.
- Parse private property-service shim requests and provider child exits.
- Classify whether the denied writes are a bounded, private, Wi-Fi-precondition
  shim gap rather than a global property mutation requirement.
- Produce the V690 gate recommendation.

## Guardrails

- no bridge/device command;
- no helper deploy;
- no daemon/service start;
- no Wi-Fi HAL, supplicant, hostapd, scan/connect, DHCP, route, credential, or
  external ping;
- no boot image or partition write.

## Success Criteria

- V688 evidence proves helper v114 context repair did not regress;
- all denied `vendor.peripheral.*.state` writes are exact known names with value
  `OFFLINE`;
- the classifier recommends either:
  - exact-name private shim acknowledgement for V690; or
  - more host-only evidence if the request set is broader than expected.

## Next Gate

If V689 returns `v689-peripheral-property-shim-candidate`, V690 should build
helper v115 with a narrow allowlist for these exact private shim writes only:

```text
vendor.peripheral.SDX50M.state=OFFLINE
vendor.peripheral.modem.state=OFFLINE
```

V690 must still block Wi-Fi HAL, credentials, scan/connect, DHCP, route changes,
and external ping.
