# V879 CMD Engine Ownership Classifier Report

## Result

| Unit | Evidence | Decision |
| --- | --- | --- |
| classifier | `tmp/wifi/v879-cmd-engine-ownership-classifier/manifest.json` | `v879-cmd-engine-ebusy-classified` |

V879 was host-only. It did not contact the device, did not deploy helpers, did
not execute eSoC ioctls, and did not bring up Wi-Fi.

## Inputs

V878 live evidence:

| Operation | rc | errno | Meaning |
| --- | --- | --- | --- |
| `REG_CMD_ENG` | `-1` | `16` | command-engine ownership was not acquired |
| `REG_REQ_ENG` | `0` | `0` | request-engine registration path works |

V878 postflight remained clean:

- cleanup removed created nodes
- selftest stayed `fail=0`
- actor hits: `0`
- Wi-Fi link hits: `0`
- dmesg included `mdm-4x esoc0: Client hooks not registered for the device`

## Classification

| Question | Answer |
| --- | --- |
| Can userspace call direct `ESOC_CMD_EXE` next? | no |
| Why? | public `esoc_dev.c` gates `ESOC_CMD_EXE` on command-engine ownership, and V878 did not acquire that ownership |
| Does the REQ-side blocker improve? | yes, `REG_REQ_ENG` returned rc `0` |
| What is the next candidate? | source/build-only helper support for holding a REQ fd while testing a bounded subsystem-open path |
| Is the next step live? | no, V880 should be source/build-only |

Local OSRC confirms the relevant surfaces:

- `include/uapi/linux/esoc_ctrl.h` has `ESOC_REG_REQ_ENG=7` and
  `ESOC_REG_CMD_ENG=8`.
- `include/linux/esoc_client.h` exposes MHI/CNSS eSoC client hook priorities.
- `drivers/bus/mhi/controllers/mhi_arch_qcom.c` registers an eSoC client and
  power-on hook.
- `drivers/soc/qcom/icnss.c` registers an eSoC client hook path.
- `drivers/soc/qcom/subsystem_restart.c` keeps subsystem `state` read-only and
  routes char-device open through `subsystem_get_with_fwname()`.

## Interpretation

The V878 `EBUSY` result closes direct userspace `CMD_EXE` for now. The useful
path is to keep using the kernel subsystem path rather than trying to own the
command engine from the helper. V878 proved the REQ engine can be registered,
which targets the earlier V849 `req_eng_wait` blocker. The next proof must also
capture the eSoC client-hook state because V878 dmesg reports missing client
hooks.

## Guardrails

- No direct userspace `ESOC_CMD_EXE` or explicit userspace `ESOC_PWR_ON`.
- No `WAIT_FOR_REQ`, no `NOTIFY`, and no actor start in the next source/build
  helper cycle.
- No Wi-Fi HAL, scan/connect, credentials, DHCP/routes, external ping, module
  load/unload, boot image write, partition write, firmware mutation,
  GPIO/sysfs/debugfs write, or reboot in V879.

## References

- Public eSoC ioctl path:
  https://android.googlesource.com/kernel/msm/+/d210dd22d8bfbd55a320f57eaac861137dd3eca0%5E2..d210dd22d8bfbd55a320f57eaac861137dd3eca0/
- Public eSoC UAPI header:
  https://android.googlesource.com/platform/hardware/qcom/msm8994/+/f480e4a/kernel-headers/linux/esoc_ctrl.h

## Next

V880 should be source/build-only helper `v138` work:

1. clear stale `errno` before successful `/dev/esoc-0` opens,
2. add a fail-closed REQ-registered subsystem-hold preflight mode,
3. keep direct userspace `CMD_EXE`, explicit userspace `PWR_ON`,
   `WAIT_FOR_REQ`, `NOTIFY`, actor starts, and Wi-Fi bring-up blocked.
