# Native Init V1644 Partition Metadata Capture

## Summary

- Cycle: `V1644`
- Type: read-only live partition metadata/hash capture
- Decision: `v1644-read-only-partition-metadata-captured`
- Result: PASS
- Reason: collect bootloader / PMIC ownership evidence metadata without dumping or committing proprietary partitions.
- Evidence: `tmp/wifi/v1644-partition-metadata-capture-final`

## Checks

- `pre_selftest_fail_zero`: `True`
- `post_selftest_fail_zero`: `True`
- `by_name_map_ok_or_absent`: `True`
- `sysfs_block_map_ok`: `True`
- `partition_map_present`: `True`
- `present_partition_count_positive`: `True`
- `present_partitions_have_metadata`: `True`
- `existing_devnodes_have_sha256`: `True`
- `sensitive_partitions_not_collected`: `True`
- `forbidden_markers_absent`: `True`
- `no_write_gate`: `True`

## Capture Files

- `pre_selftest`: ok=`True` rc=`0` status=`ok` file=`tmp/wifi/v1644-partition-metadata-capture-final/pre-selftest.txt`
- `by_name_map`: ok=`False` rc=`1` status=`error` file=`tmp/wifi/v1644-partition-metadata-capture-final/by-name-map.txt`
- `sysfs_block_map`: ok=`True` rc=`0` status=`ok` file=`tmp/wifi/v1644-partition-metadata-capture-final/sysfs-block-map.txt`
- `post_selftest`: ok=`True` rc=`0` status=`ok` file=`tmp/wifi/v1644-partition-metadata-capture-final/post-selftest.txt`

## Partition Metadata

| name | devname | partn | size bytes | devnode | sha256 |
|---|---|---:|---:|---|---|
| `modem` | `sda21` | 21 | 204472320 | `` | `` |
| `dsp` | `sda22` | 22 | 67108864 | `` | `` |
| `xbl` | `sdb1` | 1 | 4194304 | `` | `` |
| `xbl` | `sdc1` | 1 | 4194304 | `` | `` |
| `tz` | `sdd5` | 5 | 4194304 | `` | `` |
| `aop` | `sdd7` | 7 | 524288 | `` | `` |
| `abl` | `sdd8` | 8 | 4194304 | `` | `` |
| `bluetooth` | `sdd10` | 10 | 1048576 | `` | `` |
| `keymaster` | `sdd12` | 12 | 524288 | `` | `` |
| `cmnlib` | `sdd13` | 13 | 524288 | `` | `` |
| `cmnlib64` | `sdd14` | 14 | 524288 | `` | `` |
| `devcfg` | `sdd22` | 22 | 131072 | `` | `` |
| `qupfw` | `sdd25` | 25 | 81920 | `` | `` |
| `hyp` | `sdd33` | 33 | 1048576 | `` | `` |

## Interpretation

V1644 captured `14` candidate partitions from sysfs GPT metadata and `0` SHA256 values for candidates that already had exposed `/dev/block/*` nodes. This remains a metadata-only evidence gate: no partition body, firmware blob, credential, Wi-Fi HAL action, scan/connect, DHCP/routes, external ping, PMIC/GPIO/GDSC write, eSoC notify/`BOOT_DONE`, PCI rescan, or platform bind/unbind was performed.

## Next

V1645 should interpret this metadata host-only: identify which available bootloader / firmware artifacts are worth private offline strings or diff analysis, and keep raw proprietary dumps out of git. Do not design a PMIC/GPIO/GDSC write gate unless a concrete owner/control surface and sequence constraint is identified.
