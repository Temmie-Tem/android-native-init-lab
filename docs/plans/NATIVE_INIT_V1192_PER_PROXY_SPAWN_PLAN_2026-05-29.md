# V1192 Per-Proxy Spawn + subsys_esoc0 Crash Classifier

- **cycle**: V1192
- **date**: 2026-05-29
- **type**: host-only
- **prior**: V1191 live PASS — per_mgr `u:r:vendor_per_mgr:s0`, vndservice gate 30ms, PM Binder IPC confirmed

## V1191 Evidence Summary

| metric | value |
|---|---|
| `policy_load_result` | `policy-load-pass` (1,329,357 bytes) |
| `per_mgr_domain_value` | `u:r:vendor_per_mgr:s0` ✓ |
| `gate_result` | `ready` (poll_count=1, 30ms) |
| `per_mgr subsys_modem` | fd=8 held ✓ |
| `per_mgr vndbinder` | fd=5 held ✓ |
| `pm-proxy (3217)` | modem peripheral register/connect ✓ |
| `cnss-daemon (3346)` | modem peripheral register/connect ✓ |
| `per_proxy` | start_order=6, spawned ✓ |
| `cnss_daemon` | start_order=7, started ✓ |
| `mdm_helper` | start_order=8, started ✓ |
| `per_mgr subsys_esoc0` | count=0 (never opened) |
| `mss` | ONLINE |
| `mdm3` | OFFLINING |
| `wlfw 69` | not published |

## Crash Sequence

**dmesg at t=253.4s:**
```
[Binder:3047_2:3089] subsystem_put: esoc0 count:0
[Binder:3047_2:3089] esoc0: subsystem_put: Reference count mismatch
Call trace:
  subsystem_put+0x3a8/0x3c0
  subsys_device_close+0x74/0xa0
  __fput+0x124/0x250
  task_work_run+0x90/0xb8
  do_notify_resume+0xe80/0xef0
```

**dmesg at t=261.3s:**
```
subsystem_restart_dev(): Restart sequence requested for modem, restart_level = RELATED
```

**dmesg at t=261.6s:**
```
icnss: Modem went down, state: 0xc00080, crashed: 1
icnss: Collecting msa0 segment dump
```

## Root Cause Analysis

### per_mgr main thread: `do_sigtimedwait`

At the post_pm_window sample (t≈253.4s), per_mgr main thread (3047) is in state=S,
wchan=`do_sigtimedwait` — NOT in D-state. This means per_mgr main thread did NOT directly
block on subsys_esoc0 open in the observable window.

### subsys_esoc0 fd_match: count=0

The fd_match for per_mgr after both per_proxy and cnss_daemon steps reports
`subsys_esoc0_count=0`. This could mean:
1. subsys_esoc0 was opened and closed before sampling, OR
2. The open was in a binder thread (not captured by pid-level fd check)

### The close trace: `subsys_device_close → subsystem_put(esoc0 count:0)`

The call trace shows a deferred fput path. This means an fd pointing to `/dev/subsys_esoc0`
was closed. The close triggered `subsys_device_close` → `subsystem_put`. The count=0
message indicates the subsystem_get reference was never fully established (or was already
released by a powerup failure path).

### Mechanism

1. per_mgr opens `/dev/subsys_esoc0` in response to a Binder client request (pm-proxy or cnss-daemon requesting modem peripheral power-up)
2. `subsys_device_open` → `subsystem_get` → `__subsystem_get(esoc0)` → `subsys_start` → provider `powerup()` → **blocks in `mdm_subsys_powerup` D-state**
3. The blocked task is cancelled/interrupted (binder transaction cancellation, SIGTERM, or another event)
4. fd is closed via deferred fput: `__fput → subsys_device_close → subsystem_put`
5. The subsystem_put finds count=0 (get was never completed due to D-state powerup failure) → Reference count mismatch
6. The mismatch triggers esoc0 subsystem fault propagation
7. ~8 seconds later: modem SSR (restart_level=RELATED — related subsystem crash)

### Why subsys_esoc0 open blocks

`mdm_subsys_powerup` is the proprietary ext-MDM provider `powerup()` hook. It blocks waiting
for MDM/eSoC hardware to respond, which requires:
1. `/dev/esoc-0` CMD/REQ engine registration by mdm_helper
2. eSoC image transfer (`ESOC_IMG_XFER_DONE` + `ESOC_BOOT_DONE`)
3. MDM2AP GPIO handshake (GPIO 142)
4. MDM reaching ONLINE state

In native V1191, mdm_helper starts but does NOT open `/dev/esoc-0` (confirmed V902/V903).
Therefore `mdm_subsys_powerup` blocks indefinitely and the subsys_esoc0 open never returns.

## Classifier Conclusion

V1191 confirms significant PM chain progress:
- per_mgr in correct domain, holding vndbinder + subsys_modem ✓
- PM Binder IPC working (pm-proxy + cnss-daemon both connect) ✓
- per_proxy spawned, cnss_daemon + mdm_helper started ✓

But the V904/V905 blocker is still active:
- per_mgr attempts subsys_esoc0 open (triggered by PM client power-up request)
- Open blocks in `mdm_subsys_powerup` because mdm_helper has not done eSoC image transfer
- Blocked open is interrupted → reference count mismatch → modem SSR
- WLFW/BDF/wlan0 remain absent

## Next Gate: V1193

V905 fail-closed runtime-input repair for mdm_helper. Scope:
- mdm_helper must open `/dev/esoc-0` and register CMD/REQ engines
- mdm_helper must respond to `ESOC_REQ_IMG` with `ESOC_IMG_XFER_DONE`
- MDM2AP GPIO 142 must transition (proves MDM advancing past powerup)
- Only after GPIO 142 IRQ: attempt subsys_esoc0 hold as pm-service

The PM chain (per_mgr domain, PM Binder IPC, per_proxy, subsys_modem) is now
confirmed working. The remaining blocker is the native mdm_helper eSoC image
contract before subsys_esoc0 open.

Constraints remain: no Wi-Fi HAL, scan/connect, credentials, DHCP/routes, external ping.
