# Native Init V854 eSoC Actor Parity Classifier Plan

## Goal

Classify the smallest safe native-equivalent contract from the V853 Android
actor evidence before any live eSoC actor replay.

## Inputs

- V853 Android actor evidence:
  `tmp/wifi/v853-android-esoc-actor-handoff/v853-android-esoc-actor-run/manifest.json`
- V853 report:
  `docs/reports/NATIVE_INIT_V853_ANDROID_ESOC_ACTOR_HANDOFF_2026-05-25.md`
- Prior closure reports:
  - `docs/reports/NATIVE_INIT_V849_SUBSYS_ESOC0_WAIT_STATE_SAMPLER_2026-05-25.md`
  - `docs/reports/NATIVE_INIT_V840_PROVIDER_FIRST_PREARMED_LISTENER_2026-05-25.md`
  - `docs/reports/NATIVE_INIT_V764_SERVICE180_MDM_HELPER_RETRY_2026-05-24.md`

## Method

1. Parse V853 Android node, holder, ueventd, and SELinux contracts.
2. Reconcile them with prior native failures:
   manual `/dev/subsys_esoc0` open, `mdm_helper` retry, and provider-first
   PeripheralManager/CNSS retry.
3. Rank next candidates without contacting the device.
4. Select the next live gate only if it is narrower than GPIO/eSoC ioctl or
   HAL/connect.

## Guardrails

- Host-only only.
- No bridge, ADB, QRTR socket, device command, node creation/open/ioctl,
  service start, GPIO/sysfs/debugfs write, subsystem state write, module
  load/unload, boot image write, partition write, Wi-Fi HAL, scan/connect,
  credential use, DHCP/routes, or external ping.

## Success Criteria

- V853 input is present and passed.
- Android node, holder, and policy contracts are complete enough to rank.
- Prior retry closures are accounted for.
- Next gate is selected below Wi-Fi HAL/connect and below raw GPIO/eSoC writes.

## Commands

```bash
python3 scripts/revalidation/native_wifi_esoc_actor_parity_classifier_v854.py \
  --out-dir tmp/wifi/v854-esoc-actor-parity-classifier \
  run
```
