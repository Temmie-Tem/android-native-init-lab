# V889 eSoC Conditional Response Helper v141 Build Report

## Result

| Unit | Evidence | Decision |
| --- | --- | --- |
| helper build | `tmp/wifi/v889-execns-helper-v141-build/manifest.json` | `v889-helper-v141-build-pass` |

V889 was source/build-only. It did not contact the device, did not deploy the
helper, did not execute live eSoC ioctls, did not open `/dev/subsys_esoc0`, did
not issue `ESOC_NOTIFY`, and did not bring up Wi-Fi.

## Changes

- Updated `stage3/linux_init/helpers/a90_android_execns_probe.c` to helper
  marker `a90_android_execns_probe v141`.
- Added mode `wifi-companion-esoc-conditional-response-preflight`.
- Added allow flag `--allow-esoc-conditional-response-preflight`.
- Added conditional response child logic:
  - wait for `ESOC_REQ_IMG`
  - send `ESOC_IMG_XFER_DONE`
  - poll `ESOC_GET_STATUS`
  - send `ESOC_BOOT_DONE` only if status value becomes `1`
- Preserved fail-closed validation so the new response path is unreachable
  without the exact new mode and allow flag.

## Build

```text
bash scripts/revalidation/build_android_execns_probe_helper.sh \
  tmp/wifi/v889-execns-helper-v141-build/a90_android_execns_probe
```

Artifact:

- path: `tmp/wifi/v889-execns-helper-v141-build/a90_android_execns_probe`
- size: `1057232`
- sha256:
  `e6909cbfee79a4a1f55a3f039cdc29dca57f31e00c19d63a1a452d633c060f21`
- type: static AArch64 ELF
- dynamic section: absent

String checks passed for:

- `a90_android_execns_probe v141`
- `wifi-companion-esoc-conditional-response-preflight`
- `--allow-esoc-conditional-response-preflight`
- `esoc_req_registered_subsys_hold_preflight.conditional_response_mode=%d`
- `esoc_conditional_response_preflight.mode=conditional-img-xfer-status-gated-boot-done`
- `esoc_conditional_response_preflight.notify.ESOC_IMG_XFER_DONE.planned=1`
- `esoc_conditional_response_preflight.notify.ESOC_BOOT_DONE.planned=conditional`
- `esoc_conditional_response_preflight.notify.ESOC_BOOT_DONE.condition=GET_STATUS-1`
- `esoc_conditional_response_preflight.status.ready=%d`
- `esoc_conditional_response_preflight.notify.ESOC_BOOT_DONE.sent=%d`

## Interpretation

V889 prepares the exact response sequence selected by V888 but does not run it.
The next safe step is deploy-only helper `v141` parity. A live conditional
response attempt should remain separate and must include timeout and reboot
cleanup handling.

## Guardrails

- No helper deploy or device contact in V889.
- No live `REG_REQ_ENG`, `REG_CMD_ENG`, `CMD_EXE`, `PWR_ON`,
  `WAIT_FOR_REQ`, `NOTIFY`, or `/dev/subsys_esoc0` open.
- No Android actor start, service-manager, Wi-Fi HAL, scan/connect,
  credentials, DHCP/routes, external ping, boot image write, partition write,
  firmware mutation, GPIO/sysfs/debugfs write, module load/unload, or reboot.

## Next

V890 should deploy helper `v141` only and prove checksum/version/mode parity.
The live conditional response path remains a later bounded gate.
