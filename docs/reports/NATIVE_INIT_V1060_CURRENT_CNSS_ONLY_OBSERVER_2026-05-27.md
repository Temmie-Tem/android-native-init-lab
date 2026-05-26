# Native Init V1060 Current CNSS-only Observer Report

Date: `2026-05-27`

## Summary

V1060 refreshed the current-boot SELinux and firmware prerequisites, then ran
the bounded CNSS-only observer with helper v180.  The lower path restored modem
PIL readiness through QRTR TX and `sysmon-qmi`, and the helper successfully
started the lower companion set plus `cnss_diag` and `cnss-daemon`.

Decision from the runner:

```text
v735-current-cnss-only-sysmon-gap-classified
```

This is a PASS for the current CNSS-only observer.  It does not complete Wi-Fi
bring-up: no service publication, MHI, WLFW, BDF, or `wlan0` appeared.  The
remaining gap is still below service-manager, Wi-Fi HAL, scan/connect, DHCP,
routes, credentials, and external ping.

## Evidence

Private evidence directories:

```text
tmp/wifi/v1060-v401-selinuxfs/
tmp/wifi/v1060-v490-policy-load/
tmp/wifi/v1060-current-cnss-only-observer/
```

Manifests:

```text
tmp/wifi/v1060-v401-selinuxfs/manifest.json
tmp/wifi/v1060-v490-policy-load/manifest.json
tmp/wifi/v1060-current-cnss-only-observer/manifest.json
```

## Current-Boot Preconditions

| Step | Decision | Result |
| --- | --- | --- |
| V401 SELinuxFS mount | `toybox-selinuxfs-mount-live-executor-run-pass` | SELinuxFS `status` page visible |
| `mountsystem ro` | cmdv1 pass | `/mnt/system/system` and `/mnt/system/system/bin` visible |
| V490 policy load | `v490-selinux-policy-load-proof-pass` | Android split policy loaded without init reexec or daemon start |

## Live Window Result

| Check | Result |
| --- | --- |
| firmware mounts | pass |
| `/vendor/firmware-modem/image/modem.b00` | visible |
| `/dev/subsys_modem` holder | opened |
| `mss` state | `OFFLINING -> ONLINE -> ONLINE` |
| `mdm3` state | `OFFLINING -> OFFLINING -> OFFLINING` |
| lower companion set | started |
| `cnss_diag` | started |
| `cnss-daemon` | started |
| service-manager | not started |
| Wi-Fi HAL | not started |
| scan/connect/external ping | not executed |

The helper contract passed:

```text
mode=wifi-companion-start-only
order=qrtr_ns,rmt_storage,tftp_server,pd_mapper,cnss_diag,cnss_daemon
result=companion-window-pass
all_observable=1
all_postflight_safe=1
service_manager=0
wifi_hal=0
```

## Marker Result

| Marker | Count |
| --- | --- |
| `qrtr_rx` | `1` |
| `qrtr_tx` | `1` |
| `sysmon_qmi` | `1` |
| `service_notifier` | `0` |
| `wlan_pd` | `0` |
| `mhi` | `0` |
| `qca6390` | `0` |
| `wlfw` | `0` |
| `bdf` | `0` |
| `wlan0` | `0` |
| `kernel_warning` | `0` |

First positive lower markers:

```text
qrtr: Modem QMI Readiness RX cmd:0x2 node[0x0]
qrtr: Modem QMI Readiness TX cmd:0x2 node[0x1]
sysmon-qmi: ssctl_new_server: Connection established between QMI handle and modem's SSCTL service
```

QRTR service 69 readback stayed empty for instances `0` and `1`:

```text
service_events=0
qmi_attempted=0
status=complete
```

## Cleanup

The runner issued a cleanup reboot.  The reboot command intentionally lost its
END marker because the device restarted, but post-reboot native health was
proven:

```text
version_seen=true
status_healthy=true
selftest=pass=11 warn=1 fail=0
```

After cleanup reboot, the native serial bridge was healthy.  NCM/tcpctl was not
running because the netservice flag was disabled in this boot, so follow-up
loops should re-enable NCM if fast transfer is needed.

## Guardrails

- No Wi-Fi credentials used.
- No service-manager, Wi-Fi HAL, `wificond`, supplicant, scan/connect/link-up, DHCP/routes, external ping, eSoC open/ioctl, GPIO write, sysfs/debugfs write, module load/unload, firmware mutation, boot image write, partition write, or Android boot handoff.
- Device mutations were limited to SELinuxFS mount, Android system read-only mount, SELinux policy load, firmware partition read-only mounts, lower companion/CNSS-only start-only window, and cleanup reboot.

## Interpretation

V1058 identified missing runtime prerequisites, V1059 proved firmware mount
refresh, and V1060 proved the current CNSS-only lower window can recover
`qrtr_tx` and `sysmon_qmi`.  The missing transition is now narrower: QRTR
service publication for WLAN-PD/WLFW, MHI, BDF, and `wlan0` still does not occur
even after companion and CNSS-only start.

The next gate should focus on modem/WLAN-PD publication or the ICNSS/MHI trigger
boundary, still below service-manager, Wi-Fi HAL, scan/connect, DHCP/routes,
credentials, and external ping.
