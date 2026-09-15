# S22+ native session V3

Status: **REVIEW_GATED_CAPABILITY**. Transitions and native observations require
a current independent `PASS_GO` and an actual returned finite operator grant.
The separately adopted [foreground Android storage D0](S22PLUS_ANDROID_STORAGE_CENSUS_V1.md)
requires its reviewed fixed profile and healthy Android entry conditions.

This clean owner is limited to `SM-S906N/g0q/S906NKSS7FYG8`. It replaces the
live orchestration for newly prepared V3 work through the common/target
adoption below. Historical owners, consumed images,
grants, journals and admission records keep their original meanings. No V2
grant or old admission authorizes V3. Definition and review create no grant.

## One task, one owner

The task binds the operator-owned target, physical USB lane, original Android
recovery A, approved native runtime and functional-change scope, recovery mode,
finite elapsed-time and operation budgets. It also identifies the reviewed
host machinery. A fresh candidate is machine-qualified within that scope;
changing its version or hash alone requires no new human approval. Changes to
target, privilege, hardware access, transfer, authentication, recovery or health
semantics require review of those changes. Task scope and budgets never expand
as an effect of candidate preparation, observation failure or host suspend.
The implemented task lasts 60–7200 BOOTTIME seconds and permits one to three
operations. Its initially prepared E is a concrete preview; another freshly
qualified E may be selected within the same approved runtime source closure
and remaining budget. Every E content is globally one-shot in this V3 owner.
The task does not authorize functional native source changes outside that
reviewed closure. A later scope change receives its own scoped review.

The task may bootstrap one fresh N and then perform its authorized N/E/N work.
Bootstrap starts from exact healthy Android and requires attendance. An
explicit deferred-recovery task may perform native-origin operations without
attendance after bootstrap admission. Recovery following an uncertain native
state requires actual attendance. Deferred mode accepts a potentially active
device while waiting; it does not claim automatic stall recovery or quiescence.

The old global target lease and F1 owner sentinel remain shared exclusion
mechanisms. The consumed-candidate registry remains the no-replay authority.
V3 imports neither legacy live owners nor their phase schemas. It uses the
boot-only transport, raw capture, USB generation observer, physical lane
binding and wire algorithms as small shared primitives.

## State transitions and minimum proof

| Operation | Required sequence |
| --- | --- |
| Bootstrap | Healthy A → Download → fresh N → health/DETACH → fresh same-boot health/CONTROL → Download → same N → health/DETACH → fresh same-boot health/DETACH → closed native terminal and N admission |
| Storage census (D0) | Admitted N → fresh authenticated health → fixed LU0 geometry/GPT read → DETACH and actual close → healthy native terminal with a separate census verdict |
| N/E/N | Fresh starting-N health/CONTROL → Download → E → selected E observation/CONTROL → Download → admitted N → one fresh health/DETACH → closed native terminal |
| Android exit | Fresh N health/CONTROL → exact Download → original A → fresh exact rooted Android health |
| Recovery | Stop research → attended exact Download → original A at most once → fresh exact rooted Android health |

Every authentication retains its nonce, authenticated kernel boot identity,
ordinal, fixed root health, raw RX/TX and terminal acknowledgement. DETACH
also requires actual descriptor close. A new installed boot starts at ordinal
one and must differ from previous measured boots. Same-boot reentry requires
the next ordinal, an unused nonce and nondecreasing authenticated elapsed time.
CONTROL acceptance is not Download arrival: measured departure and the new
exact Download generation remain separate evidence before each transfer.
Departure must be observed within 30 seconds and normal Download arrival and
final transfer dispatch within 90 seconds of the original mode-change intent.
AP validation, publication and observation cannot renew those deadlines.

E normally uses one authentication. An explicit reentry experiment uses two,
with DETACH between them. Actual USB reconnect qualification additionally
requires measured departure and a new USB generation on the bound lane, fresh
exclusive-open/holder/property checks and authenticated same-boot reentry.
Closing and reopening an unchanged tty proves descriptor reentry only.
No partial OPEN, AUTH or CONTROL may be retried through reacquisition.

