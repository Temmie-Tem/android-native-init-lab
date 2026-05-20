# Native Init v409 Wi-Fi HAL Registration Query Plan

## Superseded Status

V409 is retained as historical design context only.  It was superseded by V410
before live deploy because the V409 approved command could stay inside the
native argument budget only by omitting explicit `--data-wifi-mode
private-empty`.  The V409 deploy and query scripts now fail closed with
`v409-superseded-by-v410` and execute no device command.

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

V409 approval gates are closed.  Do not use the old V409 deploy or query
approval phrases.  The replacement live gate is V410:

```text
approve v410 bounded lshal registration query only; no scan/connect/link-up and no Wi-Fi bring-up
```

## Expected Flow

Historical V409 flow is not executable anymore.  Any invocation of the V409
deploy wrapper or query runner records superseded refusal evidence and exits
without device commands, daemon start, HAL start, `lshal`, or Wi-Fi bring-up.

## Blockers

The direct query path requires `/system/bin/lshal` in the system image.  If it
is absent, V409 must not widen scope.  The next route is V410:

- extract Android-side `lshal` evidence while booted into Android, or
- build a minimal dedicated HIDL `IServiceManager::list` client for the private
  namespace.

## Success Criteria

The historical V409 design would have been successful only when:

- V408 evidence packet is PASS.
- helper v25 is deployed and verified by SHA-256.
- `/system/bin/lshal` is present.
- the bounded trio starts in one private namespace.
- `lshal` exits zero while the trio is alive.
- postflight proves all children are terminated/reaped.
- no Wi-Fi bring-up boundary is crossed.
