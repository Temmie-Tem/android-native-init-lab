# WSTA46 WSTA45 Profile Publish Live Pass

- Date: 2026-07-04
- Scope: live WSTA45 operator publish gate
- Device action: native warm reboot only, no flash
- Public exposure: explicit quick Tunnel live gate, URL redacted
- Decision: `wsta45-appliance-operator-wsta43-profile-pass`
- Run directory: `workspace/private/runs/server-distro/wsta46-wsta45-publish-live`

## Summary

WSTA46 ran the WSTA45 operator wrapper in `publish` mode with all explicit gates:

- `--use-native-uplink-profile`
- `--allow-operator-live`
- `--allow-native-reboot`
- `--allow-public-live`
- `--ack-credentialed-wifi`
- `--ack-public-exposure`
- native confirm token
- public confirm token

WSTA45 delegated to WSTA43, which ran WSTA28 scan-green first, then WSTA42 with the
native-uplink profile path enabled.  The full chain passed:

- WSTA45: `wsta45-appliance-operator-wsta43-profile-pass`
- WSTA43: `wsta43-orchestrated-native-uplink-dpublic-pass`
- WSTA28: `wsta28-reboot-materialization-scan-gate-pass`
- WSTA27 after reboot: `wsta27-materialization-scan-gate-pass`
- WSTA42: `wsta42-native-uplink-dpublic-tunnel-pass`

## Key Evidence

WSTA28/WSTA27 precondition:

- native warm reboot accepted, no boot flash;
- post-reboot native supported build was present;
- post-reboot `selftest fail=0`;
- WSTA27 scan gate passed with `scan_result_count=12`, `scan_engine_ok=true`,
  `scan_has_bss=true`, `trigger_rc=0`, `trigger_errno=0`.

WSTA42 profile path:

- `use_native_uplink_profile=true`
- `native_uplink_profile_staged=true`
- `native_uplink_profile_confirmed=true`
- `native_uplink_profile_cleanup_ok=true`
- profile confirmed parse included:
  - `native_uplink_profile_decision=native-uplink-profile-autoconnect-pass`
  - `native_uplink_profile_public_default=off`
  - `native_uplink_profile_secret_values_logged=0`
  - native client decision `native-wifi-uplink-client-pass`
  - native service decision `wifi-uplink-service-autoconnect-pass`
  - `public_tunnel=0` at the native uplink service boundary

D-public proof:

- native default route was via `wlan0`;
- resolver was ready from host fallback with `nameserver_count=2`;
- local loopback smoke passed;
- quick Tunnel URL was observed, value not committed;
- host public smoke passed on attempt 4:
  - `http_status=200`
  - `marker_ok=true`
  - `service_ok=true`
  - `public_exposure_marker_ok=true`
  - `url_redacted=true`
  - `body_len=80`

Cleanup and final health:

- D-public cleanup clean;
- native uplink profile helper cleanup clean and removed the staged helper/enable file;
- helper cleanup clean;
- service dir cleanup clean;
- chroot cleanup clean;
- WSTA42 final native supported build remained present;
- WSTA42 final selftest check was clean.

Independent post-run device check:

- `status`: resident `v3394-wifi-wpa-failure-detail`, `selftest fail=0`;
- `selftest`: `pass=12 warn=1 fail=0`;
- `wifi status`: `operstate=down`, `ipv4=none`, `default_route_present=0`,
  `supplicant.process_count=0`, `autoconnect.decision=wifi-autoconnect-disabled`,
  `secret_values_logged=0`.

## Safety

- No boot image was built or flashed.
- No userdata operation ran.
- No raw SSID, PSK, BSSID, public URL value, gateway, DNS value, or confirm token value is committed.
- Public exposure was bounded to the explicit WSTA45/WSTA43/WSTA42 live gate and was cleaned up.

## Validation Commands

Preconditions:

```text
python3 workspace/public/src/scripts/revalidation/a90_bridge.py status --json
python3 workspace/public/src/scripts/revalidation/a90ctl.py version
python3 workspace/public/src/scripts/revalidation/a90ctl.py status
python3 workspace/public/src/scripts/revalidation/a90ctl.py selftest
```

Live gate:

```text
workspace/public/src/scripts/server-distro/run_wsta45_appliance_operator.py --mode publish ...
```

The command was invoked through Python using the in-tree confirm-token constants so token
values were not printed in the shell command.

Post-run:

```text
python3 workspace/public/src/scripts/revalidation/a90ctl.py status
python3 workspace/public/src/scripts/revalidation/a90ctl.py selftest
python3 workspace/public/src/scripts/revalidation/a90ctl.py wifi status
```

## Next

WSTA47 should productize the successful profile publish path: either tighten WSTA42/WSTA45
run metadata such as nested `ended_utc`, or add a reusable operator command alias/documented
invocation for the WSTA45 publish gate.  Persistent/always-on public exposure remains a
separate gate.
