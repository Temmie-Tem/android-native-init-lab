# Native Init V1652 XBL Private Context Contract

## Summary

- Cycle: `V1652`
- Type: host-only private XBL context extraction contract
- Decision: `v1652-xbl-private-context-contract-ready`
- Result: PASS
- Input: `docs/reports/NATIVE_INIT_V1651_XBL_TOKEN_CLUSTER_CONTEXT_2026-06-02.md`
- Reason: define a safe bounded extraction contract before reading any XBL string context.

## Checks

- `v1651_report_present`: `True`
- `v1651_pass_recorded`: `True`
- `target_clusters_defined`: `True`
- `output_allowlist_defined`: `True`
- `output_forbidden_defined`: `True`
- `no_device_command`: `True`
- `no_live_write_gate`: `True`

## Target Clusters

| artifact | range | label | reason |
|---|---|---|---|
| `xbl_a` | `3340797..3377867` | `rpmh-aop-pmic-context` | strongest RPMh/AOP/PMIC/PON/VDD cluster |
| `xbl_b` | `3355345..3400091` | `rpmh-aop-pmic-context` | matching high-value cluster in alternate XBL slot |
| `xbl_a` | `20034..29600` | `pon-pshold-pmic-context` | early PON/PS_HOLD/PMIC/VDD/SDX cluster |
| `xbl_b` | `20027..30662` | `pon-pshold-pmic-context` | early PON/PS_HOLD/PMIC/VDD/SDX cluster in alternate slot |

## Output Contract

Tracked reports may include only:
- artifact label
- range start/end
- string offset
- string length
- sha256 of full private string
- matched token list
- redacted token-neighborhood class

Tracked reports and git must not include:
- raw string text in tracked report
- raw binary bytes
- full strings output
- partition dump
- SSID or passphrase
- PMIC/GPIO/GDSC writes
- eSoC notify/BOOT_DONE
- PCI rescan
- Wi-Fi HAL or scan/connect

## Helper Contract

- Next cycle: `V1653` source/build-only static helper.
- Helper name: `a90_xbl_context_probe`.
- Input: temporary private block devnode path, artifact label, bounded ranges, and token regex.
- Behavior: read only specified byte ranges and identify printable strings intersecting those ranges.
- Tracked output: offset, length, SHA256 of the private string, matched token list, redacted class, and source range.
- Private output: raw string text may exist only under ignored private evidence if a later gate explicitly needs it.

## Hard Stops

No raw strings in tracked files, no raw binary dump, no partition write, no PMIC/GPIO/GDSC write, no eSoC notify/`BOOT_DONE`, no PCI rescan, no Wi-Fi HAL, no scan/connect, no credentials, no DHCP/routes, and no external ping.
