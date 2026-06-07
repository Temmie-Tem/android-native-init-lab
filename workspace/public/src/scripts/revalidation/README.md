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
- `native_wifi_connect_dhcp_google_ping_handoff_v2167.py`
- `native_wifi_supplicant_dependency_probe.py`
- `a90_v725_fasttransport_baseline_validation.py`
- cleanup and inventory utilities in this directory

New commands should call this workspace path directly.

Bridge management:

```bash
python3 workspace/public/src/scripts/revalidation/a90_bridge.py ensure --device /dev/ttyACM0
python3 workspace/public/src/scripts/revalidation/a90_bridge.py doctor
sudo python3 workspace/public/src/scripts/revalidation/a90_bridge.py repair-dirs --user "$USER"
```

`repair-dirs` is limited to bridge private state under
`workspace/private/logs/bridge/` and `workspace/private/run/`.
