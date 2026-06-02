# Native Init V1647 Private Devnode SHA256 Gate

## Summary

- Cycle: `V1647`
- Type: temporary private devnode SHA256 gate
- Decision: `v1647-private-devnode-sha256-captured`
- Result: PASS
- Evidence: `tmp/wifi/v1647-private-devnode-hash-gate`
- Reason: compute hashes for selected small bootloader / PMIC-owner candidates without dumping raw proprietary partitions.

## Checks

- `pre_selftest_fail_zero`: `True`
- `post_selftest_fail_zero`: `True`
- `initial_cleanup_ok`: `True`
- `mkdir_ok`: `True`
- `all_mknod_ok`: `True`
- `all_sha256_ok`: `True`
- `all_cleanup_ok`: `True`
- `cleanup_final_absent`: `True`
- `no_raw_dump_command`: `True`
- `no_partition_write_command`: `True`
- `no_wifi_or_pmic_gate`: `True`

## Hashes

| label | name | devname | major:minor | size | sha256 | cleanup |
|---|---|---|---|---:|---|---|
| `xbl_a` | `xbl` | `sdb1` | `8:17` | 4194304 | `e73a07a0b5e3eb9e8db9199eda125ee29b218765f050f85dd934a556549ebe37` | `True` |
| `xbl_b` | `xbl` | `sdc1` | `8:33` | 4194304 | `ae1191b5d70e6de9fd67c6d629bc93aa567296605d30b5c9196ff58fcc26cb50` | `True` |
| `aop` | `aop` | `sdd7` | `8:55` | 524288 | `eadd6c78daca52221e1e3419f34a53eac7c1e2c2bb46c9b663325df1998b9c7c` | `True` |
| `devcfg` | `devcfg` | `sdd22` | `259:9` | 131072 | `0399578253dd293dfc961c6a1077f660834df3ae5e1d65555f4225e327a03d14` | `True` |
| `abl` | `abl` | `sdd8` | `8:56` | 4194304 | `1db19d11a5ce6865e3fbcabadfbdaa9045e75f144b8bc8593a58338c20a3120c` | `True` |

## Duplicate Groups

- none

## Interpretation

V1647 created temporary filesystem-only devnodes, computed SHA256 for the selected small candidates, and removed the nodes. It did not dump raw partition bytes, commit proprietary binaries, write partitions, write PMIC/GPIO/GDSC state, issue eSoC notify/`BOOT_DONE`, rescan PCI, start Wi-Fi HAL, scan/connect, use credentials, run DHCP/routes, or external ping.

## Next

V1648 should stay host-only first: interpret the hashes, decide whether `xbl` duplicate copies match, and define a bounded strings-only or external offline analysis gate only if needed. Do not proceed to modem-rail writes or Wi-Fi HAL until an actual SDX50M power-owner hypothesis is supported.
