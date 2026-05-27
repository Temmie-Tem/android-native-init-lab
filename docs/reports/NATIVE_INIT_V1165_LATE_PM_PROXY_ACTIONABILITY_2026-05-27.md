# Native Init V1165 Late pm-proxy Actionability Report

Date: `2026-05-27`

## Result

- Decision: `v1165-late-per-proxy-actionability-gap`
- Pass: `true`
- Helper: `a90_android_execns_probe v217`
- Helper SHA256: `559adaf4b2acd4c0a84d6f4082eb9bdd085717b9a875eec8766d803b51257a6f`
- Build evidence: `tmp/wifi/v1165-execns-helper-v217-build/manifest.json`
- Deploy evidence: `tmp/wifi/v1165-execns-helper-v217-deploy/manifest.json`
- Live evidence: `tmp/wifi/v1165-late-per-proxy-actionability-live-after-v490/manifest.json`
- Live summary: `tmp/wifi/v1165-late-per-proxy-actionability-live-after-v490/summary.md`

## Summary

V1165 confirms that the late `pm-proxy` process itself is not the immediate
failure.  After V401 and V490 were rerun in the same boot, native reached:

```text
firmware mounts + modem holder + Android policy load
  -> pm_proxy_helper holds /dev/subsys_modem
    -> mdm_helper holds /dev/esoc-0
      -> late pm-proxy starts and stays alive for 12 seconds
        -> pm-service Binder thread reaches connect/start-vote and returns 0
          -> pm-service still never opens /dev/subsys_esoc0
            -> no MHI, WLFW service69, BDF, or wlan0
```

This moves the blocker from process lifetime to action contract parity: native
has the visible PM actors alive and the PM server connect path returns success,
but the Android-good `__subsystem_get(esoc0)` side effect is still absent.

## Key Evidence

| key | value |
| --- | --- |
| helper marker | `a90_android_execns_probe v217` |
| late instrumentation | `v1165` |
| late poll window | `12 x 1000 ms` |
| late `pm-proxy` start | `started=1`, `pid=6105` |
| `per_proxy_alive_by_poll` | all `1` |
| `per_proxy_exit_code_by_poll` | all `-1` |
| `per_proxy_signal_by_poll` | all `0` |
| `pm-proxy` client register/connect | `0x0`, `0x0` |
| `cnss-daemon` client register/connect | `0x0`, `0x0` |
| PM server connect/start-vote | `Binder:2537_2`, hit count `2` |
| PM server connect returns | `pm_server_connect_impl_ret=['0x0','0x0']`, `pm_server_connect_ret=['0x0','0x0']` |
| `pm-service` modem fd | `/dev/subsys_modem` count `1` in every late poll |
| `pm-service` eSoC fd | `/dev/subsys_esoc0` count `0` in every late poll |
| `pm-service` binder state | Binder workers remain in `binder_ioctl_write_read`; main/timer threads wait |
| lower markers | `mhi=0`, `wlfw=0`, `bdf=0`, `wlan0=0`, service `69=0` |
| forbidden actions | Wi-Fi HAL, scan/connect, credential use, DHCP/route, external ping all `false` |

## Commands

```bash
python3 scripts/revalidation/native_wifi_late_per_proxy_helper_build_v1165.py run

python3 scripts/revalidation/wifi_execns_helper_v217_deploy_preflight.py \
  --transfer-method serial \
  --serial-chunk-size 1800 \
  --apply \
  --assume-yes \
  --approval-phrase "approve v1165 deploy execns helper v217 only; no daemon start and no Wi-Fi bring-up" \
  run

python3 scripts/revalidation/wifi_selinuxfs_toybox_mount_live_executor.py \
  --out-dir tmp/wifi/v1165-v401-selinuxfs-mount \
  --apply \
  --assume-yes \
  --approval-phrase "approve v401 toybox mount selinuxfs runtime surface only; no daemon start and no Wi-Fi bring-up" \
  run

python3 scripts/revalidation/a90ctl.py --timeout 20 mountsystem ro

python3 scripts/revalidation/native_selinux_policy_load_proof_v490.py \
  --out-dir tmp/wifi/v1165-v490-policy-load \
  --helper-sha256 559adaf4b2acd4c0a84d6f4082eb9bdd085717b9a875eec8766d803b51257a6f \
  --apply \
  --assume-yes \
  --approval-phrase "approve v490 native SELinux policy-load proof only; no init reexec, no daemon start and no Wi-Fi bring-up" \
  run

python3 scripts/revalidation/native_wifi_late_per_proxy_actionability_live_v1165.py \
  --out-dir tmp/wifi/v1165-late-per-proxy-actionability-live-after-v490 \
  --allow-tracefs-mount \
  --allow-tracefs-write \
  --allow-vendor-mount \
  --allow-selinuxfs-mount \
  --allow-pm-service-trigger-observer \
  --allow-cnss-daemon-start \
  --assume-yes \
  run
```

## Validation

- `python3 -m py_compile` passed for the three V1165 scripts.
- Helper `v217` built static AArch64 with no dynamic section.
- Remote helper deploy verified SHA and usage output.
- V401 and V490 prerequisites passed in the same boot before live execution.
- Post-cleanup native health checked:
  - `version`: `A90 Linux init 0.9.68 (v724)`
  - `selftest`: `pass=11 warn=1 fail=0`
  - `netservice`: disabled, `ncm0=absent`, `tcpctl=stopped`

## Interpretation

The remaining blocker is not that `pm-proxy` exits too early.  It remains alive
through the full 12 second late window.  The PM server connect path also returns
success.  The missing piece is the Android-only action that makes `pm-service`
transition from successful PM connect/start-vote to `__subsystem_get(esoc0)`.

## Next Gate

V1166 should inspect PM action-contract parity rather than repeat the same late
`pm-proxy` sequence.  Useful directions:

1. Compare Android `pm-proxy` Binder transaction payload/order with native.
2. Trace or classify `pm-service` state object fields around
   `pm_server_connect_impl_state_check` and `pm_server_connect_impl_start_vote`.
3. Confirm whether native lacks an Android init property, service name, client
   identity, or PM action argument required to trigger eSoC power-up.
4. Keep Wi-Fi HAL/scan/connect/credential/DHCP/external ping blocked until
   `/dev/subsys_esoc0`, MHI, WLFW service `69`, BDF, or `wlan0` appears.
