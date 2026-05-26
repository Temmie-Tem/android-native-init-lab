# Native Init V1092 PM Provider Ready Report

## Summary

V1092 passed. The current PM observer path now proves that `pm-service` can
register `vendor.qcom.PeripheralManager` when the V490 SELinux policy-load
precondition and an explicit `vndservicemanager` readiness wait are present.

Decision:

```text
v1092-pm-provider-registration-observed
```

This supersedes the earlier V1071 `pm-service exit 255` direction for the
current branch. The immediate blocker is no longer `pm-service` startup or
provider registration; the next blocker is the post-provider mdm3/WLAN-PD path.

## Evidence

| item | path |
| --- | --- |
| helper source | `stage3/linux_init/helpers/a90_android_execns_probe.c` |
| deploy wrapper | `scripts/revalidation/wifi_execns_helper_v202_deploy_preflight.py` |
| live wrapper | `scripts/revalidation/native_wifi_pm_observer_provider_ready_live_v1092.py` |
| helper artifact | `tmp/wifi/v1092-execns-helper-v202-build/a90_android_execns_probe` |
| deploy evidence | `tmp/wifi/v1092-execns-helper-v202-deploy/manifest.json` |
| live evidence | `tmp/wifi/v1092-pm-observer-provider-ready-live/manifest.json` |
| V490 evidence | `tmp/wifi/v490-native-selinux-policy-load-proof/manifest.json` |

## Result

```text
helper: a90_android_execns_probe v202
sha256: 54a2488dda1d659ffef52a89be643abc5bfaf5254477c2771d41901897211435
vndservicemanager_ready: True
vndservice_provider_seen: True
pm_service_subsys_modem_seen: False
pm_proxy_helper_subsys_modem_seen: False
wifi_hal_start_executed: False
wifi_bringup_executed: False
external_ping_executed: False
```

The provider query returned:

```text
wifi_vndservice_query.pm_observer_after_per_mgr_probe.result=query-exit-zero
wifi_vndservice_query.pm_observer_after_per_mgr_probe.vendor_qcom_peripheral_manager_seen=1
```

## Implementation Notes

- `a90_android_execns_probe v202` adds a PM-observer readiness gate for
  `vndservicemanager`.
- The observer now runs `/vendor/bin/vndservice list` after `pm-service` reaches
  the post-start probe window.
- The query child flushes inherited stdio before `fork()` and suppresses noisy
  identity-contract output while applying the service-manager identity contract.
- The observer stops after the provider appears, keeping the proof bounded and
  avoiding unnecessary `per_proxy` or Wi-Fi expansion.

## Safety

- No Wi-Fi HAL, scan/connect/link-up, DHCP, route, or external ping executed.
- No CNSS daemon or `mdm_helper` executed.
- No eSoC open/ioctl, GPIO write, partition write, flash, or reboot executed.
- Postflight checks reported no forbidden actors and no Wi-Fi link hits.
- Device remained healthy: `selftest` reported `fail=0`; NCM/tcpctl remained up.

## Capture Note

The direct tcpctl proof can still hit the tcpctl 128 KiB output cap before the
final `pm_service_trigger_observer.end` line is visible. V1092 therefore treats
the provider query fields plus postflight safety checks as the deciding
evidence. The helper itself now stops after provider detection, but future
high-volume proofs should use an on-device summary file instead of returning the
full helper transcript over tcpctl.

## Interpretation

The provider registration gap is closed. The next useful gate should keep this
provider-positive setup and classify what additional post-provider trigger is
needed to move mdm3/WLAN-PD forward without starting the Wi-Fi HAL prematurely.

Candidate next checks:

1. bounded post-provider mdm3 state and dmesg delta capture;
2. post-provider `pm_proxy_helper`/QMI surface classification;
3. only after mdm3/WLAN-PD movement, retry CNSS/WLFW observation.

## Validation

Executed:

```bash
scripts/revalidation/build_android_execns_probe_helper.sh tmp/wifi/v1092-execns-helper-v202-build/a90_android_execns_probe
python3 -m py_compile scripts/revalidation/wifi_execns_helper_v202_deploy_preflight.py scripts/revalidation/native_wifi_pm_observer_provider_ready_live_v1092.py
python3 scripts/revalidation/wifi_execns_helper_v202_deploy_preflight.py --approval-phrase "approve v1092 deploy execns helper v202 only; no daemon start and no Wi-Fi bring-up" --apply --assume-yes run
python3 scripts/revalidation/native_wifi_pm_observer_provider_ready_live_v1092.py --helper-sha256 54a2488dda1d659ffef52a89be643abc5bfaf5254477c2771d41901897211435 --helper-marker "a90_android_execns_probe v202" --local-helper tmp/wifi/v1092-execns-helper-v202-build/a90_android_execns_probe --helper-timeout-sec 8 --toybox-timeout-sec 28 --allow-mountsystem-ro --allow-selinuxfs-mount --allow-pm-service-trigger-observer --allow-cleanup-reboot --assume-yes run
```

Result:

```text
decision: v1092-pm-provider-registration-observed
pass: True
```
