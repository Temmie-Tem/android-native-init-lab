# Native Init V812 mdm3/WLAN-PD/service69 Observer Report

## Result

- decision: `v812-sysmon-without-service69`
- pass: `true`
- runner: `scripts/revalidation/native_wifi_mdm3_wlanpd_service69_observer_v812.py`
- evidence: `tmp/wifi/v812-mdm3-wlanpd-service69-observer-rerun/`

## What Ran

```bash
python3 -m py_compile scripts/revalidation/native_wifi_mdm3_wlanpd_service69_observer_v812.py

python3 scripts/revalidation/native_wifi_mdm3_wlanpd_service69_observer_v812.py \
  --out-dir tmp/wifi/v812-mdm3-wlanpd-service69-observer-plan-check \
  plan

python3 scripts/revalidation/native_wifi_mdm3_wlanpd_service69_observer_v812.py \
  --out-dir tmp/wifi/v812-mdm3-wlanpd-service69-observer-rerun \
  run
```

Postflight manual health check:

```bash
python3 scripts/revalidation/a90ctl.py --json version
python3 scripts/revalidation/a90ctl.py --json selftest
```

## Evidence Summary

| Signal | Result |
| --- | --- |
| V401 refresh | `toybox-selinuxfs-mount-live-executor-run-pass` |
| V490 refresh | `v490-selinux-policy-load-proof-pass` |
| V735 live arm | `v735-current-cnss-only-sysmon-gap-classified` |
| Lower companion contract | `qrtr-ns,rmt_storage,tftp_server,pd_mapper,cnss_diag,cnss_daemon` |
| mss state | `ONLINE -> ONLINE` during observation |
| mdm3 state | `OFFLINING -> OFFLINING` during observation |
| QRTR markers | RX/TX present |
| sysmon-qmi | present |
| service-notifier | absent in this bounded window |
| service69/WLFW/BDF/wlan0 | absent |
| QRTR readback | complete, service events `0`, timeouts `0` |
| kernel warnings | `0` in V812 classifier markers |
| postflight | v724 `version` responds and `selftest pass=11 warn=1 fail=0` |

## Classification

V812 confirms that refreshing the current boot with SELinuxfs, Android SELinux
policy, firmware mounts, a `subsys_modem` holder, and the lower companion/CNSS
diagnostic stack is still insufficient to publish WLAN-PD/WLFW service69.

The active gap remains:

```text
Native:
  mss ONLINE / QRTR RX+TX / sysmon-qmi
    -> mdm3 remains OFFLINING
      -> service-notifier absent in this window
        -> WLAN-PD absent
          -> WLFW service69 absent
            -> BDF / wiphy / wlan0 absent
```

This keeps Wi-Fi HAL, scan/connect, credential use, DHCP/routes, and external
ping blocked. The next useful work must isolate the post-sysmon mdm3/WLAN-PD
service-publication preconditions rather than retry `qcwlanstate`, `boot_wlan`,
service-manager, HAL, or scan/connect.

## Safety

- No custom kernel flash, boot image write, partition write, or bootloader
  handoff executed.
- No Wi-Fi HAL, `wificond`, supplicant, hostapd, scan/connect/link-up, or
  credential use executed.
- No DHCP, route change, or external ping executed.
- No `esoc0` access, subsystem state write, bind/unbind, driver override, or
  module load/unload executed.
- Cleanup reboot returned to healthy stock v724 native init.
- No Wi-Fi secret material was written to tracked output.

## Next

V813 should target post-sysmon mdm3/WLAN-PD service-publication preconditions.
The next gate should remain below HAL/connect and should prefer read-only or
tightly bounded classification of Android-vs-native service publication inputs:
service-locator/sysmon state, mdm3 ownership, memshare/client registration,
and lower companion lifetime/order. Do not resume custom-kernel flashing until
a separate host-only compatibility contract explains V774.
