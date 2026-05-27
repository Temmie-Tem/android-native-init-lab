# Native Init V1121 Firmware Mount-only Provider Live Report

Date: `2026-05-27`

## Result

- Decision: `v1121-firmware-mount-only-provider-still-missing`
- Pass: `true`
- Evidence: `tmp/wifi/v1121-firmware-mount-only-provider-live/manifest.json`
- Summary: `tmp/wifi/v1121-firmware-mount-only-provider-live/summary.md`
- Runner:
  `scripts/revalidation/native_wifi_firmware_mount_only_provider_live_v1121.py`

## Summary

V1121 tested the smallest provider-lifetime repair candidate after V1120:
firmware mounts only, no global `/dev/subsys_modem` holder.

Result: provider registration still disappears.

```text
firmware_mounts_executed=True
global_modem_holder_opened=False
vndservice_provider_seen=0
child.per_mgr.exited=1
child.per_mgr.exit_code=0
cnss_register_entries=0
cnss_connect_entries=0
```

So the V1120 failure is not caused only by the global modem holder. The firmware
mount/global `/vendor` surface is enough to change `pm-service` lifetime from
the V1108 provider-positive behavior.

## Evidence

Firmware mount-only state:

```text
/vendor/firmware_mnt=True
/vendor/firmware-modem=True
mss=OFFLINING->OFFLINING
mdm3=OFFLINING->OFFLINING
qrtr_services={"180": 0, "69": 0, "74": 0}
```

Provider and PM path:

```json
{
  "provider_seen": "0",
  "per_mgr_exited": "1",
  "per_mgr_exit_code": "0",
  "per_proxy_start_executed": "0",
  "per_proxy_start_skipped": "1",
  "cnss_register_entries": 0,
  "cnss_connect_entries": 0,
  "register_ret": [],
  "connect_ret": []
}
```

Cleanup returned to healthy native init:

```text
version_seen=True
status_healthy=True
selftest: pass=11 warn=1 fail=0
netservice: disabled tcpctl=stopped
```

## Comparison

| gate | firmware mounts | global holder | provider | CNSS register | CNSS connect |
| --- | --- | --- | --- | --- | --- |
| V1108 | no | no | `1` | `0x0` | `0x0` |
| V1120 | yes | yes | `0` | `0xffffffff` | not reached |
| V1121 | yes | no | `0` | not reached | not reached |

This isolates the provider regression to the firmware mount/global vendor
surface rather than the holder alone.

## Safety

- `wifi_hal_start_executed=False`
- `scan_connect_executed=False`
- `credential_use_executed=False`
- `dhcp_route_executed=False`
- `external_ping_executed=False`
- `wifi_bringup_executed=False`
- `partition_write_executed=False`
- `flash_executed=False`

## Next

V1122 should compare the provider-positive V1108 namespace with the
firmware-mounted V1121 namespace. The narrow question is why creating/mounting
global `/vendor/firmware_mnt` and `/vendor/firmware-modem` makes
`/vendor/bin/pm-service` exit cleanly before registering
`vendor.qcom.PeripheralManager`.

Candidate checks:

1. `pm-service` stderr/stdout delta between V1108 and V1121.
2. `/vendor`, `/mnt/vendor`, and private-root mount namespace differences.
3. `pm-service` dynamic linker/library path behavior when global `/vendor`
   exists.
4. Whether firmware mounts should be moved into the private runtime namespace
   instead of the global native root.
