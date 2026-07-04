# Server Distro Wi-Fi STA Upstream WSTA20 Native Service Boundary Pass

- Date: `2026-07-04`
- Decision: `wsta20-native-wifi-service-boundary-pass`
- Run evidence: `workspace/private/runs/server-distro/wsta20-native-wifi-service-boundary-20260704T004750Z/wsta20_result.json`
- Candidate: `A90 Linux init 0.11.141 (v3385-wifi-service-boundary)`
- Candidate boot SHA256: `33fabe5b90cab57c9e538236e2ad8abef28822807de4051cd8b7027053218710`
- Source/build commit: `0de9d004`

## Scope

WSTA20 proves the native-owned Wi-Fi service boundary selected after WSTA19:

- native init remains the WLAN owner;
- Debian remains a chroot consumer, not PID1 and not raw WLAN owner;
- Debian writes file requests under a shared chroot-visible directory;
- native `wifi service` processes `status` and `scan` and writes redacted response files;
- connect, DHCP, ping, association, and public tunnel work are out of scope.

## Live Result

- Checked flash: V3385 flashed through `native_init_flash.py`, readback SHA matched, and post-flash cmdv1 verification passed.
- Flash elapsed: `62.086s`.
- Baseline health after flash: `selftest pass=12 warn=1 fail=0`.
- WSTA2 materialization preflight: before `wlan0_present=0`; `wifi softap iftype-probe` completed with `wlan0_wait_elapsed_ms=102064`, `link_up_rc=0`; after `wlan0_present=1`, flags `0x1003`.
- Debian chroot SSH: marker present, Debian `12.14`, stage marker present, temporary key-only root access.
- Native service start: `wifi-service-start-pass`, poll `100ms`, lifetime `90000ms`.
- Debian status request response: `version=a90-native-wifi-service-v1`, `owner=native-init`, `wlan0_present=1`, `supplicant_process_count=0`, `dhcp_routing=0`, `public_tunnel=0`, decision `wifi-service-status-pass`.
- Debian scan request response: `owner=native-init`, `credentials=0`, `connect=0`, `dhcp_routing=0`, `public_tunnel=0`, `raw_results_redacted=1`, `scan_result_count=9`, decision `wifi-scan-pass`.
- Native service stop: `wifi-service-stop-pass`.
- Cleanup: service dir removed; chroot unmounted; loop node absent; dropbear absent on postcheck.
- Final health: V3385 still resident, `selftest pass=12 warn=1 fail=0`.

## Safety

- Boot partition was the only flashed partition, through the checked helper.
- Rollback precondition was verified: v2321, v2237, and v48 rollback images were present; v2321/v2237 SHA checks passed.
- No userdata format/populate path ran.
- No `switch_root`, DHCP, ping, public tunnel, Wi-Fi credential use, or association path ran.
- Response files intentionally carried only redacted/native-owned fields; no SSID, BSSID, PSK, or raw IP data is committed.

## Interpretation

This closes the service-boundary proof: Debian can request native-owned Wi-Fi observations without taking over the vendor WLAN control plane. Full Debian PID1 handoff remains USB-local/server-only unless we later preserve or relaunch the vendor WLAN control plane explicitly.

The next useful unit is to turn this into a small reusable Debian-side client/helper for the same file protocol, then decide whether the public tunnel should consume native-owned status/scan only or wait for a separate connect/association service rung.
