# V3431 S22+ PID1 Keystone Design Host Pass

## Verdict

`PASS; PID1-FIRST KEYSTONE CONTRACT CLOSED; HOST ONLY; NO LIVE`.

V3431 replaces the V3429 multi-gate observer candidate with a minimal proof
contract. A future candidate must first observe raw `getpid()==1`, load only the
exact dependency-free `sec_log_buf.ko` bundled in its ramdisk, require the two
observer proc nodes, emit one run-bound marker, and park. The first rollback
`/proc/last_kmsg` then supplies the only accepted positive evidence.

No candidate source, image, AP, helper, exception, device contact, reboot,
module insertion, or flash was produced or performed.

## Closed Facts

```text
kernel /init is executed by the PID1 kernel-init task       VERIFIED
finit_module success follows module init and LIVE state    VERIFIED
sec_log_buf load-bearing probe builders are synchronous    VERIFIED
/dev/kmsg write reaches capture hook before return         VERIFIED
sec_log_buf hard/soft dependencies                         none / none
CONFIG_SEC_DEBUG                                            m
V3428R manual-transition retention positive control         pinned
V3430 no-proof + pre-module osrelease bug                   pinned
native panic/pmsg/ramoops no-hit reports                    pinned
```

The observer is intentionally part of the keystone. The design does not claim a
pure module-free proof. An exact retained marker is conclusive for direct PID 1
execution plus observer activation; marker absence remains NO_PROOF.

## Contract

- Schema: `s22plus_v3431_pid1_keystone_design_v1`
- Protocol: `S22P1K1`
- Contract SHA256:
  `686207c75d2530f90049de6b6945fbd3134019ca402f84cb97418c43804a4ca5`
- Positive: `PASS_PID1_EXECUTION_AND_OBSERVER_LOAD`
- Absence: `NO_PROOF_PID1_VS_OBSERVER_UNRESOLVED_STOP`
- Integrity error: `FAIL_STOP`

The parser rejects duplicate markers, non-one PID, wrong sequence, wrong module,
contract or context, bad CRC, truncated frames, and raw current-run tokens that
are not part of one valid frame. Historical foreign-run frames cannot satisfy
the current run.

## Validation

```text
V3431 focused tests             23/23 PASS
generated contract check       PASS
exact source/report pin audit  PASS
device actions                 0
```

The generic mechanics were also cross-checked against upstream Linux initramfs,
Linux ramoops, AOSP ramdisk, and Android common module-loader sources. Exact FYG8
source and live reports remain the Samsung-specific authority.

## Next

V3432 is a host-only source/build unit for the exact freestanding candidate. It
must prove by source, disassembly, and QEMU/selftests that `getpid()==1` dominates
the one module load and marker write, that the marker PID is derived from the
syscall result, and that no fork/clone/exec, panic, reboot, USB, persistent write,
or pre-marker runtime osrelease check exists. No live helper or exception should
be created in that unit.
