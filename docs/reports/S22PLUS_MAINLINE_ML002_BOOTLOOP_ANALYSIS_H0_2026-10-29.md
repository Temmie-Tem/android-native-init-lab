# S22+ ML002 boot-loop analysis with Claude and Argon

Date: 2026-10-29 KST. Target: SM-S906N / g0q / S906NKSS7FYG8.
Status: **H0 ANALYSIS; RESET CAUSE AND PHYSICAL BOOT STAGE UNPROVED**.

Claude Opus 5.5 and Gemini 4 Argon High each completed two rounds at high
effort. They received the same initial evidence, then each other's conclusions
and a new exact firmware/kernel-byte comparison. Neither invoked tools.
The host performed the source and artifact checks below. These advisory
reviews do not create device authority or replace a capability activation.

[ML002](S22PLUS_MAINLINE_ML002_RUN_2026-10-29.md) remains consumed
`NO_PROOF / ANDROID_CLOSED_HEALTHY`: one N transfer, 117 sampled USB2 absences,
no authenticated request/PID1 evidence, the operator's approximate 8–9-second
reboot-loop observation, and one physical original-A return with final health.
This analysis made no device call, built no candidate and changed no runtime.

## Concrete finding: watchdog discovery UID differs

The exact retained FYG8 hypervisor supports the vendor watchdog control,
status, pet and timeout dispatch IDs used by the stock `gh_virt_wdt` client.
However, its standard vendor-hypervisor UID response differs from the UID
required by the current mainline automatic registration path.

| Consumer/value | Static result |
| --- | --- |
| Vendor-hypervisor UID query | `0x8600ff01` |
| Retained FYG8 response after the kernel's byte conversion | `bd54bd19-1b57-370b-9b60-6f94e69d5354` |
| `qcom_scm_gunyah_wdt_init()` expected service UID | `c1d58fcd-a453-5fdb-9265-ce36673d5f14` |
| Comparison | Different; the matching path returns before platform registration |

The derivation follows the actual owner/fast/SMC32 checks, query jump-table
entry, immediate construction and guest-register stores in the retained
`hypvm.mbn`. It then applies the exact `smccc_res_to_uuid()` conversion.
The retained firmware hash and earlier watchdog instruction spans were
reverified. A second checker compared the complete compiled
`qcom_scm_probe`, `qcom_scm_gunyah_wdt_init` and
`arm_smccc_hypervisor_has_uuid` functions, plus the referenced UID constant,
between vmlinux and the actual ML002 kernel Image. The helper call and early
exit are present in those bytes. Both external models accepted the supplied
branch/endianness/provenance derivation after cross-review.

This is **conditional static compatibility evidence**, not a live SMC result.
The candidate DT selects the SMC conduit, but the actual trap route, runtime
SMCCC version and loaded hypervisor memory were not observed. The helper also
returns false without a query when its runtime SMCCC version is too old.

ML002 already has `CONFIG_GUNYAH_WATCHDOG=n`. The mismatch therefore does not
identify its reset cause. It explains why merely enabling that driver would
not be sufficient on the analyzed firmware-dispatch path. No UID guard was
relaxed or bypassed. The separately verified watchdog API dispatch IDs do not
prove that a watchdog was armed, that a command succeeded, or that the driver
would start before a timeout.

## What the evidence does and does not narrow

The actual forced command line includes `panic=0`, and
`CONFIG_PANIC_TIMEOUT=0`. The generic panic path skips its timed
`emergency_restart()` when that value is zero; RAM PID1 error/timeout paths
park in a sleep loop. This narrows the configured software restart behavior.
A panic or other stall could still precede an external watchdog reset, and
explicit firmware/fatal restart paths remain possible.

