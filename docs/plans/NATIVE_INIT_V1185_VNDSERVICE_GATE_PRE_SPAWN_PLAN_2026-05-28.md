# V1185 PM Per-Proxy Pre-Spawn Vndservice Gate — Plan

- **cycle**: V1185
- **date**: 2026-05-28
- **type**: source/build-only PASS + deploy + live
- **prior**: V1184 host-only classifier — gate position and parse bugs identified

## Objective

Fix the V1183 gate position bug: move the vndservice gate BEFORE
`composite_spawn_child(per_proxy)` so per_proxy is only spawned after per_mgr
has published `vendor.qcom.PeripheralManager`.

## C Source Change (helper v221)

File: `stage3/linux_init/helpers/a90_android_execns_probe.c`

### Change 1 — Version bump

```c
#define EXECNS_VERSION "a90_android_execns_probe v221"
```

### Change 2 — Pre-spawn gate block (new, before composite_spawn_child)

Added a new block at the top of the spawning loop body, immediately before
`composite_spawn_child(&children[i])`, guarded by
`i == PM_OBSERVER_PER_PROXY && cfg->pm_observer_per_proxy_after_vndservice_provider`.

On timeout: marks child as skipped (`start_skipped=1`, `skip_reason=vndservice-gate-timeout`),
increments `active_child_count`, and `continue`s to CNSS_DAEMON.  
On gate open: falls through to `composite_spawn_child`.

### Change 3 — Post-spawn gate block (replaced with marker)

The old post-spawn polling loop (V1183 log-only gate) is replaced with a single
`post_spawn_check=pre_spawn_gate_ran` marker line so downstream analysis can
confirm per_proxy reached the post-spawn section only after the gate opened.

## Build Result (source/build-only PASS)

```
artifact: stage3/linux_init/helpers/a90_android_execns_probe
sha256: 120fad47dad2965ab8a541759bf1cd04396b9f81eb0c06986096e6f05dfdf05d
marker: a90_android_execns_probe v221
static aarch64, no dynamic section
```

## V1185 Python Script

New file: `scripts/revalidation/native_wifi_pm_per_proxy_vndservice_gate_v1185.py`

Wraps V1183 script with:
- Updated `DEFAULT_EXECNS_HELPER_SHA256` for v221
- Updated `DEFAULT_EXECNS_HELPER_MARKER = "a90_android_execns_probe v221"`
- Updated output dir: `tmp/wifi/v1185-pm-per-proxy-vndservice-gate-pre-spawn`

Decision outcomes:
- `v1185-vndservice-gate-not-activated`: `gate.begin != "1"` (flag absent or wrong version)
- `v1185-vndservice-gate-timeout`: gate ran but per_mgr did not register within 5s
  - Indicates per_mgr dies even without per_proxy race (SELinux or other issue)
- `v1185-vndservice-gate-ready`: gate opened, per_proxy spawned after per_mgr registered
  - Success path: check pm_server_register_ret for modem registration

## Expected Outcomes

**If V1181 hypothesis is correct** (race was the only blocker):
- Gate polls and sees `vendor.qcom.PeripheralManager` within ~1000ms
- Per_proxy spawns safely, `pm_client_register` returns success
- `pm_server_register_entry.count >= 1`, `per_mgr_vndbinder_count >= 1`
- Decision: `v1185-vndservice-gate-ready`

**If per_mgr has additional blocker** (SELinux domain, missing socket, etc.):
- Per_mgr dies without opening vndbinder (same as V1183)
- Gate times out after 5s
- Per_proxy skipped (`start_skipped=1`)
- Decision: `v1185-vndservice-gate-timeout`
- Next: capture per_mgr running domain (SELinux) and exit path

## Safety

- No Wi-Fi HAL, scan/connect, credentials, DHCP/routes, external ping
- No writes to /efs, /sec_efs, modem partitions, RPMB
- Requires `--allow-daemon-start --assume-yes` for CNSS daemon start
- cnss-daemon start follows same V1183 gate (only after per_mgr/per_proxy healthy)
