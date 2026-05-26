# Native Init V1075 PM Service Uprobe Host Classifier Report

## Summary

V1075 added a host-only classifier for the `pm-service` uprobe route.  The
classifier passed: the extracted `pm-service` is a stripped AArch64 PIE, all
selected entry/PLT offsets are 4-byte aligned, and the stock kernel supports
uprobes/BPF events while kernel kprobes remain unavailable.

This closes the V1074 ptrace limitation and selects V1076: a bounded uprobe/BPF
helper for `pm-service` entry, inferred main, mdmdetect, binder, QMI, property,
log, and basic libc callsites.

## Change

- Added `scripts/revalidation/native_wifi_pm_service_uprobe_host_classifier_v1075.py`.
- Parsed `pm-service` ELF header, dynamic dependencies, relocations, PLT, and
  diagnostic strings.
- Inferred the libc-init main candidate from the entry stub and relative
  relocation table.
- Added raw kernel config text fallback parsing so truncated JSON summaries do
  not hide `CONFIG_UPROBES=y`.
- Wrote private evidence to
  `tmp/wifi/v1075-pm-service-uprobe-host-classifier/manifest.json`.

## Evidence

| item | path / value |
| --- | --- |
| classifier | `scripts/revalidation/native_wifi_pm_service_uprobe_host_classifier_v1075.py` |
| binary | `tmp/wifi/v1073-host-only/vendor-extract/files/pm-service` |
| manifest | `tmp/wifi/v1075-pm-service-uprobe-host-classifier/manifest.json` |
| summary | `tmp/wifi/v1075-pm-service-uprobe-host-classifier/summary.md` |
| binary size | `54888` |
| ELF entry | `0x6000` |
| inferred main candidate | `0x7650` |

## Classifier Result

```text
decision: v1075-pm-service-uprobe-host-classified
pass: True
reason: pm-service is stripped PIE but has aligned entry/main and critical PLT uprobe candidates; kernel config supports uprobes/BPF events while kprobes remain unavailable
next: V1076 implement bounded uprobe/BPF helper for pm-service entry/main/get_system_info/qmi/binder/log callsites
```

## Kernel Config

The classifier merged `tmp/kernel-config/v202-kernel-config.json` with raw
ikconfig captures to recover all required options:

```text
CONFIG_UPROBES=y
CONFIG_UPROBE_EVENTS=y
CONFIG_BPF_EVENTS=y
CONFIG_BPF_SYSCALL=y
CONFIG_BPF_JIT=n
CONFIG_KPROBES=n
```

Interpretation: low-frequency userspace uprobe/BPF instrumentation is available.
Kernel function probes remain unavailable, so this route must stay focused on
`pm-service` userspace boundaries.

## Candidate Uprobes

| label | kind | symbol | offset |
| --- | --- | --- | --- |
| `elf_entry` | entry |  | `0x6000` |
| `libc_init_main_candidate` | function-entry |  | `0x7650` |
| `android_log` | PLT | `__android_log_print` | `0x9e60` |
| `binder_driver` | PLT | `android::ProcessState::initWithDriver` | `0xa0a0` |
| `binder_service_manager` | PLT | `android::defaultServiceManager` | `0xa0b0` |
| `mdmdetect_system_info` | PLT | `get_system_info` | `0x9f40` |
| `qmi_csi_register` | PLT | `qmi_csi_register_with_options` | `0x9fb0` |
| `qmi_csi_event_loop` | PLT | `qmi_csi_handle_event` | `0x9ff0` |
| `property_set` | PLT | `property_set` | `0x9ec0` |
| `pipe` | PLT | `pipe` | `0xa040` |
| `access` | PLT | `access` | `0xa310` |
| `open` | PLT | `__open_2` | `0xa2c0` |
| `select` | PLT | `select` | `0x9fd0` |
| `write` | PLT | `write` | `0xa170` |
| `close` | PLT | `close` | `0xa080` |

All selected candidates are ARM64 4-byte aligned.  `missing_critical=[]` and
`unaligned_candidates=[]`.

## Binary Surface

`pm-service` links against the expected PM/QMI/Binder dependencies:

```text
libcutils.so
libutils.so
liblog.so
libbinder.so
libqmi_cci.so
libqmi_common_so.so
libqmi_encdec.so
libqmi_csi.so
libmdmdetect.so
libperipheral_client.so
libc++.so
libc.so
libm.so
libdl.so
```

Decisive strings remain present:

```text
Failed to get system information
Failed to init peripheral
Adding Peripheral Manager service fail
QMI service start
QMI service select error
QMI service process event error
/dev/vndbinder
vendor.qcom.PeripheralManager
vendor.peripheral.
```

## Safety

V1075 was host-only.  It did not start any device-side service, write tracefs,
open eSoC/subsystem nodes, bring up Wi-Fi, or modify boot/partition artifacts.

## Interpretation

V1075 proves there is enough static binary and kernel support evidence to build
a lower-overhead PM-service observer.  It does not prove the exit-255 root cause
by itself.  V1076 should use these offsets to arm bounded uprobes before
`pm-service` starts and record which boundary is reached or missed.

## Next Gate

V1076 should implement a bounded uprobe/BPF helper with these constraints:

1. Register only selected `pm-service` uprobes and clean them from tracefs after
   the run.
2. Arm probes before `pm-service` starts.
3. Capture entry/main/log/mdmdetect/binder/QMI/property/basic libc callsite hits.
4. Avoid continuous ptrace syscall stops.
5. Keep the existing hard boundary: no `mdm_helper`, CNSS, Wi-Fi HAL,
   scan/connect/DHCP/route/external ping, `/dev/esoc*`, `wlan.ko`, or boot image
   writes.
