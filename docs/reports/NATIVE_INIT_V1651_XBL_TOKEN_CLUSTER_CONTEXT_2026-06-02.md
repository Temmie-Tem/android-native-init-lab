# Native Init V1651 XBL Token Cluster Context

## Summary

- Cycle: `V1651`
- Type: host-only XBL token cluster interpretation
- Decision: `v1651-xbl-cluster-context-ready`
- Result: PASS
- Input evidence: `tmp/wifi/v1649-bounded-token-scan-gate`
- Cluster gap: `8192` bytes
- Reason: group V1649 token-only offsets into XBL regions without dumping raw strings or binaries.

## Checks

- `v1649_manifest_present`: `True`
- `v1649_pass_recorded`: `True`
- `xbl_grep_files_present`: `True`
- `xbl_matches_present`: `True`
- `critical_clusters_present`: `True`
- `no_device_command`: `True`
- `no_live_write_gate`: `True`

## Top XBL Clusters

| artifact | rank | label | start | end | count | score | token counts |
|---|---:|---|---:|---:|---:|---:|---|
| `xbl_a` | 1 | `rpmh-aop-pmic-context` | 3340797 | 3377867 | 159 | 504 | aop=54, pcie=1, pmic=12, pon=5, rpmh=83, vdd=4 |
| `xbl_a` | 2 | `generic-power-token-context` | 3400109 | 3411069 | 53 | 126 | aop=36, gpio=7, pmic=4, pon=5, vdd=1 |
| `xbl_a` | 3 | `pon-pshold-pmic-context` | 20034 | 29600 | 32 | 111 | aop=1, pmic=15, pon=6, ps_hold=1, sdx=3, vdd=6 |
| `xbl_a` | 4 | `pcie-context` | 3666700 | 3682324 | 49 | 98 | pcie=49 |
| `xbl_a` | 5 | `sdx-mdm-context` | 3438654 | 3464312 | 32 | 68 | gpio=6, mdm=6, pmic=17, pon=1, vdd=2 |
| `xbl_a` | 6 | `generic-power-token-context` | 3475960 | 3482668 | 23 | 46 | aop=18, gpio=1, pmic=3, vdd=1 |
| `xbl_a` | 7 | `generic-power-token-context` | 46248 | 52360 | 11 | 30 | pmic=1, ps_hold=1, vdd=9 |
| `xbl_a` | 8 | `rpmh-aop-pmic-context` | 815762 | 824482 | 13 | 30 | aop=2, gpio=4, pcie=4, pmic=1, rpmh=2 |
| `xbl_b` | 1 | `rpmh-aop-pmic-context` | 3355345 | 3400091 | 125 | 376 | aop=53, gpio=6, pcie=1, pmic=8, pon=7, rpmh=49, vdd=1 |
| `xbl_b` | 2 | `pon-pshold-pmic-context` | 20027 | 30662 | 32 | 111 | aop=1, pmic=14, pon=6, ps_hold=1, sdx=3, vdd=7 |
| `xbl_b` | 3 | `pcie-context` | 3666084 | 3681708 | 49 | 98 | pcie=49 |
| `xbl_b` | 4 | `sdx-mdm-context` | 3413708 | 3453368 | 38 | 88 | gpio=9, mdm=6, pmic=17, pon=3, vdd=3 |
| `xbl_b` | 5 | `generic-power-token-context` | 3336632 | 3339289 | 18 | 40 | aop=14, pmic=3, pon=1 |
| `xbl_b` | 6 | `rpmh-aop-pmic-context` | 821026 | 829746 | 13 | 30 | aop=2, gpio=4, pcie=4, pmic=1, rpmh=2 |
| `xbl_b` | 7 | `generic-power-token-context` | 47880 | 54016 | 10 | 28 | pmic=1, ps_hold=1, vdd=8 |
| `xbl_b` | 8 | `sdx-mdm-context` | 3311470 | 3321111 | 12 | 28 | aop=3, mdm=4, pcie=1, pmic=2, pon=1, vdd=1 |

## Interpretation

The XBL token evidence is not random low-density noise. Both XBL copies contain compact regions combining PMIC/VDD/PON/PS_HOLD or RPMh/AOP/PMIC/PCIe vocabulary. This is now the strongest artifact-level explanation path for the native-vs-Android SDX50M power-state difference, but it still does not identify a concrete PMIC/GPIO/GDSC write target.

## Next

V1652 should plan a bounded private string-context extraction only around the top XBL clusters. Raw strings and proprietary binary content must stay under ignored private evidence; tracked output should contain only redacted context classes, token neighborhoods, hashes, and hypotheses. No PMIC/GPIO/GDSC write, partition write, eSoC notify/`BOOT_DONE`, PCI rescan, Wi-Fi HAL, scan/connect, credentials, DHCP/routes, or external ping.
