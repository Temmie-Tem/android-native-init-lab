# S22+ FYG8 P2.80 SCS, CFI, and Kprobe control

Date: 2026-07-27 KST

Scope: `H0`, host-only. No device connection, D0, approval, build candidate,
Full LTO, packaging, flash, reboot, or partition write occurred.

## Verdict

`PASS_HOST_ONLY`

The proposed Shadow Call Stack failure mechanism is ruled out by the exact
FYG8 arm64 Kretprobe implementation and target disassembly. CFI body/thunk
ambiguity is also statically bounded. A new pinned generic-arm64 QEMU control
then proves the tracefs entry/return ABI, exact return fetch, zero-miss
profiles, and full cleanup used by the P2.80 design.

This does not prove any S22+ USB runtime result and grants no device authority.

## Question

An adversarial review raised four points:

1. SCS and pointer authentication might let an entry probe fire while silently
   bypassing its return probe.
2. Registration success, no-fire, and fired states must not collapse.
3. Tracefs/Kprobe-event syntax and cleanup should execute in QEMU before F1.
4. A CFI jump-table thunk must not be confused with the intended function
   body.

The first and fourth points can change interpretation, so they were checked
against the exact candidate config, exact kernel source, exact vendor module,
and exact linked `vmlinux`. The third was then executed in the pinned QEMU
guest.

## Exact Inputs

Candidate evidence:

- `.config` SHA256:
  `12c68c7c48d66628443822c39022cebb8fd0c7244e68c639e7b56ec5266bf604`;
- `vmlinux` SHA256:
  `dba49dce18e645edf8bdb95281902d1361513d2e61ecb32a4a9c982d061bacfb`;
- `dwc3-msm.ko` SHA256:
  `8913b050419e88699033e957d927beef86742ed035f531dc5c4729f50cea60f1`.

Exact build-source hashes:

- arm64 `probes/kprobes.c`:
  `404b7b539bae76f25c6df98fb071c49cea488c0207c3a027ef0ad8aa383b7f81`;
- core `kernel/kprobes.c`:
  `3ae68503a7c776b5eaead02c3e6663bce175ab5df4f7184db0368d8980c76a81`;
- arm64 `kprobes_trampoline.S`:
  `7e74234768b52cc26c66689b1e71060a62d585c00fab86280f18271e2260a987`.

The exact config enables `CONFIG_SHADOW_CALL_STACK`,
`CONFIG_ARM64_PTR_AUTH`, `CONFIG_CFI_CLANG`, `CONFIG_KPROBES`,
`CONFIG_KRETPROBES`, `CONFIG_KPROBE_EVENTS`, `CONFIG_FTRACE`,
`CONFIG_TRACING`, and `CONFIG_KALLSYMS_ALL`.

## SCS and PAC Analysis

### Hypothesis

The concern assumed a return probe replaces a return address stored on the
ordinary stack while arm64 SCS later restores a different return address from
`x18`. Under that implementation, entry could fire and return could be
silently bypassed.

### Exact source result

The exact core path runs the return-probe entry handler and then calls
`arch_prepare_kretprobe()` before the target's first instruction. The arm64
implementation:

1. saves live `regs->regs[30]` as the original return address;
2. records the stack pointer; and
3. replaces live `regs->regs[30]` with `kretprobe_trampoline`.

It does not patch a saved ordinary-stack slot.

The exact trampoline invokes `kretprobe_trampoline_handler()`, moves the
returned original target into `lr`, restores registers, and returns.

### Exact target result

`dwc3_otg_start_peripheral` begins:

```text
paciasp
str x30, [x18], #8
stp x29, x30, [sp, #-48]!
```

Its return path includes:

```text
ldp x29, x30, [sp], #48
ldr x30, [x18, #-8]!
autiasp
ret
```

Because Kretprobe substitutes live `x30` before the first target instruction,
the trampoline is the value signed by `paciasp` and stored by SCS. SCS later
restores that same signed trampoline before `autiasp; ret`.

### Disposition

`RULED_OUT`: SCS does not bypass this Kretprobe by restoring an untouched
return target. The original concern was structurally valid but assumed the
wrong arm64 Kretprobe mechanism.

This is an exact-source/object conclusion. The generic QEMU guest does not
enable SCS and is not cited as SCS proof.

## Existing Three-State Semantics

P2.80 already has entry/return pairs for every decisive return:

- `start_in` / `start_out`;
- `resume_in` / `resume_out`;
- `pull_in` / `pull_out`; and
- `run_in` / `run_out`.

The design keeps these states separate:

| State | P2.80 interpretation |
|---|---|
| registration or readback failure | instrumentation failure `0xb02` |
| registered, no decisive Phase-R entry | pre-entry boundary `0xb12` or `0xb13` |
| entry, no return by the Phase-R deadline | active worker boundary `0xb14` |
| missing synchronous Phase-B return | contradiction `0xb03` |
| nonzero `nmissed` or malformed trace | instrumentation failure `0xb03` |
| ordered entry and return | function-specific result is eligible |

A new live control return probe is not added. It would prove only its own
target, not a missing return from another target, while increasing dynamic
instrumentation and cleanup surface. The source/object proof plus mandatory
QEMU control is the smaller discriminator.

