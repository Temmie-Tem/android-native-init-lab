# V884 REQ-registered Subsystem-hold Observer Report

## Result

| Unit | Evidence | Decision |
| --- | --- | --- |
| plan | `tmp/wifi/v884-esoc-req-registered-subsys-hold-plan/manifest.json` | `v884-esoc-req-registered-subsys-hold-plan-ready` |
| live | `tmp/wifi/v884-esoc-req-registered-subsys-hold-live/manifest.json` | `v884-reboot-required` |
| reboot cleanup | `tmp/wifi/v884-esoc-req-registered-subsys-hold-reboot-cleanup/` | `recovered` |

V884 executed the bounded live REQ-registered subsystem-hold observer gate. It
did not start Android actors, did not start Wi-Fi HAL, did not scan/connect,
did not use credentials, did not change DHCP/routes, and did not run external
ping.

## Live Findings

| Field | Value |
| --- | --- |
| `REG_REQ_ENG` | rc `0`, errno `0` |
| `/dev/subsys_esoc0` child open | attempted, did not return |
| child cleanup | `term_sent=1`, `kill_sent=1`, `reaped=0` |
| helper result | `reboot-required` |
| post surface | helper child remained `Ds` before reboot cleanup |

Passive `ESOC_WAIT_FOR_REQ` observer:

| Field | Value |
| --- | --- |
| `ioctl.request` | `0x8004cc02` |
| `ioctl.rc` | `4` |
| `ioctl.errno` | `0` |
| `ioctl.value` | `1` |
| `elapsed_ms` | `283` |

The helper originally labelled this as `ioctl-error` because it expected rc
`0`, but local OSRC source shows that this ioctl returns the byte count copied
from the request FIFO. `rc=4`, `errno=0`, `value=1` therefore means a request
was observed.

## Source Interpretation

Local A90 OSRC defines:

- `ESOC_WAIT_FOR_REQ` as `_IOR(ESOC_CODE, 2, unsigned int)`
  in `kernel_build/SM-A908N_KOR_12_Opensource/Kernel/include/uapi/linux/esoc_ctrl.h:9`
- `ESOC_REQ_IMG = 1`
  in `kernel_build/SM-A908N_KOR_12_Opensource/Kernel/include/uapi/linux/esoc_ctrl.h:75`

The staged OSRC `esoc_dev.c` path registers REQ engine, waits on
`req_fifo`, copies the request to userspace, and returns `err`, where `err` is
the number of bytes copied by `kfifo_out_spinlocked`:

- `tmp/wifi/v766-icnss-qcacld-patch-apply-build/source/drivers/esoc/esoc_dev.c:238`
- `tmp/wifi/v766-icnss-qcacld-patch-apply-build/source/drivers/esoc/esoc_dev.c:265`
- `tmp/wifi/v766-icnss-qcacld-patch-apply-build/source/drivers/esoc/esoc_dev.c:275`
- `tmp/wifi/v766-icnss-qcacld-patch-apply-build/source/drivers/esoc/esoc_dev.c:285`
- `tmp/wifi/v766-icnss-qcacld-patch-apply-build/source/drivers/esoc/esoc_dev.c:290`

External primary mirror agrees with the UAPI enum values:

- <https://android.googlesource.com/platform/hardware/qcom/msm8994/+/f480e4a/kernel-headers/linux/esoc_ctrl.h>

## State Snapshots

| Phase | `mss` | `mdm3` | `rpmsg_count` | `rpmsg_ipcrtr` |
| --- | --- | --- | --- | --- |
| before | `OFFLINING` | `OFFLINING` | `0` | `0` |
| hold | `OFFLINING` | `OFFLINING` | `0` | `0` |
| after | `OFFLINING` | `OFFLINING` | `0` | `0` |

Node materialization and cleanup succeeded:

- created: `/dev/esoc-0`, `/dev/subsys_esoc0`, `/dev/subsys_modem`
- removed: `/dev/esoc-0`, `/dev/subsys_esoc0`, `/dev/subsys_modem`

## Reboot Cleanup

Because `/dev/subsys_esoc0` open left an unkillable child, recovery reboot was
required. The reboot command naturally lost its protocol END marker during
reset, then native init returned:

- `tmp/wifi/v884-esoc-req-registered-subsys-hold-reboot-cleanup/reboot-command.txt`
- `tmp/wifi/v884-esoc-req-registered-subsys-hold-reboot-cleanup/result.txt`
- `tmp/wifi/v884-esoc-req-registered-subsys-hold-reboot-cleanup/post-bootstatus.json`
- `tmp/wifi/v884-esoc-req-registered-subsys-hold-reboot-cleanup/post-selftest.json`

Post-reboot checks:

- version seen on attempt `03`
- `BOOT OK`: `true`
- selftest: `fail=0`

## Guardrails

- No `REG_CMD_ENG`.
- No direct userspace `CMD_EXE`, explicit userspace `PWR_ON`, or
  `ESOC_NOTIFY`.
- No `mdm_helper`, `ks`, `pm_proxy_helper`, CNSS, service-manager, Wi-Fi HAL,
  scan/connect, credentials, DHCP/routes, or external ping.
- No module load/unload, boot image write, partition write, firmware mutation,
  GPIO/sysfs/debugfs write, or Wi-Fi link-up.

## Interpretation

V884 proves the REQ-side path is real:

1. `REG_REQ_ENG` succeeds.
2. Opening `/dev/subsys_esoc0` causes eSoC to emit `ESOC_REQ_IMG`.
3. Because native does not answer the image request with the Android-equivalent
   transfer/notify sequence, `/dev/subsys_esoc0` remains blocked in D-state.

The earlier assumption that SDX50M may not emit `ESOC_REQ_IMG` is wrong for
this live path. The next blocker is not another open retry; it is understanding
and safely modelling the Android `mdm_helper` image-request response.

## Next

V885 should be host-only first: classify the Android `mdm_helper` response to
`ESOC_REQ_IMG`, including which image transfer path and `ESOC_NOTIFY` value are
required, before any new live ioctl is attempted.
