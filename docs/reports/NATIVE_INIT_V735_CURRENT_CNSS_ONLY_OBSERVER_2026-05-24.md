# Native Init V735 Current CNSS-only Observer Report

- date: `2026-05-24 KST`
- runner: `scripts/revalidation/native_wifi_current_cnss_only_observer_v735.py`
- evidence: `tmp/wifi/v735-current-cnss-only-observer/`
- latest pointer: `tmp/wifi/latest-v735-current-cnss-only-observer.txt`
- decision: `v735-current-cnss-only-service-publication-advance`
- status: `pass`

## Scope Result

V735 executed the current-build CNSS-only gate. It mounted firmware partitions
read-only in the proof window, opened `subsys_modem`, started lower companion
services plus `cnss_diag` and `cnss-daemon`, observed kernel/QRTR markers, then
rebooted for cleanup.

It did not open `esoc0`, write subsystem state, write DSP boot nodes,
load/unload modules, start service-manager, start Wi-Fi HAL, run scan/connect,
use credentials, run DHCP, change routes, external ping, write a boot image, or
write a partition.

## Key Results

| check | result |
| --- | --- |
| V401/V490 prerequisites | pass on current boot before V735 |
| modem holder | `mss OFFLINING -> ONLINE -> ONLINE`; QRTR RX observed |
| MDM3 | stayed `OFFLINING` |
| helper order | `qrtr_ns,rmt_storage,tftp_server,pd_mapper,cnss_diag,cnss_daemon` |
| CNSS processes | `cnss_diag` pid `626`, `cnss-daemon` pid `627` started and cleaned |
| forbidden actions | service-manager/HAL/wificond/scan/connect/external ping all `0` |
| service publication | dmesg `service_notifier=1` |
| WLFW/service 69 | QRTR readback service events `0`; end-of-list `2`; QMI payloads `0` |
| MHI/QCA6390/BDF/`wlan0` | all `0` |
| cleanup | reboot returned to healthy V724 native init |

## Evidence Summary

V735 confirmed that current helper v121 can safely start CNSS userspace below
HAL/connect:

```text
mode=wifi-companion-start-only
order=qrtr_ns,rmt_storage,tftp_server,pd_mapper,cnss_diag,cnss_daemon
child_started=6
all_observable=1
all_postflight_safe=1
```

Dmesg and QRTR outcome:

```text
qrtr_rx=1
qrtr_tx=1
sysmon_qmi=1
service_notifier=1
wlan_pd=0
mhi=0
qca6390=0
wlfw=0
bdf=0
wlan0=0
kernel_warning=0
service69_readback_events=0
service69_readback_end_of_list=2
qmi_attempted=0
```

WLAN static surface remains consistent with V727:

```text
/proc/modules has wlan: false
/sys/module/wlan exists: true
/sys/module/wlan/parameters visible: true
```

## Interpretation

V735 advances beyond V733:

```text
V733: QRTR RX/TX + sysmon, service_notifier=0
V735: QRTR RX/TX + sysmon + service_notifier=1
```

But V735 still stops before MHI/QCA6390/WLFW:

```text
service publication evidence exists
  + no WLAN-PD marker
  + no service 69
  + no MHI/QCA6390/BDF/wlan0
  => next blocker is WLAN-PD/service-publication-to-MHI, not HAL/connect
```

This keeps Wi-Fi HAL, scan/connect, and credential use unjustified.

## Validation

Executed:

```bash
python3 -m py_compile scripts/revalidation/native_wifi_current_cnss_only_observer_v735.py

python3 scripts/revalidation/native_wifi_current_cnss_only_observer_v735.py \
  --out-dir tmp/wifi/v735-current-cnss-only-observer-plan2 plan

python3 scripts/revalidation/wifi_selinuxfs_toybox_mount_live_executor.py \
  --out-dir tmp/wifi/v735-v401-current-run2 \
  --approval-phrase 'approve v401 toybox mount selinuxfs runtime surface only; no daemon start and no Wi-Fi bring-up' \
  --apply --assume-yes run

python3 scripts/revalidation/native_selinux_policy_load_proof_v490.py \
  --out-dir tmp/wifi/v735-v490-current-run \
  --expect-version 'A90 Linux init 0.9.68 (v724)' \
  --helper-sha256 547232ddb352740bb7a7f1d0f9116162584e34a536b9d9b77869ed8d838e7c89 \
  --approval-phrase 'approve v490 native SELinux policy-load proof only; no init reexec, no daemon start and no Wi-Fi bring-up' \
  --apply --assume-yes run

python3 scripts/revalidation/native_wifi_current_cnss_only_observer_v735.py \
  --out-dir tmp/wifi/v735-current-cnss-only-observer run
```

The final run returned:

```text
decision: v735-current-cnss-only-service-publication-advance
pass: True
cnss_diag_start_executed: True
cnss_daemon_start_executed: True
service_manager_start_executed: False
wifi_hal_start_executed: False
scan_connect_executed: False
external_ping_executed: False
```

Post-run status check showed V724 native init healthy with `fail=0`.

## Next Gate

V736 should stay below HAL/connect and classify the new gap:

1. correlate the exact `service_notifier=1` line with Android V622 service
   `180/74` timing;
2. inspect helper CNSS focus captures for ICNSS/QCA6390 binding and MHI device
   absence;
3. classify why service publication does not progress to WLAN-PD/MHI/WLFW;
4. continue blocking Wi-Fi HAL, scan/connect, credentials, DHCP, routes, and
   external ping until WLFW/BDF/`wlan0` appears.
