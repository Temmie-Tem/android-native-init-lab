# ML020: retain power-domain providers and exclude CPUidle entry

Status: **H0 qualified and independently reviewed; separately approved
[physical run](S22PLUS_MAINLINE_ML020_RUN_2026-11-04.md) consumed `NO_PROOF`
and closed original A healthy**.

After [ML019 closed without USB or retained-entry proof](S22PLUS_MAINLINE_ML019_RUN_2026-11-04.md),
two rounds with Claude Opus 5.5 and Gemini 4 Argon High selected one functional
bring-up simplification. ML020 appends only `cpuidle.off=1` to the existing
forced kernel command line. It keeps the PHY correction, compiled DT, kernel
configuration choices, V1 writers, ordinary unparked entry and RAM PID1.
The bounded objective remains authenticated RAM PID1/USB followed by healthy
original-A return. This is not a diagnosis of an earlier failure.

## Source basis and rejected driver removal

The exact candidate enables PSCI CPUidle and its domain driver. Scheduled
CPUidle entry can call the firmware suspend path after CPU PM and hierarchical
runtime-PM work. The RAM/USB milestone does not require those optional idle
states, so one candidate can exclude their use while retaining architectural
WFI. A failure would close this experiment without falsifying an unobserved
idle hypothesis or automatically starting a series of CPU/governor toggles.

The initial alternative, `CONFIG_ARM_PSCI_CPUIDLE=n`, was rejected before a
full build. A real `olddefconfig` probe changed five related symbols. More
importantly, the exact compiled DT shows an active non-CPU consumer:
`/soc@0/rsc@17a00000` (`apps_rsc`) references the PSCI cluster power domain.
Its RPMh children supply clocks, regulators and interconnect needed by USB.
Removing the domain driver would remove that declared provider. The ordinary
platform power-domain attachment and RPMh notifier paths depend on this graph.
No DT deletion or second configuration change is introduced to work around it.

The selected token is the built-in `cpuidle.off` integer parameter. Normal
kernel parameter parsing sets it before scheduler initialization and initcalls.
The CPUidle core initializer and driver registration reject the disabled
framework; the scheduler's `cpuidle_not_available()` selects
`default_idle_call()` then ARM64 `arch_cpu_idle()` / `cpu_do_idle()`, retaining
IRQ-context handling, DSB and WFI.

This does **not** skip all PSCI or genpd activity. Architecture setup initializes
PSCI before the ordinary parameter parse and may select PC mode. The separate
PSCI domain-provider initcall remains, including its OSI/PC selection. The
PSCI idle driver can parse and attach topology before registration rejects it,
then detach during cleanup. The RPMh domain-notifier and hardware-solver paths
also remain. Scheduler CPUidle state entry is the excluded operation; there
is no blanket claim that all firmware calls or power-domain operations vanish.

Both retained vendor and candidate timers have `always-on`, with corresponding
core `local-timer-stop` properties. No timer-property mismatch was found.
There is no new watchdog or thermal control. Power, temperature and timing
effects of reduced idle-state use are unmeasured; this candidate makes no
sustained-operation, standby or automatic-recovery claim.

## Proportional validation and interpretation

Fresh preparation confirms an identical compiled DT and exactly one config
value change: the appended command-line token. PSCI firmware, both PSCI idle
driver config symbols and the existing power-domain providers remain enabled.
The corrected PHY source is byte-identical to ML019. Exact current mainline
capability and backend V27 checks pass unchanged; their retained reviews can
be reused while fresh artifact qualification and independent review cover
this candidate.

Complete kernel production passed without compiler warnings, errors or section
mismatches. The full source-tree comparison finds only the fresh generated V1
frame. The PHY, CPUidle core/driver, PSCI idle/domain, ARM64 idle and RPMh-RSC
object files are byte-identical to ML019. All other config values and the
complete DTB are unchanged; no entry park is present.

