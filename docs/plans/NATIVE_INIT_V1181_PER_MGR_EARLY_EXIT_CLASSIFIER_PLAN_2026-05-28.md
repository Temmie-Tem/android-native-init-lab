# Native Init V1181 per_mgr Early-Exit Classifier Plan

Date: `2026-05-28`

## Goal

Host-only classification of why per_mgr (`/vendor/bin/pm-service`) exits with
`exit_code=0` in V1179/V1180 (`post-pm-mdm-helper-esoc-observer` mode) while
surviving in V1105 (`pm-service-trigger-observer` mode), despite all three runs
using the same V535 property root and the same V535 `properties_serial` hash.

## Evidence Sources

- `tmp/wifi/v1180-pm-dep-early-per-proxy-zero-delay-per-mgr/host/pm-server-wchan-tracefs-observer.txt`
- `tmp/wifi/v1179-pm-dep-early-per-proxy-observer/host/pm-server-wchan-tracefs-observer.txt`
- `tmp/wifi/v1105-pm-server-raw-mutex-tracefs-live/host/pm-server-raw-mutex-tracefs-observer.txt`
- `stage3/linux_init/helpers/a90_android_execns_probe.c` (current source, post-v219)

## Classification Results

### 1. Property root is NOT the differentiating factor

All three runs use `/mnt/sdext/a90/private-property-v317/v535/dev/__properties__`
(V535 property root). The `properties_serial` sha256 is identical across V535,
V677, and V860. Property values are therefore identical in all three runs.
The initial hypothesis of a property root difference is closed.

### 2. Helper version difference introduced `/dev/subsys_modem` node

V1105 used old helper SHA `7920eeb`. V1179/V1180 used helper v218/v219.

The old helper lacked `materialize_peripheral_manager_node_parity()`, a function
present in v218/v219 that creates `/dev/subsys_modem`, `/dev/subsys_esoc0`, and
`/dev/esoc-0` in the private mount namespace before child processes start.

Evidence:
- V1105 `pm_proxy_helper` (pid=4667): `subsys_modem_count=0` at all probes
  (after_per_proxy, after_cnss_daemon). Killed by SIGTERM at cleanup.
- V1180 `pm_proxy_helper` (pid=2739): `fd=3 → /tmp/a90-v231-1070/root/dev/subsys_modem`
  at `after_per_proxy` snapshot (monotonic 321290ms). Node materialized in private dev.
- Neither V1105 nor V1180 output `wifi_companion_start.private_node.*` status lines
  between `exec_attempted=1` and first child start — the append_private_android_node_status
  calls at current source line 28009 post-date v219 compilation.

### 3. pm_proxy_helper opens `/dev/subsys_modem` when the node exists

`pm_proxy_helper` (`/vendor/bin/pm_proxy_helper`) is a oneshot binary whose purpose
is to open and hold the modem subsystem device, keeping mss powered during the
pm-proxy initialization window. When the node is absent (V1105), pm_proxy_helper
remains idle until killed by SIGTERM. When the node is present (V1179/V1180),
pm_proxy_helper opens it successfully within ~250ms of pph_spawn.

The opening of `/dev/subsys_modem` is itself harmless — mss powerup completes
without blocking (unlike esoc0 which blocks in `mdm_subsys_powerup`).

### 4. The modem registration race: per_proxy vs per_mgr initialization

**V1105 (success path):**
- per_proxy start: per_mgr + 1000ms probe (default, no `--pm-observer-per-proxy-pph-delta-ms`)
- per_mgr ran for ≥1000ms before per_proxy started
- per_mgr fully initialized: registered with vndservicemanager
  (`vendor_qcom_peripheral_manager_seen=1`), peripheral list populated (SDX50M + modem)
- V1105 tracefs (7132.530s): `pm-proxy-4675` sent `pm_client_register("modem")`,
  per_mgr matched modem entry, `pm_server_register_ret=0x0`, `pm_client_register_ret=0x0`
  → success

**V1179/V1180 (failure path):**
- V1180: `--pm-observer-per-proxy-pph-delta-ms 300` + `--pm-observer-zero-delay-per-mgr-probe`
  → per_proxy starts at pph+300ms; per_mgr probed at 0ms (observable=1, but NOT
  vndservice-registered)
