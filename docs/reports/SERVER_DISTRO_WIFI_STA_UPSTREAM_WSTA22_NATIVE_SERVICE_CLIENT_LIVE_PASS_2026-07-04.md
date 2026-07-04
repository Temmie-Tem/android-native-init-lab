# Server Distro Wi-Fi STA Upstream WSTA22 Native Service Client Live Pass

- Date: `2026-07-04`
- Decision: `wsta22-native-wifi-service-client-pass`
- Run evidence: `workspace/private/runs/server-distro/wsta22-native-wifi-service-client-20260704T011641Z/wsta22_result.json`
- Resident: `A90 Linux init 0.11.141 (v3385-wifi-service-boundary)`
- Boot flash: `none` during the passing run

## Scope

WSTA22 proves the WSTA21 Debian helper against the WSTA20 native-owned Wi-Fi service:

- native init owns Wi-Fi and runs `wifi service`;
- Debian runs as an SD-backed chroot consumer over USB/NCM SSH;
- the helper is temporarily staged into Debian, requests `status` and `scan`, then is removed/restored;
- no association, DHCP, ping, public tunnel, userdata, or `switch_root` action runs.

## Live Result

- Resident health before gate: V3385, `selftest fail=0`.
- Native pre-service scan: `wifi-scan-pass`, `scan_result_count=8`.
- SD image remote SHA was restored from a prior mutated image back to the expected clean image SHA.
- Debian chroot SSH marker: present, Debian `12.14`, stage marker present.
- Helper staging: `A90WSTA22_HELPER_STAGED`.
- Native service start: `wifi-service-start-pass`.
- Helper status: return code `0`, decision `native-wifi-service-client-pass`, native decision `wifi-service-status-pass`, `owner=native-init`, `wlan0_present=1`, `dhcp_routing=0`, `public_tunnel=0`.
- Helper scan: return code `0`, decision `native-wifi-service-client-pass`, native decision `wifi-scan-pass`, `scan_result_count=9`, `raw_results_redacted=1`, `credentials=0`, `connect=0`.
- Helper cleanup: `A90WSTA22_HELPER_REMOVED` and `A90WSTA22_HELPER_CLEANED`.
- Native service stop: `wifi-service-stop-pass`.
- Chroot cleanup/postcheck: mount absent, loop node absent, dropbear absent.
- Final health: V3385, `selftest fail=0`.

## Stale WLAN Finding

Two earlier WSTA22 attempts exposed a stale WLAN state:

- `wifi scan` failed with `trigger_errno=22`;
- forced `wifi softap iftype-probe` also failed with `ap_iftype_add_errno=22`;
- a fresh native reboot followed by WSTA2 materialization restored scan behavior.

The runner now records this explicitly: scan precheck runs before chroot/service work, and it can perform one bounded native reboot recovery if the same stale scan state appears.

## Safety

- No boot flash ran in the passing WSTA22 run.
- No Wi-Fi credentials were consumed or logged.
- No association, DHCP, ping, public tunnel, API exposure, userdata write, or `switch_root` ran.
- The helper output remained redacted and allowlisted; SSID, PSK, BSSID, MAC, DHCP lease, and concrete address fields are not committed.
- The temporary Debian helper staging is cleaned up before unmount.

## Next

The native-owned status/scan service boundary is now usable from Debian.  The next separate design choice is whether to:

1. keep D-public over Wi-Fi limited to native-owned status/scan observability for now; or
2. add a new gated native-owned connect/association/DHCP service rung with credential and public-exposure gates.
