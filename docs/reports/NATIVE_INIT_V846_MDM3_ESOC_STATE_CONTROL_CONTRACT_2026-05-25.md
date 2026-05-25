# Native Init V846 mdm3/eSoC State-Control Contract Report

## Result

- decision: `v846-mdm3-esoc-char-open-contract-selected`
- pass: `true`
- runner: `scripts/revalidation/native_wifi_mdm3_esoc_state_control_contract_v846.py`
- evidence: `tmp/wifi/v846-mdm3-esoc-state-control-contract/`

## Scope

V846 was host-only. It did not contact the device, create device nodes, open
`esoc0` or `subsys_esoc0`, write sysfs/GPIO/debugfs, start daemons, start
service-manager, start Wi-Fi HAL, scan/connect, use credentials, run DHCP,
change routes, ping externally, write boot images, write partitions, or flash a
custom kernel.

## Key Signals

| Signal | Value |
| --- | --- |
| V845 mdm3 state | `OFFLINING` |
| V845 raw `/dev/esoc*` | absent |
| V845 raw `/dev/subsys*` | absent |
| V845 `subsys_esoc0` uevent | major `236`, minor `9`, devname `subsys_esoc0` |
| OSRC subsystem `state` | `DEVICE_ATTR_RO(state)` |
| Char open path | `subsys_device_open()` → `subsystem_get_with_fwname()` → `subsys_start()` |
| Char close path | `subsys_device_close()` → `subsystem_put()` → `subsys_stop()` |
| MHI eSoC hook | power-on hook resumes PCIe and calls `mhi_pci_probe()` |
| eSoC provider implementation | not present in staged OSRC source |

## Interpretation

V845's `test -w` results are not sufficient authority for sysfs write
semantics. OSRC shows subsystem `state` has no store path, so direct
`subsys9/state` write is rejected. The exported userspace boot contract is the
subsystem char-device path: opening `subsys_esoc0` calls the kernel subsystem
get/start path, and closing it calls put/stop.

Because `/dev/subsys_esoc0` is absent even though the class uevent advertises
major/minor numbers, the next live gate must explicitly materialize only that
node, run one bounded open/hold smoke, capture dmesg/state markers, and cleanup
with reboot. Raw `/dev/esoc*` ioctl paths and opaque `esoc_link` sysfs writes
remain rejected.

## Validation

Executed:

```bash
python3 -m py_compile scripts/revalidation/native_wifi_mdm3_esoc_state_control_contract_v846.py
python3 scripts/revalidation/native_wifi_mdm3_esoc_state_control_contract_v846.py \
  --out-dir tmp/wifi/v846-plan-check \
  plan
python3 scripts/revalidation/native_wifi_mdm3_esoc_state_control_contract_v846.py \
  --out-dir tmp/wifi/v846-mdm3-esoc-state-control-contract \
  run
```

Result:

```text
decision: v846-mdm3-esoc-char-open-contract-selected
pass: True
device_commands_executed: False
mknod_executed: False
subsys_char_open_executed: False
sysfs_write_executed: False
wifi_hal_start_executed: False
scan_connect_executed: False
external_ping_executed: False
```

## Next Gate

V847 should implement and run a bounded live `subsys_esoc0` char-device
materialize/open/hold smoke. The test must include timeout handling, dmesg/state
evidence, explicit cleanup reboot, and postflight health checks. HAL/connect,
credentials, DHCP/routes, external ping, and boot-image work remain blocked.
