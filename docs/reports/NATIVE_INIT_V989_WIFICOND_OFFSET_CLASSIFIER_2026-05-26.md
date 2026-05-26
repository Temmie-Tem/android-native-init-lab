# V989 Wificond Offset Classifier

- generated: `2026-05-26`
- scope: read-only binary pull plus host-side classifier
- decision: `v989-wificond-addservice-check-failed`
- pass: `True`
- evidence: `tmp/wifi/v989-wificond-offset-classifier/manifest.json`
- input trace: `tmp/wifi/v988-android-service-window-live-v167/native/mdm-helper-cnss-before-esoc.txt`
- binary sha256: `4f97f4bcb5c375d3e9d84a0f1712ef4513521b06e185279f9c8ef9b52c84a3de`

## Summary

V989 pulled the matching `/mnt/system/system/bin/wificond` binary read-only and
classified the V988 ptrace crash offsets host-side.

The crash is no longer generic. It maps to the `wificond` service registration
check in `system/connectivity/wificond/main.cpp`:

```text
Check failed: sm->addService(android::String16(kServiceName), service) == android::NO_ERROR
```

This means the next blocker is service-manager registration success for
`wificond`, not property-shim startup or binder-device presence.

## Evidence

Binary source:

```text
/mnt/system/system/bin/wificond
size: 398224
sha256: 4f97f4bcb5c375d3e9d84a0f1712ef4513521b06e185279f9c8ef9b52c84a3de
```

Crash offsets:

| frame | offset | classification |
| --- | ---: | --- |
| `pc` | `0x8bebc` | bionic `libc.so` abort path |
| `lr` | `0x8be90` | bionic `libc.so` abort path |
| `frame0_ra` | `0x2ab04` | `android::base::LogdLogger::LogdLogger` |
| `frame1_ra` | `0x2c540` | `android::base::ScopedLogSeverity::~ScopedLogSeverity` |
| `frame2_ra` | `0x2bc30` | `android::base::LogMessage::~LogMessage` |
| `frame3_ra` | `0x199b4` | `main.cpp` fatal check block |

Matched strings:

| address | string |
| ---: | --- |
| `0xb693` | `system/connectivity/wificond/main.cpp` |
| `0xd66f` | `Check failed: ` |
| `0xb86f` | `sm->addService(android::String16(kServiceName), service)` |
| `0xe2c2` | `android::NO_ERROR` |

## Guardrails

- read-only binary pull
- host-side `addr2line`/`objdump`/string classification
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
python3 -m py_compile scripts/revalidation/native_wifi_wificond_offset_classifier_v989.py
python3 scripts/revalidation/native_wifi_wificond_offset_classifier_v989.py
```

Result:

```text
decision: v989-wificond-addservice-check-failed
pass: True
```

## Next

V990 should target the `wificond` service-manager registration path:

1. capture `servicemanager` stderr/binder state around the `addService` failure;
2. verify whether the rejected caller context is still `kernel` despite the
   requested `u:r:wificond:s0` service-default mapping;
3. classify whether the repair belongs in service context mapping, SELinux
   transition, or service-manager namespace setup before retrying the full
   service-window proof.
