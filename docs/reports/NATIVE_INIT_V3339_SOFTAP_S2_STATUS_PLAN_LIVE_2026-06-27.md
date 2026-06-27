# Native Init V3339 SoftAP S2 Status/Plan Live Validation

## Summary

- Cycle: `V3339`
- Decision: `v3339-softap-s2-status-plan-live-pass`
- Scope: flash/live validation of the S2 status/plan/prepare surface only.
- Artifact flashed: `workspace/private/inputs/boot_images/boot_linux_v3339_softap_s2_status_plan.img`
- Boot SHA256: `5f23c579ddbcac75cf9859685f638cad3371e2ebf228af8e441c6863fa25858b`
- Resident after flash: `A90 Linux init 0.11.104 (v3339-softap-s2-status-plan)`
- Wi-Fi mutation: none.
- Server exposure: none.
- Secrets/network identifiers: redacted; no SSID, PSK, MAC/BSSID, client identifier, concrete network
  address, storage UUID, or raw log is recorded.

## Flash Gate

- Rollback `v2321` image SHA256 matched `ca978551aabe4b39563abaf529ccf2522054952d8b2ad852e632d26da88168cb`.
- Fallback `v2237` image SHA256 matched `b2ea2d26d160b7702ce7d4438b84367788eea26c6a5bbe4ed93f3d270292ac7f`.
- Fallback `v48` image SHA256 matched `1c87fa59712395027c5c2e489b15c4f6ddefabc3c50f78d3c235c4508a63e042`.
- TWRP recovery image SHA256 matched `b1ef377a52ec8ab43b49a5fcc7a0b27e8efff91bf2d8cccdc565ecadadcc646c`.
- Pre-flash resident was V3335 with selftest `pass=12 warn=1 fail=0`.
- Flash was performed only through `native_init_flash.py`.
- Remote pushed image SHA and boot readback SHA both matched the V3339 artifact.
- Native-init post-flash verify passed with `version/status rc=0`.
- Post-flash selftest stayed `pass=12 warn=1 fail=0`.

## Live Commands

The first post-flash direct `a90ctl selftest` attempt missed the A90P1 end marker due to serial input
encoding noise after re-enumeration. Retrying with `--input-mode slow` resynchronized the console; this
was a host/bridge input-mode issue, not a device health failure. All validation commands below used
slow mode.

The auto HUD/menu gate initially returned busy for `wifi softap status`. `stophud` returned rc `0`, and
the SoftAP commands were then run again.

### `wifi softap status`

- rc: `0`
- decision: `softap-status-blocked-wlan-gate`
- `wififeas.decision=no-go`
- gates: `wlan=0`, `rfkill=0`, `module=0`, `candidates=1`
- inventory: `net_total=9`, `wlan_like=0`, `rfkill_wifi=0`, `module_matches=0`, `file_matches=16`
- `busybox.executable=1`
- `ssid_psk_logged=0`
- `config_write_attempted=0`
- `hostapd_start_attempted=0`
- `dhcp_server_start_attempted=0`
- `listener_start_attempted=0`
- `interface_mode_change_attempted=0`
- `address_assign_attempted=0`
- `server_exposure_attempted=0`
- `start_supported=0`
- `start_allowed=0`

### `wifi softap plan`

- rc: `0`
- decision: `softap-status-blocked-wlan-gate`
- includes `plan.s0=charter-done`
- includes `plan.s1=readonly-inventory-done`
- includes `plan.s2=status-plan-prepare-no-start`
- includes `plan.s3=blocked-until-wlan-ap-prereq-visible`
- includes `plan.s4=blocked-until-ap-and-server-start-pass`
- all config/AP/server mutation fields stayed `0`

### `wifi softap prepare`

- rc: `0`
- decision: `softap-prepare-blocked-wlan-gate`
- `prepare_dry_run=1`
- `start_supported=0`
- `start_allowed=0`
- all config/AP/server mutation fields stayed `0`

## Health

- Follow-up selftest stayed `pass=12 warn=1 fail=0`.

## Decision

V3339 closes S2: the status/plan/prepare command surface is present on-device and reports the current
SoftAP blocker without starting AP mode or exposing a server.

S3 remains blocked by the lower WLAN/AP gate. Do not start hostapd, assign an AP address, run a DHCP
server, or expose a transfer listener until a future read-only unit proves the WLAN/AP prerequisites.
