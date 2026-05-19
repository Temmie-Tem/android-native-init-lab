# v309 Plan: Property Format Source Probe

- date: `2026-05-19`
- scope: host-only AOSP property area/property info source map
- boot image change: none
- restored device build: `A90 Linux init 0.9.60 (v261)`
- status: planned

## Summary

v308 proved that the Android-backed seed is usable, but blocked runtime private
property area work because property area and serialized `property_info` formats
were not proven.

v309 fetches Android 12 AOSP source from `android.googlesource.com` and extracts
the minimum source facts needed for the next host-only serializer/builder proof.
It does not create runtime files, does not run ADB/device commands, and does not
start Android services or Wi-Fi daemons.

## Source Inputs

Default AOSP ref: `android-12.0.0_r34`, selected because the captured Android
runtime reports `ro.build.version.sdk=31`.

Key source files:

- `platform/bionic/libc/include/sys/_system_properties.h`
- `platform/bionic/libc/include/sys/system_properties.h`
- `platform/bionic/libc/bionic/system_property_api.cpp`
- `platform/bionic/libc/system_properties/system_properties.cpp`
- `platform/bionic/libc/system_properties/contexts_serialized.cpp`
- `platform/bionic/libc/system_properties/prop_area.cpp`
- `platform/bionic/libc/system_properties/include/system_properties/prop_area.h`
- `platform/bionic/libc/system_properties/include/system_properties/prop_info.h`
- `platform/system/core/property_service/libpropertyinfoparser/`
- `platform/system/core/property_service/libpropertyinfoserializer/`

## Key Checks

1. AOSP ref is Android 12 for SDK 31 seed.
2. v308 prerequisite is present.
3. Source fetch succeeds for all required files.
4. Source patterns confirm:
   - property filename is `/dev/__properties__`;
   - bionic uses `ContextsSerialized` when `property_info` is present;
   - prop area magic/version/size are visible;
   - prop area read mapping uses `O_NOFOLLOW | O_RDONLY`;
   - serialized `property_info` header fields and version 1 serializer are
     visible.

## Expected Decision

Expected current result:

```text
property-format-source-map-ready
```

This is not a runtime-ready result. It only means v310 can build a host-only
serializer/parser compatibility proof from known AOSP facts.

## Validation

```bash
python3 -m py_compile scripts/revalidation/wifi_property_format_source_probe.py
python3 scripts/revalidation/wifi_property_format_source_probe.py \
  --out-dir tmp/wifi/v309-property-format-source-probe \
  run
git diff --check
```

## Acceptance

- No boot image change.
- No device command or ADB command.
- No runtime property files.
- No property service socket.
- No service-manager/HAL/Wi-Fi daemon.
- Evidence records fetched source hashes, matched source facts, and v310
  requirements.

## References

- <https://android.googlesource.com/platform/bionic/+/android-12.0.0_r34/libc/system_properties/prop_area.cpp>
- <https://android.googlesource.com/platform/bionic/+/android-12.0.0_r34/libc/system_properties/system_properties.cpp>
- <https://android.googlesource.com/platform/bionic/+/android-12.0.0_r34/libc/system_properties/contexts_serialized.cpp>
- <https://android.googlesource.com/platform/system/core/+/android-12.0.0_r34/property_service/libpropertyinfoparser/property_info_parser.cpp>
- <https://android.googlesource.com/platform/system/core/+/android-12.0.0_r34/property_service/libpropertyinfoserializer/trie_serializer.cpp>

