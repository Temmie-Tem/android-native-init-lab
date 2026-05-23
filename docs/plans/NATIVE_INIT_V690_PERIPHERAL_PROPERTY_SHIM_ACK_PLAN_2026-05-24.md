# Native Init V690 Peripheral Property Shim Ack Plan

## Objective

V690 implements the V689 recommendation in helper v115: acknowledge only the
two exact private property-service writes that `pm-service` needs before the
provider/CNSS retry can advance.

This is not a global Android property mutation. The acknowledgement happens
only in the helper-owned private `/dev/socket/property_service` inside the
bounded private namespace.

## Scope

1. bump helper marker to `a90_android_execns_probe v115`;
2. add exact private shim acknowledgements:

```text
vendor.peripheral.SDX50M.state=OFFLINE
vendor.peripheral.modem.state=OFFLINE
```

3. keep all other property writes denied unless already explicitly allowed;
4. preserve the V688 provider/CNSS retry order;
5. deploy v115 and run one bounded live proof.

## Guardrails

- no global `/dev/socket/property_service` mutation;
- no Wi-Fi HAL or wificond start;
- no supplicant or hostapd start;
- no scan/connect/link-up;
- no credential use;
- no DHCP, route change, or external ping;
- no sysfs subsystem state write;
- no `esoc0` open/hold;
- no boot image or partition write.

## Success Criteria

- helper source compiles for AArch64 static;
- artifact contains `a90_android_execns_probe v115`;
- artifact has no dynamic section;
- V690 live proof shows the two exact private property requests return success;
- no unexpected broader `vendor.peripheral.*` request is acknowledged;
- provider/CNSS retry result is classified before Wi-Fi HAL or any credential
  bearing operation.

## Next Gate

If the provider stays alive and WLFW/BDF/`wlan0` advances, the next unit should
classify netdev readiness before scan/connect. If the provider still exits, the
next unit should classify the new post-property provider runtime output.
