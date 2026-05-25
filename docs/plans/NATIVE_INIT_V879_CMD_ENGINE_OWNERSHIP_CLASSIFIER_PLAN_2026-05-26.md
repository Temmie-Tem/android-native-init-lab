# V879 CMD Engine Ownership Classifier Plan

## Goal

Classify V878's `REG_CMD_ENG` `EBUSY` result before any retry or power-on
attempt. The immediate decision is whether direct userspace `CMD_EXE` remains
blocked and whether the next useful path is a REQ-registered subsystem powerup
gate.

## Inputs

- V878 manifest:
  `tmp/wifi/v878-esoc-engine-register-preflight-live/manifest.json`
- V878 dmesg filter:
  `tmp/wifi/v878-esoc-engine-register-preflight-live/host/post-dmesg-esoc.txt`
- Local Samsung OSRC:
  - `include/uapi/linux/esoc_ctrl.h`
  - `include/linux/esoc_client.h`
  - `drivers/soc/qcom/subsystem_restart.c`
  - `drivers/bus/mhi/controllers/mhi_arch_qcom.c`
  - `drivers/soc/qcom/icnss.c`
  - `drivers/net/wireless/cnss2/main.c`
- Research overview:
  `docs/overview/ESOC_PERIPHERAL_MANAGER_BRINGUP_RESEARCH_2026-05-25.md`

## Method

1. Parse V878's `REG_CMD_ENG` and `REG_REQ_ENG` ioctl results.
2. Confirm V878 cleanup, selftest, actor-clean, and Wi-Fi-link-clean stayed
   valid.
3. Confirm local eSoC UAPI numbers and subsystem char-device source contract.
4. Confirm local MHI/CNSS eSoC client-hook surfaces exist.
5. Select the next gate without contacting the device.

## Hard Gates

- Host-only only; no bridge/device command.
- No helper deploy, eSoC ioctl, `/dev/subsys_esoc0` open, actor start, Wi-Fi
  HAL, scan/connect, credentials, DHCP/routes, or external ping.
- No module load/unload, boot image write, partition write, firmware mutation,
  GPIO/sysfs/debugfs write, or reboot.

## Success Criteria

- Decision is `v879-cmd-engine-ebusy-classified`.
- Direct userspace `CMD_EXE` remains blocked because command-engine ownership
  was not acquired.
- V879 selects a source/build-only next step for helper repair plus
  REQ-registered subsystem-hold preflight support.

## Next

If V879 passes, V880 should be source/build-only helper `v138` work:

- clear stale errno before successful `/dev/esoc-0` opens,
- add a fail-closed REQ-registered subsystem-hold preflight mode,
- still block direct userspace `CMD_EXE`, explicit userspace `PWR_ON`,
  `WAIT_FOR_REQ`, `NOTIFY`, actors, and Wi-Fi bring-up.
