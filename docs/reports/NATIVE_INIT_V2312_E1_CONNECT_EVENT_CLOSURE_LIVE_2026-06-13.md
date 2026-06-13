# Native Init V2312 E1 Connect-Event Closure Live Validation

## Summary

- Cycle: `V2312`
- Track: active WLAN kernel-interface event epic final closure.
- Type: boot-only flash plus one bounded live Wi-Fi connect-event assertion.
- Decision: `v2312-e1-connect-event-closure-pass`
- Result: PASS
- Resident artifact: `A90 Linux init 0.9.276 (v2312-e1-connect-event-closure)`
- Boot image: `workspace/private/inputs/boot_images/boot_linux_v2312_e1_connect_event_closure.img`
- Boot SHA256: `6c8019a060627ba7c7119247337a342719f83dc2b94a626ab10a189a8e3860cb`
- Safety rollback remains: `v2237-supplicant-terminate-poll`

## Why V2312 Was Needed

The closure required `wifi events` and `wifi connect` to overlap. The host-side NCM/tcpctl second
channel was not usable without host network reconfiguration, so V2312 added a device-side
`wifi connect-event [profile] [timeout_ms]` command. The command joins nl80211 multicast groups
before forking a silenced child that runs the existing bounded `wifi connect` path, then it verifies
that `NL80211_CMD_CONNECT` and final carrier-up agree.

## Static Validation

- `python3 -m py_compile workspace/public/src/scripts/revalidation/build_native_init_boot_v2312_e1_connect_event_closure.py`
- `python3 -m py_compile tests/test_build_native_init_boot_v2312_e1_connect_event_closure.py`
- `python3 -m unittest tests.test_build_native_init_boot_v2312_e1_connect_event_closure`
- `python3 -m unittest discover -s tests -p 'test_*.py'` — `984` tests green after the final parser cap fix and live validation.
- `git diff --check`

## Flash Gate

- Flash path: `workspace/public/src/scripts/revalidation/native_init_flash.py`
- Expected SHA256: `6c8019a060627ba7c7119247337a342719f83dc2b94a626ab10a189a8e3860cb`
- Readback SHA256: `6c8019a060627ba7c7119247337a342719f83dc2b94a626ab10a189a8e3860cb`
- Post-flash version: `A90 Linux init 0.9.276 (v2312-e1-connect-event-closure)`
- Post-flash `selftest`: `pass=11 warn=1 fail=0`
- Flash result: no rollback required.

## Live Closure Evidence

- Run profile: `<redacted-ssid>`
- Profile evidence: `profile_valid=1`, `profile_key_mgmt=WPA-PSK`, `secret_values_logged=0`
- Command: `wifi connect-event <redacted-ssid> 60000`
- Event collector version: `a90-native-wifi-connect-event-v1`
- nl80211 groups joined: `mlme=1`, `scan=1`, `config=1`
- Event count: `event.count=1`
- Connect event count: `event.connect_count=1`
- Observed command: `event.0.cmd=CONNECT`
- Observed interface: `event.0.iface=wlan0`
- Connect child result: `connect.rc=0`, `connect.child_exit_code=0`, `connect.child_timed_out=0`
- Final status: `status.wlan0_present=1`, `status.carrier=1`
- Closure assertion: `event_carrier_match=1`
- Final decision: `wifi-connect-event-carrier-match`

## Cleanup Evidence

- Command: `wifi cleanup`
- Terminate result: `ctrl.terminate.rc=0`
- Cleanup result: `cleanup.run_rc=0`
- Cleanup decision: `wifi-cleanup-done`
- Post-cleanup status: `wlan0_present=1`, `carrier=0`, `supplicant.process_count=0`

## Redaction and Scope

- `raw_bssid_redacted=1`
- `raw_ip_redacted=1`
- `secret_values_logged=0`
- `connect_attempted=1`
- `dhcp_attempted=0`
- `external_ping_attempted=0`
- `cleanup_attempted=0` before cleanup, then explicit cleanup ran after the assertion.

No DHCP, route configuration, DNS installation, external ping, Wi-Fi scan request, credentials
logging, forbidden partition writes, `/dev/subsys_esoc0`, eSoC/PCIe/GDSC/PMIC/GPIO mutation, or
kernel-security trigger was performed.

## First Attempt Note

The first V2312 live attempt used an earlier build SHA and rejected the explicit `60000` timeout
argument because the generic Wi-Fi delay parser still capped values at `30000`. That attempt failed
before any connect was attempted, then `wifi cleanup` completed. The final V2312 build fixed the
parser cap specifically for `wifi connect-event` and passed the closure assertion above.

## Closure

The WLAN kernel-interface event epic is closed:

- E2 rtnetlink monitor: closed in `V2309`
- E1 nl80211 event monitor: closed in `V2310`
- Event implementation modularization: closed in `V2311`
- Credentials-gated E1 connect-event assertion: closed in `V2312`

V2312 is promoted as the current validated test baseline. `v2237` remains the known-good safety
rollback checkpoint.
