# S22+ FYG8 R4W1-E checkpoint carrier host contract

Date: 2026-07-21 KST
Scope: HOST-ONLY
Verdict: `PASS_R4W1E_CHECKPOINT_CARRIER_HOST_CONTRACT`

## Result

P2.7 implemented and host-tested the retained checkpoint carrier required by
the post-PID1 architecture. This unit produced source, a pure host codec and
static contract checker, and adversarial tests. It did not build a kernel,
create or package an image, contact a device, activate a policy, or authorize a
live run.

The implementation is intentionally one carrier rather than one new kernel
mechanism per evidence rung. E1 through E4 use profile kinds and exact stage
tables over the same fixed ABI. A separate dynamic run ID is bound by each
future exact host manifest; the profile kind is not an artifact identity.

## Exact inputs

The checker accepts only the recovered FYG8 kernel source with these base
identities:

- `init/main.c`: `7d281c86ca63646083b9f489eed28281c7d2518f397f34ceccf34c223eaa663a`;
- `init/Kconfig`: `8273d233a441c21df2fcb1d5d17a590321d758205fd5babd8b8dcb4e6a334019`;
- `gki_defconfig`: `12661b7d249fb8f80135c3fdcd331733b86d5215f2f4e88e356d1516831ab493`.

The exact patch SHA256 is
`98bb55be7b87791d5861ebd27c2ceabc234d40ae28a2c4a936cccc728c4c2f1e`.
Applying it to those inputs produces:

- `init/main.c`: `1f695064114ed3d718e5f40a4d5ae4e90ab3dfc303bc78a2d11c8b1af021a53d`;
- `init/Kconfig`: `bac6b3e9b1a836f890d509721c27e1079c7556398518f1ff87eb6f7dbe66e239`;
- `gki_defconfig`: `f123c74fe27330a48e458d146ed05b5e8e1075fbf63cc74afed6e5fe7e48af60`.

## Retained ABI

The carrier uses the already proven FYG8 retained-log mapping at physical
`0x800200000`, total size `0x200000`, and magic `0x4d474f4c`. It requires a
saturated ring and never changes the Samsung ring cursor.

One contiguous 173-byte region is selected immediately behind the append
cursor, with an end-of-payload fallback when the cursor is smaller than the
region:

- immutable entry proof: 45 bytes;
- slot A: 64 bytes;
- slot B: 64 bytes.

The exact immutable proof is
`[[S22P1E|9ac60dac17baf39c32ad46a69174edc7]]`. Its full carrier identity is
`9ac60dac17baf39c32ad46a69174edc75a7481155f57df627da4a78d09909d74`.

Each slot binds format version, slot number, monotonically increasing
generation, stage, outcome, item index, signed detail, carrier ID, profile kind,
dynamic run ID,
initial ring index, initial boot count, CRC32, reserved bytes, and a final
commit byte. Generation parity binds even generations to slot A and odd
generations to slot B.

The writer invalidates the inactive slot, writes its body, and publishes the
commit byte last. It keeps the previously committed slot intact until the new
slot is complete. It rejects generation overflow, any stage other than the
exact next profile stage, profile or run-ID changes, and updates after a
terminal outcome. The host treats a committed but CRC-invalid slot as invalid
and selects the prior valid generation; it fails only when no valid slot
remains.

## Kernel gates

The guarded source is enabled only by
`CONFIG_S22PLUS_FYG8_RUNTIME_CHECKPOINT=y`, with `OF`, `OF_ADDRESS`, and
`CRC32` dependencies. Before the fixed physical address is dereferenced, the
hook requires the `qcom,waipio-mtp` machine, one enabled
`samsung,kernel_log_buf` node with exact address and size, strategy 3, partial
reserved-memory mode, and a direct-mapped `samsung,carve-out` memory-region
that contains the full buffer. The immutable entry is initialized only after
that target gate and the unique successful `kernel_execve("/init")` edge while
the current task is PID 1. Initialization then requires exact retained magic,
a saturated index, enough payload space, and unchanged index and boot count
after publication.

`/proc/s22_checkpoint` is write-only and accepts exactly one 32-byte request
at file offset zero. The request path requires PID 1, a valid header and CRC,
one of four profile kinds, a nonzero dynamic run ID, the exact next stage and
matching generation, module item-index semantics, terminal-only success,
nonzero failure detail, unchanged retained header identity, and the unchanged
immutable entry. Immediate terminal-success publication is rejected. A runtime
client must reopen the node for each checkpoint.

