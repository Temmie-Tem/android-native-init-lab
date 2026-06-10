# Native Init V2172 Wi-Fi Status/Scan Live Validation

Date: `2026-06-08`

## Summary

- Candidate tag: `v2172-wifi-status-scan`
- Parent baseline: `v2169-transport-contract`
- Test image: `workspace/private/inputs/boot_images/boot_linux_v2172_wifi_status_scan.img`
- Test image SHA256:
  `c806de3fa5e22afa5a0a5c4040a8f40139e50e8b40e14bff98a6a30197de09f4`
- Rollback image: `workspace/private/inputs/boot_images/boot_linux_v2169_transport_contract.img`
- Rollback image SHA256:
  `190b93d0741a6eeba17913c940f3bb398fed765f38532d5e0009840112166d6d`
- Evidence:
  `tmp/wifi/runs/v2172-wifi-status-scan-live-fixed-20260608-071956/`
- Decision: `v2172-wifi-status-scan-live-pass-rollback-ok`

## First Attempt Finding

The first V2172 flash used a per-version property root:

```text
/mnt/sdext/a90/private-property-v317/v2172/dev/__properties__
```

That path does not exist on the SD workspace. The helper failed before Wi-Fi
bring-up:

```text
helper_status=setup-error
setup_error=lstat property root: No such file or directory
```

The builder was corrected to reuse the verified V726 property snapshot:

```text
/mnt/sdext/a90/private-property-v317/v726/dev/__properties__
```

No SD/private-property content was written during this fix.

## Fixed Flash

The corrected image flashed and verified:

- local image marker: `0.9.249 (v2172-wifi-status-scan)`;
- local image SHA256 matched `c806de3f...`;
- TWRP boot partition readback SHA256 matched `c806de3f...`;
- post-boot `version` reported
  `A90 Linux init 0.9.249 (v2172-wifi-status-scan)`;
- post-boot `status` reported `selftest: pass=11 warn=1 fail=0`.

## Wi-Fi Status

After the supervisor window, `wifi status` succeeded:

```text
wlan0_present=1
mac=xx:7f:3a
mac_raw_redacted=1
operstate=down
flags=0x1002
decision=wifi-status-wlan0-present
```

The helper result file was absent because the supervisor timed out the helper,
but the summary recorded the useful state:

```text
wlan0_present=1
helper_timed_out=1
baseline_ready=1
supervisor_result=wlan0-ready
```

This timeout is a cleanup/observability issue, not a scan blocker.

## Wi-Fi Scan

After hiding the menu, bounded direct nl80211 scan succeeded:

```text
credentials=0
connect=0
dhcp_routing=0
external_ping=0
raw_results_redacted=1
link_up_rc=0
ifindex=9
netlink_open=1
family_id=19
trigger_rc=0
delay_ms=8000
scan_result_count=12
decision=wifi-scan-pass
```

No Wi-Fi credentials, association, DHCP, route install, or external ping were
used.

## Rollback

Rollback to `v2169-transport-contract` succeeded:

- TWRP boot partition readback SHA256 matched
  `190b93d0741a6eeba17913c940f3bb398fed765f38532d5e0009840112166d6d`;
- post-rollback `version` reported
  `A90 Linux init 0.9.247 (v2169-transport-contract)`;
- post-rollback `selftest` reported `pass=11 warn=1 fail=0`.

## Residual Risk

- The V2172 helper reaches `wlan0-ready` but supervisor cleanup times out the
  helper. This is acceptable for scan validation, but should be cleaned before
  baseline promotion.
- The V2169/V2170 per-version property-root pattern is not sufficient for Wi-Fi
  helper bring-up unless that private-property tree exists. New Wi-Fi test boots
  should either reuse the verified V726 snapshot or explicitly provision a new
  private-property snapshot.
