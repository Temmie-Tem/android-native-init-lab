# Native Init V588 Modem/Subsys Window Values Proof

- date: `2026-05-22 KST`
- objective: capture modem/subsystem sysfs values inside the bounded companion window before any qcwlanstate, HAL, scan/connect, or external ping retry
- status: `classified`; Wi-Fi external ping is **not** complete

## Scope

- Helper: `a90_android_execns_probe v99`
- Helper sha256: `8e10ad0c72d3893c3e8edd427fd92d674e7ed29c84fdbc57ea9f4ed74409a92d`
- Deploy evidence: `tmp/wifi/v588-execns-helper-v99-deploy-preflight/`
- Live evidence: `tmp/wifi/v588-modem-subsys-window-values/`
- Plan: `docs/plans/NATIVE_INIT_V588_MODEM_SUBSYS_WINDOW_VALUES_PLAN_2026-05-22.md`

## Guardrails

- No boot image flash.
- No reboot or recovery handoff.
- No PID1/native-init boot hook.
- No subsystem sysfs writes.
- No qcwlanstate/sysfs driver-state write.
- No Wi-Fi HAL or `IWifi.start()`.
- No supplicant/hostapd/wificond.
- No scan/connect/link-up/DHCP/routing.
- No external ping.
- No credential use or credential-bearing evidence.
- Companion children are bounded and cleanup-checked.

## Deploy Result

```text
decision: execns-helper-v99-deploy-pass
pass: True
reason: helper v99 deployed or already current; V500 preflight was rerun
device_mutations: True
daemon_start_executed: False
wifi_bringup_executed: False
```

## V588 Live Result

```text
decision: v588-modem-subsys-offline-window
pass: True
reason: in-window values captured; modem/esoc states are mss=OFFLINING mdm3=OFFLINING and QRTR/QMI/WLFW markers remain absent
next: compare Android boot-time subsystem state and identify the smallest safe subsystem-readiness trigger before qcwlanstate/HAL retry
device_commands_executed: True
device_mutations: True
daemon_start_executed: True
wifi_bringup_executed: False
```

## Preconditions

```text
native-clean=pass
helper-v99-ready=pass
selinuxfs-mounted=pass
v490-current-policy-load=pass
v525-identity-contract=pass
no-active-target-processes=pass
no-wifi-link-surface=pass
v533-rmt-storage-window-proof=pass
```

## Captured Window Values

Helper v99 captured modem and external modem subsystem values inside the same bounded companion window:

```text
mss_name=modem
mss_state=OFFLINING
mss_restart_level=SYSTEM
mss_firmware_name=modem
mss_crash_count=0
mdm3_name=esoc0
mdm3_state=OFFLINING
mdm3_restart_level=SYSTEM
mdm3_firmware_name=esoc0
mdm3_crash_count=0
rpmsg_drivers_autoprobe=1
subsys_value_captures=12
```

The window still lacks the lower readiness surface:

```text
/proc/net/qrtr: absent
/dev/qrtr: absent
/sys/bus/rpmsg/devices: present but empty
/sys/kernel/debug/service_notifier: absent
QIPCRTR sockets: 0
```

## Marker Delta

Native still only reaches local CNSS netlink activity:

```text
cnss_diag_netlink=21
cnss_daemon_netlink=39
rmt_storage=2
qrtr=0
qrtr_modem_readiness=0
qmi_server_connected=0
wlfw_start=0
wlfw_thread=0
bdf_regdb=0
bdf_bdwlan=0
wlan_fw_ready=0
wlan0_event=0
wma_service_ready=0
```

No readiness marker was observed.

## Post Status

```text
init: A90 Linux init 0.9.61 (v319)
selftest: pass=11 warn=1 fail=0
exposure: guard=ok warn=0 fail=0 ncm=present tcpctl=stopped rshell=stopped boundary=usb-local
uptime: 76120.52s
battery: 100% Full temp=35.2C
thermal: cpu=42.7C gpu=41.0C
adbd: stopped
netservice: disabled tcpctl=stopped
rshell: stopped
```

## Interpretation

- V588 proves the missing QRTR/QMI path is not caused by inability to read the relevant modem subsystem sysfs values from the helper window.
- The modem and external modem subsystem nodes are visible, but both report `OFFLINING` during the native companion replay.
- `rpmsg` driver registration exists and `drivers_autoprobe=1`, but no active rpmsg device endpoint appears.
- Companion services remain observable and cleanup-safe, but their start-only replay does not move the modem/esoc state to the Android QRTR-readiness path.
- qcwlanstate/HAL, scan/connect, credentials, DHCP, routing, and external ping remain blocked until a lower readiness marker changes.

## Validation

```bash
python3 -m py_compile \
  scripts/revalidation/wifi_execns_helper_v99_deploy_preflight.py \
  scripts/revalidation/native_wifi_modem_subsys_window_values_v588.py
scripts/revalidation/build_android_execns_probe_helper.sh \
  tmp/wifi/v588-a90_android_execns_probe-v99/a90_android_execns_probe
git diff --check
python3 scripts/revalidation/wifi_execns_helper_v99_deploy_preflight.py preflight
python3 scripts/revalidation/wifi_execns_helper_v99_deploy_preflight.py --apply --assume-yes \
  --approval-phrase "approve v588 deploy execns helper v99 only; no daemon start and no Wi-Fi bring-up" run
python3 scripts/revalidation/native_wifi_modem_subsys_window_values_v588.py preflight
python3 scripts/revalidation/native_wifi_modem_subsys_window_values_v588.py --apply --assume-yes \
  --approval-phrase "approve v588 modem subsys window value proof only; no service-manager, no Wi-Fi HAL start, no scan/connect/link-up and no external ping" run
python3 scripts/revalidation/a90ctl.py --json exposure
python3 scripts/revalidation/a90ctl.py --json selftest
python3 scripts/revalidation/a90ctl.py --json status
```

Tracked diff secret scan for the target SSID/password returned no hits.

## Next Gate

Recommended V589:

1. Compare Android boot-time subsystem values against the V588 native in-window values.
2. Identify whether Android brings `modem`/`esoc0` out of `OFFLINING` before `vendor.qrtr-ns`, before `sysmon-qmi`, or before WLAN-PD.
3. Plan the smallest safe subsystem-readiness input proof that does not start HAL, scan/connect, or expose credentials.
4. Retry qcwlanstate/HAL only after QRTR modem readiness, service-notifier/WLAN-PD, QMI server connected, BDF, firmware-ready, or `wlan0` marker changes.
