# Native Init V1648 Hash Interpretation / Token Scan Plan

## Summary

- Cycle: `V1648`
- Type: host-only hash interpretation and bounded token-scan plan
- Decision: `v1648-bounded-token-scan-plan-ready`
- Result: PASS
- Input: `docs/reports/NATIVE_INIT_V1647_PRIVATE_DEVNODE_HASH_GATE_2026-06-02.md`
- Reason: interpret V1647 hashes and define the next live content-read gate without dumping raw proprietary strings or binaries.

## Checks

- `v1647_report_present`: `True`
- `v1647_pass_recorded`: `True`
- `hash_row_count_five`: `True`
- `all_hashes_present`: `True`
- `xbl_copies_are_distinct`: `True`
- `no_device_command`: `True`
- `no_live_write_gate`: `True`

## Hash Interpretation

| label | name | devname | size | sha256 |
|---|---|---|---:|---|
| `xbl_a` | `xbl` | `sdb1` | 4194304 | `e73a07a0b5e3eb9e8db9199eda125ee29b218765f050f85dd934a556549ebe37` |
| `xbl_b` | `xbl` | `sdc1` | 4194304 | `ae1191b5d70e6de9fd67c6d629bc93aa567296605d30b5c9196ff58fcc26cb50` |
| `aop` | `aop` | `sdd7` | 524288 | `eadd6c78daca52221e1e3419f34a53eac7c1e2c2bb46c9b663325df1998b9c7c` |
| `devcfg` | `devcfg` | `sdd22` | 131072 | `0399578253dd293dfc961c6a1077f660834df3ae5e1d65555f4225e327a03d14` |
| `abl` | `abl` | `sdd8` | 4194304 | `1db19d11a5ce6865e3fbcabadfbdaa9045e75f144b8bc8593a58338c20a3120c` |

Duplicate hash groups: none

The two `xbl` slots are distinct. Treat them as separate copies or versions until an external artifact comparison proves which slot is active for this boot chain.

## Proposed V1649 Token-only Gate

Use temporary private devnodes exactly as in V1647, but run bounded match-only grep instead of dumping strings:

```sh
toybox grep -a -i -b -o -m 200 -E 'sdx|sdx50|sdxprairie|pmic|pm8150|pm8150l|pmxprairie|pon|ps_hold|mdm|mdm2ap|ap2mdm|vdd|rpmh|aop|gpio|pcie|mhi' <temporary-node>
```

This emits only `offset:matched-token`, not full strings or raw binary lines. The goal is to identify which artifact contains SDX/PMIC/PON vocabulary before deciding whether any private offline string extraction is justified.

## Hard Stops

No raw partition dump, no full `strings` output, no proprietary binary commit, no partition write, no PMIC/GPIO/GDSC write, no eSoC notify/`BOOT_DONE`, no PCI rescan, no Wi-Fi HAL, no scan/connect, no credentials, no DHCP/routes, and no external ping.
