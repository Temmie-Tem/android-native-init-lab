# P362: S22+ native reboot and Samsung Download path analysis

## Result and scope

The investigation identifies a practical implementation path for both ordinary
reboot and Samsung Download, but neither operation is yet proved from the
current native P361 runtime. A command string alone is insufficient: P361 has
no post-display control receive path, the display child has no reboot capability,
and the native load plan omits the Samsung reboot-reason stack present in
healthy Android. This report activates no capability or session.

The operator authorized investigation, including D0/D1 as needed. Work performed
was host source/artifact analysis, disassembly, reference-source research, A90
source comparison and one fixed S22+ D0 module census. No new D1, F1, reboot,
Download transition, module insertion, sysfs write or partition transfer occurred.
Recent exact Android reboot and Download evidence was reused; repeating those
Android operations would not prove the missing native path. A90/S20+ received
no command. Their source examples grant no S22+ authority.

## Evidence already available

- Ordinary Android reboot: the P361 preparation D1 completed one exact normal
  reboot with changed boot ID and exact rooted FYG8/original boot/supporting
  hashes/Android health. Result `2963B/3fc1d384d3fa4f3b6efd7c376a5c29be84631c5d7f8fc3628b9bd31f354bbbb8`.
- Android to Download: P361's F1 entry used the existing exact Android Download
  request and reached the bound Odin endpoint before its sole candidate transfer.
  This is Android control evidence, not native self-return evidence.
- P361 native display: the operator saw repeated clean alternation and final
  first-frame hold. Original execution later stopped on unpublished snapshot103
  USB endpoint-departure evidence. Same-journal rollback-only recovery closed
  healthy. That unexplained incident remains preserved; it is not automatically
  an expected native reboot transition.
- Early native attempt M20A was explicitly corrected to bootloop/manual Download/
  healthy rollback/NO automatic reboot proof. Its helper's endpoint observation
  was not sufficient to attribute a software reboot. Earlier M4T3/M9A narratives
  likewise do not qualify the current runtime; source, execution stage and
  attribution differ.

## 1. Ordinary reboot

The local FYG8 kernel source provides:

`reboot syscall -> CAP_SYS_BOOT and PID-namespace checks -> kernel_restart ->
reboot notifiers -> device_shutdown -> syscore_shutdown -> machine_restart ->
restart handlers -> PSCI SYSTEM_RESET (or supported warm SYSTEM_RESET2)`.

`LINUX_REBOOT_CMD_RESTART` passes a null command; `RESTART2` copies a bounded
string before taking the same kernel restart path. The string does not directly
reach PSCI. The PSCI handler selects reset type from reboot mode and firmware
support, then calls firmware with zero arguments. The actual P361 Image contains
CONFIG_ARM_PSCI_FW=y and matching PSCI handler instructions. This makes ordinary
reboot structurally plausible; it does not prove that all shutdown callbacks
complete on the device in the experimental state.

A normal reboot does not restore Android. The experimental boot partition stays
installed, so a normal restart boots that candidate again. A first native reboot
qualification must establish a changed boot ID/new boot, issue no second reboot
or replayed display workload, and then take its separately defined Download or
attended rollback route. A new CDC endpoint alone can also be a gadget reset,
so endpoint reappearance is not sufficient reboot proof.

