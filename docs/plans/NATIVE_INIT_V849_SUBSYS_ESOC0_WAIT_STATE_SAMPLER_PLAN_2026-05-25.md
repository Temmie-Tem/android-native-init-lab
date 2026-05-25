# Native Init V849 subsys_esoc0 Wait-State Sampler Plan

## Goal

Run one bounded live `subsys_esoc0` char-open attempt and capture enough
in-window task evidence to distinguish provider `powerup()` blocking from
`wait_for_err_ready()` blocking.

## Inputs

- V848 classifier: `tmp/wifi/v848-subsys-esoc0-open-block-classifier/manifest.json`
- Device baseline: stock native `A90 Linux init 0.9.68 (v724)`
- Char node contract: `/dev/subsys_esoc0` materialized as char `236:9`

## Method

1. Verify preflight `version`, `bootstatus`, and `selftest verbose`.
2. Capture read-only node, mdm3/subsys, and `/sys/module` eSoC/MHI/ICNSS/WLAN surfaces.
3. Create only `/dev/subsys_esoc0` from the V845/V846 uevent contract.
4. Start one background holder that opens `/dev/subsys_esoc0`.
5. While the holder is blocked, capture process tree, `wchan`, `stack`,
   `status`, `syscall`, fd surface, mdm3 state, module surface, and focused dmesg.
6. Remove the node and reboot-clean to restore a known native state.
7. Run post-reboot `version`, `bootstatus`, and `selftest verbose`.

## Guardrails

- No raw `/dev/esoc*` open/ioctl.
- No GPIO/sysfs/debugfs write except creating/removing the scoped
  `/dev/subsys_esoc0` node.
- No bind/unbind, module load/unload, daemon start, service-manager, Wi-Fi HAL,
  scan/connect, credentials, DHCP/routes, external ping, boot image write,
  partition write, or custom kernel flash.

## Success Criteria

- Holder PID is present.
- At least one in-window `/proc/<pid>/wchan` and stack/status sample is captured.
- Cleanup reboot restores `BOOT OK` and selftest `fail=0`.
- The report identifies whether the block is in `mdm_subsys_powerup`,
  `wait_for_err_ready`, a downstream MHI hook, or remains unresolved.

## Command

```bash
python3 scripts/revalidation/native_wifi_subsys_esoc0_wait_state_sampler_v849.py \
  --out-dir tmp/wifi/v849-subsys-esoc0-wait-state-sampler \
  --allow-mknod \
  --allow-subsys-char-open \
  --allow-reboot-cleanup \
  --assume-yes \
  --hold-sec 12 \
  --observe-sec 8 \
  run
```
