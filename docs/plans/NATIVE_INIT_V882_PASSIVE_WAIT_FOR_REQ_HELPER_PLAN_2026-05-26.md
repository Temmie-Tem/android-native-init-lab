# V882 Passive WAIT_FOR_REQ Observer Helper Plan

## Goal

Add helper source/build-only support for passive `ESOC_WAIT_FOR_REQ`
observation during the future REQ-registered `/dev/subsys_esoc0` hold window.
The intent is to distinguish SDX50M flash/self-boot behavior from older
Sahara-style image request behavior before the next live powerup attempt.

## Inputs

- V881 deploy result:
  `docs/reports/NATIVE_INIT_V881_HELPER_V138_DEPLOY_2026-05-26.md`
- eSoC / PeripheralManager overview:
  `docs/overview/ESOC_PERIPHERAL_MANAGER_BRINGUP_RESEARCH_2026-05-25.md`
- helper source:
  `stage3/linux_init/helpers/a90_android_execns_probe.c`

## Research Basis

- Initial subsystem powerup is gated by `REG_REQ_ENG` availability, not by
  userspace `REG_CMD_ENG` ownership.
- Kernel eSoC code can execute the initial power-on command internally after
  `mdm_subsys_powerup()` passes the request-engine wait.
- SDX50M may not issue `ESOC_REQ_IMG`; if no request appears while mdm3
  progresses, that supports the PCIe/self-boot path.
- If `ESOC_WAIT_FOR_REQ` does produce a request, the next gate must classify
  the exact request before any `ESOC_NOTIFY` implementation.

## Method

1. Bump helper marker to `v139`.
2. Extend the REQ-registered subsystem-hold mode with passive wait-request
   observer markers.
3. Run the observer in a bounded child or equivalent killable process group so
   a blocking ioctl is explicit evidence, not an untracked hang.
4. Keep `ESOC_NOTIFY`, explicit userspace `PWR_ON`, direct userspace
   `CMD_EXE`, actor starts, Wi-Fi HAL, scan/connect, DHCP/routes, credentials,
   and external ping blocked.
5. Build a static ARM64 artifact and verify marker/mode/flag strings.

## Hard Gates

- Source/build-only.
- No helper deploy.
- No bridge or device command.
- No live eSoC ioctl or `/dev/subsys_esoc0` open.
- No `ESOC_NOTIFY` implementation in V882.
- No actor start, Wi-Fi HAL, scan/connect, credentials, DHCP/routes, external
  ping, boot image write, partition write, firmware mutation, GPIO/sysfs/debugfs
  write, module load/unload, or reboot.

## Success Criteria

- Static build succeeds with no dynamic section.
- Artifact advertises helper marker `a90_android_execns_probe v139`.
- Artifact includes passive wait-request observer markers.
- V882 report explicitly states whether live execution is still pending.

## Next

If V882 passes, V883 can deploy helper `v139` only. A later bounded live gate
can then run the REQ-registered subsystem-hold proof with passive
`ESOC_WAIT_FOR_REQ` observation and no Wi-Fi bring-up.
