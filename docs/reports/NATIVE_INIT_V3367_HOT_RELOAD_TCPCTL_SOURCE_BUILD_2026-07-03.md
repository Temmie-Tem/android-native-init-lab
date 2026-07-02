# Native Init V3367 Hot-Reload Tcpctl Source Build

- Cycle: `V3367`
- Decision: `v3367-hot-reload-tcpctl-source-build`
- Init: `A90 Linux init 0.11.128 (v3367-hot-reload-tcpctl)`
- Boot image: `workspace/private/inputs/boot_images/boot_linux_v3367_hot_reload_tcpctl.img`
- Boot SHA256: `acc721cafc2389404c4e9ce316f55ae7371339a21a47608995dd9bfe48f4abf0`
- Helper SHA256: `fa395d3ecb6944a57487f3966948a634596157e4de3fdc39575a2fc502d1ceef`
- Base boot: `workspace/private/inputs/boot_images/boot_linux_v3335_gpu_z3_primary_setcrtc.img`

## Change

- H4 cleanup candidate after V3366 H3: keep the reload command and V3366 clean-storage proof surface, but refresh tcpctl after PID1 hot-reload.
- The hot-reload path still skips autohud and rshell re-init, then calls `a90_netservice_start()` to refresh tcpctl on the already-live NCM interface.
- `a90_netservice_start()` avoids USB gadget reconfiguration when NCM already exists; tcpctl adopts an existing listener from `/proc/*/cmdline` or starts a new listener if none is live.
- H3 storage adoption markers remain required so the V3366 fix is not regressed.

## Validation Contract

- Static PASS requires the V3367 version strings, reload markers, retained storage adoption markers, and tcpctl refresh/adoption markers (`tcpctl-adopt`, `Hot-reload: tcpctl ready`, `refreshing tcpctl on existing NCM`).
- Live H4 PASS, separately gated, requires: staged V3367 init SHA matches; `reload` returns through the new V3367 shell; `status` reports `BOOT OK`, `storage backend=sd`, runtime SD root, `tcpctl=running`, `transport.tcpctl=ready`, and `selftest fail=0`; host tcpctl `ping` works; then rollback to v2321 and health-check clean.
- No live H4 reload result is claimed by this source-build report.

## Metadata

- Helper flags: `-DA90_WIFI_TEST_BOOT_SERVICE_OBJECT_POST_FW_READY_FWCLASS_BRIDGE=1`
- Init extra flags: ``
- Candidate type: `hot-reload-tcpctl`.
