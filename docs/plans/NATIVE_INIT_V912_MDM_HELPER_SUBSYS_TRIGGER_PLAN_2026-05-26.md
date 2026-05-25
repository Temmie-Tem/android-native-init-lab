# Native Init V912 mdm_helper-held Subsystem Trigger Plan

## Goal

Use the V911 result to plan the next bounded live gate: trigger subsystem
powerup while `mdm_helper` already owns `/dev/esoc-0` and is blocked in
`ESOC_WAIT_FOR_REQ`.

V912 is a planning/design unit. It must not execute the trigger.

## Current Evidence

V911 established:

```text
mdm_helper main thread: SyS_nanosleep
mdm_helper worker thread: esoc_dev_ioctl
worker syscall: ioctl(fd=3, request=0x8004cc02)
decoded request: ESOC_WAIT_FOR_REQ
/dev/esoc-0 fd: present
/dev/subsys_esoc0 fd: absent
ks/MHI/WLFW/wlan0: absent
```

The meaning is narrow and important: the native runtime can now reach the
eSoC request-engine wait path, but no lower powerup/request event is being
generated.

## Candidate Gate

Add a new helper mode after V912:

```text
wifi-companion-mdm-helper-runtime-subsys-trigger-capture
```

Suggested sequence:

1. Mount system/vendor/firmware surfaces as in V908.
2. Mount selinuxfs with cleanup.
3. Bind private property root.
4. Start property shim.
5. Start `per_mgr_light` (`/vendor/bin/pm-service`).
6. Start `mdm_helper`.
7. Wait until `mdm_helper` has `/dev/esoc-0` and worker is in
   `ESOC_WAIT_FOR_REQ`.
8. In a separate short-lived child, open `/dev/subsys_esoc0` only.
9. Capture whether `mdm_helper` receives an eSoC request, starts `ks`, creates
   the MHI pipe, triggers GPIO142, changes `mdm3`, or exposes WLFW/BDF/wlan0.
10. Terminate children and run cleanup/reboot if any actor is not proven safe.

## Hard Guardrails

- No `pm_proxy_helper`.
- No direct `REG_REQ_ENG` from the controller path; `mdm_helper` owns
  `/dev/esoc-0`.
- No controller `ESOC_NOTIFY`, `BOOT_DONE`, or fake response unless a later
  gate explicitly separates that step.
- No service-manager, CNSS daemon, Wi-Fi HAL, scan/connect, credentials,
  DHCP/routes, or external ping.
- No boot image write, partition write, firmware mutation, GPIO/sysfs/debugfs
  write, module load/unload, or Wi-Fi link-up.
- If `/dev/subsys_esoc0` child enters D-state or cannot be reaped, perform the
  established cleanup reboot and require post-boot `bootstatus`/`selftest`.

## Success Criteria For The Future Live Gate

At minimum the future live gate must record:

- `mdm_helper` remains in `ESOC_WAIT_FOR_REQ` or receives an eSoC request;
- `/dev/subsys_esoc0` trigger child lifecycle, wchan, syscall, and cleanup;
- `/vendor/bin/ks` process count and cmdline;
- `/dev/mhi_0305_01.01.00_pipe_10` global/private visibility;
- GPIO142 IRQ count before/during/after;
- `subsys9/state` before/during/after;
- WLFW/BDF/wlan0/QRTR dmesg and proc/net deltas;
- final actor-clean and Wi-Fi-link-clean surfaces.

## Stop Conditions

- `mdm_helper` does not reach `ESOC_WAIT_FOR_REQ` before trigger.
- `/dev/subsys_esoc0` open blocks without observable request delivery.
- Any actor cannot be terminated cleanly.
- Wi-Fi link appears unexpectedly without an explicit bring-up gate.

## Next

V913 should implement the source/build-only helper support for the new
`mdm_helper-held subsys trigger` mode. The first live run should remain
diagnostic-only and should expect cleanup/reboot as a possible normal outcome.
