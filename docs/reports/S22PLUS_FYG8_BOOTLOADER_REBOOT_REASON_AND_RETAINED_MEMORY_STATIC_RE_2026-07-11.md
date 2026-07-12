# S22+ FYG8 Bootloader Reboot-Reason and Retained-Memory Static RE

Date: 2026-07-11 KST
Target: Samsung Galaxy S22+ `SM-S906N` / `g0q` / `S906NKSS7FYG8`
Scope: host-only static analysis; no device contact, build, image generation,
flash, or live authorization

## Verdict

The exact FYG8 ABL consumer side is now proved: when Linux has successfully
stored Samsung PON restart reason `0x15`, FYG8 LinuxLoader dispatches that value
to its Odin/Download path.

Odin is not a unique reboot-reason sink. The exact LinuxLoader also converges
normal mission-boot load/authentication failure and a returned `BootLinux()`
handoff onto the Odin launcher. A later Odin endpoint therefore cannot identify
which producer selected it, even when the Linux reboot-reason module closure is
present. A producer positive control must distinguish the `0x15` path from this
generic boot-failure fallback.

The native-PID1 producer side was not present in M4T3, M21A, or M34 S10C0. The
Samsung command parser and PON-reason writer are loadable modules, not built-in
kernel code. Raw candidates loaded none of them, and S10C0's 89-module set also
omitted the required reboot-reason closure. `qcom-scm.ko` can participate in a
warm reset but does not parse the `"download"` string or write PON reason
`0x15`.

Therefore:

- a later Odin endpoint from those candidates is not proof that their
  `reboot(..., "download")` request succeeded;
- M4T3 remains timing-ambiguous, as already established by M21;
- M21A remains a negative timed-Download result with PMIC abnormal reset;
- S10C0 does not prove `cmd-db.ko` was accepted and then deliberately entered
  Download mode; it proves only the recorded host-side endpoint/reset
  correlation;
- M4T2's attended raw park remains the strongest positive native-PID1 floor.

The retained-memory review also does not justify the current broad hypothesis
that S-Boot clears all DRAM. V3439 proved that the tested ramoops record did not
survive its SysRq/RDX/reset flow, but the exact failure mechanism remains open.

Two additional exact-build boundaries are now closed:

- `XblRamdump.elf` sends the observed `NeGaTiVeAcKmNt\0` directly when its RDX
  lock flag is set. The same flag selects the `(without Token)` UI. MID and HIGH
  both reached this exact locked branch, so blind RDX protocol mutation is
  retired.
- `QcomWDogDxe` registers an ExitBootServices callback and disables its UEFI
  hardware watchdog through `SMC_ID_WDOG_CTL` before the kernel owns the
  machine. The roughly 30-second bare-PID1 reset is therefore not explained by
  an accidentally inherited UEFI watchdog.

## Pinned Bootloader Artifacts

Exact stock BL archive:

```text
workspace/private/inputs/firmware/
  SAMFW.COM_SM-S906N_SKC_S906NKSS7FYG8_fac/
  BL_S906NKSS7FYG8_S906NKSS7FYG8_MQB99315260_REV00_user_low_ship_MULTI_CERT.tar.md5
SHA256 e5aeb59de4ed16c21111945900aeda4743b717361b0919084e9d284d08e4e0ba
```

Extracted exact-build artifacts:

```text
abl.elf
SHA256 b828dffa4ea63eeaeb5d374db96daee9e1f696487f724d18aecbbc61ed993a24

LinuxLoader EFI PE32+ AArch64 image
SHA256 b1ee37a2be13a557fa05a6e603fa81c827b3d8be410df1a61145f050c67cde28
entry RVA 0x1000
.text RVA 0x1000, size 0x12c000

ResetRuntimeDxe EFI PE32+ AArch64 image
SHA256 a3fbc564366c9e607711bf834cd5d8be74c29636b08f25f47e3f49712b46348a

SecEnvDxe EFI PE32+ AArch64 image
SHA256 8e16fb88d0a7b016cccca33ae029a319c0f7ed276f6b4ffc943d0247d8a6b99c

QcomWDogDxe EFI PE32+ AArch64 image
SHA256 95237c4db1ca634eda9ace62d5a7bf6ae58e050acf8aea2b879ccad451d7842e

XblRamdump.elf AArch64 image
SHA256 0fc28798d2cfa24de2fcc370ffb0715ee73da81cf88b86727cfd71dd10cc5db6
```

