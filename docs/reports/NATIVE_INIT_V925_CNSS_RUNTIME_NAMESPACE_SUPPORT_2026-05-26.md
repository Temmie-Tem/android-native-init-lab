# Native Init V925 CNSS Runtime Namespace Support Report

## Result

| Unit | Evidence | Decision |
| --- | --- | --- |
| V925 source/build verifier | `tmp/wifi/v925-cnss-runtime-namespace-support/manifest.json` | `v925-cnss-runtime-namespace-support-pass` |

V925 implements helper `v153` as a source/build-only repair for the V924
CNSS/WLFW blocker. It does not claim native Wi-Fi bring-up; it prepares the next
bounded live gate with better namespace parity and bounded output volume.

## Implementation

- Updated helper:
  `stage3/linux_init/helpers/a90_android_execns_probe.c`
- Added verifier:
  `scripts/revalidation/native_wifi_cnss_runtime_namespace_support_v925.py`
- Helper artifact:
  `tmp/wifi/v925-execns-helper-v153-build/a90_android_execns_probe`
- Evidence:
  `tmp/wifi/v925-cnss-runtime-namespace-support/summary.md`

## Helper Changes

- Bumped `EXECNS_VERSION` to `a90_android_execns_probe v153`.
- Added `--cnss-surface-mode full|compact`.
- Restricted `--cnss-surface-mode` to
  `wifi-companion-mdm-helper-cnss-before-subsys-trigger-capture`.
- Defaulted that mode to compact output unless explicitly overridden.
- Added explicit runtime namespace defaults for the CNSS-before-eSoC path:
  - `null_device_mode=dev-null`;
  - `vndk_apex_alias_mode=v30-to-system-ext-v30`;
  - `linkerconfig_mode=copy-real`;
  - `linkerconfig_source=/cache/bin/a90_real_ld.config.txt`;
  - `apex_libraries_source=/cache/bin/a90_real_apex.libraries.config.txt`;
  - `android_selinux_context_mode=service-defaults`.
- Added helper stdout fields:
  - `cnss_before_esoc.surface_mode`;
  - `cnss_before_esoc.runtime_namespace.linkerconfig_mode`;
  - `cnss_before_esoc.runtime_namespace.vndk_apex_alias_mode`;
  - `cnss_before_esoc.runtime_namespace.android_selinux_context_mode`;
  - `cnss_before_esoc.runtime_namespace.property_root_present`;
  - `cnss_before_esoc.surface_poll_count`.

## Verification

Executed:

```bash
python3 -m py_compile scripts/revalidation/native_wifi_cnss_runtime_namespace_support_v925.py
python3 scripts/revalidation/native_wifi_cnss_runtime_namespace_support_v925.py
```

Static verifier checks:

| Check | Value |
| --- | --- |
| helper marker `v153` | `true` |
| compact output throttle | `true` |
| full surface mode retained | `true` |
| runtime namespace reporting | `true` |
| WLFW gate preserved | `true` |
| `/dev/subsys_esoc0` open remains child-only | `true` |
| service-manager/HAL/scan/connect/DHCP/external ping blocked | `true` |
| static ARM64 helper build | `true` |

Build artifact:

| Field | Value |
| --- | --- |
| path | `tmp/wifi/v925-execns-helper-v153-build/a90_android_execns_probe` |
| sha256 | `ef9b5b779909be67a6cf9a29e14f5445505220ec6a9c651c888ff48acda1326e` |
| file | `ELF 64-bit LSB executable, ARM aarch64, statically linked, stripped` |
| dynamic section | none |

## Guardrails

V925 is source/build-only:

- no device contact;
- no serial live command;
- no ADB or Android boot;
- no helper deployment;
- no actor start;
- no eSoC ioctl or `/dev/subsys_esoc0` open;
- no service-manager, Wi-Fi HAL, scan/connect, credentials, DHCP/routes, or
  external ping;
- no boot image, partition, firmware, GPIO, sysfs, debugfs, module, bind, or
  unbind mutation.

## Interpretation

V925 closes the immediate tooling blocker from V924. The next live attempt no
longer needs to rely on a transcript-truncation-derived classification, and it
will report the CNSS runtime namespace it actually used.

This still does not prove WLFW/BDF/`wlan0`. It only makes the next proof tighter
and safer.

## Next

V926 should deploy helper `v153` only, verify checksum/mode parity, and then run
a bounded compact CNSS-before-eSoC live precondition gate. It must keep
service-manager, Wi-Fi HAL, scan/connect, credentials, DHCP/routes, external
ping, and ungated `/dev/subsys_esoc0` open blocked.
