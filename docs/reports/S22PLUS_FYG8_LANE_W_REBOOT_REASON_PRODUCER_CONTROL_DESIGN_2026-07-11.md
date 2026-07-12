# S22+ FYG8 Lane W Reboot-Reason Producer Control Design

Date: 2026-07-11 KST
Target: Samsung Galaxy S22+ `SM-S906N` / `g0q` / `S906NKSS7FYG8`
Scope: host-only static analysis and design; no candidate build, image generation,
device contact, reboot, flash, or live authorization

## Verdict

Lane W now has a bounded producer/control design, but it is not ready for a
candidate build or live run.

The earlier seven-module `modules.dep` closure is necessary but not sufficient
for direct PID1. `sec_qc_qcom_reboot_reason.ko` obtains a `restart_reason` nvmem
cell at probe time. On FYG8, that cell is provided by
`nvmem_qcom-spmi-sdam.ko`, which is also modular, and the SDAM platform children
are populated only after the modular SPMI controller/PMIC stack binds.
`modules.dep` cannot express this device/provider probe dependency.

An independent review found a second hidden condition. The
`sec_qc_rbcmd` platform probe starts command registration through
`kthread_run()` and returns before that worker completes. A platform-driver
symlink therefore proves neither that `download`/`recovery` handlers are
registered nor that the worker succeeded. Exact FYG8 has `CONFIG_DEBUG_FS=y`,
and `sec_reboot_cmd` exposes its actual registered command lists in
`/sys/kernel/debug/sec_reboot_cmd`; that read-only list is the required
readiness oracle.

The corrected native control family must therefore combine:

1. the M31B watchdog closure already live-proven to survive 120 seconds;
2. the SPMI/SDAM provider closure;
3. the Samsung command parser and PON-reason writer closure;
4. `qcom-reboot-reason.ko` only to provide a matched Recovery-mode control.

The future run order is `W0 park -> W1 recovery -> W2 download`. W2 cannot be
classified from an Odin endpoint alone. It is positive only if W0 first excludes
same-image load/auth fallback and W1 proves the same nvmem/reset substrate can
select a different ABL sink.

## Source-Proved Producer Path

The exact source chain is:

```text
reboot(RESTART2, command)
  -> kernel_restart(command)
  -> reboot_notifier_list
  -> sec_reboot_cmd strict parser
  -> sec_qc_rbcmd_set_restart_reason()
  -> sec_qc_qcom_reboot_reason PON writer
  -> restart_reason nvmem cell
  -> PMK8350 SDAM register 0x7148
  -> reset
  -> FYG8 ABL ResetRuntimeDxe/LinuxLoader consumer
```

Relevant exact-source facts:

- `sec_qc_rbcmd_command.c:393-399` maps exact `download` to
  `PON_RESTART_REASON_DOWNLOAD`.
- `sec_qc_rbcmd.h:22-24` defines normal boot `0x14` and Download `0x15`.
- `sec_qc_qcom_reboot_reason.c:161-214` writes one byte, reads it back, and
  retries up to five times.
- g0q DT enables the Samsung reboot notifier at priority 250 and gives the
  writer both `restart_reason` and `pon_reason` nvmem cells.
- `qcom-reboot-reason.c:28-58` provides the distinct standard Recovery reason
  `0x01`, with notifier priority 255.
- `sec_qc_rbcmd_command.c:343-362,455-460` deliberately treats `recovery` as a
  Qualcomm pre-defined command: Samsung updates only its internal `sec_rr` and
  does not overwrite the PON reason written by `qcom-reboot-reason`.
- exact FYG8 LinuxLoader maps `0x01` to Recovery and `0x15` to Odin/Download.

The exact ABL Recovery control is independently closed against LinuxLoader PE
SHA256
`b1ee37a2be13a557fa05a6e603fa81c827b3d8be410df1a61145f050c67cde28`:

```text
PON reason 0x01
  -> table RVA 0xf40ec, entry 0x001f
  -> branch target RVA 0x4aca0
  -> mov w19, #2
  -> caller at RVA 0x4bf2c receives mode 2
  -> mode-2 branch logs "Recovery Mode, Reset param!"
  -> returns boot mode 2
```

The table address was recomputed from the AArch64 `ADRP` encoding at RVA
`0x4ac0c`, not inferred from nearby data. The same table gives normal reason
`0x14 -> 0x4ace8` and Download reason `0x15 -> 0x4ad08`.

The writer's cell is under PMK8350 `sdam@7100/restart@48`. The exact FYG8 vendor
configuration has `CONFIG_NVMEM_SPMI_SDAM=m`. `qcom-spmi-pmic.c:152` performs
`devm_of_platform_populate()`, and only then can
`nvmem_qcom-spmi-sdam.ko` bind the SDAM child and register its nvmem provider.

