# Native Init V426 Service Surface Mapper Report

Date: 2026-05-20

## Scope

V426 parses the boot-complete Android evidence captured by V425 and extracts the
native private-runtime gap.  This is host-only analysis: no ADB command, device
mutation, daemon start, Wi-Fi enable, scan/connect/link-up, credential, DHCP, or
routing action was executed.

## Implementation

```text
scripts/revalidation/wifi_v426_service_surface_mapper.py
```

The mapper:

- discovers the latest V425 live manifest by default;
- parses V423 boot-complete Android command evidence;
- structures Android props, framework services, process surface, `lshal`
  fqinstances, VINTF declarations, and rfkill/netdev snippets;
- compares the Android surface with V422 targeted wait and V407 HAL start-only
  evidence;
- writes private 0700/0600 evidence through `EvidenceStore`.

## Validation

Static checks:

```text
python3 -m py_compile scripts/revalidation/wifi_v426_service_surface_mapper.py
git diff --check
```

Plan evidence:

```text
tmp/wifi/v426-service-surface-plan-20260520-135547/
decision: v426-service-surface-mapper-plan-ready
pass: True
device_commands_executed: False
device_mutations: False
wifi_bringup_executed: False
```

Run evidence:

```text
tmp/wifi/v426-service-surface-run-parserfix-20260520-135610/
decision: v426-native-registration-surface-gap
pass: True
reason: Android boot-complete surface is present; native targeted query still times out
device_commands_executed: False
device_mutations: False
wifi_bringup_executed: False
```

Current native state was also checked after V425/V426 analysis:

```text
A90 Linux init 0.9.61 (v319)
cmdv1 version: rc=0 status=ok
```

## Android Boot-complete Surface

V426 found these Android surfaces present in the V425/V423 evidence:

- `sys.boot_completed=1`;
- framework services: `wifi`, `wifiscanner`, `wifip2p`, Samsung `sem_wifi`, `sem_wifi_aware`, `sem_wifi_p2p`;
- `init.svc.hwservicemanager=running`;
- `init.svc.vendor.wifi_hal_ext=running`;
- Wi-Fi process surface: `android.hardware.wifi@1.0-service`, `vendor.samsung.hardware.wifi@2.0-service`, `wificond`, `cnss_diag`, `cnss-daemon`, `wpa_supplicant`, WLAN kernel threads;
- VINTF Wi-Fi declaration surface: 63 Wi-Fi-looking lines;
- `dumpsys -l` Wi-Fi service names: 8 lines.

Target match:

```text
vendor.samsung.hardware.wifi@2.0::ISehWifi/default: present
vendor.samsung.hardware.wifi@2.1::ISehWifi/default: present
vendor.samsung.hardware.wifi@2.2::ISehWifi/default: present
```

## Gap Classification

Decision:

```text
v426-native-registration-surface-gap
```

Gap items:

```text
native private runtime lacks boot-complete Android framework binder surface
native private runtime does not carry Android supplicant/framework Wi-Fi state
native V407 proves HAL process lifetime, but V422 cannot observe the Samsung ISehWifi fqinstances
```

Comparison inputs:

```text
V422: v422-micro-lshal-wait-timeout / service-query-timeout / lshal-wait-timeout
V407: v407-composite-hal-start-only-retry-pass / start-only-pass / observed-until-timeout-clean-stop
V425: v425-bootcomplete-targets-present-native-gap
```

## Interpretation

The blocker is no longer whether the Samsung Wi-Fi fqinstances exist on this
Android build.  They exist at boot-complete Android runtime.  The blocker is
that the native private runtime can keep the Wi-Fi HAL process alive but cannot
reproduce or query the Android boot-complete service surface that makes those
fqinstances visible.

The next step should be V427: design and validate a minimal native read-only
service-query improvement path.  It should decide whether to add missing
service-manager/hwservice/framework/supplicant surfaces to the native private
namespace, or pivot toward an Android-managed runtime control path before any
Wi-Fi bring-up attempt.