## CFI Resolution

The exact module contains:

```text
000000000000b038 t dwc3_msm_usb_role_switch_set_role
000000000000cc3c t dwc3_otg_start_peripheral
000000000000ff88 T dwc3_msm_usb_role_switch_set_role.cfi_jt
```

P2.80 probes `dwc3_otg_start_peripheral`, not the role-switch callback. The
parent target has no same-name CFI thunk. The three built-in Phase-B targets
also resolve as exact local body symbols and have no same-name `.cfi_jt` in
the inspected `vmlinux`.

The implementation is required to add an exact-body gate in the expected text
section that rejects suffix matches, aliases, and `.cfi_jt` addresses. That
extractor is not yet implemented by this bounded control unit.

## Generic-Arm64 QEMU Control

Tracked implementation:

- `workspace/public/src/native-init/`
  `s22plus_fyg8_p280_kprobe_qemu_control.c`;
- `workspace/public/src/scripts/revalidation/`
  `s22plus_fyg8_p280_kprobe_qemu_control.py`;
- `tests/test_s22plus_fyg8_p280_kprobe_qemu_control.py`.

Pinned execution inputs:

- Debian arm64 `6.12.94+deb13-arm64`;
- kernel SHA256:
  `cbe59a02e7ea979a150661032440c94e2c4db0b735af2416e11ae5cac15a58e4`;
- config SHA256:
  `834fda1f695bb68263c61615fb6f3707ac1a54e6ba72a71376c7472d499f960a`;
- QEMU binary SHA256:
  `15d18809121fe6237c9170a5d820cc44196942d1df2df0dad0c5d8cd6154b35e`;
- QEMU version:
  `QEMU emulator version 10.2.1 (Debian 1:10.2.1+ds-1ubuntu3.1)`.

The runner rejects a kernel, config, QEMU binary, or QEMU version mismatch
before guest execution. Compilation, `cpio`, QEMU version query, and guest
execution all have explicit host timeouts.

The control:

1. mounts proc, sysfs, and exact tracefs;
2. verifies exact `__arm64_sys_close` in full kallsyms;
3. owns one isolated tracing instance and event group;
4. registers and reads back one entry/return pair;
5. filters both events to PID1 and selects counter trace clock;
6. invokes one exact `close(-1)` syscall;
7. requires one ordered entry and return with exact signed `:s32`
   `rc=-EBADF`;
8. requires one hit and zero misses for both probe profiles; and
9. removes both events and the instance, unmounts tracefs, and verifies
   cleanup.

Observed result:

```text
P280_KPROBE_QEMU result=PASS symbol=__arm64_sys_close
entry_hits=1 return_hits=1 retval=-9 nmissed=0 cleanup=ok
```

Private reproducible evidence:

- result:
  `workspace/private/outputs/s22plus_fyg8_p280_kprobe_qemu_control/result.json`;
- control source SHA256:
  `439b0286692c681dc630d53afb1a7233114dfc383bb4b865f54689434f93c2eb`;
- static init SHA256:
  `2d0253e89185d0db7b09dd4421e20a447d7553e25b32913657974c6de4dcd8d7`;
- deterministic initramfs SHA256:
  `3b3d9bcaebe7ad199fac70938223a283b5fb6fb15ca887b71bca1cafa1235e96`.

An independent second build produced the same init and initramfs hashes.

## Proof Boundary

The QEMU result proves only the generic mechanism:

- tracefs mount and control ABI;
- Kprobe-event entry/return syntax;
- PID filter and counter clock behavior;
- exact negative signed `:s32` return fetch;
- profile hit/miss parsing; and
- complete owned cleanup.

It does not prove:

- S22+ SCS/PAC behavior;
- the exact Qualcomm symbol sites;
- DWC3-MSM, PHY, redriver, VBUS, or Type-C behavior;
- physical host enumeration; or
- any live candidate outcome.

Those boundaries remain explicit in the P2.80 design.

## Independent Review

The first read-only review returned `NO-GO` for promotion as a mandatory gate:

- the runner described a pinned guest but did not enforce kernel/config/QEMU
  identity;
- the first control used positive `:s64` rather than the production
  contract's signed `:s32`;
- host compilation and archive creation lacked explicit subprocess bounds;
  and
- CFI extraction was described as completed before its implementation.

The implementation was corrected to enforce all execution pins, use exact
`close(-1) -> -EBADF` through `$retval:s32`, keep control FDs open so the
active profile contains exactly one intended close, bound every subprocess,
and mark CFI extraction as the next implementation gate.

The same reviewer then returned `GO` with no `MUST-FIX`. The only residual
`LOW` gap is that version-mismatch and subprocess-timeout branches are
visibly fail-closed but do not each have a dedicated mocked unit test.

## Result

The adversarial review improved the design without widening the live
instrumentation:

- the SCS concern is closed by exact source and linked-code evidence;
- CFI body selection is a mandatory next implementation gate, not falsely
  claimed as implemented by this unit;
- registration/no-fire/fire states remain distinct;
- the QEMU mechanism path is mandatory, no longer optional; and
- no additional live control probe is introduced.

P2.80 remains `GO` for versioned H0 implementation. It is not ready for D0 or
F1 merely because this generic control passed.
