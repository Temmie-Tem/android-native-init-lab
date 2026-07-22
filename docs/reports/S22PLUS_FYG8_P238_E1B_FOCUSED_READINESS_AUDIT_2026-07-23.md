# S22+ FYG8 P2.38 E1B focused readiness audit

Date: 2026-07-23 KST
Tier: H0
Status: `PASS_P238_E1B_FOCUSED_READINESS_H0`
Live authority: none

## Verdict

E1B is ready for a bounded host implementation unit. The runtime, checkpoint
model, exact FYG8 watchdog-module closure, and kernel/module ABI prerequisites
are already closed. No broader research or device action is needed before
implementation.

This audit did not build a new kernel, package a candidate, create a Process v2
manifest, contact a device, or authorize F1. P2.37's binding remains consumed.

## Runtime Closure

The P2.33 E1B profile reuses the exact E1A path proven live by P2.37 and then
executes these additional stages:

1. load and verify `smem.ko`;
2. load and verify `minidump.ko`;
3. load and verify `qcom-scm.ko`;
4. load and verify `qcom_wdt_core.ko`;
5. load and verify `gh_virt_wdt.ko`;
6. verify that `/proc/modules` contains exactly those five runtime names; and
7. publish E1B terminal success at stage `0x3f`.

Each module stage requires `finit_module()` to return zero before the progress
record is published. A failure publishes the failing stage, module index, and
errno before parking. The current host contracts independently rebuild the
static AArch64 runtime, pin stage ordering and syscall argument placement, and
reject module reorder, scope growth, `sec_log_buf.ko`, shell, USB, block-write,
and reboot authority.

Current reruns passed:

- `PASS_R4W1E_E1_RUNTIME_HOST_CONTRACT`;
- `PASS_P233_E1_SOURCE_IMPLEMENTATION_HOST_ONLY`; and
- the E1A/E1B model, source, legacy runtime, and P2.34 regression set: 93 tests.

## Module And ABI Closure

The five files are the exact FYG8 stock vendor-ramdisk modules already pinned by
`docs/module-map/s22plus-fyg8/inventory.tsv`. Their runtime names and vermagic
match the FYG8 kernel. The stock dependency rows require this topological order:

```text
smem
minidump -> smem
qcom_scm
qcom_wdt_core -> qcom_scm, minidump, smem
gh_virt_wdt -> qcom_wdt_core, qcom_scm, minidump, smem
```

The P2.34 build preserves the relevant module ABI:

- all 15 normalized `Module.symvers` identities match the clean R1v3 baseline;
- its `vmlinux.symvers` and ABI XML match the pinned R4W1/R2 baseline;
- the R2 audit matched all 25,864 requirement rows across the complete
  491-module on-disk corpus, with zero missing rows, mismatched symbols, or
  provider conflicts;
- the kernel banner and release match FYG8 exactly; and
- `CONFIG_MODULES`, `CONFIG_MODULE_UNLOAD`, and `CONFIG_MODVERSIONS` are enabled,
  while module-signature enforcement is disabled.

This closes the host-side compatibility question. It does not substitute for
the future E1B observation that each exact `finit_module()` call returned zero.

M31B previously loaded this same closure and survived the full 120-second park
window, removing the earlier approximate 30-second reset ceiling. That result
supports the watchdog architecture but did not provide the stage-by-stage,
candidate-bound retained proof that E1B is intended to add.

## Effective Rootfs Correction

The five modules must not be injected into the boot AP. They already reside in
the unchanged stock `vendor_boot` vendor ramdisk. Android boot-v4 composes the
candidate's generic boot ramdisk with the vendor ramdisk, producing the
effective `/lib/modules` tree.

Therefore the E1B candidate remains one boot-only AP member. Its independent
checker must parse the candidate boot image and the pinned stock `vendor_boot`,
compose every newc layer in boot order, reject duplicate or overriding paths,
and verify the five module bytes and metadata in vendor layers. Connected D0
already binds the live `vendor_boot`, DTBO, and recovery hashes as supporting
partition identities; E1B must retain that gate.

## Implementation Gap

The P2.34 machinery cannot be reused unchanged:

- candidate intent fixes `PROFILE = "E1A"`, profile number 1, and an E1A-only
  run-ID domain;
- userspace compilation fixes `S22PLUS_FYG8_P233_PROFILE=1`;
- candidate packaging and independent reconstruction add only E1A `/init` and
  the child and do not audit the effective vendor-rootfs modules;
- static evidence promotion accepts only E1A and terminal stage `0x2f`; and
- the Process v2 observation contract names E1A terminal success.

The next implementation must preserve P2.34 E1A outputs and tests while adding
one profile-driven E1B closure. Reuse the existing P2.34 clean-build,
deterministic boot-only packaging, and Process v2 primitives, plus the older
R4W1-E module-derivation and effective-rootfs audit. Do not fork the roughly
4,800-line candidate stack or create a candidate-specific live runner.

The required E1B delta is limited to:

1. new E1B candidate identity and profile-2 kernel configuration;
2. profile-2 static `/init` with the existing child;
3. pinned stock vendor-ramdisk module closure and effective-rootfs audit;
4. E1B terminal/failure decoding and offline evidence promotion; and
5. final two-build Full-LTO reproduction only for the actual candidate.

## Limits

This audit does not prove E1B live execution, module probe/bind, watchdog
registration or ownership, platform bind, UDC, ACM bytes, NCM, a shell, or
Debian. E1B terminal success will prove module insertion and exact
`/proc/modules` visibility, not driver bind. Those remain separate later rungs.

## Decision

Proceed to P2.39 H0 implementation. Stop before candidate packaging if the
effective rootfs cannot be independently reconstructed from one boot-only
candidate plus the exact pinned stock `vendor_boot`. No D0 or F1 step belongs in
P2.39.
