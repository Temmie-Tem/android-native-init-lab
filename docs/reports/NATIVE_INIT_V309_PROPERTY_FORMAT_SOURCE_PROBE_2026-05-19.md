# Native Init v309 Property Format Source Probe Report

- date: `2026-05-19`
- scope: host-only AOSP property area/property info source map
- boot image change: none
- restored device build: `A90 Linux init 0.9.60 (v261)`
- plan: `docs/plans/NATIVE_INIT_V309_PROPERTY_FORMAT_SOURCE_PROBE_PLAN_2026-05-19.md`
- tool: `scripts/revalidation/wifi_property_format_source_probe.py`

## Summary

v309 fetched Android 12 AOSP property runtime sources and confirmed the source
facts needed to design the next host-only serializer/parser compatibility proof.

This does not authorize runtime property file creation. It only narrows v310 to
a host-side proof for serialized `property_info` and `prop_area` generation.

## Evidence

| item | path | result |
| --- | --- | --- |
| source probe | `tmp/wifi/v309-property-format-source-probe/` | `property-format-source-map-ready` |

## Validation

```bash
python3 -m py_compile scripts/revalidation/wifi_property_format_source_probe.py
python3 scripts/revalidation/wifi_property_format_source_probe.py \
  --out-dir tmp/wifi/v309-property-format-source-probe \
  run
git diff --check
```

Result: PASS.

## Source Facts

| fact | result |
| --- | --- |
| AOSP ref | `android-12.0.0_r34` |
| source fetch | `11/11` PASS |
| required source patterns | PASS |
| prop area constants | `PROP_AREA_MAGIC=0x504f5250`, `PROP_AREA_VERSION=0xfc6ed0ab`, `PA_SIZE=128*1024` |
| bionic read path | `ContextsSerialized` selected when `/dev/__properties__/property_info` exists |
| property info format | header fields and serializer version `1` visible |

## Decision

- decision: `property-format-source-map-ready`
- reason: AOSP source facts identify the required property area and
  `property_info` structures.
- next step: v310 host-side `property_info` / `prop_area` serializer
  compatibility proof.

## Derived v310 Requirements

- Build a host-only serializer/parser proof for `property_info` header version
  `1`.
- Build a host-only `prop_area` file builder proof using the AOSP magic,
  version, and size constants.
- Model private namespace file layout with `property_info`,
  `properties_serial`, and per-context property files.
- Continue blocking global `/dev/__properties__`, property service socket,
  daemon starts, and Wi-Fi bring-up.

## Safety

- No device command execution.
- No ADB command execution.
- No runtime property file creation.
- No property service socket creation.
- No service-manager/HAL/Wi-Fi daemon execution.
- No Wi-Fi scan/connect/link-up/credential/DHCP/routing.

## References

- <https://android.googlesource.com/platform/bionic/+/android-12.0.0_r34/libc/system_properties/prop_area.cpp>
- <https://android.googlesource.com/platform/bionic/+/android-12.0.0_r34/libc/system_properties/system_properties.cpp>
- <https://android.googlesource.com/platform/bionic/+/android-12.0.0_r34/libc/system_properties/contexts_serialized.cpp>
- <https://android.googlesource.com/platform/system/core/+/android-12.0.0_r34/property_service/libpropertyinfoparser/property_info_parser.cpp>
- <https://android.googlesource.com/platform/system/core/+/android-12.0.0_r34/property_service/libpropertyinfoserializer/trie_serializer.cpp>

