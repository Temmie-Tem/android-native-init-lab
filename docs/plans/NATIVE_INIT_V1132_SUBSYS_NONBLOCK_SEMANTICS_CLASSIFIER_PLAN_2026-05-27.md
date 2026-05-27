# Native Init V1132 Subsys Nonblock Semantics Classifier Plan

Date: `2026-05-27`

## Objective

Classify why the V1131 `/dev/subsys_modem` pre-holder did not return even when
opened with `O_NONBLOCK`, and decide whether another nonblocking
`/dev/subsys_modem` retry is technically meaningful.

## Inputs

- V1131 live report:
  `docs/reports/NATIVE_INIT_V1131_POST_POLICY_GLOBAL_FIRMWARE_MODEM_HOLDER_LIVE_2026-05-27.md`
- V1131 classifier manifest:
  `tmp/wifi/v1131-post-policy-global-firmware-modem-holder-classifier/manifest.json`
- Local Samsung OSRC subsystem source:
  `kernel_build/SM-A908N_KOR_12_Opensource/Kernel/drivers/soc/qcom/subsystem_restart.c`
- Existing eSoC research:
  `docs/overview/ESOC_PERIPHERAL_MANAGER_BRINGUP_RESEARCH_2026-05-25.md`
  `docs/overview/MDM3_ESOC_SDX50M_BRINGUP_RESEARCH_2026-05-25.md`

## Scope

Host-only. No device command, no bridge command, no tracefs write, no helper
deploy, no daemon start, no `/dev/subsys_*` open, no eSoC ioctl, no Wi-Fi HAL,
no scan/connect, no credentials, no DHCP/route, no external ping, no partition
write, no boot image write, and no flash.

## Method

Implement:

```text
scripts/revalidation/native_wifi_subsys_nonblock_semantics_classifier_v1132.py
```

The classifier checks:

1. `subsys_device_open()` calls `subsystem_get_with_fwname()`.
2. `subsys_device_open()` does not inspect `file->f_flags`.
3. `subsys_device_open()` has no `O_NONBLOCK`/`FMODE_NONBLOCK` branch.
4. `__subsystem_get()` synchronously calls `subsys_start()` when refcount is 0.
5. `subsys_start()` synchronously calls `desc->powerup()`.
6. V1131 evidence proves the pre-holder attempted `/dev/subsys_modem`,
   produced no open result, and the PM Binder worker still blocked in
   `__subsystem_get`.

## Success Criteria

- Source analysis proves there is no nonblocking open behavior in the subsys
  char-device open path.
- V1131 evidence proves the attempted nonblocking pre-holder did not solve the
  lower blocker.
- The route is explicitly closed for another plain/nonblocking
  `/dev/subsys_modem` pre-holder retry.

## Expected Decision

```text
v1132-subsys-open-nonblock-unsupported-route-closed
```

## Next

Move away from `/dev/subsys_modem` synthetic pre-holder retries and classify
lower eSoC/SDX50M powerup preconditions using host-only/read-only evidence
first. The likely next unit is a source/evidence delta around Android-good
`mdm_helper`/`pm_proxy_helper` ordering, eSoC request-engine state, and
`sdx50m_toggle_soft_reset`/GPIO readiness.
