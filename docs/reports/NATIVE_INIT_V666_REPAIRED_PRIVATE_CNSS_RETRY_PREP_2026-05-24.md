# Native Init V666 Repaired Private CNSS Retry Prep

- date: `2026-05-24 KST`
- runner: `scripts/revalidation/native_wifi_repaired_private_cnss_retry_v666.py`
- status: prepared; live proof not executed in this prep report

## Result

V666 adds a narrow runner for the next Wi-Fi blocker:

```text
V665 repaired private registry/property path
  -> V666 repeats fresh cnss-daemon retry with --property-root
  -> Wi-Fi HAL/scan/connect/external ping still blocked
```

The runner reuses the V655 service `74` gated
`vndservicemanager` readiness plus CNSS retry path, but requires helper v109 and
adds the V317 private property root to the helper command. The resulting helper
argv count is exactly `30`, matching the existing native safe limit.

Plan-only validation passed:

```text
decision: v666-repaired-private-cnss-retry-plan-ready
pass: True
device_commands_executed: False
wifi_bringup_executed: False
```

Evidence:

- `tmp/wifi/v666-repaired-private-cnss-retry-plan-check/`

## Guardrails

V666 does not authorize:

- ADSP/CDSP/SLPI boot-node writes;
- `esoc0` open/hold;
- `qcwlanstate` or Wi-Fi driver-state writes;
- Wi-Fi HAL, `wificond`, supplicant, or hostapd start;
- scan/connect/link-up, credential use, DHCP, route changes, or external ping;
- boot image or partition writes.

## Expected Evidence

The live proof should capture:

- service `74` gate state;
- `vndservicemanager` readiness state;
- initial `cnss-daemon` cleanup and retry child status;
- `context.dev_properties.*`;
- `wifi_hal_composite_start.property_service_shim.*`;
- WLFW/WLAN-PD/QMI/BDF/`wlan0` dmesg counts;
- reboot cleanup health.

## Next

Refresh current-boot V641/V401/V490 prerequisites, run V666 preflight, then run
the bounded live proof. Do not proceed to Wi-Fi HAL, scan/connect, DHCP, route,
or external ping until V666 shows lower-surface advancement that justifies the
next gate.

## Local Validation

Executed:

```bash
python3 -m py_compile scripts/revalidation/native_wifi_repaired_private_cnss_retry_v666.py
python3 scripts/revalidation/native_wifi_repaired_private_cnss_retry_v666.py --out-dir tmp/wifi/v666-repaired-private-cnss-retry-plan-check plan
git diff --check
```

The resource-safe changed-file secret scan also passed and scanned only the new
V666 runner/docs plus `docs/README.md`.