HUD acquisition is an explicit E observation, omitted from bootstrap and final
N health. A complete negative or unavailable optional HUD result does not
invalidate independently proved health. Missing or malformed required health,
uncertain command execution and incomplete raw evidence stop research effects.
Normal return, scientific result, admission, recovery and terminal health are
reported separately.

## Before the first effect

Host privilege setup is completed outside live observation/transfer deadlines.
A root-owned fixed no-argument helper only enumerates holders of the configured
native gadget on the bound PC port. Its polkit rule names one invoking account
and a dedicated polkit action mapped only to that exact program. The readiness
query uses that action without caller-supplied authorization details. It grants
no arbitrary root command. The matching udev
rule excludes only this native gadget family from ModemManager probing.

Before any mode-changing intent, the owner checks the installed bytes and
permissions and uses noninteractive `pkcheck` to establish current readiness.
Every native descriptor acquisition compares the helper's complete census,
exact candidate identity and device generation with the held descriptor.
The permanent host configuration remains installed across phases and is
reported as verified external configuration, never as a released temporary
guard. The helper itself grants no target or device authority.

Initial Android health is a fixed bounded same-boot bracket: ADB inventory,
devpath and properties; numeric root and boot/supporting partition digests;
then inventory, devpath and properties again. It does not require empty pstore
or count unrelated historical marker families. Its original private raw files
stay in their preflight location. Successful preflight is referenced directly
by the operation; it is never copied, relabelled or used as final A health.

A failed host/Android preflight before any device effect records the failure
without consuming operation capacity or creating an F1 owner. It never
extends the original grant deadline. Native observation attempts retain any
consumed authentication and uncertainty even if CONTROL was never attempted.
There is no automatic observation retry.
Immediately before the first native-origin authentication, the owner creates
one exclusive attempt record keyed by the prior closed terminal. That terminal
cannot start another authentication across operations or grants. This records
possible protocol consumption separately from F1 operation capacity; a stopped
read cannot make an old terminal fresh. Admission and prior-tail consumers also
compare the original physical target and Android A with the new task.
The native attempt retains the shared recovery owner even before CONTROL.
An uncertain OPEN, authentication or required-health read closes research and
permits only the original attended one-shot A recovery. Mode-changing operations
are charged at their first mode-changing intent; a storage census is charged
when its native attempt begins. Neither authorizes another native read after
uncertainty. Pure host/Android
preflight failures occur before that attempt and retain no recovery owner.

## Fixed storage census

The separately adopted Android D0 entry reads through existing Android block
nodes after a proved closed original-A return. It shares the GPT decoder and
reviewed host primitives, not the old transition grant. Its exact foreground
authority and transcript are defined in the linked Android profile above.

`S22PLUS_NATIVE_STORAGE_CENSUS_V1` is the fixed `storage-census` operation on
an already admitted N. The existing health session issues one additional
authenticated EXEC and ends with DETACH, never normal CONTROL or AP transfer.
The decoded script selects exactly one userdata node, verifies its FYG8 UFS
controller/LU0 ancestry and block-device identity, checks 4096-byte logical
blocks and capacity, then captures six primary and five final metadata blocks
between matching geometry records. The command uses only input reads; it has
no block output operand or write ioctl. It reads no userdata files or keys.
The native runtime uses tmpfs `/dev`, so the command creates one mode-0400
block-node alias `/dev/.s22-gpt-$$` in the existing `/dev` tmpfs using the
verified parent's device number. Its shell-PID path must not exist. Only after
successful creation is cleanup armed for that path; success removes it before
the final marker. A failed command retains an unproved cleanup result and
does not issue another command to clean up. This alias changes no storage or
root privilege and disappears on the original-A reboot if recovery is needed.
The `/s22-root-work` cwd stays unchanged; its `nodev` restriction is preserved.

