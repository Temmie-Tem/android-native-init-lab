# V894 MDM2AP Ready Surface Classifier Report

## Result

| Unit | Evidence | Decision |
| --- | --- | --- |
| classifier | `tmp/wifi/v894-mdm2ap-ready-surface/manifest.json` | `v894-mdm2ap-ready-surface-classified` |

V894 found a safe read-only observer for the next readiness proof.

## Findings

Source evidence:

- `sdx5xm-external-soc.dtsi` maps `qcom,mdm2ap-status-gpio` to GPIO `142`.
- `sdx5xm-external-soc.dtsi` maps `qcom,ap2mdm-status-gpio` to GPIO `135`.
- `sm8150-sdx50m.dtsi` marks the external modem as `qcom,ext-sdx50m`.
- `esoc-mdm-4x.c` handles `MDM2AP_STATUS` IRQ and sets `mdm->ready = true`
  when the status value becomes `1`.

Current native read-only surface:

- `/sys/bus/msm_subsys/devices/subsys9/state` reports `OFFLINING`.
- debugfs GPIO is not available in the current native boot.
- `/proc/interrupts` exposes:
  `msmgpio-dc 142 Edge mdm status`.
- The observed mdm status IRQ total is currently `0`.

## Interpretation

The next useful live proof can avoid GPIO export/write and debugfs writes.
Sampling `/proc/interrupts` around the existing guarded `ESOC_IMG_XFER_DONE`
flow can tell whether the MDM2AP status IRQ fires at all.

Local ESOC source also confirms that initial power-up is gated on
`REG_REQ_ENG`, not `REG_CMD_ENG`. V891 already observed `ESOC_REQ_IMG`, so the
next proof should keep the existing request-engine path and add only the
read-only MDM2AP IRQ snapshots.

If the IRQ count does not change after image-done, the blocker is below
userspace notification: SDX50M does not drive MDM2AP status high. If the IRQ
count changes but `ESOC_GET_STATUS` remains `0`, the blocker is in the kernel
ready-state handling after the IRQ.

## Guardrails

- no device mutation
- no live eSoC ioctl
- no `/dev/subsys_esoc0` open
- no `ESOC_NOTIFY`
- no GPIO export/write, debugfs write, sysfs write, actor start, Wi-Fi HAL,
  scan/connect, credentials, DHCP/routes, or external ping

## Next

V895 should add bounded `mdm status` IRQ snapshots to the conditional response
flow and rerun the live proof with cleanup reboot. `ESOC_BOOT_DONE` remains
blocked unless readiness is proven.
