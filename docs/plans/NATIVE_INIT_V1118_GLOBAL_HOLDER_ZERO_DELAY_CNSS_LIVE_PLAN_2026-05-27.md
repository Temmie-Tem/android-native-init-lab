# V1118 Global Holder Zero-delay CNSS Live Plan

Date: `2026-05-27`

## Goal

Deploy helper `v211` and prove whether removing the V1116 `20 ms` pre-CNSS
sample delay changes the PM register result.

## Scope

- Deploy only `/cache/bin/a90_android_execns_probe`.
- Run global firmware mounts and global `/dev/subsys_modem` holder.
- Fork `cnss-daemon` immediately after `per_mgr`, with no post-`per_mgr` sleep,
  drain, or vndservice query before CNSS.
- Use the same tracefs PM client/server observer as V1116.
- Cleanup by reboot and verify native health.

## Guardrails

- No `/dev/subsys_esoc0` open.
- No Wi-Fi HAL, wificond, supplicant, scan/connect/link-up, credentials,
  DHCP/routes, or external ping.
- No partition write, boot image write, or flash.
- Firmware mounts are read-only and tracefs writes are bounded.

## Success Criteria

V1118 passes if:

- helper `v211` deploy is proven;
- global firmware mounts and global modem holder are proven;
- QRTR RX appears under holder;
- PM observer contract shows:
  - `start_cnss_zero_delay_after_per_mgr=1`;
  - `child.per_mgr.post_start_probe_wait_ms=0`;
  - `child.per_mgr.post_start_probe_deferred_until_after_cnss=1`;
  - `per_proxy_start_executed=0`;
  - `child.per_proxy.start_skipped=1`;
  - `cnss_daemon_start_executed=1`;
- cleanup returns to healthy native init.

## Expected Branches

- PM register/connect improves: continue into lower PM/eSoC side-effect
  classification.
- PM register still returns `0xffffffff`: close the timing hypothesis and trace
  the PM register failure semantics.