## Existing Stock Ground Truth

The repository already contains the producer positive and generic-reset control
that the prior report had not pinned.

### Stock Download positive

Artifact:

```text
workspace/private/runs/s22plus_v3430_phase_observer_20260710T121509Z/
  first_boot_last_kmsg_1.bin
SHA256 4081a8389310caed3b95effd7cd46586828a7f808dc2985f4c7b32a8c2b95db0
```

Contiguous retained lines prove:

```text
cmd : download
power on reason: 0x00000015
0x15 is written successfully. (retry = 0)
reboot mode: 0xFFFFFFFF
set_dload_mode <0>
```

This is a real FYG8 stock-kernel producer proof, not merely a later Odin
endpoint. It proves the shipped modules, DT, nvmem provider, and PMIC write path
work when normal Android has loaded them.

### Stock generic-reset control

Artifact:

```text
workspace/private/runs/s22plus_o3r1_native_retained_sysrq_live_gate_20260709T221905Z/
  android_pstore/postrollback_o3r1_last_kmsg.bin
SHA256 8069cece37209ce7ded62dc8ffc5d4405b9fb8cbe9020608a762e30baadd21ee
```

Contiguous retained lines prove:

```text
cmd : userrequested
power on reason: 0x00000014
0x14 is written successfully. (retry = 0)
reboot mode: 0xFFFFFFFF
set_dload_mode <0>
```

The paired host log reports `sys_boot_reason=reboot,userrequested`. This proves
that the same stock producer writes normal-boot `0x14` and returns to Android.
It is the generic-reset semantic control. Repeating that command from a
persistent native boot candidate is not selected for live use because the same
candidate would reboot again and create an unbounded reset loop.

## Corrected Native Runtime Closure

`modules.dep` gives the hard symbol closure, while source/DT gives the additional
runtime provider closure. The proposed deterministic order preserves the exact
M31B prefix that already survived 120 seconds:

```text
 1  smem.ko
 2  minidump.ko
 3  qcom-scm.ko
 4  qcom_wdt_core.ko
 5  gh_virt_wdt.ko
 6  regmap-spmi.ko
 7  qti-regmap-debugfs.ko
 8  spmi-pmic-arb.ko
 9  qcom-spmi-pmic.ko
10  nvmem_qcom-spmi-sdam.ko
11  qcom-dload-mode.ko
12  sec_reboot_cmd.ko
13  sec_qc_rbcmd.ko
14  sec_qc_qcom_reboot_reason.ko
15  qcom-reboot-reason.ko
```

Roles:

| Group | Modules | Reason |
|---|---|---|
| watchdog floor | 1-5 | preserve M31B's live-proven 120-second survival |
| nvmem provider | 6-10 | instantiate PMIC children and register `spmi_sdam` |
| Samsung producer | 11-14 | parse `download`, write/read-verify `0x15`, reset |
| alternate sink | 15 | map `recovery` to `0x01` for W1 only; harmless to W0/W2 |

The 15 exact shipped modules are present in the vendor ramdisk corpus. Their
hashes are already pinned by `docs/module-map/s22plus-fyg8/inventory.tsv`.

## Mandatory In-Candidate Gates

All three variants must reuse one byte-identical compiled init and one
byte-identical module payload. Do not compile three binaries. The only allowed
unpacked ramdisk delta is one owned regular file, `/lane-w-mode`, with exactly
one of three equal-length five-byte contents:

```text
PARK\n
RECV\n
DOWN\n
```

The shared init must open this file read-only with `O_NOFOLLOW`, require a
regular file with the pinned mode/uid/gid and exact size, read exactly five
bytes plus EOF, and select the terminal action only after every common gate
passes. An invalid token parks forever. Both eight-byte reboot command strings
are present in the same binary regardless of selected mode.

Before any terminal action:

1. mount only private `proc`, `sysfs`, `devtmpfs`/minimal `/dev`, tmpfs, and a
   private debugfs used only for the bounded read below;
2. load and gate the closure in dependency phases, preserving the numbered
   order above:
   - load 1-3, then require `/firmware/qcom_scm` compatible `qcom,scm` bound
     under driver `qcom_scm` before loading any SCM consumer;
   - load 4-10, then require an `spmi_sdam` nvmem device whose exact OF node is
     PMK8350 `sdam@7100` before loading either restart-reason consumer;
   - load 11, then require `/soc/dload_mode` compatible `qcom,dload-mode`
     bound under driver `qcom-dload-mode`;
   - load 12, then require `/soc/samsung,reboot_cmd` bound under driver
     `samsung,reboot_cmd` before starting the asynchronous command producer;
   - load 13, then require `/soc/samsung,qcom-reboot_cmd` bound under driver
     `samsung,qcom-reboot_cmd` and pass the debugfs command-readiness oracle;
   - load 14, then require `/soc/samsung,qcom-qcom_reboot_reason` bound under
     driver `samsung,qcom-qcom_reboot_reason`;
   - load 15, then require `/soc/reboot_reason` compatible
     `qcom,reboot-reason` bound under driver `qcom-reboot-reason`;
