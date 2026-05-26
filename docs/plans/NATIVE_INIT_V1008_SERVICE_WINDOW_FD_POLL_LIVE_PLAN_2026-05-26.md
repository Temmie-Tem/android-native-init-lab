# V1008 Service-window fd Poll Live Plan

## Goal

Run helper `v171` in the repaired Android service-window subsystem trigger mode
and capture the new `mdm_helper` `/dev/esoc-0` fd-poll markers.

## Scope

1. Reconfirm current native health.
2. Refresh current-boot SELinux prerequisites:
   - V401 `selinuxfs` mount surface;
   - read-only `mountsystem ro`;
   - V490 policy-load proof;
   - V997 current-boot service-domain proof.
3. Run helper `v171` mode
   `wifi-companion-android-wifi-service-window-subsys-trigger-capture`.
4. Classify whether `android_wifi_service_window.fd_poll.*` observed
   `/dev/esoc-0`.
5. Preserve cleanup or cleanup reboot before continuing.

## Guardrails

Allowed only inside the bounded gate:

- current-boot SELinux policy load;
- Android service-window actors;
- repeated read-only `/proc/<mdm_helper>/fd` polling;
- `/dev/subsys_esoc0` child open only if the final fd gate is positive;
- cleanup reboot only if actor cleanup is not proven.

Forbidden:

- `qcwlanstate`;
- `IWifi.start`;
- eSoC ioctl;
- Wi-Fi scan/connect/link-up;
- credential use;
- DHCP/routes;
- external ping;
- boot image or partition write;
- firmware mutation;
- GPIO/sysfs/debugfs write.

## Success Criteria

V1008 passes if it records one of these classified outcomes with no forbidden
actions:

- fd-poll observed but final trigger gate closed;
- fd-poll not observed, narrowing the native service-window gap;
- final fd gate opened and subsystem trigger evidence was captured with cleanup;
- WLFW precondition was observed without scan/connect.

A pass is not the final Wi-Fi objective. It is the next lower-gate classifier
toward native Wi-Fi connect/ping.

## Validation

```bash
python3 -m py_compile scripts/revalidation/native_wifi_android_service_window_fd_poll_live_v1008.py
python3 scripts/revalidation/native_wifi_android_service_window_fd_poll_live_v1008.py plan
```
