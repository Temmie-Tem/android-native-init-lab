# V883 Helper v139 Deploy-only Report

## Result

| Unit | Evidence | Decision |
| --- | --- | --- |
| plan | `tmp/wifi/v883-execns-helper-v139-plan/manifest.json` | `execns-helper-v139-deploy-plan-ready` |
| preflight | `tmp/wifi/v883-execns-helper-v139-preflight/manifest.json` | `execns-helper-v139-deploy-preflight-ready` |
| deploy | `tmp/wifi/v883-execns-helper-v139-deploy-preflight/manifest.json` | `execns-helper-v139-deploy-pass` |
| postdeploy read-only check | `tmp/wifi/v883-execns-helper-v139-postdeploy/manifest.json` | `execns-helper-v139-deploy-preflight-ready` |

V883 deployed helper `v139` to `/cache/bin/a90_android_execns_probe`.
It did not execute live eSoC ioctls, did not open `/dev/subsys_esoc0`,
did not start Android actors, and did not bring up Wi-Fi.

## Deployed Artifact

- local artifact:
  `tmp/wifi/v882-execns-helper-v139-build/a90_android_execns_probe`
- remote path: `/cache/bin/a90_android_execns_probe`
- sha256:
  `077ced65ae5b0b546ecdf3b1bb0c808d3ec34bfa2462516e6ceba170b18f23c5`
- marker: `a90_android_execns_probe v139`
- mode token:
  `wifi-companion-esoc-req-registered-subsys-hold-preflight`

The postdeploy preflight confirmed remote helper parity:

- `remote-helper-v139`: `pass`
- `sha_match`: `True`
- `marker_mode`: `True`

## Transfer

NCM was not available, so the deploy wrapper used serial
appendfile/uudecode:

- method: `serial`
- chunk size: `1850`
- chunks written: `788`
- encoded bytes: `1456699`
- max cmdv1 line bytes: `3890`
- safe line limit: `3968`
- `cmdv1x`: `True`

The serial line-size check passed before writing chunks.

## Health Checks

- native version: `A90 Linux init 0.9.68 (v724)`
- native status/selftest: `rc=0`, `fail=0`
- post-deploy direct selftest: `pass=11 warn=1 fail=0`
- service-manager process hits: `0`
- Wi-Fi netdev hits: `0`

Host NCM address and NCM reachability stayed warning-only because transfer
method was `auto` and the active native `netservice` was not enabled.

## Guardrails

- No live `REG_REQ_ENG`, `REG_CMD_ENG`, `CMD_EXE`, explicit userspace
  `PWR_ON`, `WAIT_FOR_REQ`, `NOTIFY`, or `/dev/subsys_esoc0` open.
- No `mdm_helper`, `ks`, `pm_proxy_helper`, CNSS, service-manager, Wi-Fi HAL,
  scan/connect, credentials, DHCP/routes, or external ping.
- No boot image, partition, firmware, GPIO, sysfs, debugfs, module, or reboot
  action.

## Interpretation

V883 closes the deployment prerequisite for the helper that can observe a
passive `ESOC_WAIT_FOR_REQ` result during a future REQ-registered
subsystem-hold window. The next live gate should rely on `REG_REQ_ENG` as the
required unlock, not on `REG_CMD_ENG` ownership, and should treat absence of
`ESOC_REQ_IMG` as diagnostic data rather than immediate failure.

## Next

V884 should run a bounded live REQ-registered subsystem-hold observer
preflight using deployed helper `v139`. It should record the passive
`ESOC_WAIT_FOR_REQ` observer result while continuing to block Android actors,
Wi-Fi HAL, scan/connect, credentials, DHCP/routes, and external ping.
