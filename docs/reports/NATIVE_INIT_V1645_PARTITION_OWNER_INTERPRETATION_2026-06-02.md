# Native Init V1645 Partition Owner Interpretation

## Summary

- Cycle: `V1645`
- Type: host-only partition owner interpretation
- Decision: `v1645-partition-owner-priority-classified`
- Result: PASS
- Input: `docs/reports/NATIVE_INIT_V1644_PARTITION_METADATA_CAPTURE_2026-06-02.md`
- Reason: classify V1644 sysfs GPT partition metadata into plausible SDX50M / PMIC / PON owner artifacts before any raw extraction or write gate.

## Checks

- `v1644_report_present`: `True`
- `v1644_pass_recorded`: `True`
- `candidate_count_positive`: `True`
- `high_priority_candidates_present`: `True`
- `raw_binaries_not_required_for_this_cycle`: `True`
- `no_device_command`: `True`
- `no_live_write_gate`: `True`

## Candidate Priority

| name | devname | size | priority | class | reason |
|---|---|---:|---|---|---|
| `modem` | `sda21` | 204472320 | `context-only` | `downstream-firmware-context` | modem firmware can explain downstream protocol expectations but not the pre-MDM2AP AP-side power owner |
| `dsp` | `sda22` | 67108864 | `context-only` | `downstream-firmware-context` | DSP firmware is downstream context, not a bootloader/PMIC ownership candidate |
| `xbl` | `sdb1` | 4194304 | `high` | `bootloader-pmic-owner-candidate` | earliest bootloader stage; most plausible place for board/PMIC/rail policy before Linux starts |
| `xbl` | `sdc1` | 4194304 | `high` | `bootloader-pmic-owner-candidate` | earliest bootloader stage; most plausible place for board/PMIC/rail policy before Linux starts |
| `tz` | `sdd5` | 4194304 | `medium` | `secure-firmware-context` | secure firmware may constrain access but is not a direct AP-native modem rail control surface |
| `aop` | `sdd7` | 524288 | `high` | `always-on-power-firmware-candidate` | AOP/RPMh-side firmware is a plausible owner for always-on power sequencing and PMIC coordination |
| `abl` | `sdd8` | 4194304 | `medium` | `late-bootloader-context` | ABL can affect Linux handoff state but is less likely than XBL/AOP to be the cold SDX rail owner |
| `bluetooth` | `sdd10` | 1048576 | `context-only` | `downstream-firmware-context` | Bluetooth firmware is not expected to own SDX50M power sequencing |
| `keymaster` | `sdd12` | 524288 | `low` | `security-service-context` | key service firmware, not a likely PMIC or SDX rail owner |
| `cmnlib` | `sdd13` | 524288 | `low` | `security-library-context` | common security library, unlikely to own board power sequencing |
| `cmnlib64` | `sdd14` | 524288 | `low` | `security-library-context` | 64-bit common security library, unlikely to own board power sequencing |
| `devcfg` | `sdd22` | 131072 | `medium-high` | `hardware-config-candidate` | device configuration can carry board resource policy consumed by early firmware or boot stages |
| `qupfw` | `sdd25` | 81920 | `low-medium` | `bus-firmware-context` | QUP firmware is peripheral-bus context, not a likely SDX50M main-rail owner |
| `hyp` | `sdd33` | 1048576 | `low-medium` | `secure-firmware-context` | hypervisor context may constrain devices but is unlikely to be the primary PMIC owner |

## Interpretation

The highest-value artifacts are `xbl` and `aop`, followed by `devcfg` and `abl`. These are the only currently plausible places for bootloader / always-on / board-resource policy that could explain why Android starts with a usable SDX50M power state while native reaches the correct eSoC provider path but still sees no MDM2AP response. `modem`, `dsp`, and `bluetooth` remain downstream context and should not pull the loop back into MHI/WLFW analysis before MDM2AP responds.

V1644 did not expose candidate `/dev/block/<devname>` nodes, so raw content and SHA256 are intentionally absent. That absence is a runtime surface finding, not permission to write partitions or to force PMIC/GPIO/GDSC state.

## Next

V1646 should be a separate private read-only artifact access preflight. It should choose one safe path: temporary private devnodes derived from sysfs major/minor with cleanup, or TWRP/Android read-only pull. It must hash only selected small high-priority candidates first (`xbl`, `aop`, `devcfg`, `abl`), keep binary content out of git, and avoid PMIC/GPIO/GDSC writes, eSoC notify/`BOOT_DONE`, PCI rescan, Wi-Fi HAL, scan/connect, credentials, DHCP/routes, and external ping.
