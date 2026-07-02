# Native Init V3368 Hot-Reload Autohud Source Build

- Cycle: `V3368`
- Decision: `v3368-hot-reload-autohud-source-build`
- Init: `A90 Linux init 0.11.129 (v3368-hot-reload-autohud)`
- Boot image: `workspace/private/inputs/boot_images/boot_linux_v3368_hot_reload_autohud.img`
- Boot SHA256: `c8bd3eab12eaa17502ac187053353c50e1a0a35d86492b15932d66969f56948c`
- Helper SHA256: `fa395d3ecb6944a57487f3966948a634596157e4de3fdc39575a2fc502d1ceef`
- Base boot: `workspace/private/inputs/boot_images/boot_linux_v3335_gpu_z3_primary_setcrtc.img`

## Change

- H5 candidate after V3367 H4: keep the reload command, storage adoption, and tcpctl refresh, but make the display side a DRM-master handoff.
- `reload` no longer stops the existing autohud child. The reload path also preserves `/tmp` and skips boot splash KMS presents, so the old HUD process keeps its existing DRM fd/master/fb state.
- The reloaded PID1 calls `auto_hud_adopt_pidfile()` and records `hotreload-autohud` instead of running a new modeset or SETCRTC retry.
- After tcpctl refresh, rshell is started when its opt-in flag is enabled.
- Bright line retained: no panel re-init, no backlight/PMIC/regulator/GDSC/GPIO writes, no reload SETCRTC retry.

## Validation Contract

- Static PASS requires the V3368 version strings, reload markers, retained storage/tcpctl markers, and H5 markers (`reload: preserving autohud`, `Hot-reload: autohud adopted`, `hotreload-autohud`, `Hot-reload: rshell ready`, `hotreload-rshell`).
- Live H5 PASS, separately gated, requires: staged V3368 init SHA matches; `reload` returns through the new V3368 shell; `status` reports `BOOT OK`, `storage backend=sd`, runtime SD root, `autohud=running`, `tcpctl=running`, `transport.tcpctl=ready`, `rshell=running` when enabled, and `selftest fail=0`; host tcpctl `ping` works; operator confirms HUD remains visible; then rollback to v2321 and health-check clean.
- If autohud cannot be adopted without a SETCRTC/panel re-init, H5 clean-closes the hot-reload epic at H4 by design.
- No live H5 reload result is claimed by this source-build report.

## Metadata

- Helper flags: `-DA90_WIFI_TEST_BOOT_SERVICE_OBJECT_POST_FW_READY_FWCLASS_BRIDGE=1`
- Init extra flags: ``
- Candidate type: `hot-reload-autohud`.
