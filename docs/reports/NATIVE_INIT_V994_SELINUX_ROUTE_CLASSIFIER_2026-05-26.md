# V994 SELinux Route Classifier

- generated: `2026-05-26`
- scope: host-only classifier after V993
- decision: `v994-current-boot-selinux-refresh-selected`
- pass: `True`
- evidence: `tmp/wifi/v994-selinux-route-classifier/manifest.json`
- script: `scripts/revalidation/native_wifi_selinux_route_classifier_v994.py`

## Summary

V994 classifies the V993 blocker and selects the next route:

```text
fresh-current-boot-policy-load-and-domain-proof-before-service-window
```

The important correction is that V993 proved the `wificond` SELinux transition
gap, but V993 itself did not run a current-boot V490 policy-load/domain proof
before the service-window. A historical V490/V491 pass proves the mechanism can
work in this environment, but it is not proof that the current boot was prepared
before V993.

## Evidence

| Check | Result |
| --- | --- |
| historical V490 policy-load pass | PASS |
| historical V491 domain proof pass | PASS |
| `wifinl80211` service context present | PASS |
| `wificond` `setexeccon` accepted | PASS |
| traced `wificond` remained `kernel` after `exec` and crash | PASS |
| V993 had no embedded current-boot policy-load proof | PASS |
| V993 no-Wi-Fi guardrails held | PASS |

## Source Interpretation

AOSP `servicemanager` does not simply accept a service registration by name. Its
`addService` path reaches `canAddService`, and the access layer resolves service
contexts and checks `service_manager:add` against the caller SELinux SID.

AOSP `init` also treats SELinux as a boot-stage transition: load policy, restore
the init file context, then exec into the proper domain. That makes a private
service-manager bypass the wrong first repair. It would patch around the
security model instead of proving that native init can reproduce the Android
domain setup sufficiently for `wificond` and the service-manager trio.

Primary references:

- `https://android.googlesource.com/platform/frameworks/native/+/refs/heads/main/cmds/servicemanager/ServiceManager.cpp`
- `https://android.googlesource.com/platform/frameworks/native/+/4257ea6038/cmds/servicemanager/Access.cpp`
- `https://android.googlesource.com/platform/system/core/+/refs/heads/main/init/selinux.cpp`

## Decision

The next unit should not be another full Android service-window retry.

V995 should refresh SELinux on the current boot and prove target domains without
starting service-manager, Wi-Fi HAL, `wificond`, scan/connect, credentials,
DHCP, or external ping:

1. mount or verify `selinuxfs`;
2. run current-boot V490 policy-load proof;
3. run a targeted post-load exec-domain proof for `servicemanager`,
   `hwservicemanager`, `vndservicemanager`, and `wificond`;
4. only if those post-exec contexts are correct, plan a later service-window
   retry.

## Guardrails

- host-only classifier
- no device command
- no policy load
- no actor start
- no service-manager start
- no Wi-Fi HAL start
- no scan/connect/link-up
- no credential use
- no DHCP/route/external ping
- no boot image or partition write

## Validation

```bash
python3 scripts/revalidation/native_wifi_selinux_route_classifier_v994.py
```

Result:

```text
decision: v994-current-boot-selinux-refresh-selected
pass: True
route: fresh-current-boot-policy-load-and-domain-proof-before-service-window
```

## Next

V995 should implement the fresh current-boot SELinux refresh/domain proof as a
bounded live diagnostic gate. It should stop before any service-window actor
starts.
