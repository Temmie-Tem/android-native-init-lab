# v374 Report: Execns Service-Manager Start-Only Mode

- date: `2026-05-20`
- scope: local helper support for bounded service-manager start-only mode
- boot image change: none
- device mutation: none
- plan: `docs/plans/NATIVE_INIT_V374_EXECNS_SERVICE_MANAGER_MODE_PLAN_2026-05-20.md`
- result: `PASS / deploy pending`

## Summary

V374 updates `stage3/linux_init/helpers/a90_android_execns_probe.c` to helper
`v12` with a gated `service-manager-start-only` mode. The new mode supports
`system-servicemanager` and `system-hwservicemanager` target profiles and remains
blocked unless `--allow-service-manager-start-only` is explicitly supplied.

This commit only builds the local static helper artifact. It does not deploy the
helper and does not start any service-manager process.

## Evidence

| item | path | result |
| --- | --- | --- |
| helper artifact | `tmp/wifi/v374-a90_android_execns_probe-v12/a90_android_execns_probe` | static ARM64 |
| source | `stage3/linux_init/helpers/a90_android_execns_probe.c` | helper marker `v12` |

Artifact:

```text
sha256=fef21de2897b16e4ead7fe780eff1817675d4ce988e558013ac9a37dc928d918
file=ELF 64-bit LSB executable, ARM aarch64, statically linked, stripped
```

String checks:

```text
a90_android_execns_probe v12
service-manager-start-only
allow-service-manager-start-only
system-servicemanager
system-hwservicemanager
service_manager_start.reason=missing-allow-service-manager-start-only
```

## Guardrails Kept

- No `/cache/bin/a90_android_execns_probe` deployment was performed in V374.
- No service-manager, HAL, `wificond`, supplicant, hostapd, CNSS, or diagnostic
  daemon was started.
- No Wi-Fi scan/connect/link-up/credential/DHCP/routing was executed.
- No temporary `/dev` node, rfkill, ICNSS, module, firmware, or Android
  partition mutation occurred.

## Next Step

V375 should be a deploy/preflight packet: install the v12 helper to `/cache/bin`,
verify remote marker/SHA-256, run remote `--help`, and rerun V373 preflight. Live
service-manager start-only should still require the V373 exact approval phrase.
