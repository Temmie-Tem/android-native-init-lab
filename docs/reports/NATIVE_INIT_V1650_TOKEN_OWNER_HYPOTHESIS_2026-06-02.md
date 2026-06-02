# Native Init V1650 Token Owner Hypothesis

## Summary

- Cycle: `V1650`
- Type: host-only token owner hypothesis
- Decision: `v1650-xbl-first-private-analysis-hypothesis`
- Result: PASS
- Input: `docs/reports/NATIVE_INIT_V1649_BOUNDED_TOKEN_SCAN_GATE_2026-06-02.md`
- Reason: convert V1649 token-only evidence into an artifact-analysis priority without running another live gate.

## Checks

- `v1649_report_present`: `True`
- `v1649_pass_recorded`: `True`
- `summary_rows_present`: `True`
- `xbl_rows_dominate`: `True`
- `secondary_context_present`: `True`
- `no_device_command`: `True`
- `no_live_write_gate`: `True`

## Ranked Artifacts

| rank | label | name | matches | power score | sdx score | specific score |
|---:|---|---|---:|---:|---:|---:|
| 1 | `xbl_a` | `xbl` | 413 | 328 | 85 | 554 |
| 2 | `xbl_b` | `xbl` | 333 | 247 | 86 | 452 |
| 3 | `aop` | `aop` | 13 | 13 | 0 | 2 |
| 4 | `devcfg` | `devcfg` | 3 | 3 | 0 | 2 |
| 5 | `abl` | `abl` | 2 | 1 | 1 | 2 |

## Hypothesis

- Primary target: `xbl_a` / `xbl_b`.
- Secondary context: `aop` / `devcfg`.
- Defer: `abl` for this blocker.

XBL artifacts contain dense PMIC/VDD/PON/PS_HOLD/RPMh/SDX/PCIe vocabulary; AOP/devcfg contain weaker but relevant context; ABL is too sparse for this blocker.

This does not prove a concrete PMIC write target. It only narrows the next private offline analysis target to the XBL artifacts. PMIC/GPIO/GDSC mutation remains unjustified.

## Next

V1651 should be a host-only/private-evidence plan for bounded XBL string-context extraction around offsets already observed in V1649. Raw proprietary content must remain under ignored private storage; tracked output should summarize only non-sensitive token contexts and hypotheses. No Wi-Fi HAL, scan/connect, credentials, DHCP/routes, external ping, partition write, PMIC/GPIO/GDSC write, eSoC notify/`BOOT_DONE`, or PCI rescan.
