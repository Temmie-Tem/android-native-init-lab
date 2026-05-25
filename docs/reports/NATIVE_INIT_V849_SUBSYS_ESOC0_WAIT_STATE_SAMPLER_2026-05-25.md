# Native Init V849 subsys_esoc0 Wait-State Sampler Report

## Result

- runner decision: `v849-subsys-esoc0-block-provider-powerup-or-opaque`
- evidence interpretation: `mdm_subsys_powerup` D-state block
- pass: `true`
- runner: `scripts/revalidation/native_wifi_subsys_esoc0_wait_state_sampler_v849.py`
- evidence: `tmp/wifi/v849-subsys-esoc0-wait-state-sampler/`

## Scope

V849 performed one bounded live mutation: it created `/dev/subsys_esoc0`,
started one background holder, sampled the holder's `/proc` wait state, removed
the node, and reboot-cleaned back to native v724. It did not open raw
`/dev/esoc*`, write GPIO/sysfs/debugfs, bind/unbind drivers, load/unload
modules, start daemons, start service-manager, start Wi-Fi HAL, scan/connect,
use credentials, run DHCP, change routes, ping externally, write boot images,
write partitions, or flash a custom kernel.

## Key Evidence

| Signal | Value |
| --- | --- |
| Preflight | v724, `BOOT OK`, selftest `fail=0` |
| Materialized node | `/dev/subsys_esoc0`, char `236:9` |
| Holder state | blocked, no `holder.opened=1` |
| Holder `wchan` | `mdm_subsys_powerup` |
| Holder task state | `D (disk sleep)` |
| Holder stack | `mdm_subsys_powerup -> __subsystem_get -> subsys_device_open` |
| `wait_for_err_ready` marker | absent |
| MHI/WLFW/BDF/`wlan0` live progress | absent |
| mdm3/subsys9 | remained `OFFLINING` |
| Cleanup | reboot restored `BOOT OK` and selftest `fail=0` |

## Interpretation

V849 resolves the V848 branch. The open is not reaching
`wait_for_err_ready()` and is not visibly progressing to MHI/WLFW. The holder
blocks in `mdm_subsys_powerup`, which is the proprietary ext-mdm provider
`powerup()` path missing from the staged OSRC source. This places the current
Wi-Fi blocker inside the ext-mdm/SDX50M provider power-up handshake, before
SDX50M can publish WLFW service 69.

The practical consequence is that blind longer holds, HAL/connect retries, MHI
`power_up` writes, raw eSoC ioctls, and GPIO pokes remain unjustified. The next
step should classify the ext-mdm provider surface that can explain why
`mdm_subsys_powerup` waits: GPIO status, interrupt readiness, module/sysfs
state, and Android reference behavior.

## Validation

Executed:

```bash
python3 -m py_compile scripts/revalidation/native_wifi_subsys_esoc0_wait_state_sampler_v849.py
python3 scripts/revalidation/native_wifi_subsys_esoc0_wait_state_sampler_v849.py \
  --out-dir tmp/wifi/v849-plan-check \
  plan
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

Result:

```text
decision: v849-subsys-esoc0-block-provider-powerup-or-opaque
pass: True
device_commands_executed: True
mknod_executed: True
subsys_char_open_executed: True
proc_wait_state_sampled: True
reboot_cleanup_executed: True
raw_esoc_open_executed: False
wifi_hal_start_executed: False
scan_connect_executed: False
external_ping_executed: False
```

## Next Gate

V850 should be host-only/read-only first: classify the ext-mdm provider around
`mdm_subsys_powerup` using V849 stack evidence, current live sysfs/module
surfaces, available kernel symbols, and Android reference evidence. It should
not write GPIO/sysfs, open raw eSoC ioctls, start Wi-Fi HAL, scan/connect, run
DHCP/routes, ping externally, or change boot images.