The LinuxLoader image was recovered from the nested ABL firmware volumes with
`uefi-firmware`, identified with `pefile`, and disassembled as AArch64 with
Capstone. All offsets below are RVAs in that exact LinuxLoader PE, not runtime
virtual addresses and not offsets borrowed from another firmware release.

## Exact FYG8 ABL Consumer

LinuxLoader's reboot-reason dispatcher starts at RVA `0x4aac8`. It reads the
current reset reason through the platform protocol, records it in the global
state near RVA `0x17a9bc`, attempts the protocol's clear operation, and
dispatches reason values `1..99` through the table at RVA `0xf40ec`.

The exact Download case is:

```text
PON reason 0x15
  -> jump-table target RVA 0x4ad08
  -> mov w0, #0x10000
  -> common path RVA 0x4ac34
  -> call RVA 0x508a0
  -> return mode 1
  -> caller at RVA 0x4bf2c consumes the selected boot mode
```

The matched Recovery control is separately decoded from the same exact table:

```text
PON reason 0x01
  -> jump-table entry 0x001f
  -> target RVA 0x4aca0
  -> mov w19, #2
  -> caller at RVA 0x4bf2c takes its mode-2 branch
  -> log string at RVA 0xf4490: "Recovery Mode, Reset param!"
  -> return boot mode 2
```

The table RVA was independently recomputed by decoding the `ADRP` instruction
at RVA `0x4ac0c`: instruction `0xd000054a` resolves page `0xf4000`, then the
following `add #0xec` selects `0xf40ec`.

Selected table entries cross-checked against the exact FYG8 Samsung enum:
`kernel_platform/msm-kernel/include/linux/samsung/debug/qcom/sec_qc_rbcmd.h`.

| PON value | Meaning | LinuxLoader target RVA |
|---:|---|---:|
| `0x01` | Recovery | `0x4aca0` |
| `0x14` | normal boot | `0x4ace8` |
| `0x15` | Download/Odin | `0x4ad08` |
| `0x2b` | multicmd | `0x4ad10` |
| `0x30` | debug LOW | `0x4adc8` |
| `0x31` | debug MID | `0x4ae18` |
| `0x32` | debug HIGH | `0x4ae54` |
| `0x4d` | dump-sink USB | `0x4b084` |
| `0x4e` | dump-sink bootdev | `0x4b0a0` |
| `0x4f` | dump-sink SD | `0x4b0bc` |

The image also contains the expected exact-build diagnostics and command
tokens, including `Failed to get Reboot reason`,
`Current Reset Reason Value : 0x%x`, `ERROR: failed to clear ResetReason`,
`Update BootReason: %x`, `debug0x4f4c`, `debug0x494d`, `debug0x4948`, and
`xbl_ramdump`.

This proves only the consumer implication:

```text
PON restart reason 0x15 reaches FYG8 ABL -> ABL selects Download/Odin
```

It does not prove that an arbitrary Linux `reboot(RESTART2, "download")` call
wrote `0x15`.

## Non-Unique Odin Paths

The exact mission-boot path calls the boot-mode selector at RVA `0x188c`. The
normal image-loading path then has the following shape:

```text
RVA 0x1c2c  load/authenticate boot inputs through RVA 0x59f0
RVA 0x1c50  call BootLinux at RVA 0x15738
RVA 0x1c54  a returned BootLinux converges on common failure handling
RVA 0x1c9c  common pre-Odin cleanup/check
RVA 0x1cbc  call Odin launcher at RVA 0x1410
```

