# S22+ FYG8 R4W1-E0 PID1 userspace proof host build

Date: 2026-07-22 KST
Scope: H0 host-only
Status: clean Full-LTO build and static audit passed; no candidate or live authority

## Verdict

`PASS_R4W1E0_PID1_USERSPACE_PROOF_HOST_BUILD`

R4W1-E0 is a minimal two-state diagnostic for the R4W1-E no-proof result. It
reuses the exact 45-byte retained slot already proven by R4W1-D and removes the
new R4W1-E OF/resource carrier gates, 173-byte carrier, and A/B slots from the
question. No device was contacted and no AP candidate was constructed.

## Diagnostic contract

After successful `kernel_execve("/init")` on PID 1, the kernel writes one exact
ENTRY marker immediately behind the saturated Samsung retained-log cursor:

`[[S22P1U|ba234c7de4105b2a23222436284605f2]]`

The kernel also registers a write-only `/proc/s22_checkpoint`. The pinned E1
runtime's first action mounts proc and sends its exact first 32-byte checkpoint
request. The handler accepts only PID 1, offset zero, the exact request, an
unchanged retained header, and the exact ENTRY marker. It then overwrites the
same slot with:

`[[S22P1U|ec8d029b05288644bbe7b5f7c7af190c]]`

The request is bound to probe ID `64554e8469385878c5bf8d57c44edeea` and is:

`53323251010110000000000064554e8469385878c5bf8d57c44edeeafd118a62`

The proc path is one-shot. It changes no retained header field and introduces
no reboot, panic, block I/O, OF lookup, or device control path.

## Runtime binding

The host checker reproduces the static runtime twice from pinned sources,
requires byte identity, compiles the request probe, and records the exact tools
and flags in a canonical receipt. The promoted private runtime identities are:

- `init`: 66,056 bytes, SHA256
  `c3fd6cc88d8de494421ff2bf0f082d278745fdf9c2a74a2b5edba9fb8ca93627`;
- `s22-e1-child`: 720 bytes, SHA256
  `9a57b30aa3fb08ee0aab4d045d2805dd36875bb80bcba7b0b6606f619df71639`;
- runtime receipt: 5,383 bytes, SHA256
  `4ab9bae4d974c087fc68dda75d91d08babaeacaaa0f11f56d3b309b0fa42c2be`.

An initial independent review found that the first implementation reused the
consumed R4W1-E run ID and did not bind the checker to the actual compiled
runtime. The in-progress exploratory build was stopped and not promoted. The
new probe ID, exact request, two-build receipt, and artifact check close those
findings before the clean build below.

## Full-LTO build

The final clean build completed with return code zero:

- elapsed: 36:27.12;
- maximum RSS: 24,242,880 KiB;
- swaps: zero;
- generated modules: 2,397;
- result JSON SHA256:
  `3303a528229d2b6e79e8b4393e7b7d1fd80a9e8ba489991b214bd554e8035857`.

Core output identities:

- `Image`: 41,490,944 bytes, SHA256
  `54d637f9ee018e9daac017847c1a233dfa8913c20830a357ea597baf3f9232f9`;
- `Image.lz4`: 21,591,117 bytes, SHA256
  `69a49a6ba755fa0fef6428f6089e94201f6123e62df545006de41571eca16e73`;
- `vmlinux`: 476,927,984 bytes, SHA256
  `ffd2d35316441f71c7c475fedb7bb78b41b1f8ec84fe00500b42eb4e14597ac3`;
- `System.map`: 5,072,855 bytes, SHA256
  `2d922106e2507ac5de834b4130637323aa9a5602d4b1d11c064e13d99cf9466b`;
- `.config`: 185,339 bytes, SHA256
  `f98f7962517c195b8b9e5e652df1fddf6c14f4483f995ea02f6c5f00921c6120`.

The `Image` keeps the exact 41,490,944-byte stock geometry and 1,536 bytes of
pre-ramdisk slack. ENTRY and USERSPACE occur exactly once each in both `Image`
and `vmlinux`; the shared family occurs exactly twice and all historical proof
families are absent. The exact config and FIPS enable each occur once. All
inherited output, module, banner, provider, source-delta, and symlink
restoration gates passed.

## Linked-code audit

The linked ARM64 output confirms:

- `kernel_init` calls `run_init_process`, accepts only return zero, checks
  `/init` and PID 1, validates the retained header, and stores ENTRY;
- `s22plus_fyg8_p1u_write` checks PID, one-shot state, count, offset, all 32
  request bytes, retained-header identity, and ENTRY before storing USERSPACE;
- no post-publication header check can return `-ESTALE` after a complete
  USERSPACE marker has been written; and
- the late init stub calls `proc_create` with mode `0200` and the linked
  `s22plus_fyg8_p1u_ops` table.

`vmlinux` is an ARM64 statically linked ELF with debug information. `Image` is
a valid ARM64 Linux boot image and `Image.lz4` is valid LZ4 data.

## Interpretation boundary

With a clean pre-candidate baseline, exactly one USERSPACE marker would prove
that the exact PID1 proc callback accepted the exact first request and stored
the marker. It would not prove the syscall returned to userspace, later E1
stages, child execution, retained durability, candidate PASS, rollback, or
final health.

ENTRY-only, no marker, duplicate family, mixed identity, or a non-clean
baseline is not accepted as userspace proof. The classifier keeps those cases
separate instead of converting absence into a negative execution claim.

## Validation and next unit

The complete matching R4W1-D and R4W1-E/E0 suites pass 127 tests. Targeted Python
bytecode compilation and `git diff --check` pass. Independent high-reasoning
review found no remaining high or medium blocker for this host build.

The next bounded unit is H0 only: reuse the existing P2.9 boot-only candidate
packager and static checker as a thin adapter binding this exact kernel,
runtime, receipt, clean-baseline requirement, and one-family classifier. Do
not fork the Process v2 runner, contact the device, or create F1 authority in
that unit.
