# ML027: authenticated normal Download return from packaged Debian RAM

Status: **H0 QUALIFIED / INDEPENDENT PASS_GO / PREAPPROVAL D0 VERIFIED / NOT EXECUTED**.

Following ML026's same-boot packaged Debian PID1 and fixed unprivileged SSH
success, two discussion rounds each with Claude and Argon selected normal
Download return as the next useful bounded capability. The first round differed
on whether to extend RAM services first; both final responses selected Download
after the exact reboot-mode source and retained stock cell were checked.
The four advisory calls, actual model outputs and separate before/after quota
and token accounting are private. Advisory agreement is not execution review
or device authority. No further external calls were needed for implementation.

## Selected behavior and source evidence

This candidate uses the four signed-package Debian RAM SysVinit closure and
its direct observer child. It adds one fixed authenticated control on the same
connection that supplied complete sealed base evidence. It is distinct from
the SSH variant and exposes no general command. Full base proof precedes the
fresh Session intent and the only control send. The command and ACK bind the
candidate, nonce and measured boot ID. Uncertain sends never replay.

The device's exact reboot-mode class output and driver/OF-node links must
match. The current kernel's show function includes a trailing NUL after its
newline; the actual function body was compiled and exercised to establish the
expected bytes. After ACK and write-half shutdown, the observer requires EOF
without extra bytes, rechecks readiness and the original deadline, then calls
one `RESTART2("download")`. A returning syscall parks without another reset.
ACK and EOF do not prove reset, Download arrival or verified host receipt.

The sole DT change adds `mode-download = <0x15>` to the existing NVMEM reboot
mode. The actual stock strict-command table and its CFI relocation, retained
stock DT, mainline source and unchanged kernel configuration join the same
PMK8350 SDAM byte and seven-bit reboot-reason field. The existing bitfield
write preserves bit 0. Existing SCM NODUMP shutdown and cold-default PSCI
SYSTEM_RESET remain separate parts of the normal chain. No vendor module,
new SMC, raw NVMEM writer, warm-reset override or Linux storage access is added.
The notifier does not propagate a cell-write failure to abort reset, so a
mislanding remains possible. Registration proves neither the actual write nor
firmware consumption/clearing; attended physical recovery remains necessary.

An operation-local lock coordinates the existing conditional replug cue with
normal control. An issued cue is durable before emission and requires its
actual completion or explicit cancellation before control. No issued cue
closes issuance immediately without another human question. Waiting retains
the original observation deadline; late actual resolution can still be
recorded without renewing it. Historical evidence rechecks do not require the
current host boot to equal the execution host boot. Live binding still does.

Normal return automatically waits for a machine-bound Download arrival,
transfers original A once and obtains complete final rooted Android health.
The arrival deadline is fixed at control intent to 600 seconds, capped by the
original grant. A health-only continuation may complete that same normal A;
physical recovery cannot substitute for normal-return success. A failed control
may retain independently proved base PID1/USB while the Download unit closes
NO_PROOF. The original host/device observation windows remain distinct.

## Qualification and corrections

The final physical and VM observers were built from the corrected C source,
and the physical binary was identified as static ARM64. The kernel config and
PHY patch are unchanged from ML026; the DT delta is only the selected mode.
Fresh candidate/key/marker identity, the complete signed CPIO, loader guards,
actual EL1/EL2 loader entry, retained-marker fixtures and A/B boot-only envelope
were qualified. Existing completed outputs were reused while their inputs
remained unchanged.

The independent reviewer also ran the complete real initramfs producer with
each retained key and the original input paths/bytes. Both variants reproduced
the candidate ID, seal, observer ELF, packaged PID1 and complete CPIO exactly.

The same kernel in QEMU proved packaged RAM PID1 and the authenticated control
through an actual guest-requested reset. A QMP channel issues only
`qmp_capabilities` and distinguishes guest reset from host termination. Six
actual observer negatives cover wrong control key, wrong boot, legacy magic,
extra tail, partial control and missing EOF through the original deadline.
A separate wrong-request-key case returns no base proof. All passed.
The selected VM captures retain their original producer snapshots. The current
checker adds only the stricter shutdown-event assertion distinguishing guest
reset from host stop; all retained raw cases rederived under that checker.
No capture was repinned or rerun merely for this checker-only change.
QEMU's readiness fixture is explicit and has no Samsung PMIC or Download-mode
proof. Seventeen ARM64 C cases exercise the actual ready/control code with
mocked syscalls, including final deadline expiry, lost binding and a returned
reset syscall. Host tests exercise sealed framing, production result/terminal
consumers, cue races, no replay and original-A recovery with an unavailable
candidate checker. The complete current mainline suite passed 174 tests;
the focused native Session suite passed 21 tests.