The parameter boot selector independently maps parameter value `3` through RVA
`0x4c0f0`, logs `PARAM_BOOT_DOWNLOAD_FAIL`, and converges on boot mode `1` at
RVA `0x4bfd8`. This is separate from PON reason `0x15`.

`BootLinux()` reaches its final kernel entry through an indirect `blr` at RVA
`0x16784` or its alternate handoff at RVA `0x167ac`. A kernel reset after that
handoff does not return to LinuxLoader. The fallback proves that a later boot
load/authentication failure can launch Odin; it does not prove that a running
native PID1 panic directly returned through `BootLinux()`.

The `bl_boot_complete` diagnostic is also pre-kernel state, not an Android or
native-userspace completion marker. `BootLinux()` calls RVA `0x5bd18` at RVA
`0x165f8`, before the kernel-entry branch. That routine invokes the secure
`bl_boot_complete` operation and reports `bl_boot_complete failure!!` on error.
It cannot be used as evidence that PID1 or Android completed.

The A/B code contains both `A/B retry count NOT decremented` and alternate-slot
handling. Its exact branch at RVAs `0x36708..0x36878` skips retry decrement when
the active-slot state does not satisfy the decrement conditions. No evidence
currently shows that these native-init trials exhausted a slot or that slot
metadata selected their later Odin endpoint.

## Reset-Reason Ownership

The exact `ResetRuntimeDxe` implements read, save, and clear operations over the
platform reset-reason protocol:

- RVA `0x295c` reads the reason and logs `Failed to read reset reason` on error;
- RVA `0x2b8c` saves a reason and logs `Failed to save reset reason` on error;
- RVA `0x2a94` calls that save path with zero and logs
  `Unable to clear reset reason` if it fails.

The exact `SecEnvDxe` separately classifies PMIC/PON history. Its compact table
at RVA `0xc150` maps internal indices to `SP`, `WP`, `DP`, `KP`, `MP`, `PP`,
`RP`, `BP`, `NP`, `TP`, and `CP`. The PM-log S2-reset path at RVA
`0x353c` logs `Detect S2 Reset from PM Log, RR set [MP]` and selects table index
`5`, while undefined reset reasons select `NP` at RVA `0x395c`.

This grounds the observed `/proc/reset_reason=MPON`: `MP` is an early-boot
PMIC/reset classifier later exposed with the `ON` suffix, not a native-init
marker. It corroborates the abnormal-reset class but does not identify the last
native-PID1 instruction.

## RDX Authorization Boundary

The exact `XblRamdump.elf` packet state machine is at virtual address
`0xa7d16ca0` and references the protocol literals directly:

```text
PrEaMbLe             VA 0xa7e71045
AcKnOwLeDgMeNt       VA 0xa7e7104e
NeGaTiVeAcKmNt       VA 0xa7e7105d
PoStAmBlE            VA 0xa7e7106c
DaTaXfEr             VA 0xa7e71080
PrObE                VA 0xa7e71089
```

At VA `0xa7d16e90`, the preamble branch tests the global RDX lock flag. Flag
`1` sends the 15-byte negative acknowledgement at VA `0xa7d16eac`; only the
other branch sends the positive acknowledgement at VA `0xa7d1702c`. The same
flag selects `locked` versus `unlocked` text and `(without Token)` in the UI.

This upgrades V3440/V3443R from merely “consistent with a lock” to an exact
binary-backed result: both runs reached the firmware's locked preamble branch.
It does not reveal or bypass the signing/token authority that can clear the
flag. No further RDX command, probe, transfer, or protocol mutation is justified
by the current evidence.

## UEFI Watchdog Handoff

