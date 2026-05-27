# Native Init V1122 Provider Namespace Delta Classifier Report

Date: `2026-05-27`

## Result

- Decision: `v1122-provider-regression-is-global-firmware-vendor-surface`
- Pass: `true`
- Evidence: `tmp/wifi/v1122-provider-namespace-delta-classifier/manifest.json`
- Summary: `tmp/wifi/v1122-provider-namespace-delta-classifier/summary.md`
- Classifier:
  `scripts/revalidation/native_wifi_provider_namespace_delta_classifier_v1122.py`

## Summary

V1122 compared the V1108 provider-positive path with the V1121 firmware
mount-only path.

The no-pre-CNSS `per_proxy` contract is the same, but the result changes:

| gate | firmware/global `/vendor` surface | provider | CNSS PM register | CNSS PM connect |
| --- | --- | --- | --- | --- |
| V1108 | absent | `1` | `0x0` | `0x0` |
| V1121 | present | `0` | not reached | not reached |

## Evidence

Key flags:

```text
v1108_provider_positive=True
v1121_provider_missing=True
same_no_pre_cnss_per_proxy_contract=True
v1108_cnss_pm_success=True
v1121_cnss_pm_not_reached=True
v1121_firmware_mounts_present=True
v1121_no_global_holder=True
per_mgr_lifetime_delta=True
```

Interpretation:

- global `/dev/subsys_modem` holder alone is not required for the provider
  regression;
- pre-CNSS `per_proxy` ordering is not the differentiator;
- CNSS does not fail inside PM register in V1121 because it never reaches PM
  register;
- the active delta is the global firmware `/vendor` mount surface created before
  the PM observer.

## Safety

- `device_commands_executed=False`
- `firmware_mounts_executed=False`
- `global_modem_holder_opened=False`
- `tracefs_write_executed=False`
- `pm_actor_executed=False`
- `cnss_daemon_start_executed=False`
- `wifi_hal_start_executed=False`
- `scan_connect_executed=False`
- `credential_use_executed=False`
- `dhcp_route_executed=False`
- `external_ping_executed=False`
- `wifi_bringup_executed=False`
- `partition_write_executed=False`
- `flash_executed=False`
- `reboot_executed=False`

## Next

V1123 should avoid mutating global `/vendor` and test one of two narrow paths:

1. private-namespace firmware mounts inside the helper runtime namespace, or
2. trace `pm-service` early clean exit under the global vendor surface.

The first path is closer to Wi-Fi bring-up because it tries to preserve V1108's
provider-positive behavior while adding firmware visibility.
