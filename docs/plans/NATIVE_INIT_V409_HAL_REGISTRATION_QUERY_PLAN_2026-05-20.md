# Native Init v409 Wi-Fi HAL Registration Query Plan

## Scope

V409 prepares the first direct runtime registration query after the V407/V408
service-surface proof.

The intended live path starts only the same bounded trio from V407 plus one
bounded query child:

- `servicemanager`
- `hwservicemanager`
- first Wi-Fi HAL candidate `vendor.samsung.hardware.wifi@2.0-service`
- `/system/bin/lshal`

V409 still does not approve scan/connect/link-up, credentials, DHCP, routing,
`wificond`, supplicant, hostapd, CNSS lifecycle changes, persistence, or Wi-Fi
bring-up.

## References

- AOSP VINTF resources describe `lshal` as the device-side tool that lists HALs
  registered to `hwservicemanager` and passthrough implementations:
  <https://source.android.com/docs/core/architecture/vintf/resources?hl=en>
- AOSP HIDL interface documentation states that `hwservicemanager` tracks
  registered HIDL interfaces by package/version/interface and instance name:
  <https://source.android.com/docs/core/architecture/hidl-cpp/interfaces>
- AOSP `lshal` source uses `android.hidl.manager@1.0::IServiceManager::list`
  for binderized services registered through `hwservicemanager`:
  <https://android.googlesource.com/platform/frameworks/native/+/ad8d827/cmds/lshal/ListCommand.cpp>

## Implementation

V409 adds helper v25:

- version marker: `a90_android_execns_probe v25`
- new mode: `wifi-hal-composite-lshal-list`
- new explicit guard: `--allow-hal-service-query`
- fixed query tool: `/system/bin/lshal`
- query timeout: bounded inside the helper
- output prefix: `wifi_hal_service_query.*`

The helper keeps the existing private namespace setup:

- private Binder/HwBinder/VndBinder nodes
- private SELinux status surface
- private property area
- `system_ext` VNDK v30 APEX aliasing
- copied real linker config inputs
- private empty `/data/vendor/wifi`

## Approval Gates

Helper deploy and live registration query are separate approvals.

Deploy approval phrase:

```text
approve v409 deploy execns helper v25 only; no daemon start and no Wi-Fi bring-up
```

Live query approval phrase:

```text
approve v409 bounded lshal registration query only; no scan/connect/link-up and no Wi-Fi bring-up
```

## Expected Flow

1. Build helper v25 locally.
2. Run deploy plan/no-approval checks.
3. With deploy approval, install only `/cache/bin/a90_android_execns_probe`.
4. Run V409 read-only preflight.
5. If helper v25 and `/mnt/system/system/bin/lshal` are present, request live
   query approval.
6. With live approval, run the bounded query and classify:
   - `v409-hal-registration-query-pass`
   - `v409-hal-registration-query-tool-missing`
   - `v409-hal-registration-query-runtime-gap`
   - `v409-hal-registration-query-review-required`

## Blockers

The direct query path requires `/system/bin/lshal` in the system image.  If it
is absent, V409 must not widen scope.  The next route is V410:

- extract Android-side `lshal` evidence while booted into Android, or
- build a minimal dedicated HIDL `IServiceManager::list` client for the private
  namespace.

## Success Criteria

V409 is successful only when:

- V408 evidence packet is PASS.
- helper v25 is deployed and verified by SHA-256.
- `/system/bin/lshal` is present.
- the bounded trio starts in one private namespace.
- `lshal` exits zero while the trio is alive.
- postflight proves all children are terminated/reaped.
- no Wi-Fi bring-up boundary is crossed.