The exact `QcomWDogDxe` registers callback RVA `0x1694` with
`CreateEventEx()` and the exact `gEfiEventExitBootServicesGuid` bytes at RVA
`0x6028` (`27abf055-b1b8-4c26-8048-748f37baa2df`). The callback reaches RVA
`0x1e5c`, which issues the `SMC_ID_WDOG_CTL` disable operation and reports
`ERROR: SMC_ID_WDOG_CTL Disable failed` on error.

Therefore the boot-services watchdog is deliberately disabled at kernel
handoff. The later bare-PID1 timeout belongs to a post-handoff watchdog owner or
policy. This is consistent with M31B: loading the exact stock watchdog closure
allowed the parked native PID1 to survive 120 seconds. The result strengthens
the kernel/hypervisor/PMIC watchdog-ownership model without proving which one
arms the post-handoff timer.

## Linux Producer Chain

The exact FYG8 source tree shows the intended complete path:

1. `LINUX_REBOOT_CMD_RESTART2` copies the user string and calls
   `kernel_restart(buffer)` in `kernel/reboot.c:371-380`.
2. `kernel_restart_prepare()` invokes reboot notifiers before device shutdown
   in `kernel/reboot.c:74-80`.
3. `machine_restart(cmd)` invokes the restart-handler chain through
   `do_kernel_restart(cmd)` in `arch/arm64/kernel/process.c:187-207`.
4. Samsung's strict parser maps exact string `download` to
   `PON_RESTART_REASON_DOWNLOAD` in
   `drivers/samsung/debug/qcom/reboot_cmd/sec_qc_rbcmd_command.c:393-399`.
5. The Samsung reason writer obtains the `restart_reason` nvmem cell, writes
   one byte, reads it back, and retries up to five times in
   `drivers/samsung/debug/qcom/reboot_reason/sec_qc_qcom_reboot_reason.c:88-101,161-214`.
6. The base Samsung reboot-command driver registers both a reboot notifier and
   a restart handler in
   `drivers/samsung/debug/reboot_cmd/sec_reboot_cmd.c:496-542,587-595`.

The corresponding g0q device-tree nodes exist for Qualcomm reboot reason,
Samsung reboot command, Samsung Qualcomm command mapping, and Samsung Qualcomm
reboot-reason writing. Device-tree presence alone does not instantiate modular
drivers.

## Missing Producer Closure in Native PID1

The generated FYG8 vendor configuration states:

```text
CONFIG_POWER_RESET_QCOM_REBOOT_REASON=m
CONFIG_SEC_QC_RBCMD=m
CONFIG_SEC_QC_QCOM_REBOOT_REASON=m
# CONFIG_POWER_RESET_MSM is not set
```

The exact shipped module metadata gives this hard symbol dependency closure:

```text
sec_qc_qcom_reboot_reason.ko
  -> sec_qc_rbcmd.ko
  -> sec_reboot_cmd.ko
  -> qcom-dload-mode.ko
  -> qcom-scm.ko
  -> minidump.ko
  -> smem.ko
```

Direct `modinfo` confirms:

```text
sec_qc_rbcmd              depends: sec_reboot_cmd
sec_qc_qcom_reboot_reason depends: sec_qc_rbcmd,qcom-dload-mode
qcom_dload_mode           depends: qcom-scm,minidump
minidump                  depends: smem
```

This seven-module list is not a complete direct-PID1 runtime closure.
`sec_qc_qcom_reboot_reason.ko` obtains its `restart_reason` nvmem cell during
probe, but FYG8 builds the cell provider `nvmem_qcom-spmi-sdam.ko` as a module.
The SPMI controller, PMIC regmap, PMIC child population, and SDAM nvmem provider
are runtime device/probe dependencies that `modules.dep` does not encode. The
corrected control design is recorded in
`docs/reports/S22PLUS_FYG8_LANE_W_REBOOT_REASON_PRODUCER_CONTROL_DESIGN_2026-07-11.md`.

