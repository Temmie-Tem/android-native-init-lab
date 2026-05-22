# Native Init V587 QRTR/Modem Window Surface Proof

- date: `2026-05-22 KST`
- objective: capture in-window QRTR/modem surface evidence from the bounded companion helper before any qcwlanstate, HAL, scan/connect, or external ping retry
- status: `classified`; Wi-Fi external ping is **not** complete

## Scope

- Helper: `a90_android_execns_probe v98`
- Helper sha256: `be9b59f20af3013e996266e35c225487d266d789455a4f656dfaa2efeacd7f23`
- Deploy evidence: `tmp/wifi/v587-execns-helper-v98-deploy-preflight/`
- Live evidence: `tmp/wifi/v587-qrtr-modem-window-surface/`
- Plan: `docs/plans/NATIVE_INIT_V587_QRTR_MODEM_WINDOW_SURFACE_PLAN_2026-05-22.md`

## Guardrails

- No boot image flash.
- No reboot or recovery handoff.
- No PID1/native-init boot hook.
- No qcwlanstate/sysfs driver-state write.
- No Wi-Fi HAL or `IWifi.start()`.
- No supplicant/hostapd/wificond.
- No scan/connect/link-up/DHCP/routing.
- No external ping.
- Companion children are bounded and cleanup-checked.

## Deploy Result

NCM preflight initially failed until the host NCM interface was configured. A slow serial deploy attempt was stopped before completion, then NCM was used after reachability returned.

```text
decision: execns-helper-v98-deploy-pass
pass: True
reason: helper v98 deployed or already current; V500 preflight was rerun
device_mutations: True
daemon_start_executed: False
wifi_bringup_executed: False
```

## V587 Live Result

```text
decision: v587-window-surface-no-readiness-delta
pass: True
reason: helper v98 captured in-window QRTR/modem surfaces and cleaned companions, but no QRTR/QMI/WLFW/BDF/FW-ready marker appeared
next: compare Android/native modem/rpmsg/subsys inputs or plan the smallest host-controlled QRTR readiness input proof before qcwlanstate/HAL retry
device_commands_executed: True
device_mutations: True
daemon_start_executed: True
wifi_bringup_executed: False
```

## Precondition Checks

```text
native-clean=pass
helper-v98-ready=pass
selinuxfs-mounted=pass
v490-current-policy-load=pass
v525-identity-contract=pass
no-active-target-processes=pass
no-wifi-link-surface=pass
v533-rmt-storage-window-proof=pass
```

## Window Surface

Helper v98 captured the following in-window surface summary:

```text
window_surface_ready=True
window_proc_qrtr_captured=False
window_msm_subsys_captured=True
window_rpmsg_captured=True
window_service_notifier_captured=False
```

Detailed in-window evidence:

```text
/proc/net/qrtr: open-error=No such file or directory
/dev filtered: wlan
/sys/bus/msm_subsys/devices: subsys0..subsys9 visible
/sys/bus/rpmsg/devices: present but count=0
/sys/class/remoteproc: open-error=No such file or directory
/sys/kernel/debug/service_notifier: open-error=No such file or directory
/sys/devices/platform/soc/soc:qcom,mdm3: visible with subsys9
/sys/devices/platform/soc/4080000.qcom,mss: visible with subsys0
```

## Marker Delta

Native still only reaches CNSS netlink activity:

```text
cnss_diag_netlink=21
cnss_daemon_netlink=39
rmt_storage=2
qrtr_modem_readiness=0
wlfw_start=0
wlfw_thread=0
qmi_server_connected=0
bdf_regdb=0
bdf_bdwlan=0
wlan_fw_ready=0
wlan0_event=0
```

No readiness marker was observed.

## Post Status

```text
init: A90 Linux init 0.9.61 (v319)
selftest: pass=11 warn=1 fail=0
exposure: guard=ok warn=0 fail=0 ncm=present tcpctl=stopped rshell=stopped boundary=usb-local
adbd: stopped
netservice: disabled tcpctl=stopped
rshell: stopped
```

## Interpretation

- V587 proves the helper can capture in-window modem-related sysfs surfaces without reintroducing the v572 boot-time PID1 risk.
- `msm_subsys` and modem platform sysfs are visible, so the blocker is not simply total modem sysfs absence.
- `/proc/net/qrtr`, `/dev/qrtr`, `service_notifier`, and active rpmsg endpoints remain absent or empty during the companion window.
- `cnss-daemon` reaching netlink remains insufficient; it still does not progress to QRTR modem readiness, WLFW, QMI server connected, BDF, firmware ready, or `wlan0`.
- qcwlanstate/HAL, scan/connect, and external ping should remain blocked until a lower readiness marker changes.

## Validation

```bash
python3 -m py_compile scripts/revalidation/wifi_execns_helper_v98_deploy_preflight.py \
  scripts/revalidation/native_wifi_qrtr_modem_window_surface_v587.py
scripts/revalidation/build_android_execns_probe_helper.sh \
  tmp/wifi/v587-a90_android_execns_probe-v98/a90_android_execns_probe
python3 scripts/revalidation/wifi_execns_helper_v98_deploy_preflight.py preflight
python3 scripts/revalidation/wifi_execns_helper_v98_deploy_preflight.py --apply --assume-yes \
  --approval-phrase "approve v587 deploy execns helper v98 only; no daemon start and no Wi-Fi bring-up" run
python3 scripts/revalidation/native_wifi_qrtr_modem_window_surface_v587.py preflight
python3 scripts/revalidation/native_wifi_qrtr_modem_window_surface_v587.py --apply --assume-yes \
  --approval-phrase "approve v587 QRTR modem window surface proof only; no service-manager, no Wi-Fi HAL start, no scan/connect/link-up and no external ping" run
```

## Next Gate

Recommended V588:

1. Compare Android/native `msm_subsys`, rpmsg, and service-notifier/sysmon surfaces at the file-content level, not only directory presence.
2. Capture selected read-only values under `subsys0` and `subsys9` such as `name`, `state`, `restart_level`, `firmware_name`, or equivalent present attributes.
3. Determine whether the missing readiness input is modem/subsystem state, QRTR endpoint registration, service-notifier debugfs absence, or an Android init/service ordering dependency.
4. Keep qcwlanstate, HAL start, scan/connect, credentials, DHCP, routing, and external ping blocked until a lower readiness marker changes.