- 342 actual V1 writer cases, six real-EL marker cases, 20 linked-loader cases,
  1,051 aligned copies and three real-EL loader entries pass.
- The new kernel/RAM PID1 VM passes in 5.686 seconds; its complete raw evidence
  rechecks. Two boot images and boot-only AP packages are byte-identical.
- A separate VM-only ARM64 PID1 reads the actual kernel parameter and interface.
  The retained ML019 Image reports `off=0` with the CPUidle interface present;
  ML020 reports `off=1` with it absent. Both show CPU 0 online and complete a
  250 ms sleep. The same fresh probe CPIO is used with both exact Images,
  without an appended QEMU command line. Raw serial, command, binary and input
  pins are retained. This is QEMU parameter/timer evidence, not physical PSCI
  or WFI execution proof, and adds no device observer or canary behavior.
- The 32 actual-C PHY cases and four negative cases are reused from complete
  immutable raw evidence, with unchanged checker, fixture, PHY source, DT and
  compiled object. The retained review keeps its original producer provenance.

Final independent artifact review returned `PASS_GO` with no findings, binding
100 sources and 349 artifact/raw pins. It verified the single compiled integer
parameter entry and its actual storage/consumer, the Image's embedded config,
both VM parameter transcripts, preserved provider code, complete authenticated
VM evidence and fresh init/loader/AP joins. The existing capability and backend
V27 receipts are reused without a policy, selector or old-receipt repin.
These H0 results do not prove physical boot, USB, standby or automatic recovery.

Unmocked production image/task consumers and the connector binding pass. The
new task uses closed ML019's exact original-A recovery evidence. The connected
worker retains V27 and its unchanged stable sources. One fixed preapproval D0
completed; all seven successful, complete raw captures rederived exact
original-A health before approval. The operator then returned the exact finite
approval with attendance and usable Download recovery. N and A each transferred
once. No USB or V1 record proof was obtained; the first recovery-health procedure
closed original A healthy without a health-only continuation. The approval and
grant are consumed, and no F1 owner remains. The linked run report records the
separate physical result; H0 qualification did not supply its authority or
permit replay.

An authenticated response would establish the RAM PID1/USB milestone under
this configuration, without proving idle was historically causal. Endpoint
visibility without authentication remains insufficient. Absent USB or V1
records would remain `NO_PROOF` with an unknown cause after original-A closure.
No new observer, park experiment or watchdog audit is an admission prerequisite.

The watchdog alternative remains unresolved. Retained guest-object defaults,
hypervisor-owned timeout values and separate hardware banks do not establish
a current HLOS servicing obligation or deadline. The two advisory models'
initial causal and permanent-exoneration claims were corrected in round two.
No firmware UID guard is bypassed and no watchdog call is introduced.

Applicable past-failure rows are ARTIFACT, SEMANTIC, WIRE, ROUTE, PERSIST and
RETURN: exact config/source/package joins, narrow interpretation, real raw
consumers, unchanged owner routing, durable evidence and original-A recovery.
The exact finite attended approval and current effect-time checks are still
required before a physical run. A90, S20+ and unrelated initial files remain
untouched.

Private preparation is under
`workspace/private/outputs/s22plus-mainline-ml020-h0-20261104-1/`; discussion,
the rejected config probe and provider-consumer evidence are under
`workspace/private/outputs/s22plus-ml019-next-discussion-20261104-1/`.

## External discussion accounting

All four calls completed without retries, fallback or tool invocation. Claude
reported four uncached input, 26,889 cache-creation input and 16,488 output
tokens, including 11,198 thinking tokens. Its five-hour account meter moved
from 11% to 13% used. Argon reported 42,659 input and 15,219 output tokens,
including 11,139 thinking tokens, for 57,878 total; weekly remaining moved
from 93.79% to 92.18%. Before/after records are private. These account-wide
changes are distinct from per-call tokens. Claude's USD 0.544888 price
equivalent is not a subscription charge; Argon cost was unavailable.
