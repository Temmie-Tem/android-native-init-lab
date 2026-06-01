# Native Init V1466 Provider AP2MDM Branch Classifier

## Summary

- Cycle: `V1466`
- Type: host-only classifier over V1464/V1465, V1318, and source/static provider evidence
- Decision: `v1466-ap2mdm-branch-divergence-needs-pil-parity-test-boot`
- Result: PASS
- Reason: V1464 proves the test boot reaches the PON side but does not observe AP2MDM, while V1318 proves an earlier native PM path emitted esoc0 PIL notifications and AP2MDM high; the current test boot lacks PIL tracepoint parity, so the next safe gate is source/build-only.

## Evidence Inputs

- V1465 manifest: `tmp/wifi/v1465-provider-tracepoint-classifier/manifest.json`
- V1464 evidence: `tmp/wifi/v1464-wifi-test-boot-exact-provider-tracepoint-handoff`
- V1318 report: `docs/reports/NATIVE_INIT_V1318_CRITICAL_LOWER_TRACE_COLLECTOR_2026-05-31.md`
- Static provider analysis: `docs/reports/ESOC_PROVIDER_STATIC_ANALYSIS_2026-06-01.md`
- Provider research note: `docs/overview/MDM3_ESOC_SDX50M_BRINGUP_RESEARCH_2026-05-25.md`
- PID1 source: `stage3/linux_init/v724/90_main.inc.c`

## V1464 Exact-Provider Test Boot

- tracepoint armed: `True`
- summary still armed when collected: `True`
- PON low-high seen: `True`
- PON low-to-high interval ms: `180.115`
- GPIO135/AP2MDM event count: `0`
- GPIO142/MDM2AP event count: `0`
- AP2MDM absent: `True`
- MDM2AP absent: `True`
- downstream progress absent: `True`
- provider wchan path seen: `True`

## V1318 Reference Evidence

- GPIO135 high count: `1`
- GPIO142 line count: `0`
- esoc0 PIL notification seen: `True`
- PON trace seen: `True`

## Source/Static Contract

- source expects AP2MDM after PON: `True`
- provider is GPIO/ioctl only: `True`
- current PID1 tracepoint sampler lacks PIL notification parity: `True`

## Interpretation

V1464 is not yet a safe basis to jump to Wi-Fi HAL, scan/connect, or network
testing. It proves the test boot enters the provider/PON side but does not
prove the same lower tracepoint contract as V1318, because the V1462 PID1
sampler only arms GPIO tracepoints. V1318 saw `fw=esoc0` PIL notifications
and then GPIO135/AP2MDM high, while V1464 saw PON/errfatal activity but no
GPIO135 event through the current exact-provider window.

The next aligned step is not a lower write or another blind live retry. It is
a source/build-only test boot update that adds `msm_pil_event:pil_notif`
parity to the exact-provider GPIO tracepoint sampler and records whether the
PIL notification branch appears before expecting AP2MDM.

## Safety Scope

This classifier was host-only. It did not issue device commands, flash,
reboot, start Wi-Fi HAL, scan/connect, use credentials, configure
DHCP/routes, perform external ping, or write PMIC/GPIO/GDSC/eSoC controls.

## Next

V1467 source/build-only exact-provider PIL+GPIO tracepoint test boot
