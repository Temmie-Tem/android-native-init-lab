# Native Init V3340 SoftAP S3 Lower WLAN Split Live

## Summary

- Cycle: `V3340`
- Decision: `v3340-softap-s3-lower-wlan-split-ap-iftype-still-blocked`
- Scope: live lower-gate check for the SoftAP S3 bring-up prerequisite.
- Source change: none.
- New boot artifact built: none.
- Images flashed: existing V3339 SoftAP S2 image, existing V2237 Wi-Fi-proven fallback, then rollback V2321.
- Wi-Fi mutation: no AP mode, no station connect, no DHCP, no ping, no address assignment.
- Server exposure: none.
- Secrets/network identifiers: redacted; no SSID, PSK, MAC/BSSID, client identifier, concrete network
  address, storage UUID, or raw log is recorded.

## Flash Gate

- Rollback `v2321` image SHA256 matched `ca978551aabe4b39563abaf529ccf2522054952d8b2ad852e632d26da88168cb`.
- Fallback `v2237` image SHA256 matched `b2ea2d26d160b7702ce7d4438b84367788eea26c6a5bbe4ed93f3d270292ac7f`.
- Fallback `v48` image SHA256 matched `1c87fa59712395027c5c2e489b15c4f6ddefabc3c50f78d3c235c4508a63e042`.
- TWRP recovery image SHA256 matched `b1ef377a52ec8ab43b49a5fcc7a0b27e8efff91bf2d8cccdc565ecadadcc646c`.
- V3339 SoftAP S2 image SHA256 matched `5f23c579ddbcac75cf9859685f638cad3371e2ebf228af8e441c6863fa25858b`.
- All flashes were performed only through `native_init_flash.py`.
- Remote pushed image SHA and boot readback SHA matched for each flashed image.

## V3339 Current SoftAP Lineage

Resident:

- `A90 Linux init 0.11.104 (v3339-softap-s2-status-plan)`
- Health after flash: `selftest pass=12 warn=1 fail=0`

Lower-gate checks:

- `wifi softap status` returned `decision=softap-status-blocked-wlan-gate`.
- Gates stayed `wlan=0`, `rfkill=0`, `module=0`, `candidates=1`.
- `start_supported=0`, `start_allowed=0`.
- All config/AP/server mutation fields stayed `0`.
- `wifi scan` failed at link-up with `errno=19` / no such device.
- A redacted lower probe showed `wlan0_present=0`, `wlan_like_count=0`, and `udhcpd_busybox=1`.

Decision for V3339: the current SoftAP command lineage still lacks the lower WLAN surface, so AP bring-up
must not start from this resident.

## V2237 Wi-Fi-Proven Lineage

Resident:

- `A90 Linux init 0.9.268 (v2237-supplicant-terminate-poll)`
- Initial health after flash: `selftest pass=11 warn=1 fail=0`

The V2237 helper needed its normal long window before the kernel-facing WLAN surface appeared:

- helper summary became present
- `supervisor_result=wlan0-ready`
- `helper_exit_code=0`
- `helper_timed_out=0`
- `wlan0_present=1`
- `operstate=down`

Redacted S3 lower probe after the helper completed:

- `wlan0_present=1`
- `wlan0_operstate=down`
- `iw_system=0`
- `iw_vendor=0`
- `iw_cache=0`
- `iw_wpa_standalone=0`
- `udhcpd_busybox=1`
- `wpa_standalone=1`
- `sta_supplicant_pidof=0`
- `hostapd_pidof=0`
- `dnsmasq_pidof=0`
- `udhcpd_pidof=0`

One longer combined probe exceeded the A90P1 end-marker window after printing the early WLAN fields. A
follow-up `version` and `selftest` immediately passed, so this is recorded as a bounded command framing
miss, not a device health failure.

Decision for V2237: the Wi-Fi-proven lineage can surface `wlan0`, and no station supplicant or server
worker was running. However, no `iw` binary is visible, so the required `AP iftype settable` gate remains
unproven.

## Rollback

After the split check, the device was rolled back to the clean resident baseline:

- `A90 Linux init 0.9.285 (v2321-usb-clean-identity-rodata)`
- Post-rollback `version/status` verification passed.
- Follow-up selftest: `pass=11 warn=1 fail=0`

## Decision

S3 remains blocked, but the blocker is now narrower and better defined:

- V3339 SoftAP S2 lineage: no `wlan0`, so S3 cannot start there.
- V2237 Wi-Fi-proven lineage: `wlan0` appears after the helper window, standalone `wpa_supplicant` is
  staged, and BusyBox `udhcpd` is available.
- The missing proof is AP iftype settable on the live WLAN surface. The current resident images do not
  expose an `iw` binary to run that read-only add/delete test.

## Next Unit

The next bounded unit should not start AP service yet. It should first close the AP-iftype gate by one of
these narrow paths:

- port the V2237 WLAN helper/standalone supplicant route into the current SoftAP baseline and add a tiny
  native cfg80211/nl80211 AP-iftype probe with cleanup; or
- stage a minimal `iw` equivalent in the private runtime and run only `wlan0 -> temporary __ap interface
  add/delete` before any AP address, DHCP server, listener, SSID, or PSK is created.

Only after that read-only gate passes should S3 proceed to a bounded `wpa_supplicant mode=2` SoftAP start
with cleanup and no WAN/NAT.