The Linux syscall requires reboot capability in the relevant user/PID namespace.
AOSP init similarly uses RESTART2 with a target string; its property/service
shutdown path belongs to Android and is not present merely because a native
CDC ACM endpoint exists. See [Linux reboot API](https://man7.org/linux/man-pages/man2/reboot.2.html)
and [AOSP RebootSystem](https://android.googlesource.com/platform/system/core/+/refs/tags/android-13.0.0_r49/init/reboot_utils.cpp).

## 2. Samsung Download is a reboot-reason path

In the local Samsung source, the strict `download` command maps to
PON_RESTART_REASON_DOWNLOAD. `sec_qc_rbcmd` dispatches it to the registered
Samsung reason writer; `sec_qc_qcom_reboot_reason` writes the named restart_reason
NVMEM cell, with bounded write/readback handling. Empty/null/adb-prefixed normal
commands instead select the normal-boot reason. The underlying reset still
uses the kernel restart path. The NVMEM core returns a written byte count,
matching this vendor writer's positive-return check.

Important distinction: `qcom-dload-mode` handles `edl` and `qcom_dload` dump-mode
requests. Those are not aliases for Samsung Odin Download. Its normal-reboot
notifier clears dump mode. It is also a symbol dependency of the Samsung reason
writer. Its probe can configure dump behavior, so loading that module is not a
pure readiness observation and must be included in future F1 qualification.
No EDL, raw PMIC/NVMEM/MMIO write, BCB write or dump command was attempted here.

The stock vendor configuration marks the relevant reboot drivers as modules.
A fresh D0 census found the following modules loaded in healthy exact Android;
the corresponding native P361 plan includes only qcom-scm from this table:

| Module | Healthy Android D0 | P361 planned load |
| --- | --- | --- |
| sec_reboot_cmd | present | absent |
| sec_qc_rbcmd | present | absent |
| sec_qc_qcom_reboot_reason | present | absent |
| qcom-reboot-reason | present | absent |
| qcom-dload-mode | present | absent |
| qcom-pon | present | absent |
| reboot-mode | present | absent |
| nvmem_qcom-spmi-sdam | present | absent |
| qcom-scm | present | present |

This is a candidate missing-function/provider set, not a reviewed instruction
to load every row. The next H0 implementation must determine the smallest
symbol and live device-tree provider closure. Retained stock modules.dep links
the Samsung writer to sec_qc_rbcmd, sec_reboot_cmd, qcom-dload-mode, qcom-scm,
minidump and smem. NVMEM/PMIC provider binding adds dependencies not expressed
by symbol linkage alone. qcom-scm/minidump/smem are already represented in the
current native plan. Current stock module presence is not proof of each
module's successful binding or of their native load-order sufficiency.

The hash-bound stock base/overlay audit applied both applicable bases to all
11 overlays (22 merges). The selected reboot/PSCI/SDAM nodes are available in
all merges and their inspected properties agree; PSCI method is smc. Local
references in all 11 overlay blobs link both restart_reason and pon_reason to
available qcom,spmi-sdam providers. The restart_reason cell is required by the
Samsung writer; pon_reason is an optional debugging read in that implementation.
This narrows provider work without proving actual native probe completion.

## 3. The USB owner must handle control

P361's actual generated parent runtime authenticates and consumes one display
dispatch, then supervises the child. While display is active it drains local
output and checks the deadline, but deliberately skips the cancel/control
receive path. When the child ends it returns the terminal protocol error rather
than accepting a next command. There is no existing `reboot` or `download`
command to send to this display session. Its CDC ACM endpoint is not adbd.

The display child closes the inherited TTY, drops to UID/GID65534, clears all
capability sets and sets no_new_privs. Reboot belongs in the privileged native
supervisor/control owner, outside that child. The renderer should remain
unprivileged. A fixed authenticated control frame can be handled while the
supervisor continues its existing bounded child monitoring; a new generic shell
or proxy is not needed merely to receive two fixed actions.

The necessary new behavior is a reviewed fixed `reboot`/`download` command path,
with host intent durable before dispatch, one-shot consumption, authentic
request parsing and a bounded syscall-return failure report. A pre-effect
acknowledgment proves only request acceptance. Physical reset/Download arrival
must be observed separately. The prior stop behavior and failed raw snapshots
cannot simply be converted into successful expected transitions.

## 4. A90 comparison

The inspected A90 working-tree implementation in native-init/v319 provides useful
API examples: `handle_reboot` stops its HUD, syncs and calls RB_AUTOBOOT;
`cmd_recovery` calls RESTART2 with `recovery`. The former also contains a SysRq
fallback; this investigation does not copy or authorize that fallback for S22+.
These source examples are not fresh A90 live proof, and a recovery command is
not evidence of Samsung Download behavior on another device.

The A90 contract's fixed TWRP System-reboot hook includes its special 256-byte
misc handling. That is a different recovery-to-system problem and an A90-only
exception. It is not required or transferable for the S22+ Samsung reason-driver
approach. The useful common pattern is native-owned privileged control separated
from a display/HUD child; device-specific reason handling remains separate.

## 5. Disassembly and artifact limits

The current P361 Image was hash-verified before inspection. A retained P310
vmlinux supplies reference function locations. Byte comparison proved exact
matches for psci_sys_reset and kernel_restart_prepare. An initial assertion
that all five reference functions would match failed: __arm64_sys_reboot,
kernel_restart and machine_restart differ by 3, 8 and 2 bytes respectively.
Those deltas are preserved privately. Full reference-vmlinux identity is not
claimed; the affected functions were separately disassembled from current Image
slices. The PSCI reset handler's actual decoded instructions select the two
reset function IDs and zero argument registers, matching the source behavior.
No rebuild or binary patch was performed to force identity agreement.

This establishes code-path evidence, not live native reboot proof. The earlier
native raw-reboot failures do not prove the current PSCI path will fail, and
current static matches do not erase those earlier unproved results.

## 6. Smallest next implementation and qualification

1. Add fixed supervisor-owned reboot and Download request parsing; preserve
   authentication, one-shot accounting and the unprivileged display child.
2. Qualify the smallest reason/NVMEM provider module closure from exact build
   artifacts and device-tree binding, including module-init side effects and
   defaults. Keep ordinary reboot and Download classifications distinct.
3. First attended native qualification: request one normal reboot, prove a new
   boot without repeating the command/workload, then complete the predeclared
   exact rollback. A normal restart by itself is not Android restoration.
4. Separate attended Download qualification: accept one authenticated request,
   observe fresh exact Odin Download, roll back once and verify Android health.
5. Repeat recovery qualification with the display child exited and stopped,
   while kernel/PID1/USB and the fixed display-driver path remain unchanged.
   Kernel/USB/driver deadlock is not proved recoverable by a child-stop test.

Only after those actual failure-specific results should a finite automatic F1
scope be reviewed and activated. This investigation changes no target/common
contract, runner, schema, production C or consumed source closure. It builds no
F1 candidate and creates no approval token.

## Private evidence and validation

Evidence root: `workspace/private/outputs/s22plus_fyg8_p362/`.
D0 run: `workspace/private/runs/device-action-d0-p362-reboot-analysis/stock-module-census-20260907-1/`.
The fixed census read /proc/modules once between exact same-boot healthy
snapshots under the existing shared target lease. All 482 module names were
parsed privately; raw module addresses and identifiers remain private. No
other-target command, write, reboot or Download transition occurred.

Source/tool/artifact identities, disassembly receipts and D0 result identity
are recorded in the private analysis receipt. Analysis-script syntax passed. D0 result identity:
`10988B/181713a10ead327211c0ffa28e82dfa84b5d2096df005a472b6277f457bfbfd4`.
Private analysis receipt SHA-256:
`d92c712ffb416d5b2856e2fed940e54124ceb45a090a554aa9ecac22673a9e4f`.
Source/result/tool receipt revalidation, document links, token exclusion,
repository boundary check and git diff --check passed.

## Follow-up: smaller module set and control/readiness details

The operator clarified that rebooting the same native PID1 is an intentional
feature, and renewed D0/D1/root-read authorization. Ordinary native restart and
Download return should remain two distinct fixed actions. The former returns
to the installed candidate; only the latter enables the subsequent exact boot
rollback. No new live control action was taken during this follow-up.

### Five added modules resolve against the current Image

Three Samsung module files were acquired through fixed root D0 reads and matched
the FYG8 module inventory hashes. The remaining needed artifacts were extracted
host-only from the stock vendor_boot image whose complete SHA-256 matches the
latest final-health binding. The retained native module set was reverified
unchanged against its existing union audit.

Adding these five modules to the current set gives an acyclic 87-module graph:

| Added module | Direct module dependencies reported by its actual ELF |
| --- | --- |
| sec_reboot_cmd | none |
| sec_qc_rbcmd | sec_reboot_cmd |
| qcom-dload-mode | qcom-scm, minidump (already in the native set) |
| sec_qc_qcom_reboot_reason | sec_qc_rbcmd, qcom-dload-mode |
| nvmem_qcom-spmi-sdam | none; its live PMIC/SPMI provider still matters |

All 4,532 imported symbol/version entries resolve to exactly one provider with
a matching CRC against the actual current Image and module exports. There are
zero unresolved or mismatched imports. This is H0 linkage evidence, not proof
that the five modules probe or reboot correctly in native runtime. The larger
stock comparison table above is not an installation list: qcom-pon,
reboot-mode and generic qcom-reboot-reason are not required by this selected
Samsung Download symbol/provider path. Other reboot targets could differ.

### Module return is not command readiness

The actual sec_qc_rbcmd ELF has the kthread creation/wakeup calls found in the
source. Its platform probe spawns a director thread that registers the command
tables and returns without waiting for those registrations. Thus finit_module
success, /sys/module presence, or a bound sec_qc_rbcmd platform driver alone
cannot prove the Download handler is ready.

The source already exposes a read-only sec_reboot_cmd debugfs listing containing
stage, default handler and registered commands. A future readiness observation
can check the intended reboot-notifier stage, its default and exact download
registration, together with the synchronous Samsung writer/provider binding.
Raw output includes pointer/symbol fields and must stay private or be reduced
inside native code. This is a candidate observation design, not an activated
new gate. Debugfs availability and the actual producer must be qualified first.
No arbitrary fixed sleep should stand in for registration evidence.

Actual qcom-dload-mode disassembly also confirms calls to
qcom_scm_set_download_mode and qcom_scm_disable_sdi in parameter/probe paths.
The stock default enables dump behavior; choosing download_mode=0 also invokes
firmware-side operations. Neither loading the default nor overriding it is a
passive read. These initialization effects belong in the next capability review;
there was no module insertion, parameter write or SCM invocation in this work.
Registering the Samsung secondary-reason writer also immediately writes its
default SEC_DEBUG_MODE reason, before any explicit reboot request.

### Existing boot identity has narrower semantics

The current authenticated wire boot_id is generated by
p335_getrandom_boot_id from getrandom at native publisher entry. A separate
fresh device-generated session nonce authenticates each session. This supports
the existing logical-runtime continuity contract, but the wire field is not
/proc/sys/kernel/random/boot_id and must not silently be relabelled as that
kernel value. Existing consumed evidence is unchanged.

For a new normal-reboot qualification, explicitly authenticate the kernel boot
ID (or its canonical digest) before and after the restart, and require it to
change. Keep the fresh session challenge and the host's durable consumed action
ordinal. Do not issue the restart/display command again merely because a new
connection appears. This can reuse the existing framing/journal concepts;
it needs no persistent boot marker or counter written to a partition.

### Keep return control independent of child cleanup

The current supervisor bounds kill/reap and process-group cleanup to one second,
but deliberately stops its display session and parks afterward. Its display
loop also skips cancel/control reads. Simply adding reboot to the ordinary shell
command allowlist would not make it reachable while a display action is active.

The next implementation should dispatch a fixed authenticated control frame
from the supervisor's existing nonblocking loop, independently of renderer exit,
and preserve access to preapproved return handling after normal display
completion. Partial or invalid control input must produce no reboot; duplicate
or stale requests must not create another effect. A syscall that returns is a
failed/uncertain return attempt, not permission to try SysRq or another reboot.
Child exit/stop tests qualify only that failure class. An uninterruptible driver
operation or kernel shutdown deadlock remains a separate unproved recovery case.

### D0 failures and final health are preserved

The first non-root artifact read produced Permission denied. That invocation
stopped before acquiring an ELF and retained its raw output and stop receipt.
A fresh fixed root-read invocation acquired the three Samsung modules, then
stopped when qcom-dload-mode.ko was absent from /vendor/lib/modules. The missing
file was not treated as an absent loaded module; it was sourced from the exact
stock vendor_boot artifact offline. No failed read was retried inside its closed
invocation, and no device file was written.

A final D0 health-only observation passed, with the same kernel boot ID as the
original P362 census and exact rooted FYG8/original boot/supporting hashes/Android
health. Result `910B/ea3ca3af37dd3913c573648f9dd68a977fc7e138367ed96880943b140c1b767f`.
All work remained H0/D0; no D1, F1, candidate build, activation or production
runtime edit occurred. A90/S20+ were not commanded.

Follow-up evidence: `workspace/private/outputs/s22plus_fyg8_p362/followup/`.
The acyclic graph, 87 module identities, import results, actual disassembly,
source hashes and D0 failure/health receipts are retained there. Follow-up
receipt SHA-256:
`8258dbea4ad7c202ef0de6d5bf423210273befee58e223b12463dc937b6b16d0`.

Follow-up receipt revalidation, private script syntax, document links, token
exclusion, repository boundary and diff checks passed.
