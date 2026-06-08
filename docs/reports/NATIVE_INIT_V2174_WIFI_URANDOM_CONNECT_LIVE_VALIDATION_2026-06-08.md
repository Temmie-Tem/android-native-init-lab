# Native Init V2174 Wi-Fi Urandom Connect Live Validation

## Summary

- Decision: `v2174-connect-carrier-up-rollback-pass`
- Pass: `True`
- Reason: native-init wifi connect reached carrier and rollback selftest fail=0
- Run dir: `workspace/private/runs/wifi/v2174-wifi-urandom-connect-carrier-20260608-201332`
- Bridge ready for cmdv1: `True`
- Bridge probe: `connected-no-immediate-error`
- Serial candidates: `1`
- Wi-Fi env valid: `True`
- Test image: `workspace/private/inputs/boot_images/boot_linux_v2174_wifi_urandom_connect.img`
- Test SHA256: `cda957e4302d66e407fc97a95932501f0ef2ac655ee264c94519111fece0b3ba`
- Rollback image: `workspace/private/inputs/boot_images/boot_linux_v2169_transport_contract.img`
- Rollback SHA256: `190b93d0741a6eeba17913c940f3bb398fed765f38532d5e0009840112166d6d`

## Connect Scope

- Command: `wifi connect [profile]`
- Scope: association/carrier only.
- Explicitly excluded: DHCP, route installation, DNS, external ping, boot autoconnect, raw credential logging.
- Connect decision: `wifi-connect-carrier-up`
- Carrier up: `1`
- Secret values logged: `0`
- DHCP/routing field: `0`
- External ping field: `0`
- WPA state: `COMPLETED`
- Key management: `WPA2-PSK`
- Associated frequency: `5745`
- Supplicant log collected: `True`
- Supplicant log redacted file: `logs/device/wpa_supplicant-connect-redacted.log`

## Root Cause

- Prior no-carrier runs reached association but failed in the 4-way handshake because `wpa_supplicant` could not open `/dev/urandom` and could not generate SNonce.
- The native `/dev` bootstrap now creates `/dev/random` and `/dev/urandom` char nodes before Wi-Fi userspace starts.
- This run reached `wpa_state=COMPLETED` and `carrier=1`, confirming the random-device gap was the immediate connect blocker.

## Rollback

- Rollback OK: `True`
- Rollback attempt: `from-native`
- Rollback selftest fail=0: `True`

## Notes

- This report contains only redacted high-level fields. Full stdout/stderr evidence is private under the run dir.
- If the decision is preflight-blocked, no test flash was attempted.
