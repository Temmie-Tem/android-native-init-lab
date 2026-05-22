# Native Init V633 CDSP Surface Read-Only Plan

- date: `2026-05-23 KST`
- cycle: `v633`
- scope: live read-only collector
- target: collect native v319 CDSP loader/firmware/readiness surfaces before
  any further CDSP write proof

## Background

V632 classified V631's active blocker as a CDSP prerequisite gap:

```text
ADSP write: returned
CDSP write: blocked until bounded timeout
SLPI write: returned
```

Android V622 reaches CDSP SSCTL and service `74`; native V631 does not. The
next safe action is not another boot-node write. It is a read-only inventory of
the CDSP surfaces that the CDSP loader would depend on.

## Guardrails

V633 must not:

- write sysfs or boot ADSP/CDSP/SLPI;
- touch `boot_wlan`, `qcwlanstate`, or `shutdown_wlan`;
- build or flash a boot image;
- start companion daemons, service-manager, CNSS, Wi-Fi HAL, supplicant, or
  hostapd;
- scan/connect/link-up, use credentials, run DHCP, change routes, or ping
  externally.

## Live Inputs

- current native v319 device reachable through the serial bridge
- `/cache/bin/toybox` available
- existing V632 classification:
  `docs/reports/NATIVE_INIT_V632_CDSP_BLOCKER_CLASSIFIER_2026-05-23.md`

## Collection

1. Capture `bootstatus` through the normal protocol path; skip raw `version`
   output because the current banner contains operator-identifying text that is
   not needed for CDSP classification.
2. Read `/sys/kernel/boot_cdsp` metadata and readable attributes only.
3. Read `/sys/bus/msm_subsys/devices/*` names/states/firmware hints.
4. Read `firmware_class.path`, firmware/vendor/persist mounts, and CDSP/turing
   firmware filename visibility.
5. Capture CDSP/fastrpc/Q6-related kernel threads.
6. Capture CDSP/fastrpc/subsys/sysmon/service-notifier/firmware dmesg markers.

## Success Criteria

V633 passes if it records one of these outcomes with no mutation:

- `v633-cdsp-firmware-surface-missing`
- `v633-cdsp-subsys-unready`
- `v633-cdsp-already-online`
- `v633-cdsp-readonly-surface-captured`

Passing V633 does not authorize Wi-Fi HAL, `boot_wlan`, `qcwlanstate`,
scan/connect, credentials, DHCP, route changes, or external ping. It only
selects the next CDSP-specific prerequisite or proof step.
