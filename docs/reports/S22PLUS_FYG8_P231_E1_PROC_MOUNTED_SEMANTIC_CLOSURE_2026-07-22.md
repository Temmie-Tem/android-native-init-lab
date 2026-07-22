# S22+ FYG8 P2.31 E1 proc-mounted semantic closure

Date: 2026-07-22 KST
Tier: H0, host-only evidence correlation
Status: `PASS_P231_E1_PROC_MOUNTED_SEMANTIC_CLOSURE_HOST_ONLY`
Live authority: none

## Result

P2.31 correlates the exact P2.26 candidate closure, P2.29 transfer receipt,
P2.29 raw retained bytes, P2.30 multiboot decoder, userspace control flow, and
kernel write gate. The combined evidence establishes at least one execution of
this exact sequence by the custom PID 1:

```text
mount("proc", "/proc", "proc", ...) == 0
statfs("/proc", ...) == 0
f_type == PROC_SUPER_MAGIC
write(exact E1/PROC_MOUNTED/PROGRESS request)
kernel exact gate stores USERSPACE record
```

This is a technical semantic closure over already collected evidence. It does
not change P2.29's immutable exact-one contract or its durable
`NO_PROOF_F1_V2_CANDIDATE_ROLLED_BACK` verdict.

## Artifact And Transfer Binding

The P2.26 independent checker was rerun from the current tree. Its result was
byte-identical to the archived P2.26 result and again passed the kernel, boot,
ramdisk, static `/init`, child, writer-exclusion, and boot-only AP closure.

The AP identity from that result equals the P2.27 typed static result, the
prepared Process v2 binding, and the completed P2.29 candidate-transfer
receipt. A similarly named older E0 static result has a different AP identity
and is explicitly outside this evidence chain.

## Control-Flow Binding

The exact `/init` requires PID 1 before entering E1. Its first E1 operation is
`mount_proc()`. `mount_and_verify()` returns success only after the mount
syscall succeeds, `statfs()` succeeds, and the returned filesystem type equals
`PROC_SUPER_MAGIC`. `E1_REQUIRE` publishes the first progress checkpoint only
after that operation returns zero; an operation error publishes failure and
parks instead.

The first request decodes as a 32-byte, CRC-valid request with profile E1,
stage `PROC_MOUNTED` (`0x10`), outcome `PROGRESS`, zero detail/item/reserved,
and the fixed candidate run identity. The kernel writer requires PID 1, the
initialized entry state, exact offset and length, byte-exact request equality,
an unchanged retained header, and the exact ENTRY record before replacing it
with USERSPACE.

The writer stores USERSPACE before its final header-stability check. Therefore
the retained record proves that the exact request reached the kernel and the
store occurred, but it does not prove that the write syscall returned success
to userspace.

## Observation Binding

The two pre-candidate baseline reads were byte-identical and clean. The two
post-rollback reads were also byte-identical and contained two pure exact
USERSPACE records with no ENTRY, UNSAT, foreign family, malformed record, or
snapshot-edge partial. P2.30 accepts that raw shape and supplies a lower bound
of two candidate boots under the source-pinned one-write-per-boot guard. This
matches the operator-confirmed missed Download entry and second candidate
boot.

## Exact Boundary

Established in at least one candidate boot:

- the exact P2.26 boot-only candidate was transferred;
- the custom `/init` ran as PID 1;
- procfs mount returned success;
- `/proc` readback matched `PROC_SUPER_MAGIC`;
- the exact first E1 progress request reached the kernel; and
- the kernel exact gate stored USERSPACE in the retained slot.

Not established:

- successful return from the first checkpoint write;
- sysfs, `/dev`, or `/run` tmpfs setup;
- `/dev/null` creation or verification;
- child exec, token, EOF, exit, or reap;
- any watchdog module result or E1 terminal success; or
- USB module registration, platform bind, UDC, ACM, or host exchange.

## Next Bounded Unit

Do not advance to E2. P2.32 is H0 design for continued E1 observation using
the already proven compact frozen-cursor geometry. It must define a bounded
latest-stage record with exact candidate/run identity, strict stage-successor
rules, CRC/integrity checks, and fail-closed handling of torn, mixed, foreign,
or partial records. It should separate:

- E1A: remaining mounts, required node, and exact child lifecycle;
- E1B: the five-module watchdog closure and E1 terminal success.

Only after E1A and E1B are separately evidenced may E2 start USB registration,
platform-bind, and UDC work. P2.31 created no image, manifest, approval, device
action, or live authority.
