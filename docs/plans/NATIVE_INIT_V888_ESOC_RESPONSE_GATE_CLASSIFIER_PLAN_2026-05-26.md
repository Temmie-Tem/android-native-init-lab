# V888 eSoC Response Gate Classifier Plan

## Goal

Classify the first safe response gate after V884 observed `ESOC_REQ_IMG` and
V887 deployed helper `v140`. V888 is host-only and must not execute
`ESOC_NOTIFY`.

## Inputs

- V884 request evidence:
  `tmp/wifi/v884-esoc-req-registered-subsys-hold-live/manifest.json`
- V887 deploy evidence:
  `tmp/wifi/v887-execns-helper-v140-deploy-preflight-retry1850/manifest.json`
- local eSoC UAPI:
  `kernel_build/SM-A908N_KOR_12_Opensource/Kernel/include/uapi/linux/esoc_ctrl.h`
- staged Samsung OSRC eSoC source:
  `tmp/wifi/v766-icnss-qcacld-patch-apply-build/source/drivers/esoc/`
- classifier:
  `scripts/revalidation/native_wifi_esoc_response_gate_classifier_v888.py`

## Method

1. Confirm V884 observed `ESOC_REQ_IMG`.
2. Confirm V887 deployed helper `v140`.
3. Trace source semantics for `ESOC_IMG_XFER_DONE`.
4. Trace source semantics for `ESOC_BOOT_DONE`.
5. Decide the next source/build-only helper change before any live response.

## Hard Gates

- Host-only.
- No bridge/device command.
- No live eSoC ioctl.
- No `/dev/subsys_esoc0` open.
- No `ESOC_NOTIFY`.
- No direct userspace `ESOC_PWR_ON`, `REG_CMD_ENG`, or `CMD_EXE`.
- No Android actor start, service-manager, Wi-Fi HAL, scan/connect,
  credentials, DHCP/routes, external ping, boot image write, partition write,
  firmware mutation, GPIO/sysfs/debugfs write, module load/unload, or reboot.

## Success Criteria

- Decision is `v888-esoc-response-gate-classified`.
- The first response is classified as `ESOC_IMG_XFER_DONE`.
- `ESOC_BOOT_DONE` is classified as conditional only after readiness evidence.
- Next step is source/build-only helper `v141`, not a live response run.

## Next

If V888 passes, V889 should build helper `v141` with a fail-closed conditional
response mode: observe `ESOC_REQ_IMG`, send `ESOC_IMG_XFER_DONE`, poll
`ESOC_GET_STATUS`, and only send `ESOC_BOOT_DONE` if readiness is proven.
