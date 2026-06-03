# Native Init V1855 SDX50M Bridge Live Delta Classifier

## Summary

- Cycle: `V1855`
- Type: host-only design-delta classifier for any future live-capable SDX50M bridge unit
- Decision: `v1855-live-delta-must-be-new-v356-bridge-not-v1221-reuse-host-pass`
- Label: `live-delta-must-be-new-v356-bridge-not-v1221-reuse`
- Result: PASS
- Reason: The next live-capable unit must be a new reviewed V1846/v356 bridge delta; V1854 stays fail-closed and the legacy V1221 v253 live path must not be reused verbatim
- Evidence: `tmp/wifi/v1855-sdx50m-bridge-live-delta-classifier`

## Current Guard

- V1854: `v1854-sdx50m-bridge-wrapper-fail-closed-ready-host-pass` / `sdx50m-bridge-wrapper-fail-closed-ready` modes `['dry-run']` live_supported `False`
- V1853: `v1853-bridge-test-image-ready-no-rebuild-host-pass` / helper `a90_android_execns_probe v356` boot_sha_ok `True` baseline `/dev/subsys_modem`

## Legacy Route

- script: `scripts/revalidation/native_wifi_private_cnss_daemon_sdx50m_live_v1221.py` exists `True`
- helper/private flag/path: `a90_android_execns_probe v253` / `--pm-observer-private-cnss-daemon-sdx50m` / `/cache/bin/cnss-daemon.sdx50m`
- legacy traits: esoc_dev_node_flag `True`, removes_subsys_esoc0_flag `True`, live_child_command `True`

## Delta Requirements

- must be new cycle: `True`
- must not modify V1854 to enable live: `True`
- must not reuse V1221 verbatim: `True`
- required helper surface: `a90_android_execns_probe v356 or later with V1847 open-context labels`
- required artifacts: `['V1220 private SDX50M cnss-daemon artifact', 'V1846/V1853 bridge-ready test image', 'V1852 dry-run field scaffold', 'V1854 fail-closed wrapper negative test']`
- required live guards: `['one-run bounded timeout', 'rollback to v724 with filtered version check and selftest fail=0', 'PM register/connect rc=0 before interpreting lower state', 'PM-service path must select /dev/subsys_esoc0; no direct host open', 'stop on no GPIO142/PCIe/MHI/WLFW/wlan0 response', 'stop on modem crash/down marker increase', 'Wi-Fi HAL/scan/connect still forbidden until WLFW service 69 and wlan0']`
- blocked legacy traits: `['helper v253 surface', 'legacy child-command patch chain', 'implicit live path inside historical V1221 script']`

## Interpretation

- V1221 remains useful as historical proof that SDX50M selection can reach PM-service eSoC powerup, not as the current live runner.
- The current candidate must be based on the V1846/v356 open-context image and V1852 field scaffold so PM selection and lower response are distinguishable.
- V1854 must remain fail-closed; live support needs a separate reviewed source/build unit and cannot be hidden behind a mode switch.
- Wi-Fi connect and ping remain blocked until WLFW service 69 and `wlan0` are observed first.

## Safety Scope

Host-only. This classifier did not issue live device commands, flash, reboot, stage properties, start actors, open `/dev/subsys_esoc0`, start `boot_wlan`, issue restart-PD request, force RC1, fake ONLINE state, write PMIC/GPIO/GDSC controls, perform eSoC notify, BOOT_DONE spoof, PCI rescan, platform bind/unbind, start Wi-Fi HAL, scan/connect, use credentials, configure DHCP/routes, or external ping.

## Next

- Do not proceed to Wi-Fi HAL/scan/connect unless WLFW service 69 and `wlan0` are present.
- Next source/build candidate: V1856 new v356 bridge delta skeleton that imports the fail-closed contract and has no live default.