| Question | Current evidence and limit |
| --- | --- |
| Initial failure/stall | Loader rejection, early kernel failure, a driver wait, panic or PID1 park remain possible. None was observed directly. |
| Reset executor | Inherited Gunyah/APSS/PMIC watchdog and firmware/hypervisor fatal reset are hypotheses. No reset-reason or armed-state evidence was acquired. |
| Primary-CPU idle | CPU idle/PSCI support and DT states are present. `maxcpus=1` does not disable primary-CPU idle, but no entered state or failed suspend was observed. |
| Boot progress | The screen behavior and 117 sampled USB absences cannot identify loader, kernel or PID1 progress. Short USB events could be missed. |

The [earlier exact FYG8 watchdog analysis](S22PLUS_FYG8_STOCK_FIRST_WATCHDOG_H0_2026-10-20.md)
provides reusable ABI and firmware structure. Its P437 watchdog timing and
vendor-kernel behavior are not ML002 evidence. Its HCR/WFx findings are static:
live HCR and idle execution were not captured. In particular, `cpuidle.off`
still permits the architecture's WFI path; it does not eliminate all
hypervisor idle interactions.

The cross-review corrected these overstatements:

- Missing `cpuidle.off` is a testable variable, not a demonstrated defect.
  A kernel panic is possible, not established as the leading initiating fault.
- ML001's reported unchanged screen is not a continuously measured
  120-second no-reset control. The visual difference alone proves no progress.
- Host USB events do not prove the exact UDC-bind call or authenticated PID1.
  An event recorder is useful optional diagnosis, not a blanket prerequisite.
- A visible progress marker needs fresh candidate/boot attribution and actual
  refresh validation; old-cycle pixels can persist. A pre-branch loader marker
  proves only that point, and absence of a marker is inconclusive. Cache
  operations require the actual memory/entry contract.
- Ordinary selected SCM initialization is not automatically an authority
  violation. Its default no-dump/SDI calls remain concrete initialization paths
  to inspect, with actual reachability/effects unobserved in ML002.
- `gunyah_wdt_probe()` ignores its stop return before registration and does not
  establish `WDOG_HW_RUNNING` on that failure path. This is a prospective
  driver error-path concern if enabled and bound, not a cause in the current
  compiled-out configuration. Enabling, disabling or servicing a watchdog is
  not adopted as a default fix here.

## Selected next bounded H0 unit

The models agreed on the unknown inherited watchdog state but proposed
different starting points: Claude selected the hypervisor watchdog object's
initialization; Argon selected ABL/UEFI ExitBootServices handoff processing.

Start with **the HLOS virtual-watchdog object's initial state in the retained
FYG8 hypervisor**. Its STATUS/CONTROL consumers and exact bytes are already
identified, making this the narrower starting point. Trace their state fields
to the VM creation/initialization path, limited to that binary.

Completion is a source-backed answer, or an explicit "not determinable from
retained artifacts", for each of: initial enable state; initial bark/bite
values and timebase; and whether a boot path enables it without a guest call.
An object's default state would still not prove its state at ML002 handoff.
If a caller-supplied value or another firmware stage decides the state, record
that unresolved input and finish this unit rather than expanding indefinitely.

ABL/UEFI handoff tracing, inherited-display marker feasibility, a bounded USB
event recorder and a later single-variable idle experiment remain separate
follow-ups. This selection creates no new gate, candidate or device grant.

## Evidence and accounting

Private packets, raw model replies, retained input pins, two syntax-checked
static checkers and their passing results are under
`workspace/private/outputs/s22plus-mainline-ml002-bootloop-analysis-20261029-1/`.
The checks neither executed firmware nor changed consumed evidence. A90,
S20+ and unrelated dirty work were untouched. The ML002 healthy closure remains
the last device evidence; it was not refreshed by this host-only analysis.

All four model responses and final token records were received. Argon's second
CLI process did not exit after its complete SUCCESS result; the bounded wrapper
terminated that process group. The response, usage and process-exit anomaly
were preserved, with no request replay. Private before/after quota snapshots
and the append-only usage ledger distinguish account-wide changes, per-call
tokens and list-price estimates from actual billing.
