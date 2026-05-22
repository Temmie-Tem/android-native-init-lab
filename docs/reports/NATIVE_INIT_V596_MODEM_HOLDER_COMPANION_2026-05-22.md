# Native Init V596 Modem Holder Companion Report

- date: `2026-05-22 KST`
- status: `readiness advanced`; Wi-Fi external ping is **not** complete
- runner: `scripts/revalidation/native_wifi_modem_holder_companion_v596.py`
- evidence: `tmp/wifi/v596-modem-holder-companion-proof/`
- related baseline: `tmp/wifi/v596-v490-current-run/manifest.json`

## Scope

V596 tested the narrowest live path after V594/V595:

- global read-only firmware mounts for `/vendor/firmware_mnt` and
  `/vendor/firmware-modem`;
- a temporary holder for `subsys_modem` only;
- QRTR RX gating before companion start;
- bounded companion daemon start-only replay.

It did not start service-manager, Wi-Fi HAL, `qcwlanstate`, supplicant,
hostapd, wificond, scan/connect/link-up, credentials, DHCP, routes, or external
ping.

## Live Result

The generated manifest returned:

```text
decision: v596-modem-holder-not-started
pass: False
reason: modem holder did not report opened
device_mutations: True
daemon_start_executed: True
wifi_bringup_executed: False
```

That decision was a runner classification bug, not the actual kernel outcome.
The holder status file was sampled before the background open wrote `opened`,
and the shell also used unqualified `grep`. The runner was patched afterward to
poll the status file and to classify holder-open from QRTR RX or `mss=ONLINE`.
The live test was not repeated because the target readiness evidence was already
captured and the device reboot cleanup passed.

## Positive Evidence

The holder opened only `subsys_modem`; no `esoc0` open was used. Dmesg proved
modem PIL and QRTR RX:

```text
subsys-restart: __subsystem_get(): __subsystem_get: modem count:0
subsys-pil-tz 4080000.qcom,mss: modem: loading ...
subsys-pil-tz 4080000.qcom,mss: modem: Brought out of reset
subsys-pil-tz 4080000.qcom,mss: modem: Power/Clock ready interrupt received
qrtr: Modem QMI Readiness RX cmd:0x2 node[0x0]
```

The companion stack then started in the intended order:

```text
wifi_companion_start.order=qrtr_ns,rmt_storage,tftp_server,pd_mapper,cnss_diag,cnss_daemon
wifi_companion_start.child.qrtr_ns.start_order=1
wifi_companion_start.child.rmt_storage.start_order=2
wifi_companion_start.child.tftp_server.start_order=3
wifi_companion_start.child.pd_mapper.start_order=4
wifi_companion_start.child.cnss_diag.start_order=5
wifi_companion_start.child.cnss_daemon.start_order=6
```

New readiness markers appeared:

```text
qrtr: Modem QMI Readiness TX cmd:0x2 node[0x1]
sysmon-qmi: ssctl_new_server: Connection established between QMI handle and modem's SSCTL service
```

The runner summary counted:

```text
qrtr_rx=1
qrtr_tx=1
sysmon_qmi=1
kernel_warning=0
```

## Remaining Gap

The companion helper still ended with:

```text
wifi_companion_start.all_postflight_safe=1
wifi_companion_start.result=start-only-runtime-gap
```

No `service-notifier`, WLAN-PD, WLFW/QMI connected, BDF/regdb/bdwlan, FW-ready,
or `wlan0` marker appeared in this window. So V596 moved the blocker from
"modem never reaches QRTR TX/sysmon" to "post-sysmon companion/WLAN-PD/WLFW
readiness is still missing."

## Cleanup

V596 used reboot as the cleanup boundary. Post-reboot checks confirmed:

```text
version_seen=True
status_healthy=True
A90 Linux init 0.9.61 (v319)
selftest: pass=11 warn=1 fail=0
```

Additional post-reboot checks found no residual helper/CNSS/QRTR/TFTP/pd-mapper
processes and no global firmware/vendor mounts.

## Safety Notes

- V596 did not reproduce the V595 `subsystem_put: esoc0 count:0` / reference
  mismatch WARNING.
- The companion helper emitted private namespace `EXT4-fs ... for active
  namespaces on umount` messages for its bounded mount cleanup. The device
  rebooted cleanly afterward, but the next runner should keep reboot cleanup for
  companion windows until the helper mount cleanup is separately tightened.
- The current Wi-Fi goal is still incomplete because no scan/connect/link-up or
  external ping has been attempted in native init after this readiness advance.

## Next Gate

Recommended V597:

1. Treat global firmware mounts + `subsys_modem` holder + QRTR RX gate as the
   new minimum precondition.
2. Extend observation around the post-sysmon gap without adding scan/connect:
   `service-notifier`, WLAN-PD, WLFW, BDF/regdb/bdwlan, and `wlan0`.
3. Keep `esoc0` unopened and keep reboot cleanup for the next companion proof.
4. Only after WLFW/BDF or `wlan0` appears should the project move back toward
   qcwlanstate/HAL/scan/connect gates.