3. require every `finit_module` return to be `0` or `-EEXIST` and give each
   phase at most 10 seconds to reach its exact readiness predicate;
4. implement every platform predicate by enumerating the exact driver's sysfs
   directory and comparing the bound device's canonical `of_node` and binary
   `compatible` property. Never trust a platform-device basename alone;
5. implement the nvmem predicate by enumerating
   `/sys/bus/nvmem/devices/spmi_sdam*` and comparing its inherited `of_node`
   against the exact `sdam@7100` node and `qcom,spmi-sdam` compatible;
6. for the command-readiness oracle, read at most 64 KiB from
   `/sys/kernel/debug/sec_reboot_cmd`, reject
   truncation, parse only the `Reboot Notifier` section, and require:
   - priority exactly 250;
   - a non-warning default handler;
   - exactly one registered `download` command;
   - exactly one registered `recovery` command;
7. require all expected module names in `/proc/modules`;
8. on any mismatch, timeout, truncation, or unexpected errno, park forever and
   never call reboot.

Do not replace item 6 with a fixed delay. In
`builder_pattern.h:275-308`, `sec_director_probe_dev_threaded()` returns after
creating `drct-qc_rbcmd`; its per-builder results are not propagated through
the platform probe. The debugfs list is protected by the same command-list
mutex and therefore observes the actual completed registration state.

The SCM and dload bindings are not cosmetic. The Samsung reason-writer probe
calls `qcom_set_dload_mode(1)`. The clean-reboot path relies on the bound
priority-255 `qcom-dload-mode` notifier to set `QCOM_DOWNLOAD_NODUMP` before
reset. Without that binding, an RDX/download-mode transition can be mixed into
the intended PON-reason result. A bound `qcom_scm` device is also required
before either set/clear operation is accepted as usable.

The phase barriers are also semantic, not startup padding. In particular,
`__qc_rbcmd_init_on_reboot()` converts an unready `sec_reboot_cmd` singleton to
`-EPROBE_DEFER`, but the enclosing `drct-qc_rbcmd` thread does not schedule a
new platform probe. Loading module 13 before module 12 is actually ready can
therefore leave a permanently bound parser device with no registered commands.

These gates prove readiness inside the candidate but are not by themselves a
host-visible result. The cross-run W0/W1/W2 differential remains mandatory.

## Three-Run Matrix

### W0 - Full-closure park and boot-failure control

- Terminal action: no reboot syscall; park with the M31B 10-second cadence.
- Required observation: no Odin, Recovery, ADB, fast loop, PMIC/RDX reset, or
  operator-visible failure for 120 seconds.
- Meaning: proves the exact candidate family reaches a stable native PID1 and
  does not independently fall into LinuxLoader's load/auth/returned-handoff
  Odin fallback.
- Recovery: attended physical Download entry after the observation window,
  followed by the separately pinned boot-only rollback.

W0 failure stops the lane. W1 and W2 must not run.

### W1 - Matched alternate-reason control

- Terminal action: exactly one `reboot(RESTART2, "recovery")` call.
- `recovery` and `download` are both eight-byte command strings.
- The priority-255 Qualcomm notifier must be bound before the call; it writes
  `0x01`. The priority-250 Samsung parser recognizes `recovery` as pre-defined
  and intentionally does not replace that PON value.
- The debugfs readiness oracle must already contain both terminal commands in
  the priority-250 `Reboot Notifier` stage, eliminating the asynchronous
  registration race.
- Required observation: direct transition to the exact stock Recovery path,
  not Odin and not RDX.
- Meaning: with the same candidate family and closure, proves the nvmem/reset
  substrate can select a non-Odin ABL sink. It also excludes the claim that any
  terminal reboot from this image inevitably becomes Odin.
- Recovery: use Recovery's normal reboot-to-Download operation only as an
  attended rollback step; never count that later Download endpoint as W1 proof.

W1 failure or Odin entry stops the lane as confounded. W2 must not run.

### W2 - Download producer positive

- Terminal action: exactly one `reboot(RESTART2, "download")` call.
- Required observation: Odin endpoint appears within the predeclared immediate
  window and before any manual input.
- PASS requires prior W0 and W1 PASS, exact image-family parity, exact module
  payload parity, and only the terminal mode/string difference.
- Meaning: W0 excludes same-image boot failure, W1 proves the alternate reason
  path, stock retained logs prove the exact FYG8 writer emits and verifies
  `0x15`, and exact ABL RE proves `0x15 -> Odin`. Together these identify the
  producer path much more strongly than a lone endpoint.

