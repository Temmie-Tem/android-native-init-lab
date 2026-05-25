# Native Init V915 Corrected Native Trigger Gate Plan

## Goal

Use V914 to correct the next native trigger gate before implementing or running
another `/dev/subsys_esoc0` live attempt.

V915 is a planning/design unit. It does not run a live trigger.

## Inputs

- V911: native `mdm_helper` reaches `/dev/esoc-0` and blocks in
  `ESOC_WAIT_FOR_REQ`.
- V912: proposed `mdm_helper`-held `/dev/subsys_esoc0` trigger gate.
- V913: Android handoff captured the positive Android boot timeline and restored
  native v724.
- V914: Android upper Wi-Fi path is positive while post-boot lower markers are
  non-positive.

## Corrected Interpretation

The V914 result changes the success model:

```text
Android positive path:
service-notifier 180/74
  -> WLFW start
  -> WLAN-PD indication
  -> BDF regdb/bdwlan
  -> wlan0

Android sampled lower post-boot state:
subsys9/state=OFFLINING
GPIO142 mdm status IRQ count=0
current ks=false
current MHI pipe=false
```

Therefore the next native trigger must not require sampled post-boot
`subsys9=ONLINE`, GPIO142 IRQ increment, current `ks`, or current MHI pipe as
mandatory success criteria. Those are diagnostics only.

## Candidate Gate

Keep the V912 candidate but correct its success criteria:

```text
wifi-companion-mdm-helper-runtime-subsys-trigger-capture
```

Suggested live sequence for the future implementation:

1. Mount system/vendor/firmware surfaces as in V908.
2. Mount selinuxfs with cleanup.
3. Bind private property root.
4. Start property shim.
5. Start `per_mgr_light` (`/vendor/bin/pm-service`), excluding
   `pm_proxy_helper`.
6. Start `mdm_helper`.
7. Wait until `mdm_helper` holds `/dev/esoc-0` and worker is in
   `ESOC_WAIT_FOR_REQ`.
8. Trigger a short-lived, separately monitored `/dev/subsys_esoc0` open.
9. Capture request delivery, child lifecycle, wchan/syscall/stack, and cleanup.
10. Classify upper Wi-Fi progression first: service-notifier, WLFW, BDF, `wlan0`.

## Success Criteria

Primary success markers:

- service-notifier `180` and `74` connection/indication;
- `cnss-daemon wlfw_start`;
- WLAN-PD state indication;
- BDF requests for `regdb.bin` and `bdwlan.bin`;
- `wlan0` or a clear next ICNSS/HDD boundary.

Diagnostic lower markers:

- `mdm_helper` `/dev/esoc-0` fd and `ESOC_WAIT_FOR_REQ` state;
- `/dev/subsys_esoc0` trigger child lifecycle;
- `pm-service` `/dev/subsys_modem` and `/dev/subsys_esoc0` fd state;
- `subsys9/state`;
- GPIO142 IRQ line and count;
- `ks` and MHI pipe visibility;
- PCIe/MHI dmesg if present.

## Hard Guardrails

- No Wi-Fi HAL start, scan/connect, credentials, DHCP/routes, or external ping.
- No `pm_proxy_helper`.
- No controller `ESOC_NOTIFY`, `BOOT_DONE`, or fake response in the first live
  attempt.
- No boot image write, partition write, firmware mutation, GPIO/sysfs/debugfs
  write, module load/unload, or Wi-Fi link-up.
- If the trigger child enters D-state or cannot be reaped, perform cleanup
  reboot and require post-boot `bootstatus`/`selftest`.

## Stop Conditions

- `mdm_helper` does not reach `ESOC_WAIT_FOR_REQ`.
- `/dev/subsys_esoc0` child blocks without observable request delivery.
- Any actor remains after cleanup.
- Service-notifier/WLFW/BDF/`wlan0` surfaces do not move and the lower evidence
  does not explain why.

## Next

V916 should be source/build-only helper support for the corrected trigger mode.
The later live run should stay diagnostic-only and should treat cleanup/reboot
as an expected possible outcome.
