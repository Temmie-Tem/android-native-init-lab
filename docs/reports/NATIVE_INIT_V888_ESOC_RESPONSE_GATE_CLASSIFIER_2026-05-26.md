# V888 eSoC Response Gate Classifier Report

## Result

| Unit | Evidence | Decision |
| --- | --- | --- |
| response gate classifier | `tmp/wifi/v888-esoc-response-gate-classifier/manifest.json` | `v888-esoc-response-gate-classified` |

V888 was host-only. It did not contact the device, did not execute live eSoC
ioctls, did not open `/dev/subsys_esoc0`, did not issue `ESOC_NOTIFY`, and did
not bring up Wi-Fi.

## Findings

- V884 established `ESOC_REQ_IMG` after `REG_REQ_ENG`.
- V887 established that helper `v140` is deployed and ready.
- `ESOC_IMG_XFER_DONE` is the first bounded response to `ESOC_REQ_IMG`.
- `ESOC_IMG_XFER_DONE` can schedule modem-status observation when
  `MDM2AP_STATUS` is still low.
- `ESOC_BOOT_DONE` emits `ESOC_RUN_STATE`.
- `ESOC_RUN_STATE` completes the subsystem powerup wait as `PON_SUCCESS`.

## Decision

The next live response proof must not send blind `ESOC_BOOT_DONE`.

The selected response gate is:

1. observe `ESOC_REQ_IMG`
2. notify `ESOC_IMG_XFER_DONE`
3. poll `ESOC_GET_STATUS` or equivalent mdm2ap readiness evidence
4. notify `ESOC_BOOT_DONE` only if readiness is proven

## Guardrails

- no bridge/device command in V888
- no live eSoC ioctl
- no `/dev/subsys_esoc0` open
- no `ESOC_NOTIFY`
- no direct userspace `ESOC_PWR_ON`, `REG_CMD_ENG`, or `CMD_EXE`
- no Android actor start, service-manager, Wi-Fi HAL, scan/connect,
  credentials, DHCP/routes, external ping, boot image write, partition write,
  firmware mutation, GPIO/sysfs/debugfs write, module load/unload, or reboot

## Next

V889 should be source/build-only helper `v141`:

- add conditional response mode
- preserve fail-closed behavior by default
- send no live response in V889
- keep live response for a separate bounded proof with cleanup/reboot criteria
