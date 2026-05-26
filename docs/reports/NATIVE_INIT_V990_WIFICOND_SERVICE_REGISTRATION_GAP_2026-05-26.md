# V990 Wificond Service Registration Gap

- generated: `2026-05-26`
- scope: read-only service context classifier
- decision: `v990-wificond-addservice-selinux-transition-gap`
- pass: `True`
- evidence: `tmp/wifi/v990-wificond-service-registration-gap/manifest.json`
- input trace: `tmp/wifi/v988-android-service-window-live-v167/native/mdm-helper-cnss-before-esoc.txt`
- input offset classifier: `tmp/wifi/v989-wificond-offset-classifier/manifest.json`

## Summary

V990 classifies the V989 `wificond` `addService` failure.

The service name is `wifinl80211`, and the platform service context exists:

```text
wifinl80211 u:object_r:wifinl80211_service:s0
```

Therefore the immediate blocker is not a missing service-context entry. The
blocking delta is that both `wificond` and the private `servicemanager` still
execute as SELinux `kernel` context even though the helper requested
service-default target domains.

## Findings

- V989 mapped the abort to:
  `sm->addService(android::String16(kServiceName), service) == android::NO_ERROR`.
- The pulled `wificond` binary contains service name `wifinl80211`.
- `/mnt/system/system/etc/selinux/plat_service_contexts` maps `wifinl80211` to
  `u:object_r:wifinl80211_service:s0`.
- V988 shows `setexeccon` accepted the requested `u:r:wificond:s0` target.
- V988 also shows runtime context remained `kernel`:
  - `wificond.identity.after.selinux.current=kernel`
  - `wifi_hal_composite_child.wificond.selinux.exec=kernel`
  - `wifi_hal_composite_child.servicemanager.selinux.exec=kernel`
- Binder devices and property shim were already present, so the next repair
  should not repeat those routes.

## Guardrails

- read-only service context grep
- host-side evidence classification
- no actor start during classifier
- no `qcwlanstate`
- no `IWifi.start`
- no `/dev/subsys_esoc0` open
- no eSoC ioctl
- no scan/connect/link-up
- no credential use
- no DHCP/route/external ping

## Validation

Commands:

```bash
python3 -m py_compile scripts/revalidation/native_wifi_wificond_service_registration_gap_v990.py
python3 scripts/revalidation/native_wifi_wificond_service_registration_gap_v990.py
```

Result:

```text
decision: v990-wificond-addservice-selinux-transition-gap
pass: True
device_mutations: False
wifi_bringup_executed: False
```

## Next

V991 should be source/build-only and should target the SELinux transition gap
directly:

1. add explicit evidence for procattr/setexeccon before and after `execv`;
2. capture whether `/proc/<pid>/attr/current` changes after `execv`;
3. avoid another full service-window retry until the `kernel` context gap is
   either repaired or proven unavoidable;
4. keep service-manager, Wi-Fi HAL, scan/connect, DHCP, and external ping
   blocked unless this lower registration path is fixed.
