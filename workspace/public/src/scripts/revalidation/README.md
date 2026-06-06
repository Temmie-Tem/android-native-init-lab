# Current Revalidation Entrypoints

This directory contains the current script entrypoints for native-init baseline
work. The legacy `scripts/revalidation/` tree is retained for historical scripts,
dependency modules, and compatibility wrappers.

Current migrated entrypoints:

- `build_native_init_boot_v724.py`
- `build_native_init_boot_v725_fasttransport.py`
- `build_native_init_wifi_test_boot_v2168.py`
- `build_native_init_boot_v726_wifi_lifecycle.py`
- `native_wifi_connect_dhcp_google_ping_handoff_v2167.py`

The wrappers at the old paths should keep existing commands working, but new
commands should call this workspace path directly.
