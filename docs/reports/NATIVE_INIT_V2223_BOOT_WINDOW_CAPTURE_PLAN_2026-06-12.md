# Native Init V2223 Boot-Window Capture Plan

## Result

- decision: `v2223-boot-window-plan-ready-approval-required`
- pass: `true`
- runner: `workspace/public/src/scripts/revalidation/native_kernel_a90_boot_window_plan_v2223.py`
- evidence: `workspace/private/runs/kernel/v2223-boot-window-plan-20260612-070207/`
- plan: `workspace/private/runs/kernel/v2223-boot-window-plan-20260612-070207/boot_window_execution_plan.json`
- source preflight: `workspace/private/runs/kernel/v2222-boot-window-preflight-20260612-065709/summary.json`

## What Ran

```bash
python3 -m py_compile \
  workspace/public/src/scripts/revalidation/native_kernel_a90_boot_window_plan_v2223.py
PYTHONPATH=workspace/public/src/scripts/revalidation \
  python3 workspace/public/src/scripts/revalidation/native_kernel_a90_boot_window_plan_v2223.py
```

The runner is host-only. It consumed the latest V2222 preflight contract,
audited the helper source route, inventoried baseline boot images, and wrote a
boot-window execution plan.

It did not talk to the device, reboot, flash, create or enable tracefs events,
attach BPF, execute `probe_write_user`, scan/connect Wi-Fi, change routes, or
write partitions.

## Evidence Summary

| Signal | Value |
| --- | ---: |
| V2222 preflight pass | `true` |
| source route audit | `true` |
| baseline V2189 boot present | `true` |
| ready for approval | `true` |
| dedicated V2223 observer test boot present | `false` |
| device I/O | `false` |

Audited helper source markers:

- mode: `wifi-companion-wlan-pd-cnss-output-visibility-start-only`
- allow flag: `--allow-wlan-pd-cnss-output-visibility`
- summary function: `append_wlan_pd_cnss_nonlog_control_flow_summary`
- trace collector: `cnss_wlfw_uprobe_collect_trace`
- result path flag: `--result-output-path`
- mode/allow guard: present

Baseline boot images recorded in the plan:

| Image | SHA-256 | Size |
| --- | --- | ---: |
| `workspace/private/inputs/boot_images/boot_linux_v2189_security_p0_stage_fix.img` | `f54becb2b720ad198413c2a0089912626ca295c79a96f13e0921cf4f05b39f51` | `60948480` |
| `workspace/private/inputs/boot_images/boot_linux_v725_fasttransport.img` | `b9afa0e3c1c677c55a764a0b8dbd7027089dd134318084332bfd52cdf008830f` | `59166720` |
| `workspace/private/inputs/boot_images/boot_linux_v724.img` | `ae01fa106391756dae12fc9a6c9f57d4111b2180c82cdcfe3691ee31f7542adc` | `54571008` |

## Capture Contract

The approved boot-window capture should observe:

```text
a90cnss:wlfw_start
→ a90cnss:wlfw_service_request
→ a90cnss:wlfw_cap_qmi
→ a90cnss:wlfw_bdf_entry
```

The helper runtime route is:

```text
/bin/a90_android_execns_probe
  --system-root /mnt/system/system
  --vendor-block /dev/block/sda29
  --vendor-fstype ext4
  --target-profile cnss-daemon
  --mode wifi-companion-wlan-pd-cnss-output-visibility-start-only
  --allow-wlan-pd-cnss-output-visibility
  --result-output-path /mnt/sdext/a90/logs/<label>-helper.result
  --timeout-sec 95
```

That command is recorded for command-shape validation only. The actual capture
must run in an early supervised helper/test-boot window. A late manual helper
invocation can test plumbing, but it cannot substitute for boot-window WLFW/QMI
evidence.

## Remaining Gap

V2223 confirms the plan is ready for approval, but it also makes the remaining
artifact gap explicit:

- no dedicated V2223 observer test-boot image exists yet;
- live boot-window capture therefore needs either:
  1. selecting an existing rollbackable observer test boot with this helper
     mode; or
  2. building a new rollbackable V2224 observer test boot from the current
     baseline.

Both paths still require explicit approval before any flash/reboot.

## Next

V2224 can proceed host-only by building the dedicated observer test-boot
artifact. The live V2225 capture should only run after explicit user approval
and should immediately postprocess the helper summary through the V2220 parser.
