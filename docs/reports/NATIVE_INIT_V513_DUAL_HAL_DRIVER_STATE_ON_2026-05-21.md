# Native Init V513 Dual-HAL Driver-State ON Proof

- date: `2026-05-21`
- objective: test whether private `/dev/wlan` plus concurrent service-manager, dual Wi-Fi HAL, and CNSS is enough to advance toward native-init Wi-Fi scan/connect/external-ping
- status: `in-progress`; Wi-Fi external ping is **not** complete

## Scope

- Deploy `a90_android_execns_probe v59` over NCM.
- Mirror `/dev/wlan` into the private execns root as in V510.
- Start helper-owned private `servicemanager`, `hwservicemanager`, both Wi-Fi HAL daemons, and `cnss-daemon`.
- During that same bounded private namespace, write `ON` to private `/dev/wlan`.
- Observe whether `wlan0`, wiphy, `IWifi/default`, or other Wi-Fi runtime surfaces appear.

## Guardrails

- No SSID/password read.
- No scan/connect/link-up/DHCP/external ping.
- No Android partition write.
- No firmware mutation.
- No ICNSS bind/unbind.
- Helper-owned processes are cleaned up after the bounded window.

## Implementation

- `stage3/linux_init/helpers/a90_android_execns_probe.c`
  - bumped helper marker to `a90_android_execns_probe v59`
  - added `--allow-wlan-driver-state-on`
  - writes static `ON` to private `/dev/wlan` only after service-manager, HAL, and CNSS allow flags are present
  - records write rc/errno/duration under `wifi_hal_composite_start.wlan_driver_state_on.*`
- `scripts/revalidation/wifi_execns_helper_v59_deploy_preflight.py`
  - V513 deploy/preflight wrapper for helper v59
- `scripts/revalidation/native_wifi_dual_hal_driver_state_on_v513.py`
  - V513 bounded live proof wrapper
  - removes optional `--timeout-sec` from this one command so the extra allow flag fits under the v319 serial shell token limit
- `scripts/revalidation/wifi_execns_helper_v12_deploy_preflight.py`
  - keeps helper deploy default on NCM
  - raises serial fallback chunk default to safe `1900`
  - rejects unsafe serial chunk sizes that exceed the 4096-byte native console/cmdv1x line limit

## Build and Deploy Evidence

```text
artifact: tmp/wifi/v513-a90_android_execns_probe-v59/a90_android_execns_probe
sha256: 9eb52d625974470427a1dda225e11fb5c1c1dffe18c1839f27626cdca6906100
ELF: aarch64 static, no dynamic section
```

NCM deploy was used:

```text
method: ncm
925920 bytes (904 K) copied, 0.019 s, 46 M/s
installed /cache/bin/a90_android_execns_probe sha256=9eb52d625974470427a1dda225e11fb5c1c1dffe18c1839f27626cdca6906100
```

Evidence:

- `tmp/wifi/v513-execns-helper-v59-deploy-preflight/`

## V513 Result

Command result:

```text
decision: v513-dual-hal-driver-state-on-icnss-timeout-captured
pass: True
reason: private /dev/wlan write attempted rc=1 errno=22; CNSS/HAL context captured without link-up
next: triage ICNSS readiness below qcwlanstate before scan/connect
```

Key proof:

```text
wifi_hal_composite_start.wlan_driver_state_on=1
wifi_hal_composite_start.wlan_driver_state_on.allowed=1
wifi_hal_composite_start.wlan_driver_state_on.executed=1
wifi_hal_composite_start.wlan_driver_state_on.path=/dev/wlan
wifi_hal_composite_start.wlan_driver_state_on.write_rc=1
wifi_hal_composite_start.wlan_driver_state_on.write_errno=22
wifi_hal_composite_start.wlan_driver_state_on.duration_ms=19993
wifi_hal_composite_start.child.cnss_daemon.observable=1
wifi_hal_composite_start.child.cnss_daemon.proc_attr_current_captured=1
wifi_hal_composite_start.child.cnss_daemon.postflight_safe=1
wifi_surface_composite.during.wlan_count=0
wifi_surface_composite.during.phy_count=0
wifi_hal_micro_query.result=service-query-timeout
```

Post-run state:

```text
wlanboot.status.qcwlanstate.value=OFF
wlanboot.status.dev_wlan.exists=1
wlanboot.status.dev_wlan.major=478
wlanboot.status.dev_wlan.minor=0
wlanboot.status.sys_class_net_wlan0.exists=0
wlanboot.status.sys_class_ieee80211.count=0
selftest: pass=11 warn=1 fail=0
exposure: guard=ok warn=0 fail=0 ncm=present tcpctl=stopped rshell=stopped boundary=usb-local
```

Dmesg confirms the V513 helper write reached the WLAN driver:

```text
a90_android_exe: Wifi Turning On from UI
cnss-daemon: ctrl_getfamily ... cld80211
icnss: Modules not initialized just return
```

Evidence:

- `tmp/wifi/v513-dual-hal-driver-state-on/`
- `tmp/wifi/v513-dual-hal-driver-state-on/dmesg-after-v513.txt`

## Interpretation

- V510 private `/dev/wlan` reflection remains correct.
- V513 proves the private helper can execute the qcwlanstate `ON` write while service-manager, both Wi-Fi HAL daemons, and CNSS are alive in the same private namespace.
- The blocker is now below the helper/namespace/HAL orchestration layer: the WLAN driver does not finish module readiness, so qcwlanstate stays `OFF`, `IWifi/default` times out, and no `wlan0`/wiphy appears.
- The V513 first run exposed a command transport limit: the legacy serial shell dropped the final argument when the command reached 31 helper arguments. The wrapper now avoids that by using helper default timeout for this proof.

## Source References

- QCACLD qcwlanstate `ON` path and module readiness behavior:
  - https://android.googlesource.com/kernel/msm/+/android-msm-wahoo-4.4-oreo-m4/drivers/staging/qcacld-3.0/core/hdd/src/wlan_hdd_main.c
- The same source shows `boot_wlan` calls WLAN module init, and a successful path should continue to driver registration:
  - https://android.googlesource.com/kernel/msm/+/android-msm-wahoo-4.4-oreo-m4/drivers/staging/qcacld-3.0/core/hdd/src/wlan_hdd_main.c

## Next Gate

V514 completed the read-only ICNSS/WLAN module-readiness classification. See:

- `docs/reports/NATIVE_INIT_V514_ICNSS_MODULE_READINESS_2026-05-21.md`

Recommended V515:

1. Keep ICNSS bind/unbind and firmware mutation blocked.
2. Turn the Android boot-complete order into a machine-readable comparator.
3. Prepare a bounded native CNSS userspace-sequence proof with `cnss_diag` before `cnss-daemon`.
4. Wait for WLFW/QMI/BDF readiness markers before any qcwlanstate retry.
5. Do not move to scan/connect/ping until `wlan0` or wiphy appears.
