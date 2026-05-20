# Native Init V425 Boot-complete hwservice Handoff Report

Date: 2026-05-20

## Scope

V425 implemented and live-validated a boot-complete Android handoff.  It boots
Android temporarily, waits for `sys.boot_completed=1`, runs the V423 read-only
hwservice/lshal inventory, restores native init v319, and compares the result
against native V422/V407 evidence.

No Wi-Fi enable, scan/connect/link-up, credentials, DHCP, routing, rfkill/sysfs
write, module load/unload, property mutation, or direct Wi-Fi daemon start
command was executed by the runner.

## Implementation

```text
scripts/revalidation/android_hwservice_settled_handoff_v425.py
```

The runner adds to the V424 handoff pattern:

- read-only boot-complete polling using `getprop`;
- bounded settle snapshot after boot completion;
- V423 output under `v423-android-hwservice-bootcomplete-run`;
- comparison against latest V422 and V407 manifests;
- fail-closed rollback if boot-complete or V423 capture fails after Android boot.

## Validation

Static checks:

```text
python3 -m py_compile scripts/revalidation/android_hwservice_settled_handoff_v425.py
python3 -m py_compile scripts/revalidation/android_hwservice_handoff_v424.py scripts/revalidation/wifi_android_hwservice_inventory_v423.py
git diff --check
```

Plan evidence:

```text
tmp/wifi/v425-settled-handoff-plan-20260520-134730/
decision: v425-handoff-plan-ready
pass: True
device_commands_executed: False
device_mutations: False
wifi_bringup_executed: False
```

Dry-run evidence:

```text
tmp/wifi/v425-settled-handoff-dryrun-20260520-134730/
decision: v425-handoff-dryrun-ready
pass: True
device_commands_executed: False
device_mutations: False
wifi_bringup_executed: False
```

Live evidence:

```text
tmp/wifi/v425-settled-handoff-live-20260520-134752/
decision: v425-bootcomplete-targets-present-native-gap
pass: True
reason: boot-complete Android lshal contains all Samsung ISehWifi targets; native private micro query still timed out earlier
wifi_bringup_executed: False
```

Boot-complete proof:

```text
sys.boot_completed=1
dev.bootcomplete=1
init.svc.bootanim=stopped
init.svc.servicemanager=running
init.svc.hwservicemanager=running
init.svc.vendor.wifi_hal_ext=running
init.svc.wificond=running
```

Boot-complete V423 result:

```text
tmp/wifi/v425-settled-handoff-live-20260520-134752/v423-android-hwservice-bootcomplete-run/
decision: v423-android-hwservice-targets-present
pass: True
matched_targets:
- vendor.samsung.hardware.wifi@2.0::ISehWifi/default
- vendor.samsung.hardware.wifi@2.1::ISehWifi/default
- vendor.samsung.hardware.wifi@2.2::ISehWifi/default
```

Comparison inputs:

```text
V422: v422-micro-lshal-wait-timeout / service-query-timeout / lshal-wait-timeout
V407: v407-composite-hal-start-only-retry-pass / start-only-pass / observed-until-timeout-clean-stop
```

Native rollback verification after live run:

```text
A90 Linux init 0.9.61 (v319)
cmdv1 version/status: rc=0 status=ok
adbd: stopped
netservice: disabled tcpctl=stopped
storage: backend=sd writable=yes
```

## Observations

Boot-complete Android has the target runtime surface that native private
runtime does not yet reproduce:

- all three Samsung `ISehWifi/default` fqinstances are present in `lshal` output;
- Android framework Wi-Fi binder services are visible (`wifi`, `wifiscanner`, `wifip2p`, Samsung `sem_wifi` services);
- Android boot-complete process surface includes `android.hardware.wifi@1.0-service`, `vendor.samsung.hardware.wifi@2.0-service`, `wificond`, `cnss_diag`, `cnss-daemon`, and `wpa_supplicant`.

Important caveat: Android itself starts some Wi-Fi-related services by normal
boot.  V425 did not directly start Wi-Fi daemons or perform scan/connect/link-up,
but the Android baseline includes more framework/supplicant state than the
native private namespace experiments.

## Interpretation

V425 converts the previous early-boot Android evidence into boot-complete
evidence.  The blocker is now narrower: native private runtime can start the HAL
process cleanly, but its service-query path still cannot observe the same
boot-complete Android registration/service-manager surface.

The next step should be V426: read-only boot-complete Android service-surface
mapping and native-gap extraction, focused on the service-manager/hwservice and
supplicant/framework state that V425 shows is missing from the native private
runtime path.
