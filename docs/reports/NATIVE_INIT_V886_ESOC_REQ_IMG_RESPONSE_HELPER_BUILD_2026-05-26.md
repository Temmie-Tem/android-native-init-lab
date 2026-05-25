# V886 ESOC_REQ_IMG Response Helper v140 Build Report

## Result

| Unit | Evidence | Decision |
| --- | --- | --- |
| helper build | `tmp/wifi/v886-execns-helper-v140-build/manifest.json` | `v886-helper-v140-build-pass` |

V886 was source/build-only. It did not contact the device, did not deploy the
helper, did not execute live eSoC ioctls, did not open `/dev/subsys_esoc0`, did
not issue `ESOC_NOTIFY`, and did not bring up Wi-Fi.

## Changes

- Updated `stage3/linux_init/helpers/a90_android_execns_probe.c` to helper
  marker `a90_android_execns_probe v140`.
- Repaired passive `ESOC_WAIT_FOR_REQ` observer semantics:
  - rc equal to copied `sizeof(u32)` is now `request-observed`
  - request value `1` is labelled `ESOC_REQ_IMG`
  - output includes byte count, expected byte count, request name, and
    request-observed markers
- Added fail-closed response scaffold markers for:
  - `ESOC_REQ_IMG`
  - `ESOC_IMG_XFER_DONE`
  - `ESOC_BOOT_DONE`
- Preserved `notify_attempted=0`; V886 does not execute a live response.

## Build

```text
bash scripts/revalidation/build_android_execns_probe_helper.sh \
  tmp/wifi/v886-execns-helper-v140-build/a90_android_execns_probe
```

Artifact:

- path: `tmp/wifi/v886-execns-helper-v140-build/a90_android_execns_probe`
- size: `1057232`
- sha256:
  `894fdd753cb6567b2abbb3c94f332ce63cf959b7d1708768cf3bcdc10b2b53e0`
- type: static AArch64 ELF
- dynamic section: absent

String checks passed for:

- `a90_android_execns_probe v140`
- `esoc_req_registered_subsys_hold_preflight.wait_for_req_observer.ioctl.byte_count=%d`
- `esoc_req_registered_subsys_hold_preflight.wait_for_req_observer.ioctl.request_name=%s`
- `esoc_req_registered_subsys_hold_preflight.wait_for_req_observer.ioctl.request_observed=%d`
- `esoc_req_registered_subsys_hold_preflight.wait_for_req_success_semantic=nonnegative-sizeof-u32-byte-count`
- `esoc_req_registered_subsys_hold_preflight.response_scaffold_supported=1`
- `esoc_req_registered_subsys_hold_preflight.response_scaffold.live_response_attempted=0`
- `esoc_req_registered_subsys_hold_preflight.response_scaffold.notify_attempted=0`
- `esoc_req_registered_subsys_hold_preflight.response_scaffold.ESOC_REQ_IMG.value=1`
- `esoc_req_registered_subsys_hold_preflight.response_scaffold.ESOC_IMG_XFER_DONE.value=1`
- `esoc_req_registered_subsys_hold_preflight.response_scaffold.ESOC_BOOT_DONE.value=2`

## Interpretation

V886 closes the helper-side semantics bug that caused V884 `rc=4` to look like
an ioctl error. It does not claim that native init can safely answer the image
request yet. The next safe step is deploy-only parity for helper `v140`; live
`ESOC_NOTIFY` should remain blocked until a separate bounded response gate.

## Guardrails

- No helper deploy or device contact in V886.
- No live `REG_REQ_ENG`, `REG_CMD_ENG`, `CMD_EXE`, `PWR_ON`,
  `WAIT_FOR_REQ`, `NOTIFY`, or `/dev/subsys_esoc0` open.
- No Android actor start, service-manager, Wi-Fi HAL, scan/connect,
  credentials, DHCP/routes, external ping, boot image write, partition write,
  firmware mutation, GPIO/sysfs/debugfs write, module load/unload, or reboot.

## Next

V887 should deploy helper `v140` only and prove checksum/version/mode parity.
The live response path must remain a later bounded gate.
