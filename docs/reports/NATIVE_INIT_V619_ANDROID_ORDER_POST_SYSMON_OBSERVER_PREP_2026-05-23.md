# Native Init V619 Android-Order Post-Sysmon Observer Prep Report

- date: `2026-05-23 KST`
- helper: `a90_android_execns_probe v104`
- runner: `scripts/revalidation/native_wifi_android_order_post_sysmon_observer_v619.py`
- deploy preflight: `scripts/revalidation/wifi_execns_helper_v104_deploy_preflight.py`
- evidence:
  - `tmp/wifi/v619-execns-helper-v104-build/`
  - `tmp/wifi/v619-android-order-post-sysmon-observer-plan/`
  - `tmp/wifi/v619-execns-helper-v104-deploy-plan/`
  - `tmp/wifi/v619-android-order-post-sysmon-observer-preflight/`
  - `tmp/wifi/v619-execns-helper-v104-deploy-preflight/`
- decision: `v619-android-order-observer-prep-ready-with-env-blockers`
- status: prep pass; live execution remains blocked by current environment

## Scope

V619 implements the V618 next gate: a no-CNSS/no-HAL Android-order lower
companion observer. It is intended to determine whether the missing native
`service-notifier` publication is caused by companion ordering around
`pd_mapper`, not by CNSS/HAL/userspace Wi-Fi retry logic.

## Implemented Contract

```text
helper_version: a90_android_execns_probe v104
mode: wifi-companion-android-order-post-sysmon-observer-start-only
order: qrtr_ns,pd_mapper,rmt_storage,tftp_server
CNSS: not started
service-manager: not started
Wi-Fi HAL: not started
scan/connect/link-up: not executed
external ping: not executed
QMI payload: 0
```

The helper keeps the existing post-sysmon observer guardrails and only changes
the lower companion order. The runner reuses the V615 firmware/DSP/modem-holder
observer path and changes the companion command to the new v104 mode.

## Validation

Static build:

```text
artifact: tmp/wifi/v619-execns-helper-v104-build/a90_android_execns_probe
sha256: f811c18d1a9af92f5ca9fadcfd4dbd94593318240744a0c86d0419280bbea019
static: no INTERP segment and no dynamic section
```

Plan checks:

```text
native observer plan: v619-android-order-post-sysmon-observer-plan-ready
helper deploy plan: execns-helper-v104-deploy-plan-ready
```

Current live preflight is blocked before mutation:

```text
helper deploy: blocked by host-ncm-address, ncm-host-reachable
observer: blocked by v490-current-policy-load, helper-v104-ready,
          firmware surface/current menu busy state, subsys_modem/boot-node
          visibility checks
```

These blockers are environmental/current-boot prerequisites. They do not
invalidate the helper v104 contract.

## Interpretation

The V598/V597 observation remains valid: `service-notifier` appears immediately
after `sysmon-qmi` in Android, which points to a kernel/QMI registration event
rather than a late userspace CNSS/HAL trigger. V619 now provides the narrow
native test for the remaining actionable delta:

```text
pd_mapper before rmt_storage/tftp_server
```

If V619 live restores `service-notifier` `180/74`, the next gate should be a
CNSS-only WLFW/BDF observer. If V619 live still reaches sibling `sysmon-qmi`
without service-notifier, the next gate should classify the lower QMI service
publication dependency before any HAL or Wi-Fi link action.

## Next Steps

1. Restore current command surface by hiding/quitting the auto menu before
   preflight commands.
2. Restore NCM host address or use explicit serial transfer for helper deploy.
3. Refresh current-boot V401/V490 policy-load evidence.
4. Deploy helper v104.
5. Run V619 bounded observer with reboot cleanup.

