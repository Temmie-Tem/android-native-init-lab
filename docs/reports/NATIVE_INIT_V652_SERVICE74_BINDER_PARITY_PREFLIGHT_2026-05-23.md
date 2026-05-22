# Native Init V652 Service-74 Binder Parity Preflight Report

- date: `2026-05-23 KST`
- status: `blocked/preflight`; Wi-Fi external ping is **not** complete
- runner: `scripts/revalidation/native_wifi_service74_binder_parity_v652.py`
- evidence: `tmp/wifi/v652-service74-binder-parity-preflight/`
- decision: `v652-service74-binder-parity-blocked`

## Scope

V652 combines the V641 clean-DSP state, the V644 lower CNSS path, and the
current helper v104 CNSS-first delayed service-manager mode. It remains a
bounded start-only proof: no DSP boot-node write, no `esoc0` open, no Wi-Fi HAL
start, no scan/connect/link-up, no credentials, no DHCP, no route change, and
no external ping.

The preflight contacted the device for read-only/runtime checks but did not
execute daemon start, service-manager start, Wi-Fi bring-up, or any mutation.

## Result

```text
decision: v652-service74-binder-parity-blocked
pass: False
reason: blocked by v490-current-policy-load, v641-clean-dsp-state
next: resolve blockers before V652
device_commands_executed: True
device_mutations: False
daemon_start_executed: False
wifi_bringup_executed: False
```

## Blockers

| blocker | evidence | interpretation | next |
| --- | --- | --- | --- |
| `v490-current-policy-load` | `tmp/wifi/v652-v490-current-run/manifest.json` missing | current boot has no fresh V490 SELinux policy-load proof for the V652 namespace | rerun V490 after clean-DSP boot is refreshed |
| `v641-clean-dsp-state` | `log_clean=False`, `node_clean=True`, `rpmsg_clean=False` | current v641 boot does not prove the armed clean-DSP one-shot completed and does not expose required sibling RPMSG nodes | re-arm V641 one-shot and reboot before V652 live |

## Ready Checks

| check | status | evidence |
| --- | --- | --- |
| native shell | pass | current boot responds over serial bridge |
| helper v104 | pass | CNSS-first delayed service-manager mode is present |
| real linkerconfig | pass | `/cache/bin/a90_real_ld.config.txt` exists with expected size |
| real APEX library config | pass | `/cache/bin/a90_real_apex.libraries.config.txt` exists with expected size |

## Required Prep Before Live

1. Arm the V641 one-shot clean-DSP flag in `/cache`.
2. Reboot into the same V641 image and wait for shell readiness.
3. Verify the proof log contains the V641 completion marker and that
   ADSP/CDSP/DSPS RPMSG nodes are present.
4. Run V490 policy-load proof for the current boot into
   `tmp/wifi/v652-v490-current-run/`.
5. Rerun V652 preflight; only if it passes, run the bounded V652 live proof.

## Next Gate

The next action is not Wi-Fi HAL, scan, connect, DHCP, or external ping. The
next gate is to refresh the clean-DSP current boot and V490 policy-load state so
V652 can test whether service `74` and binder-clean CNSS runtime can coexist
long enough for WLFW to advance.