The Recovery control has a second binding-sensitive writer. Exact FYG8
`qcom-reboot-reason.c:28-58,61-78` maps `recovery` to `0x01` only after the
`qcom,reboot-reason` platform device probes and obtains the same
`restart_reason` nvmem cell. The Samsung parser explicitly classifies
`recovery` as Qualcomm pre-defined and updates only Samsung `sec_rr`, leaving
the Qualcomm PON write intact
(`sec_qc_rbcmd_command.c:343-362,455-460`). Consequently, a native W1 control
must gate the actual `/soc/reboot_reason` driver binding; module presence alone
does not prove that `0x01` can be emitted.

The Samsung command parser has an additional readiness race. Its platform
probe invokes `sec_director_probe_dev_threaded()` and returns as soon as the
`drct-qc_rbcmd` kthread is created; command-registration failures are retained
in an internal result array and are not returned by probe
(`builder_pattern.h:242-308`). Thus even a bound
`samsung,qcom-reboot_cmd` device is insufficient. Exact FYG8 has
`CONFIG_DEBUG_FS=y`, and `sec_reboot_cmd.c:315-391` exposes the mutex-protected
registered lists at `/sys/kernel/debug/sec_reboot_cmd`. A future producer
candidate must bounded-read that file and prove the priority-250 Reboot
Notifier stage contains its default, `download`, and `recovery` handlers before
any terminal syscall.

The control must also gate the exact `/firmware/qcom_scm` and
`/soc/dload_mode` bindings. `sec_qc_qcom_reboot_reason` arms full dump mode in
its probe through `qcom_set_dload_mode(1)`, while the bound priority-255
`qcom-dload-mode` reboot notifier clears it to `QCOM_DOWNLOAD_NODUMP` on a
clean reboot (`qcom-dload-mode.c:272-293,312-353`). Missing that synchronous
probe state can confound an intended Recovery/Download PON reason with an RDX
path even when all module names appear in `/proc/modules`.

The normal first-stage `modules.load` includes `minidump.ko`,
`qcom-dload-mode.ko`, `qcom-reboot-reason.ko`, `qcom-scm.ko`, and `smem.ko`,
but not the three Samsung reboot-command modules. Those Samsung modules appear
only in `modules.load.recovery` at lines 347, 348, and 356.

M4T3 and M21A load no modules. S10C0's exact 89-module list includes
`smem.ko`, `minidump.ko`, and `qcom-scm.ko`, but omits
`qcom-dload-mode.ko`, `qcom-reboot-reason.ko`, `sec_reboot_cmd.ko`,
`sec_qc_rbcmd.ko`, and `sec_qc_qcom_reboot_reason.ko`.

The Qualcomm SCM restart handler confirms why a reset can still occur. In
`drivers/firmware/qcom_scm.c:2630-2639`, `qcom_scm_do_restart()` ignores the
restart command pointer; for a warm reboot it calls `qcom_scm_reboot()` and
returns `NOTIFY_OK`. It does not parse `download` and does not write PON reason
`0x15`.

Consequently, the prior candidates lacked the only source-backed producer path
that connects the Linux command string to the FYG8 ABL Download selector.

## Evidence Reclassification

### M4T2

Retain as the strongest positive native-PID1 floor. Its raw AArch64 `/init`
parked, and the operator observed the expected stable behavioral difference.
This is attended behavioral evidence, not a retained instruction pointer, but
it is stronger than the later Download inference.

### M4T3

Retain the raw observation, but not the old conclusion. The later Odin
endpoint is timing-ambiguous and the candidate had no reboot-reason modules.
M21 already downgraded it from a hard PASS.

### M21A

Retain `NO TIMED-DOWNLOAD PROOF`. The full 90-second dwell plus grace produced
no Odin endpoint; the operator observed PMIC abnormal reset. This result is
consistent with a generic reset or failure path, not a successful PON `0x15`
write.

### M34 S10C0

