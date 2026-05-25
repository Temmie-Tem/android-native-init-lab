# Native Init V916 mdm_helper Subsys Trigger Helper Build Report

## Result

| Unit | Evidence | Decision |
| --- | --- | --- |
| source/build-only verifier | `tmp/wifi/v916-mdm-helper-subsys-trigger-support/manifest.json` | `v916-mdm-helper-subsys-trigger-support-pass` |

V916 adds helper `v150` support for the corrected native trigger gate defined after V913/V914. The helper now has a dedicated mode for running `pm-service` and `mdm_helper`, then attempting a bounded `/dev/subsys_esoc0` open only from a child process after `mdm_helper` is observable and already holds `/dev/esoc-0`.

## Implemented

- Added mode `wifi-companion-mdm-helper-runtime-subsys-trigger-capture`.
- Added allow flag `--allow-mdm-helper-subsys-trigger-capture`.
- Added config/status/validation dispatch for the new mode.
- Reused the runtime-contract private Android namespace setup, property shim, firmware mounts, RMT storage surface, binder nodes, and SELinux defaults.
- Added `mdm_helper_subsys_trigger` output keys for gate state, trigger child lifecycle, postflight safety, and upper Wi-Fi surface snapshots.
- Preserved hard gates: no service-manager, CNSS daemon, Wi-Fi HAL, scan/connect, credentials, DHCP/routes, external ping, controller eSoC notify, controller BOOT_DONE, boot image write, partition write, firmware mutation, GPIO/sysfs/debugfs write, or Wi-Fi bring-up.

## Build

- artifact: `tmp/wifi/v916-execns-helper-v150-build/a90_android_execns_probe`
- sha256: `920283483ade4ce3a989cfe84ecc6094b3b45dcb1af323bbba374f6e22e93572`
- static check: `statically linked`, `There is no dynamic section`

## Validation

Executed:

```bash
scripts/revalidation/build_android_execns_probe_helper.sh tmp/wifi/v916-execns-helper-v150-build/a90_android_execns_probe
python3 -m py_compile scripts/revalidation/native_wifi_mdm_helper_subsys_trigger_support_v916.py
python3 scripts/revalidation/native_wifi_mdm_helper_subsys_trigger_support_v916.py
```

Verifier decision:

```text
decision: v916-mdm-helper-subsys-trigger-support-pass
pass: True
```

## Live Scope

No live actor was started in this unit. V916 is source/build-only and did not contact the device, deploy the helper, start `pm-service`, start `mdm_helper`, open `/dev/subsys_esoc0`, start Wi-Fi HAL, scan/connect, use credentials, run DHCP/routes, ping externally, reboot, flash, or mutate partitions.

## Next

V917 should deploy helper `v150` and run the bounded corrected native trigger gate. Primary review should focus on service-notifier/WLFW/BDF/wlan0 progression, while lower eSoC markers remain diagnostic-only per V914.