- V1180 tracefs (321.216s): `pm-proxy-3036` sent `pm_client_register("modem")` at
  pph+~257ms; per_mgr received the Binder call but `pm_server_register_entry` never
  fired in tracefs → per_mgr's internal peripheral list was not yet populated
- `pm_client_register_ret.count=0` (call never returned), per_mgr exited 0
- V1179: `--pm-observer-per-proxy-pph-delta-ms 800` + 1000ms per_mgr probe →
  per_mgr dead at 1000ms probe (`post_start_observable=0`);
  `elapsed_since_pph_ms=1244` at per_proxy loop (already_elapsed, starts immediately)
  → per_mgr died even earlier, before the 1000ms probe, consistent with pm-proxy
  spawned by pm_proxy_helper registering "modem" before per_mgr was ready

**Per_mgr initialization time requirement:** per_mgr needs approximately ≥1000ms to
read its configuration, build the internal peripheral list (SDX50M, modem, etc.),
and register with vndservicemanager before it can safely handle `pm_client_register`
Binder calls. Delivering a modem registration before this completes causes per_mgr
to encounter an uninitialized list entry → assertion or null dereference → exit 0.

### 5. Per_proxy timing is the root trigger

The `--pm-observer-per-proxy-pph-delta-ms` flag (introduced in v218 to replicate
Android's ~2159ms pm_proxy_helper→per_proxy delta) sets per_proxy start relative to
pm_proxy_helper spawn (`pph`), not relative to per_mgr readiness. Since per_mgr
starts slightly after pm_proxy_helper (order 5 vs 4), per_proxy at pph+300ms or
pph+800ms means per_mgr has had only ~250ms–750ms to initialize — not enough.

The pph_delta approach is fundamentally decoupled from per_mgr readiness. The
Android reference delta of 2159ms was observed on a fully running Android system
where per_mgr had already been online for a long time — it is not a safe
initialization-time proxy.

## Root Cause Summary

| Factor | V1105 | V1179 | V1180 |
|--------|-------|-------|-------|
| Helper version | old (no subsys_modem node) | v218 (node materialized) | v219 (node materialized) |
| pm_proxy_helper subsys_modem | count=0 (idle) | count=1 | count=1 |
| per_proxy start timing | per_mgr+1000ms | pph+800ms (already_elapsed, ~1244ms) | pph+300ms |
| per_mgr init time before per_proxy modem reg | ≥1000ms | <1000ms | ~247ms |
| vendor_qcom_peripheral_manager_seen | 1 (full init) | 0 (dead) | 0 (not ready) |
| pm_client_register("modem") result | ret=0 (success) | no ret (per_mgr dead) | no ret (per_mgr dead) |

## Rejected Hypotheses

- Property root difference: all three runs use V535, same properties_serial hash → closed
- Mode string difference: mode string changes logging/flags but not property root or node materialization logic path for this variable
- SELinux context difference: all three use `--android-selinux-context-mode service-defaults`

## Next Step: V1182

Host-only design of a **per_mgr-ready gate** for per_proxy start.

Per_proxy must not start until per_mgr has registered with vndservicemanager
(`vendor_qcom_peripheral_manager_seen=1`). The current pph_delta approach is a
timing proxy that is not safe for initialization ordering.

V1182 should design a helper change (source/build-only) that:
1. After spawning per_mgr (with or without zero-delay probe), polls the vndservice
   list at short intervals (e.g. 50ms) until `vendor.qcom.PeripheralManager` is
   visible, with a bounded timeout (e.g. 5s)
2. Only after vndservice readiness is confirmed, spawns per_proxy
3. Preserves the existing pph_delta log for diagnostic purposes but uses the
   vndservice gate as the actual spawn trigger
4. Adds a new flag (e.g. `--pm-observer-per-proxy-after-vndservice-provider`) to
   enable the gated mode vs the existing pph_delta timing mode

This is analogous to how V1105 waited for `per_mgr+1000ms` and then checked
vndservice readiness — but made explicit and not dependent on a fixed time delay.

Wi-Fi HAL, scan/connect, credentials, DHCP/routes, external ping remain blocked.
No device live action in V1181 or V1182 (source/build-only).
