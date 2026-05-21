# Native Init V510-V512 WLAN Devnode and ICNSS Gate

- date: `2026-05-21`
- objective: move native-init Wi-Fi toward real scan/connect/external-ping by closing the `/dev/wlan` runtime-surface gap
- status: `in-progress`; Wi-Fi external ping is **not** complete

## Scope

- V510 deploys `a90_android_execns_probe v58`.
- V510 mirrors host `/dev/wlan` into the private execns root as a fixed char node only when host `/dev/wlan` already exists.
- V511 writes `ON` to the fixed `/dev/wlan` qcwlanstate node and observes kernel WLAN surfaces.
- V512 refreshes read-only ICNSS/CNSS lifecycle evidence after the V511 failure.

## Guardrails

- No SSID/password read.
- No scan/connect/link-up/DHCP/external ping.
- No Android partition write.
- No firmware mutation.
- No ICNSS bind/unbind.

## Implementation

- `stage3/linux_init/helpers/a90_android_execns_probe.c`
  - bumped helper marker to `a90_android_execns_probe v58`
  - added private `/dev/wlan` path materialization for Wi-Fi HAL composite modes
  - source node must be existing host `/dev/wlan` and must be a char device
  - private node is created as `uid=1010 gid=1010 mode=0660`
- `scripts/revalidation/wifi_execns_helper_v58_deploy_preflight.py`
  - V510 deploy/preflight wrapper for helper v58
- `scripts/revalidation/native_wifi_dual_hal_private_devnode_v510.py`
  - V510 live proof for private `/dev/wlan` reflection
- `scripts/revalidation/native_wlan_driver_state_on_v511.py`
  - V511 bounded qcwlanstate `ON` write/observe proof

## Build and Deploy Evidence

```text
artifact: tmp/wifi/v510-a90_android_execns_probe-v58/a90_android_execns_probe
sha256: 85b241e504426d041f64388408f78bbfc5d955a57ca1c08690c54a9e24116a19
ELF: aarch64 static, no dynamic section
```

NCM deploy was used, not serial appendfile:

```text
225+2 records in
225+2 records out
925920 bytes (904 K) copied, 0.014 s, 63 M/s
installed /cache/bin/a90_android_execns_probe sha256=85b241e504426d041f64388408f78bbfc5d955a57ca1c08690c54a9e24116a19
```

Evidence:

- `tmp/wifi/v510-execns-helper-v58-deploy-preflight/`

## V510 Result

Command result:

```text
decision: v510-dual-hal-private-devnode-reflected
pass: True
reason: private /dev/wlan reflected mode=660; IWifi/default still not registered helper_result=service-query-runtime-gap micro_result=service-query-timeout
next: inspect whether qcwlanstate ON or another runtime surface is still required
```

Key proof:

```text
wifi_runtime_surface.before.host.dev_wlan.exists=1
wifi_runtime_surface.before.host.dev_wlan.rdev=478:0
wifi_runtime_surface.before.private.dev_wlan.exists=1
wifi_runtime_surface.before.private.dev_wlan.mode=660
wifi_runtime_surface.before.private.dev_wlan.uid=1010
wifi_runtime_surface.before.private.dev_wlan.gid=1010
wifi_runtime_surface.before.private.dev_wlan.rdev=478:0
```

Interpretation:

- The previous V507/V509 private-runtime gap is closed.
- Binder/service-manager/HAL/CNSS children remain cleanup-safe and observable.
- `IWifi/default` still does not register, so private `/dev/wlan` was necessary but not sufficient.

Evidence:

- `tmp/wifi/v510-dual-hal-private-devnode/`

## V511 Result

Command result:

```text
decision: v511-wlan-driver-state-on-write-failed
pass: False
reason: helper_result=driver-state-on-write-failed write_rc=1 errno=22
next: inspect qcwlanstate write failure and dmesg
```

Key proof:

```text
wlanboot.dev_wlan_on.write_attempted=1
wlanboot.dev_wlan_on.write_rc=1
wlanboot.dev_wlan_on.write_errno=22
wlanboot.after.qcwlanstate.value=OFF
wlanboot.after.sys_class_net_wlan0.exists=0
wlanboot.after.sys_class_ieee80211.count=0
```

Dmesg shows the qcwlanstate write reached the WLAN driver, then timed out:

```text
wlan: Loading driver v5.2.022.3Q-HL210630A ...
wlan_hdd_state wlan major(478) initialized
Wifi Turning On from UI
Timed-out!!
icnss: Modules not initialized just return
```

Interpretation:

- The write payload was accepted as a Wi-Fi ON request.
- The failure is not a missing `/dev/wlan` node and not a private namespace problem.
- The current blocker is lower: ICNSS/WLAN module readiness does not complete, so qcwlanstate stays `OFF` and no `wlan0`/wiphy appears.

Evidence:

- `tmp/wifi/v511-wlan-driver-state-on/`

## V512 Read-Only Refresh

Command result:

```text
PASS out_dir=/home/temmie/dev/A90_5G_rooting/tmp/wifi/v512-icnss-current-lifecycle-native decision=lifecycle-map-ready reason=Android lifecycle evidence plus v214 failure are sufficient for v216 service replay modeling
```

Current native ICNSS state:

```text
/sys/devices/platform/soc/18800000.qcom,icnss/uevent:
DRIVER=icnss
OF_COMPATIBLE_0=qcom,icnss

/sys/bus/platform/drivers/icnss:
18800000.qcom,icnss
bind
unbind

/sys/class/net:
ncm0, lo, dummy0, ...

/sys/class/ieee80211:
empty

/proc/net/wireless:
header only

/sys/module/firmware_class/parameters/path:
/vendor/firmware_mnt/image
```

Evidence:

- `tmp/wifi/v512-icnss-current-lifecycle-native/`

## Source References

- QCACLD qcwlanstate write path copies the userspace value, accepts `ON`, and waits for WLAN start completion when the driver is not loaded:
  - https://android.googlesource.com/kernel/msm/+/android-msm-wahoo-4.4-oreo-m4/drivers/staging/qcacld-3.0/core/hdd/src/wlan_hdd_main.c
- The same source shows boot-time WLAN module init creates qcwlanstate, starts HDD/CDS, and registers the WLAN driver before `wlan driver loaded` is expected:
  - https://android.googlesource.com/kernel/msm/+/android-msm-wahoo-4.4-oreo-m4/drivers/staging/qcacld-3.0/core/hdd/src/wlan_hdd_main.c

## Conclusion

V510 is a real forward step: private Wi-Fi HAL runtime now sees `/dev/wlan`.

V511 proves the next hard blocker is ICNSS/WLAN module readiness, not the device node or Binder/private namespace. The kernel accepts the `ON` path far enough to log `Wifi Turning On from UI`, then times out with repeated `icnss: Modules not initialized just return`.

## Next Gate

V513 completed the qcwlanstate retry inside the concurrent private service-manager/dual-HAL/CNSS namespace. See:

- `docs/reports/NATIVE_INIT_V513_DUAL_HAL_DRIVER_STATE_ON_2026-05-21.md`

Recommended V514:

1. Keep ICNSS bind/unbind blocked.
2. Build a bounded ICNSS/WLAN module-readiness classifier that does not mutate firmware or partitions.
3. Correlate exact Android boot-complete ICNSS sequence against native:
   - power/runtime state
   - QRTR/QMI service visibility
   - `cnss-daemon` ordering relative to qcwlanstate ON
   - `wlan_con_mode` and `fwpath` state before ON
4. Only after that, retry scan-only or qcwlanstate ON in the corrected sequence.
