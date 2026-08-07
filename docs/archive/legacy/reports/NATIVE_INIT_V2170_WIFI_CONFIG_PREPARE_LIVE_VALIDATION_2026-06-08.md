# Native Init V2170 Wi-Fi Config Prepare Live Validation

## Summary

- Candidate tag: `v2170-wifi-config-prepare`
- Parent baseline: `v2169-transport-contract`
- Decision: `v2170-wifi-config-prepare-live-pass`
- Result: PASS
- Device under test: `DEVICE-A90-01`
- Test boot image: `workspace/private/inputs/boot_images/boot_linux_v2170_wifi_config_prepare.img`
- Test boot SHA256: `e774812a0b29b8255d374d756f851a53eccfd1eb9d1ebd304d91c0ee839ff035`
- Rollback image: `workspace/private/inputs/boot_images/boot_linux_v2169_transport_contract.img`
- Rollback SHA256: `190b93d0741a6eeba17913c940f3bb398fed765f38532d5e0009840112166d6d`
- Live artifact root: `tmp/wifi/runs/v2170-wifi-config-prepare-live-20260608-054245`

## Flash Result

- Flashed version: `A90 Linux init 0.9.248 (v2170-wifi-config-prepare)`
- Flash path: native-init to TWRP recovery, `adb push`, boot partition write, readback SHA verification, reboot to native init.
- `adb push`: 60,882,944 bytes at 82.6 MB/s.
- Boot readback SHA: matched.
- Flash total wall time: 63.865s.
- V2170 post-boot status:
  - `selftest: pass=11 warn=1 fail=0`
  - `transport.contract=1`
  - `transport.ncm=ready`

## Wi-Fi Config Prepare Test

- Scope: synthetic credential profile only.
- Not run: Wi-Fi scan, association, DHCP, route installation, external ping, boot autoconnect.
- Synthetic profile:
  - SSID source file: owner-only file under `/cache/a90-wifi/config/secrets`
  - PSK source file: owner-only file under `/cache/a90-wifi/config/secrets`
  - Raw real secret used: no
- `wifi config status` result:
  - `autoconnect_config_valid=1`
  - `profile_valid=1`
  - `profile_inline_secret_key_seen=0`
  - `secret_values_logged=0`
  - `decision=wifi-config-ready`
- `wifi config prepare synthetic` result:
  - `prepare_rc=0`
  - `supplicant_config.path=/cache/a90-wifi/wpa_supplicant.conf`
  - `supplicant_config.mode=0600`
  - `supplicant_config.owner_only=1`
  - `ctrl_interface.dir=/cache/a90-wifi/sockets`
  - `secret_values_logged=0`
  - `decision=wifi-config-supplicant-prepared`
- Generated supplicant config:
  - Owner/group/mode: `1010:1010 0600`
  - Control socket directory: `/cache/a90-wifi/sockets`
  - Control socket owner/group/mode: `1010:1010 0770`
  - `psk_vector_match=1`
  - `raw_passphrase_found=0`
  - SHA256: `c1a80f4ef65bf3bd504d5bf11d202d83c2db28381c92fcfb1e8fc8e98a7ccc15`
- V2170 selftest after prepare:
  - `selftest: pass=11 warn=1 fail=0`

## Cleanup And Rollback

- Synthetic config cleanup result: `cleanup_rc=0`.
- Final cleanup residue check after rollback:
  - `/cache/a90-wifi/config absent`
  - `/cache/a90-wifi/wpa_supplicant.conf absent`
  - `/cache/a90-wifi/wpa_supplicant.conf.tmp absent`
  - `/cache/a90-wifi/sockets absent`
- Rolled back version: `A90 Linux init 0.9.247 (v2169-transport-contract)`
- Rollback path: native-init to TWRP recovery, `adb push`, boot partition write, readback SHA verification, reboot to native init.
- `adb push`: 60,882,944 bytes at 84.7 MB/s.
- Boot readback SHA: matched.
- Rollback total wall time: 64.370s.
- Final rollback selftest:
  - `selftest: pass=11 warn=1 fail=0`
- Final bridge status:
  - `bridge_process=running`
  - `bridge_probe=connected-no-immediate-error`
  - `wrapper_contract=1`
  - `selected_realpath=/dev/ttyACM0`

## Notes

- An operator-side validation mistake briefly ran serial probes in parallel, causing `busy-serial-lock` and one malformed serial response.
- The device was recovered by sequential retries with `--hide-on-busy`.
- The final sequential checks passed: v2169 version, `selftest fail=0`, no Wi-Fi config residue, and bridge connected.