Interim independent review found and corrected a codec-call error, candidate
checker failures blocking original-A recovery, a missing final clock check,
blocking lock acquisition/repeated full guards, improper rejection of late
actual cue resolution, and a current-host-epoch requirement in historical
rechecking. The final C bytes were rebuilt after those changes. Earlier C and
build artifacts remain explicitly superseded with their source provenance.

The first VM reset oracle expected a kernel printk on the observer's console,
although the kernel console differed. Its raw ACK and successful QEMU exit
were retained; the corrected oracle uses actual QMP guest-reset evidence and
was rerun without changing the candidate. A private copied release-path error
was corrected while preserving its incomplete preparation. A private fixture
receipt initially attempted to use a nonempty-record pin for empty stderr;
empty raw files remain in the review packet, and the fixture receipt names
nonempty evidence. No acceptance assertion or device effect was bypassed.

## Scope, review and preparation

The target and mainline policy adopt this exact normal-control variant. Common
permanent boundaries remain unchanged. Existing review receipts, consumed
ML026 approval/journal and retained artifacts keep their original identity;
the changed source closure received a new capability/backend review. The stable
transport worker remains unchanged. Final independent review returned
`PASS_GO` with no findings against 113 source pins and 527 artifact/raw/advisory
pins. Its isolated real qualification, image binding, task preparation and
current terminal bundle passed with acquisition, USB, sockets, process launch,
readiness, grant and start effects blocked. Missing human approval was rejected.

The reviewed publication helper then created the new Download capability and
backend V32 receipts, exact image/task/proposal and connector preparation.
Actual production admission accepted the original image and rejected twelve
mutations covering missing/cross modes, runtime/key identity, physical/VM
manifest joins, incomplete or misjoined control evidence, a false physical
proof claim and incorrect source/fixture bindings. These reached their intended
consumer checks before generic independent-coverage rejection. Five retained
real CPIO negatives were also rejected by the current checker; the unchanged
original remained valid.

The connected worker verified backend V32 and unchanged resident sources.
One named fixed foreground D0 then completed. An acquisition-blocked audit
rederived all seven successful Android health captures, empty stderr, exact
task/current capability and no F1 owner. No approval, grant or operation was
created. Readiness is a point-in-time observation: grant opening still checks
its original 300-second freshness and current effect binding. Source, artifact,
capability/backend and worker pins remained unchanged after these checks.

The prior 798-line goal was archived byte-for-byte under
[the ML026 snapshot](../archive/roadmaps/GOAL_THROUGH_ML026_MAINLINE_RAM_2026-11-05.md).
The current goal retains product direction, proved limits and this selected
unit. The byte-identical snapshot's links retain their original repository-root
context; active-document links were checked from their current locations.
No historical approval is renewed. Applicable past-failure checks cover
actual ARM64 constants/producer-consumer behavior, raw-before-parse ordering,
effect-time binding, source versus artifact provenance, deadlines, stage
ordering and no replay. Marker-retention causality and unrelated target/root
admission work do not gate this bounded capability.

Physical success requires `PASS_MAINLINE_DOWNLOAD_RAM`: same-boot authenticated
base/control evidence, exact normal Download arrival and original-A/full final
health. This does not prove full SysV shutdown, automatic stall recovery,
unattended execution, Linux UFS, installed/persistent Debian or residency.
No ML027 device control, transfer or grant has occurred. A90 and S20+ are
untouched; unrelated existing dirty files are preserved.

Private artifacts and complete raw evidence are under
`workspace/private/outputs/s22plus-mainline-ml027-download-return-h0-20261105-1/`;
the four advisory responses and source/cell audit are under
`workspace/private/outputs/s22plus-ml026-next-discussion-20261105-1/`.