The kernel carrier deliberately does not claim that a stage corresponds to a
real userspace event. That claim must come from the next candidate's static
control-flow checker plus the retained record. The transport and evidence
producer remain separate trust layers.

A read-only API cross-check against the retained FYG8 base source archive
confirmed `struct proc_ops.proc_write`, `proc_create()`, the required OF
address/phandle helpers, and the exact Samsung `sec_log_buf_head` field order
(`boot_cnt`, `magic`, `idx`, `prev_idx`, `buf`). The vendor log driver itself
uses `phys_to_virt()` when the reserved-memory node lacks `no-map`. This reduces
source-API uncertainty but is not a compiler or linked-Image result.

`sec_log_buf.ko` must remain absent from every checkpoint-bearing native module
plan. The carrier depends on the R4W1-D invariant that no later Samsung-ring
writer advances the cursor or overwrites the pre-cursor region.

## Profiles and run binding

Four protocol profile kinds are fixed: E1=`1`, E2=`2`, E3=`3`, and E4=`4`.
Their schema hashes derive from the complete ordered stage sequence, terminal
stage, profile number, and ABI sizes rather than descriptive prose.

The 16-byte run ID is separate and dynamic. P2.7 model IDs are explicitly
non-live. Before any later evidence is accepted, Process v2 must supply the
exact expected run ID from an exact-hash manifest that maps that ID to the
kernel, init, child/helpers, ordered closure, payload roots, stage schema, and
independent checker result. The run ID is a manifest key, not a standalone
cryptographic attestation and not a self-referential hash of binaries that
embed it.

E1 stages cover proc/sys/dev mounts and readbacks, an exact static child token,
exit and reap, five-module watchdog closure, quiet park, and terminal result.
E2 extends this with exact per-module results, platform bind, DWC3 child, and
UDC. E3 adds configfs ACM, peripheral role, `ttyGS0`, and one exact banner. E4
adds one request read, verification, and one nonce-bound response.

## Host validation

The focused suite passes 23 tests. It covers exact ABI sizes and derived IDs,
all profile requests, CRC and reserved-byte corruption, unknown profiles,
invalid stages, terminal semantics, initial state, A/B alternation, torn
inactive writes, committed-new-slot CRC fallback, no-valid-slot failure,
nonadjacent generations, slot-generation parity, profile and run-ID changes,
immediate terminal success, terminal replay, exact expected run/seed/boot
identity, impossible unsaturated seed identity, observer cardinality,
truncation, foreign and partial-family markers, both cursor geometry branches,
exact source and patch identities, weakened target/stage/source gates,
duplicate C transition cases, unsafe run-ID self-copy, commit ordering, and
absence of build or device authority.

The patch applies cleanly to the exact base files. Python bytecode compilation
and `git diff --check` pass. `ruff` is not installed on this host.

## Independent review

One independent reviewer examined the carrier over three rounds. The first
round found five contract defects: missing runtime target geometry gating,
insufficient run/boot identity binding, immediate terminal-success acceptance,
profile/artifact identity conflation, and failure to retain a prior valid slot
when a newer committed slot was corrupt. The second round confirmed those
fixes and found two further issues: partial marker-family tokens were not all
rejected, and repeated kernel writes could pass persistent `run_id` storage as
both `memcpy` source and destination. All seven findings were fixed and pinned
by adversarial tests.

The final read-only re-review reported no critical, high, or medium findings
and returned `GO` for this host-only P2.7 contract. It retained two low risks:
the DT gate identifies the Waipio/Samsung retained-log geometry rather than the
complete product/build identity, and compile, Full-LTO, repeated live updates,
and device behavior remain unproved. Process v2 target and exact-manifest
binding therefore remain load-bearing.

## Limits and next unit

This result is a source-level and executable host-model proof, not a compiled
kernel result. Kernel API compatibility, emitted machine code, Full-LTO
reproducibility, final Image cardinality, candidate control-flow dominance,
retained persistence of repeated updates, and device behavior remain unproved.

The next bounded unit is P2.8: implement the E1 static PID1 runtime, exact
child, and small checkpoint client with compile/static tests and an independent
checker. It remains host-only. One clean R4W1-E Full-LTO build is scheduled
only after the remaining architecture host gates are complete.
