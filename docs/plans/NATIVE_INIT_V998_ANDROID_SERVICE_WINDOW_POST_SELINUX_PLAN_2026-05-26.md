# Native Init V998 Android Service-Window Post-SELinux Plan

## Goal

Retry the bounded Android service-window once after V997 proves current-boot
SELinux domain handoff for the service-window critical domains.

V998 must determine whether the V993 `wificond` SELinux/addService blocker is
fixed, without starting scan/connect or using credentials.

## Preconditions

- Helper `v169` deployed.
- V401 `selinuxfs` mount PASS.
- V490 current-boot policy-load PASS.
- V997 domain proof PASS for service-manager trio, `wificond`, and Wi-Fi HAL.

## Guardrails

- No `qcwlanstate`.
- No `IWifi.start`.
- No `/dev/subsys_esoc0` open.
- No eSoC ioctl.
- No scan/connect/link-up.
- No credential use.
- No DHCP/routes or external ping.
- Cleanup must leave bootstatus/selftest/exposure healthy.

## Success Criteria

- All planned service-window actors start and become observable.
- `wificond` post-exec context is `u:r:wificond:s0`.
- If WLFW/BDF/`wlan0` appears, stop and classify before scan/connect.
- If WLFW remains absent, classify the next blocker as a lower WLFW
  precondition gap rather than a SELinux service-registration gap.

## Next

If V998 reaches `service-window-no-wlfw`, route to a host-only classifier that
decides which guarded eSoC/CNSS trigger should be retried with the SELinux
service-window blocker removed.
