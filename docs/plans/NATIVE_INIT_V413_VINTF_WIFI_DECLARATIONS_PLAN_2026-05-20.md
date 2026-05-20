# Native Init v413 VINTF Wi-Fi Declarations Plan

## Scope

V413 collects Wi-Fi-looking VINTF declarations from the mounted Android
system/vendor trees.  This is a read-only inventory step to constrain later
HIDL registration and client-proof work.

V413 is not Wi-Fi bring-up.  It does not deploy helpers, start
`servicemanager`, start `hwservicemanager`, start the Wi-Fi HAL, start
`wificond`, start supplicant/hostapd, scan/connect/link-up, write credentials,
run DHCP, mutate firmware, or write Android partitions.

## Rationale

V411 asks `hwservicemanager` what was registered at runtime.  V413 asks the
static VINTF declarations what Wi-Fi-related services are expected.  Comparing
both answers is safer than moving directly from a start-only HAL proof to Wi-Fi
daemon/client work.

AOSP HIDL documentation states `hwservicemanager` tracks registered HIDL
interfaces by name and version, and clients retrieve services by interface and
instance.  The `IServiceManager.hal` interface exposes `list()` and
`listByInterface()` for registered service names.  AOSP `hwservicemanager`
implements `list()` by returning existing service strings and
`listByInterface()` by returning live instance names.

References:

- <https://source.android.com/docs/core/architecture/hidl-cpp/interfaces>
- <https://android.googlesource.com/platform/system/libhidl/+/refs/heads/android12L-tests-dev/transport/manager/1.0/IServiceManager.hal>
- <https://android.googlesource.com/platform/system/hwservicemanager/+/refs/heads/master/ServiceManager.cpp>

## Implementation

Add:

```text
scripts/revalidation/wifi_v413_vintf_wifi_declared_services.py
```

Modes:

- `plan`: no device command.
- `run`: read-only cmdv1 collection plus `mountsystem ro` for Android partition
  visibility.

Collected surfaces:

- native version/status;
- read-only Android mount visibility;
- VINTF directories under `/mnt/system/system`, `/mnt/system/system/vendor`,
  `/mnt/system/system/system_ext`, `/mnt/system/vendor`, and `/mnt/system/odm`;
- Wi-Fi-looking VINTF lines matching `wifi`, `supplicant`, or `hostapd`;
- structured XML package/interface/instance candidates from discovered VINTF XML
  files;
- process and netdev cleanliness.

## Success Criteria

- `plan` executes no device command.
- `run` records `device_mutations=false`, `daemon_start_executed=false`,
  `wifi_hal_start_executed=false`, and `wifi_bringup_executed=false`.
- Evidence output is private.
- The parser extracts Wi-Fi-looking declarations such as
  `android.hardware.wifi@1.0::IWifi/default` when present.
- Current process/netdev surfaces are clean before any later live gate.

## Next Use

V413 does not supersede the V411 deploy gate.  The current next live action is
still:

```text
approve v411 deploy execns helper v27 only; no daemon start and no Wi-Fi bring-up
```

After V411 deploy and bounded V411 binderized query, compare:

- V411 runtime registrations;
- V412 branch decision;
- V413 static VINTF declarations.

Only then select a targeted no-scan/no-link HIDL client proof or a smaller
micro registration query.
