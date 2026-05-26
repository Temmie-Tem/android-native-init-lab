# Native Init V1061 Global Firmware PM Full-Contract Report

Date: `2026-05-27`

## Summary

V1061 combined the V1059/V1060 global firmware prerequisite with the V1055 PM
full-contract-with-modem-holder gate.  The result narrowed the blocker:

```text
v1061-global-firmware-modem-holder-confirmed-pm-contract-missing
```

The global firmware mount and global `/dev/subsys_modem` holder fixed the helper
modem pre-holder failure seen in V1055.  Helper v180 now confirmed the modem
pre-holder and observed `pm_proxy_helper` holding `/dev/subsys_modem`.  The PM
full contract still did not complete because `pm-service`/`per_mgr` never held
`/dev/subsys_modem`.

No Wi-Fi HAL, `wificond`, scan/connect, credentials, DHCP/routes, or external
ping was executed.

## Evidence

Private evidence directories:

```text
tmp/wifi/v1061-v401-selinuxfs/
tmp/wifi/v1061-v490-policy-load/
tmp/wifi/v1061-global-firmware-pm-full-contract/
```

Manifest:

```text
tmp/wifi/v1061-global-firmware-pm-full-contract/manifest.json
```

## Preconditions

| Step | Decision | Result |
| --- | --- | --- |
| V401 SELinuxFS mount | `toybox-selinuxfs-mount-live-executor-run-pass` | SELinuxFS mounted |
| `mountsystem ro` | cmdv1 pass | Android system root visible |
| V490 policy load | `v490-selinux-policy-load-proof-pass` | policy loaded without init reexec or daemon start |

## Live Result

| Item | Value |
| --- | --- |
| firmware mounts | pass |
| `/vendor/firmware-modem/image/modem.b00` | visible |
| global `/dev/subsys_modem` holder | opened |
| `mss` state | `OFFLINING -> ONLINE -> ONLINE` |
| `mdm3` state | `OFFLINING -> OFFLINING -> OFFLINING` |
| `qrtr_rx` | `1` |
| `qrtr_tx` | `0` |
| `sysmon_qmi` | `0` |
| QRTR service `69/74/180` | `0/0/0` |
| MHI/WLFW/BDF/`wlan0` | absent |

## PM Contract Result

V1061 fixed the first V1055 failure:

```text
modem_pre_holder_confirmed=1
modem_pre_holder_opened=1
modem_pre_holder_nonblock_opened=1
modem_pre_holder_nonblock_errno=0
pm_proxy_helper_start_executed=1
pm_proxy_helper_subsys_modem_fd_count=1
mdm_helper_esoc0_fd_seen=1
```

The remaining PM contract gap:

```text
per_mgr_start_attempted=1
per_mgr_subsys_modem_fd_count=0
pm_proxy_started=1
pm_full_contract_seen=0
result=pm-full-contract-missing-no-open
```

This means the next blocker is no longer kernel firmware visibility or helper
modem pre-holder startup.  It is the `pm-service`/`per_mgr` side of the Android
PM fd contract.

## Safety Finding

The live window also produced a kernel warning during cleanup:

```text
subsystem_put(): subsystem_put: esoc0 count:0
esoc0: subsystem_put: Reference count mismatch
WARNING: CPU: 0 PID: 623 at drivers/soc/qcom/subsystem_restart.c:1123 subsystem_put+0x3a8/0x3c0
```

The cleanup reboot completed and post-reboot native health passed:

```text
version_seen=true
status_healthy=true
selftest=pass=11 warn=1 fail=0
```

Because the warning indicates an eSoC reference-count cleanup mismatch, the
runner was tightened after this evidence so future repeats block on
`kernel-warning-review`.  Do not widen this path toward subsystem trigger,
service-manager, Wi-Fi HAL, or scan/connect until the warning path is
classified.

## Guardrails

- No Wi-Fi credentials used.
- No Wi-Fi HAL, `wificond`, `IWifi.start`, `qcwlanstate`, scan/connect/link-up, DHCP/routes, or external ping.
- No eSoC controller ioctl, notify, BOOT_DONE spoofing, GPIO write, sysfs/debugfs write, module load/unload, firmware mutation, partition write, boot image write, or Android boot handoff.
- `/dev/subsys_esoc0` open was not attempted.

## Next

V1062 should be host-only or read-only first: classify why native
`pm-service`/`per_mgr` does not open `/dev/subsys_modem` despite:

- `pm_proxy_helper` holding `/dev/subsys_modem`;
- `pm-service` running in `u:r:vendor_per_mgr:s0`;
- `pm-proxy` running;
- `mdm_helper` `/dev/esoc-0` fd observed.

Focus points:

1. Compare Android V1024 `pm-service` fd evidence with V1061 `pm-service` fd and property-service shim evidence.
2. Classify whether `pm-service` needs a missing binder/vndbinder transaction, property value, service-manager registration, or timing input before opening `/dev/subsys_modem`.
3. Classify the V1061 eSoC reference-count warning before any repeat or widening.