An Odin endpoint outside the immediate window, after manual input, or without
W0/W1 PASS is `NO_PROOF_NON_UNIQUE_SINK`.

## Host Gate Contract

Any future implementation must remain fail-closed and one-shot:

- three separately SHA-pinned boot-only APs, each containing only
  `boot.img.lz4`;
- exact shared kernel, boot header, ramdisk modules, compiled init SHA256, and
  every other unpacked ramdisk entry demonstrated by a normalized comparison;
- normalized ramdisk manifests include path, type, mode, uid/gid, mtime,
  device numbers, xattrs where present, size, and content SHA256; only the
  five-byte `/lane-w-mode` content SHA256 may differ;
- compressed ramdisk and boot-image hashes are expected to differ and are not
  accepted as a substitute for the unpacked one-file-delta proof;
- no USB/configfs setup, no Android/Magisk handoff, no persistent filesystem
  mount, no block write, and no partition other than boot;
- no automatic fallback flash to an ambiguous endpoint;
- physical mode observations recorded by the operator and host USB identity;
- mandatory boot-only rollback and final Android/boot identity after each run;
- `timeline.json` uses only `events:[{name,timestamp_utc}]` and contains all
  eight mandatory phases;
- one failure stops the sequence; no retry is inherited from a prior approval.

Candidate building, packaging, connected dry-run, reboot, and flashing remain
unauthorized. A future implementation needs a fresh design review followed by a
narrow SHA-pinned `AGENTS.md` exception and explicit operator approval for each
live rung.

## Consequences

1. The old seven-module list must not be used to build a producer candidate.
2. `qcom-pon.ko` and `reboot-mode.ko` are not part of this producer path; the
   Samsung writer directly uses the SDAM nvmem cell.
3. `qcom-reboot-reason.ko` does not parse `download`; it exists here only for
   the W1 Recovery control. Its `/soc/reboot_reason` probe binding is a hard W1
   precondition, not an optional corroborating check.
4. Platform binding of `sec_qc_rbcmd` is not a command-readiness proof. The
   asynchronous worker and its non-propagated result make the bounded debugfs
   command-list check mandatory for W1 and W2.
5. `qcom-scm.ko` and `qcom-dload-mode.ko` presence is not enough. Their exact
   live-DT bindings are required so the Samsung probe's dump-mode arm and the
   priority-255 clean-reboot disarm cannot silently fail or be absent.
6. Final-state polling cannot replace phase barriers. Several consumers can
   bind or launch one-shot setup work before their runtime providers are ready,
   and not all such failures trigger deferred reprobe.
7. A native malformed-command generic-reset candidate is rejected because it
   creates a persistent reboot loop and has less information value than W1.
8. Lane K Full-LTO work remains independent and can continue on the 32 GiB
   build host while this design awaits review.

## Host Validation

Read-only validation against the exact local FYG8 corpus produced:

```text
ordered_module_count=15
hash_inventory_match=1
hard_dependency_topological_order=pass
abl_jump_table_rva=0xf40ec
abl_recovery_pon_0x01_target_rva=0x4aca0
abl_recovery_mode=2
abl_recovery_mode_string=Recovery Mode, Reset param!
sec_qc_rbcmd_registration=asynchronous-kthread
sec_qc_rbcmd_readiness_oracle=debugfs-registered-command-list
runtime_provider_barriers=phased-not-final-poll
six_live_dt_binding_nodes=pass
stock_download_control_marker_count=3
stock_generic_reset_control_marker_count=3
git_diff_check=pass
```

The two retained logs rehashed to their pinned values during this unit. No
device command, build, repack, image generation, or flash was performed.

## Independent Review Disposition

The static review is complete and produced these corrections:

1. the seven-module hard closure became a 15-module runtime closure with
   explicit provider barriers;
2. six platform predicates and the SDAM nvmem predicate are keyed by canonical
   OF node plus compatible, not unstable device basenames;
3. exact LinuxLoader independently proves `0x01` reaches explicit Recovery
   mode, while `0x15` reaches Download;
4. the asynchronous Samsung command-registration race is closed by the bounded
   mutex-protected debugfs readiness oracle;
5. the three variants use one binary and differ only in one normalized
   five-byte mode file.

Static disposition: `GO_TO_HOST_SOURCE_REVIEW_ONLY`. This does not prove that
the closure binds under native PID1, does not authorize implementation under
the current design-only GOAL, and grants no build, image, flash, reboot, or
live action. Before implementation, the operator must explicitly open a
host-source unit. Before any live rung, W0/W1/W2 need separate one-shot policy
clauses, exact artifact/source pins, and fresh approval.
