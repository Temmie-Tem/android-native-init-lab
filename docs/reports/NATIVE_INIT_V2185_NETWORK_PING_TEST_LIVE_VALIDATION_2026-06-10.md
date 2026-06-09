# Native Init V2185 Network Ping Test Live Validation

## Summary

- Candidate tag: `v2185-network-ping-test`.
- Device-visible init: `A90 Linux init 0.9.257 (v2185-network-ping-test)`.
- Type: live flash plus Wi-Fi ping primitive validation.
- Decision: `v2185-network-ping-test-live-pass`.
- Result: PASS.
- Reason: V2185 flashed, booted, connected through the private default Wi-Fi
  profile, acquired DHCP, and `wifi ping all` passed gateway plus fixed external
  IP checks.
- Evidence directory:
  `workspace/private/runs/wifi/v2185-network-ping-live-20260610-075819`.
- Boot image:
  `workspace/private/inputs/boot_images/boot_linux_v2185_network_ping_test.img`.
- Boot SHA256:
  `3ab13707c4ad93cb0b23c26174407be9a0ca30460fce879131ba6bea0df253b7`.

## Live Results

- Flash/readback: boot partition prefix SHA matched local image.
- Boot verify: `version` and `status` passed, initial selftest `fail=0`.
- Initial Wi-Fi state: `wlan0` was absent immediately after boot; later appeared
  before manual connect.
- Connect: `wifi connect` reached `wifi-connect-carrier-up`.
- DHCP: `wifi dhcp` reached `wifi-dhcp-pass`.
- Status after DHCP: `wlan0` was `up`, carrier was `1`, IPv4 was assigned.
- Ping: `wifi ping all` reached `wifi-ping-pass`.
- Menu smoke: `screenmenu` accepted the request after adding
  `NETWORK > PING TEST`.
- Final selftest: `fail=0`.

Ping details:

| Target | Result | Packets | Loss | Average RTT |
| --- | --- | --- | --- | --- |
| Gateway | pass | `3/3` | `0%` | `1.814ms` |
| Internet fixed IP | pass | `3/3` | `0%` | `13.814ms` |

## Safety Scope

- Gateway address, private IP, SSID, BSSID, MAC-derived peer details, and
  credentials are omitted from this public report.
- `wifi ping all` was explicit user/test scope; status/HUD/profile/scan paths do
  not auto-run ping.
- No Wi-Fi credential readback, scan/connect beyond the private default profile,
  unbounded ping, DHCP beyond the bounded test, external route mutation beyond
  the existing DHCP route, or file transfer was run in this cycle.
- No PMIC/GPIO/GDSC/regulator writes, eSoC notify/BOOT_DONE, PCI rescan,
  platform bind/unbind, or `/dev/subsys_esoc0` path was used.

## Notes

- A first `wifi autoconnect once` attempt was affected by serial/protocol noise
  and was not used as the validation gate.
- The deterministic validation path was separated into `wifi connect`,
  `wifi dhcp`, and `wifi ping all`.
- The device remains on V2185 test boot after this validation unless explicitly
  rolled back or promoted.
