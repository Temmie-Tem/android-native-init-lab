# V1118 Global Holder Zero-delay CNSS Live Report

Date: `2026-05-27`

## Result

- Decision: `v1118-zero-delay-cnss-pm-register-path-reached`
- Pass: `true`
- Build evidence: `tmp/wifi/v1117-execns-helper-v211-build/manifest.json`
- Deploy evidence: `tmp/wifi/v1118-execns-helper-v211-deploy/manifest.json`
- Live evidence: `tmp/wifi/v1118-global-holder-zero-delay-cnss-live/manifest.json`
- Helper: `a90_android_execns_probe v211`

## Summary

V1118 deployed helper `v211` and ran the zero-delay CNSS gate. The result is
functionally the same as V1116: CNSS reaches PM register, but PM register returns
`0xffffffff` and PM connect is not reached.

Deploy:

```text
decision=execns-helper-v211-deploy-pass
method=serial appendfile + uudecode
serial_chunk_size=1850
sha256=6bcf4ad606453f56c4cc25744f6ab90ff6b4cb89942b13c4cc86a7b2f024e44d
```

Live:

```text
decision=v1118-zero-delay-cnss-pm-register-path-reached
reason=register_entries=1 register_ret=['0xffffffff'] cnss_hits=2
firmware_mounts_executed=True
global_modem_holder_opened=True
tracefs_write_executed=True
cnss_daemon_start_executed=True
wifi_hal_start_executed=False
wifi_bringup_executed=False
external_ping_executed=False
```

## Key Evidence

Zero-delay contract:

```text
start_cnss_zero_delay_after_per_mgr=1
child.per_mgr.post_start_probe_wait_ms=0
child.per_mgr.post_start_probe_deferred_until_after_cnss=1
per_proxy_start_executed=0
child.per_proxy.start_skipped=1
cnss_daemon_start_executed=1
```

Trace result:

```text
pm_client_register_entry: cnss-daemon=1
pm_client_register_ret: cnss-daemon=['0xffffffff']
pm_client_connect_entry: 0
pm_client_connect_ret: 0
cnss_daemon_hit_count=2
```

Cleanup:

```text
boot: BOOT OK shell 4.2s
selftest: pass=11 warn=1 fail=0
netservice: disabled tcpctl=stopped
```

## Interpretation

The `20 ms` pre-CNSS sample delay is not the cause of the V1116 PM register
failure. Zero-delay CNSS still reaches only `pm_client_register`, and that
register call returns `0xffffffff`.

The next blocker is no longer ordering delay. It is the PM client register
failure semantics inside `libperipheral_client.so`/`pm-service` under native
init.

## Next

V1119 should trace the register failure return path:

- classify what `0xffffffff` means in the PM client library on this build;
- determine whether the failure is provider lookup, Binder transaction, server
  reject, or client-side precondition;
- avoid widening to Wi-Fi HAL or scan/connect until PM register succeeds or the
  failure is explained.
