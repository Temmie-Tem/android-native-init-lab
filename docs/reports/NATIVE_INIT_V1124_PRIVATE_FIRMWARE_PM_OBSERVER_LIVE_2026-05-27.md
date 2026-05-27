# V1124 Private Firmware PM Observer Live Report

Date: `2026-05-27`

## Result

- Decision: `v1124-private-firmware-provider-regressed`
- Pass: `true`
- Evidence: `tmp/wifi/v1124-private-firmware-pm-observer-live/manifest.json`
- Summary: `tmp/wifi/v1124-private-firmware-pm-observer-live/summary.md`
- Runner: `scripts/revalidation/native_wifi_private_firmware_pm_observer_live_v1124.py`
- Helper: `a90_android_execns_probe v212`

## Summary

V1124 replayed the V1108 no-pre-CNSS `per_proxy` order with helper-private
firmware mounts. The private firmware mounts succeeded, but
`vendor.qcom.PeripheralManager` provider visibility still regressed.

Key result:

```text
private_firmware_mounts_requested=1
private_firmware_mnt_mounted=1
private_firmware_modem_mounted=1
vndservice_provider_seen=0
child.per_mgr.exit_code=0
per_proxy_start_executed=0
child.per_proxy.start_skipped=1
start_cnss_zero_delay_after_per_mgr=1
cnss_daemon_start_executed=1
```

Tracefs confirmed `cnss-daemon` reached PM register but not PM connect:

```text
pm_client_register_entry=1
pm_client_register_ret=0xffffffff
pm_client_connect_entry=0
pm_client_connect_ret=0
```

## Interpretation

This closes the narrow V1122 hypothesis that global `/vendor` mutation alone
caused the provider loss. The provider also disappears when firmware partitions
are mounted inside the helper-private namespace.

The next blocker is therefore not the global mount surface by itself. It is the
`pm-service` early clean-exit branch that appears when firmware visibility is
present in the PM observer runtime namespace.

## Safety

- `tracefs_write_executed=true`
- `cnss_daemon_start_executed=true`
- `wifi_hal_start_executed=false`
- `scan_connect_executed=false`
- `credential_use_executed=false`
- `dhcp_route_executed=false`
- `external_ping_executed=false`
- `wifi_bringup_executed=false`

The observer reported `observer-reboot-required` because `pm_proxy_helper`
remained in D-state after the window. A cleanup reboot was performed after
evidence capture.

Post-reboot verification:

```text
version: A90 Linux init 0.9.68 (v724)
selftest: pass=11 warn=1 fail=0
netservice: ncm0=absent tcpctl=stopped
residual PM/service-manager/CNSS actors: none matched
```

Additional post-reboot process evidence:
`tmp/wifi/v1124-post-reboot-ps.txt`.

## Next

V1125 should trace the `pm-service` early clean-exit branch inside the
private-firmware PM observer namespace. The likely useful probes are the
`addService`, provider lookup, and mdmdetect/firmware-visibility branches rather
than another broad syscall/BPF search.