Retain all raw run artifacts and rollback facts. Withdraw the semantic claim
that direct `cmd-db.ko` `finit_module` acceptance caused a deliberate
self-Download. The host observed a later endpoint, while the candidate's
module manifest lacked the parser/writer closure needed to encode reason
`0x15`. Internal candidate state was not retained independently.

## Retained-Memory Boundary

The exact vendor-boot DTB set defines `ramoops_region` as a dynamic reserved
memory allocation:

```text
compatible = "ramoops"
size = <0x200000>
alloc-ranges = <0x0 0x0 0xffffffff 0xffffffff>
pmsg-size = <0x200000>
mem-type = <2>
```

It has no fixed `reg` address. `drivers/of/of_reserved_mem.c` allocates such a
region at boot with `memblock_find_in_range()`. `fs/pstore/ram.c` obtains the
resolved base from reserved-memory state, and `persistent_ram_post_init()` in
`fs/pstore/ram_core.c` preserves an old record only when the signature, size,
and start metadata validate.

V3439 proved all of the following:

- the candidate ramoops backend registered and bound;
- the operator observed the intended SysRq/RDX event;
- patched Android returned before stock-DTBO rollback;
- two stable pstore reads contained no current-run record;
- `/proc/last_kmsg` retained panic text.

It did not capture the resolved ramoops physical base before and after reset,
nor prove a global DRAM clear. Remaining explanations include dynamic-base
mismatch, invalidated header/signature metadata, selective reset-path
preservation, or explicit clearing outside the searched ABL strings. Exact ABL
and XBL images expose ramdump, reset, and selected-region handling, but no
ramoops-specific clear was identified.

Verdict: `S-Boot clears RAM` remains a hypothesis, not a proved root cause.

## Next Host-Only Design

Download can become a useful one-bit checkpoint only after a positive control
proves its producer path under native PID1. The next design unit should compare
two otherwise identical raw candidates:

1. load the exact dependency closure in topological order;
2. fail closed to an infinite park if any `finit_module` result is neither `0`
   nor `-EEXIST`;
3. require the Samsung parser and writer to bind to their exact DT nodes;
4. candidate A requests `reboot(RESTART2, "download")`;
5. control B performs a generic reset or parks at the same boundary;
6. classify Download as a checkpoint beacon only if the two controls are
   externally distinguishable and the producer closure has independent
   positive evidence;
7. treat any image load/authentication failure, `PARAM_BOOT_DOWNLOAD_FAIL`, or
   unmatched Odin entry as a confounder rather than a positive checkpoint.

A corrected dependency order must preserve the M31B watchdog floor and include
the hidden SPMI/SDAM provider path:

```text
smem -> minidump -> qcom-scm -> qcom_wdt_core -> gh_virt_wdt
regmap-spmi + qti-regmap-debugfs + spmi-pmic-arb
  -> qcom-spmi-pmic -> nvmem_qcom-spmi-sdam
qcom-dload-mode -> sec_reboot_cmd -> sec_qc_rbcmd
  -> sec_qc_qcom_reboot_reason
```

The selected differential is now three rungs: full-closure 120-second park,
matched `recovery` alternate-reason control, then exact `download` positive.
The positive is not interpreted unless the first two pass.

Static-analysis priority after this audit:

1. finish Lane K R1/R2 build and module-ABI gates; this remains the shortest
   route to a kernel-owned early witness;
2. design the reboot-reason producer/control pair only with independent proof
   of reason `0x15` and matched generic-failure controls;
3. inspect `SerialPortDxe` plus exact DT/pinctrl if a physical early UART route
   becomes actionable;
4. inspect `xbl_s.melf` DRAM warm-reset and selected-region handling only if a
   fixed-address retained witness is selected;
5. keep RDX packet mutation, broad bootloader auth work, BLDP counters, and
   blind downstream USB work retired absent materially new evidence.

This report authorizes design and static validation only. Any build, boot
candidate, flash, reset, or live comparison requires a new narrow SHA-pinned
`AGENTS.md` exception and fresh explicit operator approval.
