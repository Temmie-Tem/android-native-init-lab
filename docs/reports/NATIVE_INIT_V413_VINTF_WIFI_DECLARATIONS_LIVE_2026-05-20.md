# Native Init V413 VINTF Wi-Fi Declarations Live

Date: 2026-05-20

## Scope

V413 ran a read-only VINTF Wi-Fi declaration inventory.  It collected static
Wi-Fi-looking service declarations from mounted Android VINTF XML files and
checked that the process/netdev surface stayed clean.

This pass did not deploy helpers, start `servicemanager`, start
`hwservicemanager`, start any Wi-Fi HAL, start `wificond`, start supplicant or
hostapd, scan/connect/link-up, write credentials, run DHCP, mutate firmware, or
write Android partitions.

## Implementation

```text
scripts/revalidation/wifi_v413_vintf_wifi_declared_services.py
```

Plan evidence:

```text
tmp/wifi/v413-vintf-plan-20260520-120842/
```

Live read-only evidence:

```text
tmp/wifi/v413-vintf-live-20260520-120842/
```

## Result

```text
decision: v413-vintf-wifi-declarations-ready
pass: True
reason: parsed 46 Wi-Fi-looking VINTF declaration candidates
next: compare declared candidates against V411 binderized lshal output after helper v27 deploy
declared_wifi_candidates: 46
device_commands_executed: True
device_mutations: False
wifi_bringup_executed: False
```

Evidence permissions:

```text
700 tmp/wifi/v413-vintf-live-20260520-120842
600 tmp/wifi/v413-vintf-live-20260520-120842/manifest.json
600 tmp/wifi/v413-vintf-live-20260520-120842/summary.md
```

## Checks

```text
native-version: pass
mountsystem-ro: pass
vintf-source-visible: pass
wifi-declarations: pass candidate_count=46
structured-wifi-declarations: pass structured_candidate_count=46
wifi-link-surface-clean: pass wifi_like_netdev_count=0
manager-wifi-process-surface-clean: pass manager_wifi_process_count=0
```

## Candidate Highlights

Primary Wi-Fi declarations include:

```text
android.hardware.wifi@1.3-5::IWifi/default
vendor.samsung.hardware.wifi@2.0-2::ISehWifi/default
vendor.samsung.hardware.wifi.hostapd@4.0::ISehHostapd/default
vendor.samsung.hardware.wifi.supplicant@3.0-1::ISehSupplicant/default
vendor.qti.hardware.wifi.supplicant@2.0-3::ISupplicantVendor/default
vendor.qti.hardware.wifi.hostapd@1.0-3::IHostapdVendor/default
android.system.wifi.keystore@1.0::IKeystore/default
```

The complete structured list is in:

```text
tmp/wifi/v413-vintf-live-20260520-120842/manifest.json
```

## Source Notes

The live Android mount exposed VINTF files under `/mnt/system/system/...` and
`/mnt/system/system/system_ext/...`.  Direct `/mnt/system/vendor/etc/vintf` and
`/mnt/system/odm/etc/vintf` were absent in this run, so the current candidate
set is a static framework/device-matrix view, not proof of runtime registration.

Source files captured include:

```text
/mnt/system/system/etc/vintf/compatibility_matrix.3.xml
/mnt/system/system/etc/vintf/compatibility_matrix.4.xml
/mnt/system/system/etc/vintf/compatibility_matrix.5.xml
/mnt/system/system/etc/vintf/compatibility_matrix.6.xml
/mnt/system/system/etc/vintf/manifest.xml
/mnt/system/system/etc/vintf/compatibility_matrix.device.xml
/mnt/system/system/system_ext/etc/vintf/manifest.xml
```

## Interpretation

V413 gives a static target set for comparison.  It does not prove that the Wi-Fi
HAL registered with `hwservicemanager`; that still requires V411 helper v27
deploy and bounded binderized `lshal` runtime evidence.

Current next live gate remains:

```text
approve v411 deploy execns helper v27 only; no daemon start and no Wi-Fi bring-up
```

After V411 runtime evidence exists, compare:

- V411 binderized `lshal` runtime registrations;
- V412 router decision;
- V413 static VINTF declaration candidates.

Only then select a targeted no-scan/no-link HIDL client proof or a smaller
micro registration query.

## References

- AOSP HIDL interfaces: <https://source.android.com/docs/core/architecture/hidl-cpp/interfaces>
- AOSP `IServiceManager.hal`: <https://android.googlesource.com/platform/system/libhidl/+/refs/heads/android12L-tests-dev/transport/manager/1.0/IServiceManager.hal>
- AOSP `hwservicemanager` implementation: <https://android.googlesource.com/platform/system/hwservicemanager/+/refs/heads/master/ServiceManager.cpp>
