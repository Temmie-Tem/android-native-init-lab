# Current Revalidation Entrypoints

This directory contains the current script entrypoints for native-init baseline
work. Historical scripts and compatibility symlinks live under
`workspace/public/archive/scripts/revalidation/`.

Current migrated entrypoints:

- `a90ctl.py`
- `a90_bridge.py`
- `a90_transport.py`
- `serial_tcp_bridge.py`
- `a90_ncm_transport.py`
- `a90_ncm_transport_smoke.py`
- `a90_ncm_host_preflight.py`
- `ncm_host_setup.py`
- `native_init_flash.py`
- `build_native_init_boot_v724.py`
- `build_native_init_boot_v725_fasttransport.py`
- `build_native_init_wifi_test_boot_v2168.py`
- `build_native_init_boot_v726_wifi_lifecycle.py`
- `build_native_init_boot_v2169_transport_contract.py`
- `build_native_init_boot_v2170_wifi_config_prepare.py`
- `build_native_init_boot_v2172_wifi_status_scan.py`
- `build_native_init_boot_v2174_wifi_urandom_connect.py`
- `build_native_init_boot_v2176_wifi_dhcp.py`
- `build_native_init_boot_v2178_wifi_profile_autoconnect.py`
- `a90_wifi_profile_stage.py`
- `native_wifi_connect_carrier_handoff_v2174.py`
- `native_wifi_dhcp_ping_handoff_v2176.py`
- `native_wifi_hold_reconnect_handoff_v2177.py`
- `native_wifi_v2178_autoconnect_phase_validation.py`
- `native_wifi_supplicant_dependency_probe.py`
- `a90_v725_fasttransport_baseline_validation.py`
- `inventory_revalidation_scripts.py`
- cleanup and inventory utilities in this directory

New commands should call this workspace path directly.

Archived/superseded entrypoints:

- `workspace/public/archive/scripts/revalidation/native_wifi_connect_dhcp_google_ping_handoff_v2167.py`

Bridge management:

```bash
python3 workspace/public/src/scripts/revalidation/a90_bridge.py ensure --device /dev/ttyACM0
python3 workspace/public/src/scripts/revalidation/a90_bridge.py doctor
sudo python3 workspace/public/src/scripts/revalidation/a90_bridge.py repair-dirs --user "$USER"
```

`repair-dirs` is limited to bridge private state under
`workspace/private/logs/bridge/` and `workspace/private/run/`.
