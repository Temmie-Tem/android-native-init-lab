# S22+ FYG8 P2.84 Sysfs Ingestion Correction H0

Date: 2026-07-29 KST

Verdict:

`PASS_P284_PRE_FULL_LTO_QUALIFICATION_HOST_ONLY`

## Scope

This was host-only work. It did not build a kernel, start Full LTO, package an
AP, contact a device, invoke Odin, authorize F1, reboot, or flash.

P2.84 is a versioned correction overlay. The historical P2.82 source files,
classifier, retained ABI, module sequence, generated kernel inputs, and linked
tables remain unchanged.

## Live Evidence Reinterpretation

P2.82 retained progress `0x8d/detail=0` and then stopped at
`0x8e/detail=0xc10`. The exact parent `none` write helper completed, but the
readback comparison could never succeed:

1. `p260_read_value()` required one trailing newline.
2. It removed that newline before returning the value and length.
3. P2.82 expected `"none\n"`, `"peripheral\n"`, `"suspended\n"`, and
   `"active\n"`.
4. Every valid read therefore became `-EIO`, which the bounded waiter retried
   until the `0xc10` deadline.

`0xc10` is a comparator false negative. It does not prove that the kernel failed
to enter NONE, and it does not prove that NONE was reached. Later child
suspend/resume, PHY reinitialization, gadget bind, and bus-state boundaries
were not executed.

## Correction

P2.84 defines one normalized token for each value. It derives:

- write wire as `token + "\n"`; and
- readback as the token without wire framing.

Only the four generated readback defines differ from P2.82. Kernel-generated
inputs and linked tables are byte-identical.

The retry policy remains narrow:

- `ENOENT`, `ENODEV`, and valid-value mismatch/empty-read `EIO` are bounded
  retries;
- malformed framing (`EPROTO`) and overflow (`EOVERFLOW`) fail immediately;
- permission, argument, allocation, and other unexpected kernel errors are not
  silently converted into timeouts.

This deliberately does not generalize trailing newline into a global sysfs ABI.
Each accepted value and framing rule is bound to the exact FYG8 attribute
implementation that emits it.

## Source-Bound Oracle

The new host oracle pins and verifies:

- FYG8 `dwc3_msm_mode_show()` source and its three emitted values;
- FYG8 `runtime_status_show()` source and its six emitted values;
- the exact unchanged P2.60 read/strip/compare functions; and
- the exact unchanged P2.82 bounded retry branch.

It then cross-compiles a static AArch64 harness and executes it under QEMU. The
harness covers:

- all nine source-emitted tokens;
- exact match and valid mismatch;
- empty read;
- missing newline;
- overflow; and
- three retryable plus eight representative hard-error values.

The result is
`PASS_P284_SYSFS_INGESTION_ORACLE_HOST_ONLY`.

## Production-Path Validation

The end-to-end qualification and independent review exposed and closed six host
integration defects before any kernel build:

1. a stale Process-v2 docs assertion still named the older P2.80 frontier;
2. the thin P2.84 closure adapter omitted the private `_entrypoints` delegate
   consumed by the production verifier; and
3. the newly added ingestion receipt was not normalized to a repository-relative
   path before portable re-verification;
4. the first P2.84 userspace source audit inherited P2.82's source-check run ID
   instead of using the versioned P2.84 identity;
5. the qualification-only ingestion oracle was incorrectly included in the
   candidate source preimage; and
6. the new receipt path lacked direct relocation, tamper, runtime-mutation, and
   historical-receipt-injection regression tests.

P2.84 now owns its userspace source-check identity. The oracle remains
cryptographically bound to pre-LTO gate 20, but changing the qualification tool
alone cannot change candidate identity or force Full LTO.

After correction:

- current P2.82/P2.84 contract plus Process-v2 regression: `126 tests`, pass;
- P2.84 userspace A/B: byte-identical;
- current generic P2.60, kprobe, lifecycle, and classifier QEMU receipts: pass;
- P2.84 linked-audit meta receipt: pass;
- P2.84 pre-LTO qualification: `20/20`, pass;
- Python bytecode compilation: pass; and
- pinned Ruff `0.6.9`: pass.

The post-fix independent review returned `GO` with no remaining correctness
finding or scope warning. A fresh private v2 intent, userspace result,
linked-audit receipt, and `20/20` qualification replaced the now-stale v1
identity.

The actual build wrapper successfully rehydrated and accepted the P2.84
qualification in its isolated temporary repository after the review fixes. Its
overall local
`build_allowed` remained false because this workstation lacks the populated
kernel worktree/toolchain and the required Full-LTO memory and free-disk
capacity. That is a build-host readiness result, not a P2.84 contract failure.

## Interpretation

P2.84 closes the known ingestion-contract defect and reaches the Full-LTO
boundary with a production-path `20/20` qualification. It does not prove the
corrected userspace on S22+ hardware.

The next candidate unit is Full-LTO A/B on the qualified build host, followed by
the existing linked, package, static, and promotion gates. No S22+ F1 live run
is currently authorized.

## References

- Linux kernel sysfs documentation:
  <https://docs.kernel.org/6.10/filesystems/sysfs.html>
- Linux kernel sysfs rules:
  <https://docs.kernel.org/6.15/admin-guide/sysfs-rules.html>
- umockdev trailing-newline fixture limitation:
  <https://github.com/martinpitt/umockdev/issues/175>
