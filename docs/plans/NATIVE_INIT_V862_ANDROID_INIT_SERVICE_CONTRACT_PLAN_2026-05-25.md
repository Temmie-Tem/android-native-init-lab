# Native Init V862 Android Init Service Contract Plan

## Goal

Classify the Android init-managed service contract that V861 direct exec still
does not reproduce for PeripheralManager.

## Inputs

| Evidence | Path |
|---|---|
| V210 vendor init capture | `tmp/wifi/v210-vendor-asset-classifier/native/commands/cat-etc-init-hw-init.target.rc.txt` |
| V210 vendor init inventory | `tmp/wifi/v210-vendor-asset-classifier/manifest.json` |
| V853 Android actor sample | `tmp/wifi/v853-android-esoc-actor-handoff/v853-android-esoc-actor-run/manifest.json` |
| V861 native replay | `tmp/wifi/v861-pm-service-domain-parity-live-r2/manifest.json` |
| helper source | `stage3/linux_init/helpers/a90_android_execns_probe.c` |

## Scope

1. Parse Android init service definitions for `vendor.per_mgr`,
   `vendor.per_proxy`, and `vendor.per_proxy_helper`.
2. Compare init lifecycle semantics against the current helper model:
   `class`, `user`, `group`, `disabled`, property-triggered start/stop,
   `ioprio`, service domain, and fd ownership outcome.
3. Select the next lower-risk native gate before `mdm_helper`/`ks`.

## External Reference

- Android init README: services are init-launched programs with options that
  affect when and how init runs them, including `disabled`, `user`, `group`,
  `seclabel`, `class`, and `start`.
  <https://android.googlesource.com/platform/system/core/+/74b6f94/init/README.md>
- Android vendor init: vendor init scripts run through Android init/vendor-init
  context and are not equivalent to arbitrary direct exec from native PID 1.
  <https://source.android.com/docs/security/features/selinux/vendor-init>

## Hard Gates

- No device command.
- No daemon, `mdm_helper`, `ks`, Wi-Fi HAL, supplicant, or hostapd start.
- No scan/connect/link-up, credential use, DHCP/routes, or external ping.
- No raw eSoC ioctl, GPIO write, sysfs/debugfs/subsystem write, module load,
  boot image write, or partition write.

## Success Criteria

- Host-only classifier emits a manifest and summary.
- The classifier identifies whether the next useful gate is:
  - read-only `pm_proxy_helper.rc` capture,
  - an init-equivalent `pm-service` lifecycle wrapper,
  - SELinux transition semantics,
  - or manual review.
- All findings are traceable to V210/V853/V861 evidence.
