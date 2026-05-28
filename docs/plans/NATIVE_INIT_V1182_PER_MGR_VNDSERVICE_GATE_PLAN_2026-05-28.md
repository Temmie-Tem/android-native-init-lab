# Native Init V1182 per_mgr Vndservice Gate Plan

Date: `2026-05-28`

## Goal

Add a `--pm-observer-per-proxy-after-vndservice-provider` flag to the helper
(`a90_android_execns_probe`) that gates per_proxy spawn on per_mgr registering
with vndservicemanager (`vendor.qcom.PeripheralManager` visible in `vndservice
list`), replacing the unsafe fixed-time `--pm-observer-per-proxy-pph-delta-ms`
approach that caused the V1179/V1180 race.

V1181 root cause: helper v218/v219 materializes `/dev/subsys_modem` in the
private mount namespace → pm_proxy_helper opens it → pm-proxy spawned by
pm_proxy_helper sends `pm_client_register("modem")` before per_mgr's internal
peripheral list is built (~1000ms) → per_mgr crashes with exit_code=0.

## Root Cause Summary (from V1181)

| Factor | V1105 (success) | V1179/V1180 (failure) |
|--------|-----------------|----------------------|
| subsys_modem node | absent (old helper) | materialized (v218/v219) |
| per_proxy start trigger | per_mgr+1000ms default | pph+800ms / pph+300ms |
| per_mgr init time before pm_client_register | ≥1000ms | <1000ms |
| vendor_qcom_peripheral_manager_seen | 1 | 0 |
| pm_client_register("modem") result | success | per_mgr dead |

## V1182 Helper Change (v220)

### New flag

```
--pm-observer-per-proxy-after-vndservice-provider
```

Requires `--pm-observer-start-cnss-after-provider`. Mutually exclusive with
`--pm-observer-per-proxy-pph-delta-ms`.

### Behavior

When set and `i == PM_OBSERVER_PER_PROXY`, before spawning per_proxy:

1. Polls `vndservice list` at 200ms intervals (via `append_vndservice_query`)
2. Checks for `vendor.qcom.PeripheralManager` (`vendor_qcom_peripheral_manager_seen=1`)
3. Bounded timeout: 5000ms
4. Logs `pm_service_trigger_observer.per_proxy_vndservice_gate.*`:
   - `begin=1`, `timeout_ms=5000`, `poll_interval_ms=200`
   - `poll_count=N`, `elapsed_ms=W`, `gate_open=0|1`
   - `result=ready|timeout|error`
5. Falls through to per_proxy spawn regardless of gate result (log-only gate;
   live gating confirmed in subsequent V1183 live run)

### Source changes

File: `stage3/linux_init/helpers/a90_android_execns_probe.c`

1. Config struct: added `bool pm_observer_per_proxy_after_vndservice_provider`
2. Flag parsing: `--pm-observer-per-proxy-after-vndservice-provider`
3. Validation: requires `pm_observer_start_cnss_after_provider`; rejects
   simultaneous `pm_observer_per_proxy_pph_delta_ms > 0`
4. Per_proxy timing block: new first branch before `early_per_proxy_delta_ms`
   check; polls in a `while (!gate_open && monotonic_ms() < gate_deadline)` loop

### Build result

```
SHA256 (v0, before EXECNS_VERSION bump): b456ca27ca7ba3becfea538ea4a3c723500084499537900e1a5a83ac72601654
SHA256 (v220 marker added):              985675707ee433ec0203cbd1e59b0cd439dee0bc05d315266657b889d0c384a0
ELF 64-bit LSB executable, ARM aarch64, statically linked
No dynamic section.
```

## V1182 is source/build-only

No device flash, no deploy, no live action. V1183 will deploy and run the gate.

## Intended V1183 mode

```
wifi-companion-post-pm-mdm-helper-esoc-observer
--allow-post-pm-mdm-helper-esoc-observer
--pm-observer-start-cnss-after-provider
--pm-observer-per-proxy-after-vndservice-provider
--pm-observer-zero-delay-per-mgr-probe
```

Expected gate behavior in V1183:
- per_mgr starts (order 4), zero-delay probe confirms observable
- Gate polls vndservice every 200ms; per_mgr needs ~1000ms to register
- Gate opens (`result=ready`) after ~1000ms, per_proxy spawns
- `vendor_qcom_peripheral_manager_seen=1` at per_proxy spawn time
- pm_proxy_helper's pm-proxy should now successfully register "modem" with
  per_mgr (per_mgr's peripheral list populated before pm_client_register)

Wi-Fi HAL, scan/connect, credentials, DHCP/routes, external ping remain blocked.
