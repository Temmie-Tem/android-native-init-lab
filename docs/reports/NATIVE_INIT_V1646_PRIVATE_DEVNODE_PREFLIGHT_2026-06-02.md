# Native Init V1646 Private Devnode Preflight

## Summary

- Cycle: `V1646`
- Type: read-only private devnode artifact access preflight
- Decision: `v1646-private-devnode-preflight-ready`
- Result: PASS
- Evidence: `tmp/wifi/v1646-private-devnode-preflight`
- Reason: verify whether selected high-priority partitions have enough sysfs major/minor metadata to support a later private temporary-devnode SHA256 gate.

## Checks

- `pre_selftest_fail_zero`: `True`
- `post_selftest_fail_zero`: `True`
- `toybox_command_list_ok`: `True`
- `required_toybox_tools_present`: `True`
- `selected_count`: `True`
- `selected_major_minor_present`: `True`
- `selected_names_match`: `True`
- `selected_size_present`: `True`
- `no_devnode_created`: `True`
- `no_partition_content_read`: `True`
- `no_live_write_gate`: `True`

## Tool Checks

- `mknod`: `True`
- `mkdir`: `True`
- `rm`: `True`
- `sha256sum`: `True`
- `ls`: `True`
- `cat`: `True`

## Selected Partitions

| label | name | devname | major:minor | size bytes | start | ro | reason |
|---|---|---|---|---:|---:|---|---|
| `xbl_a` | `xbl` | `sdb1` | `8:17` | 4194304 | 48 | `1` | early bootloader PMIC owner candidate |
| `xbl_b` | `xbl` | `sdc1` | `8:33` | 4194304 | 48 | `1` | alternate early bootloader copy |
| `aop` | `aop` | `sdd7` | `8:55` | 524288 | 21552 | `1` | always-on power / RPMh-side firmware candidate |
| `devcfg` | `devcfg` | `sdd22` | `259:9` | 131072 | 74568 | `1` | board resource configuration candidate |
| `abl` | `abl` | `sdd8` | `8:56` | 4194304 | 22576 | `1` | late bootloader handoff context |

## Interpretation

V1646 does not create devnodes and does not read partition contents. It only proves the selected `xbl`, `aop`, `devcfg`, and `abl` candidates have sysfs major/minor metadata and that the required toybox helpers exist for a later private SHA256-only gate.

## Next

V1647 may create temporary private devnodes under ignored evidence storage, compute SHA256 for the selected small candidates, remove the devnodes, and document only hashes/metadata. Raw proprietary binaries must stay out of git. Do not write partitions or enter PMIC/GPIO/GDSC, eSoC notify/`BOOT_DONE`, PCI rescan, Wi-Fi HAL, scan/connect, credentials, DHCP/routes, or external ping paths.
