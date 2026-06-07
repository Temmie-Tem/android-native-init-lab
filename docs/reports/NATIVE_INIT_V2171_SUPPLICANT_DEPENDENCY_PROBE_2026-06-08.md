# Native Init V2171 Supplicant Dependency Probe

Date: `2026-06-08`

## Header

- Run ID: `V2171`
- Native init under probe: `A90 Linux init 0.9.246 (v726-wifi-lifecycle)`
- Probe boot image: `workspace/private/inputs/boot_images/boot_linux_v726_wifi_lifecycle.img`
- Probe boot SHA256: `6b34aac93d4fa6d5b40355b9e13b2c1ae847c24a3685d84b0d1cd78751351d40`
- Rollback baseline after probe: `A90 Linux init 0.9.247 (v2169-transport-contract)`
- Rollback boot image: `workspace/private/inputs/boot_images/boot_linux_v2169_transport_contract.img`
- Rollback boot SHA256: `190b93d0741a6eeba17913c940f3bb398fed765f38532d5e0009840112166d6d`
- Helper: `a90_android_execns_probe helper-v427` already staged on device
- Device flash: yes, `v2169-transport-contract` -> `v726-wifi-lifecycle` -> `v2169-transport-contract`
- Host commit: uncommitted

## Decision

`supplicant-dependency-standalone-only-ctrl-ready`

Native `wifi connect` should keep the staged standalone `wpa_supplicant` route.
The current native namespace does not expose a usable vendor supplicant binary.

## Evidence

- Probe runner: `workspace/public/src/scripts/revalidation/native_wifi_supplicant_dependency_probe.py`
- Control helper: `workspace/public/src/native-init/helpers/a90_wpa_ctrl_request.c`
- Final evidence: `tmp/wifi/runs/native-wifi-supplicant-dependency-probe-no-connect-v726-wlan0-final-20260608-064510/manifest.json`
- Initial blocked evidence: `tmp/wifi/runs/native-wifi-supplicant-dependency-probe-no-connect-precondition-20260608-063534/manifest.json`
- Transport: `ncm`
- Final selftest after rollback: `pass=11 warn=1 fail=0`

## Results

| Candidate | Path | Context | Present | Executable | PING | Cleanup |
| --- | --- | --- | --- | --- | --- | --- |
| `standalone_native` | `/cache/a90-wifi/wpa-standalone/wpa_supplicant-a90.sh` | native direct | yes | yes | pass | no live process |
| `standalone_halctx` | `/cache/a90-wifi/wpa-standalone/wpa_supplicant-a90.sh` | `u:r:hal_wifi_supplicant_default:s0` | yes | yes | pass | no live process |
| `vendor_hw_native` | `/vendor/bin/hw/wpa_supplicant` | native direct | no | no | not run | clean |
| `vendor_hw_halctx` | `/vendor/bin/hw/wpa_supplicant` | `u:r:hal_wifi_supplicant_default:s0` | no | no | not run | clean |
| `vendor_native` | `/vendor/bin/wpa_supplicant` | native direct | no | no | not run | clean |
| `vendor_halctx` | `/vendor/bin/wpa_supplicant` | `u:r:hal_wifi_supplicant_default:s0` | no | no | not run | clean |

The standalone candidates reported `log_fail=0`, `log_permission=0`, and
`log_avc=0`.

## Interpretation

- Vendor-supplicant optimization is not available on the current native route:
  both common vendor paths are absent in the probed namespace.
- SELinux exec-context switching is not required for no-connect `nl80211`
  control readiness: native direct and `hal_wifi_supplicant_default` both pass.
- The practical minimal baseline dependency is the staged standalone wrapper plus
  its bundle under `/cache/a90-wifi/wpa-standalone/`.
- This probe is a credential-free control-readiness discriminator, not a full
  association/DHCP/ping proof. Existing V2167 evidence remains the connect proof
  for the standalone route.

## Safety

- No SSID/PSK was used.
- No DHCP, route, DNS, or external ping was run by the dependency probe.
- Probe scratch `/cache/a90-wifi/supplicant-dependency-probe/` was removed.
- Post-probe process check reported `real_wpa_processes=0`.
- Device was rolled back to `v2169-transport-contract` and selftest reported
  `fail=0`.
