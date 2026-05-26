# V1002 Android Service-window Subsystem Trigger Support Plan

## Goal

Add source/build-only helper support for the V1001-selected next gate: a
service-window-scoped `/dev/subsys_esoc0` trigger capture.

V1001 showed the previous WLFW-precondition gate was circular because Android
reaches `/dev/subsys_esoc0` get before `wlfw_start`. V1002 therefore prepares a
narrow helper mode that can attempt the subsystem open only after the Android
Wi-Fi service-window actors are already running and `mdm_helper` is observed
holding `/dev/esoc-0`.

## Scope

Modify `stage3/linux_init/helpers/a90_android_execns_probe.c` only.

Add:

- helper version `v170`;
- mode `wifi-companion-android-wifi-service-window-subsys-trigger-capture`;
- allow flag `--allow-android-wifi-service-window-subsys-trigger-capture`;
- fail-closed validation requiring both service-window allow flags;
- post-spawn `/proc/<mdm_helper>/fd` gate for `/dev/esoc-0`;
- trigger child using the existing `/dev/subsys_esoc0` opener;
- D-state/blocker snapshot and read-only Wi-Fi/eSoC surface captures;
- cleanup accounting for trigger child termination/reaping.

## Guardrails

V1002 is source/build-only.

- No deploy.
- No device command.
- No actor start.
- No `/dev/subsys_esoc0` open on the live device.
- No eSoC ioctl.
- No Wi-Fi scan/connect/link-up.
- No credential use.
- No DHCP, route mutation, or external ping.
- No boot image or partition write.

The live V1003/V1004 sequence must refresh current-boot SELinux proof before
using the new mode because reboot/rollback loses V490 policy state.

## Expected Runtime Contract

The new mode must emit enough evidence to distinguish these outcomes:

- `subsys-trigger-not-attempted-no-mdm-helper-esoc-fd` when `mdm_helper` does
  not hold `/dev/esoc-0`;
- `subsys-trigger-start-failed` when the fd gate opens but the trigger child
  does not start;
- `subsys-trigger-window-captured` when the scoped trigger child starts and
  either exits or is cleaned up with blocker evidence.

The mode must keep these explicit negatives in the transcript:

- `qcwlanstate_write=0`;
- `iwifi_start=0`;
- `esoc_ioctl_attempted=0`;
- `scan_connect_linkup=0`;
- `credentials=0`;
- `dhcp_routing=0`;
- `external_ping=0`.

## Validation

```bash
mkdir -p tmp/wifi/v1002-execns-helper-v170-build
scripts/revalidation/build_android_execns_probe_helper.sh \
  tmp/wifi/v1002-execns-helper-v170-build/a90_android_execns_probe \
  2>&1 | tee tmp/wifi/v1002-execns-helper-v170-build/build.log

git diff --check
strings tmp/wifi/v1002-execns-helper-v170-build/a90_android_execns_probe | \
  rg 'a90_android_execns_probe v170|wifi-companion-android-wifi-service-window-subsys-trigger-capture|allow-android-wifi-service-window-subsys-trigger-capture|subsys-trigger-window-captured|subsys-trigger-start-failed|service-window-mdm-helper-esoc-fd'
```
