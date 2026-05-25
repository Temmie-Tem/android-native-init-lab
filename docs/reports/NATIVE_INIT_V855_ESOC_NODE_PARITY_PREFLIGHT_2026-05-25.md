# Native Init V855 eSoC Node Parity Preflight Report

## Result

- decision: `v855-esoc-node-parity-clean`
- pass: `true`
- runner: `scripts/revalidation/native_wifi_esoc_node_parity_preflight_v855.py`
- evidence: `tmp/wifi/v855-esoc-node-parity-preflight/`
- next: V856 `pm-service` start-only with Android node parity; still no
  `mdm_helper`, `ks`, Wi-Fi HAL, scan/connect, DHCP/routes, or external ping

## Scope

V855 performed a bounded native live mutation: it created Android-equivalent
eSoC/subsys device nodes, verified no holders, removed the nodes it created,
and checked native health. It did not open or ioctl those nodes, start
`pm-service`, `mdm_helper`, `ks`, CNSS retry, Wi-Fi HAL, scan/connect, use
credentials, run DHCP, change routes, ping externally, write GPIO/sysfs/debugfs,
write subsystem state, load/unload modules, or write boot/partition data.

## Preflight

Native exposed the required kernel surfaces:

| Surface | Result |
| --- | --- |
| `/proc/devices` `subsys` | major `236` present |
| `/proc/devices` `esoc` | major `484` present |
| `/sys/class/subsys/subsys_esoc0/dev` | `236:9` |
| `/sys/class/subsys/subsys_modem/dev` | `236:0` |
| `/sys/bus/esoc/devices/esoc0/uevent` | `DRIVER=mdm-4x`, `qcom,ext-sdx50m` |
| `/sys/bus/esoc/devices/esoc0/esoc_link` | `PCIe` |
| `/sys/bus/esoc/devices/esoc0/esoc_name` | `SDX50M` |
| `/sys/bus/esoc/devices/esoc0/esoc_link_info` | `0305_01.01.00` |

## Node Materialization

V855 created all three target nodes:

```text
CREATED /dev/esoc-0 c 484 0 mode=0660 owner=0:1001
CREATED /dev/subsys_esoc0 c 236 9 mode=0640 owner=1000:1000
CREATED /dev/subsys_modem c 236 0 mode=0640 owner=1000:1000
```

The resulting node listing matched Android metadata:

```text
crw-rw----    1 0        1001      484,   0 ... /dev/esoc-0
crw-r-----    1 1000     1000      236,   9 ... /dev/subsys_esoc0
crw-r-----    1 1000     1000      236,   0 ... /dev/subsys_modem
```

## Holder and Cleanup

No actor or process held the materialized nodes:

```text
holder_found=0
```

Cleanup removed all nodes created by this run:

```text
REMOVE /dev/esoc-0
REMOVE /dev/subsys_esoc0
REMOVE /dev/subsys_modem
```

Post-cleanup checks confirmed the target nodes were absent again, and native
postflight remained `BOOT OK` with selftest `fail=0`.

## Interpretation

V855 closes the node-parity prerequisite. The native kernel exposes the same
major/minor surfaces Android uses, and the node metadata can be safely
materialized and cleaned up without implicit holders or health regression.

The next meaningful live gate is not GPIO or `mdm_helper` replay. It is a
bounded `pm-service`/PeripheralManager start-only proof while the Android node
parity nodes are present. That matches V853 ordering where `pm-service` holds
`/dev/subsys_esoc0` and `/dev/subsys_modem` before the broader `mdm_helper`/`ks`
contract is replayed.

## Validation

Executed:

```bash
python3 -m py_compile scripts/revalidation/native_wifi_esoc_node_parity_preflight_v855.py
python3 scripts/revalidation/native_wifi_esoc_node_parity_preflight_v855.py \
  --out-dir tmp/wifi/v855-esoc-node-parity-plan plan
python3 scripts/revalidation/native_wifi_esoc_node_parity_preflight_v855.py \
  --out-dir tmp/wifi/v855-esoc-node-parity-preflight \
  --allow-node-materialization \
  --allow-node-cleanup \
  --assume-yes \
  run
git diff --check
```

Result:

```text
decision: v855-esoc-node-parity-clean
pass: True
device_commands_executed: True
device_mutations: True
raw_esoc_open_executed: False
subsys_char_open_executed: False
wifi_bringup_executed: False
external_ping_executed: False
```

## Next Gate

V856 should run a bounded `pm-service` start-only proof with Android node parity
present. It should create the same nodes as V855, start only `pm-service` if the
exact vendor binary/runtime prerequisites are available, capture whether it
holds `/dev/subsys_esoc0` and `/dev/subsys_modem`, then terminate/cleanup and
verify native health. V856 should still avoid `mdm_helper`, `ks`, raw eSoC
ioctl, Wi-Fi HAL, scan/connect, DHCP/routes, external ping, GPIO/sysfs/debugfs
writes, subsystem state writes, module load/unload, and boot-image changes.