The readable fixed script and its literal gzip/base64 transport encoding are
checked for byte equality. Encoding fits the existing 767-byte command limit;
it grants no caller script and changes no native runtime bytes. ARM64 BusyBox
decoding, shell syntax and exact dd input counts are validated in H0 fixtures.
The one-command timeout is ten seconds within the original observation and
task deadlines. If the remaining observation cannot admit it, the census is
explicitly unproved; no deadline is extended.

`PASS_METADATA_ONLY` requires the full protective MBR, primary and backup GPT
headers/entry arrays inside the declared capture, valid CRCs, matching tables,
nonoverlapping extents and exact userdata/sysfs agreement. Metadata and unique
identifiers remain private. A completed negative command or malformed dataset
is `NO_PROOF` independently of authenticated health and DETACH. Uncertain
protocol delivery uses the existing original-A recovery and no-replay rules.
These read bounds define this capability; a different GPT shape requires a
reviewed read-profile change, not an inferred wider block read. No census result
qualifies partition-write recovery or activates GPT changes or formatting.

## Effects, closure and recovery

The owner publishes a durable intent immediately before each effect. The
transport's final callback runs after AP/tool validation and rechecks the
original grant and exact endpoint before the claim and launch intent. Once an
intent exists, failure or ambiguous delivery cannot make that effect fresh.

Any uncertain mode-changing effect closes research for that operation. Only
its original one-shot A recovery may continue from the journal. A failure
before A dispatch may wait for the required physical action; an A dispatch
intent may never be repeated. After a proved A transfer, health acquisition
and H0 reporting may resume without transferring again. Expiry does not
remove recovery authority or restore experimental capacity.
This runner's device effects, including recovery, are restricted to the
original host boot. A host OS restart permits H0 evidence reconstruction but
requires a separately reviewed, original-journal-bound recovery route before
another device effect. A new research grant cannot replace that recovery.

A raw-proved final native DETACH or Android health result may be rederived and
published after a host reporting interruption. Reporting failure never triggers
another transition. The F1 owner is retired only after a verified terminal.
Original open evidence, actual descriptor/exclusion closure and raw protocol
completion are recorded separately. A missing aggregate is reconstructed only
from those matching facts. Missing physical-close evidence remains unproved.
Bootstrap admission is derived from both installations and all four required
native observations, never a result flag alone. Retained N keeps its original
artifact and source provenance. Old consumed unadmitted content remains
ineligible even if placed in a new manifest or task.

One structured result, one ordered immutable journal and bounded private raw
captures describe a run. A capability change or incident receives a concise
report. H0 tests cover real protocol producers plus interrupted effects,
publication repair, no-effect preflight failure, expiry and exact recovery.
The independent review covers this reachable owner and its execution-critical
dependencies. This policy creates no extra temporary gate or recovery route.

## Implementation and adoption

The live entry point is `s22plus_native_task_v3.py`; ordering is owned by
`s22plus_native_session_v3.py`, with fixed I/O in
`s22plus_native_adapter_v3.py`. The independent capability review binds the
reachable Python closure, common/target/policy inputs, the host installer and
the approved native producer/source closure. Original artifact provenance is
retained independently from the current host implementation. The H0 exporter
joins the actual A/B build, AP member and authentication key; the live reader
checks those joins against the approved native scope.

The reviewed host installation is a one-time explicit PC administrator action
for five fixed paths, including the dedicated polkit action policy. It is
completed before a task grant opens. An update may replace only exact prior
installation bytes bound by the prior manifest; unknown different destination
content is not replaced. The permanent census exception
authorizes only the fixed no-argument read helper, never the installer.

This common-incorporated and target-adopted V3 scope specializes native N reuse,
bootstrap admission, the native terminal proof count, task budgets and the
explicit deferred-attendance option only for this owner. Ordinary boot-only
boundaries, exact one-shot A, target isolation and uncertainty stops remain.
Recovery evidence is independently reopened from a completed same-target A
transfer and fresh raw rooted Android health; a receipt or ready flag alone is
insufficient. The next live bootstrap still requires current exact Android
health and actual attendance.
