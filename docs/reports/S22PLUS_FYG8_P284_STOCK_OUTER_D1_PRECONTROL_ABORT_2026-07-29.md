# S22+ FYG8 P2.84 stock outer-work D1 pre-control abort

Date: 2026-07-29 KST

Scope: one commit-bound D1 setup under approval
`DEVICE-ACTION-D1-P284-STOCK-OUTER-V1-APPROVE:b4eb6f57455a0a6687adfc2a30e371bf7dcca62b`.
No payload, partition action, role write, reboot, property change, `adbd`
restart, control lane, challenge lane, or F1 action occurred.

## Verdict

`ABORTED_PRE_CONTROL_KRETPROBE_READBACK_NORMALIZATION_BUG; ZERO_ROLE_WRITES; CLEANUP_AND_HEALTH_PASS`

The trace definitions were accepted, but setup compared kernel-normalized
kretprobe readback against an input-spelling regular expression. It counted
only the 19 entry/offset probes, expected 27, and stopped before creating the
trace instance or launching control.

The same defective expression initially made cleanup report zero while eight
`r16:` return probes remained. An exact group search caught them immediately;
all eight were removed by exact event name. Final cleanup and device health
pass. The approval is consumed and must not be reused.

## Preflight

Immediately before D1 mutation:

- HEAD was exactly `b4eb6f57455a0a6687adfc2a30e371bf7dcca62b`;
- tracked status was clean;
- all 60 P2.84 frozen source receipts matched;
- exactly one attached target matched `SM-S906N/g0q/S906NKSS7FYG8`;
- Android boot, stopped boot animation, root UID 0, and running `adbd` passed;
- parent mode was `peripheral`; parent and child runtime status were `active`;
- EUD enable was zero;
- exact DWC3 and HS-PHY module hashes matched;
- every required module-qualified symbol had cardinality one;
- tracefs contained no `p284stock` event or instance; and
- no global IPv4 or IPv6 address existed, so TCP ADB remained excluded.

The host-side runner contained all 27 committed definitions byte-for-byte,
used no forbidden transport or partition operation, and had SHA256
`a75c4a193fd2b1db5fcd01611ed95c6dc5bcb01d0a49336d5e707aa369c0843e`.

## Exact actions

The first temporary-file transfer stopped before copying any runner bytes:
the root-created `/data/local/tmp/p284stock-v1` directory was not writable by
the `adb push` shell user. Role and tracefs state were unchanged. The directory
was opened only for that exact transfer, then restored to root-only mode. The
transferred runner hash matched the host hash.

The synchronous `setup` action then:

1. wrote the 27 approved kprobe/kretprobe definitions;
2. read `kprobe_events` before creating an instance;
3. counted lines using `^[pr]:p284stock/`;
4. obtained 19 instead of 27; and
5. returned before `mkdir instances/p284stock`.

The detached `control` entry point was never invoked. Therefore:

- NONE writes: 0;
- PERIPHERAL writes: 0;
- watchdog arms: 0;
- normal reboots: 0;
- control attempts: 0; and
- challenge attempts: 0.

## Root cause

Kretprobe input without explicit maxactive is written as:

```text
r:p284stock/event ...
```

The exact kernel fills the default `kretprobe.maxactive`. On this eight-CPU
target it becomes 16, and `trace_kprobe_show()` renders:

```text
r16:p284stock/event ...
```

The exact source makes both transformations explicit:

- kretprobe registration replaces nonpositive maxactive with
  `max(10, 2 * num_possible_cpus())` under preemption; and
- readback prints `r`, then the nonzero resolved maxactive, then `:group/event`.

All 19 entry/offset probes appeared with `p:`. After the initial cleanup, the
eight exact return probes appeared with `r16:`:

- `mode_store_out`;
- `outer_sm_work_out`;
- `stop_peripheral_out`;
- `child_suspend_out`;
- `phy_suspend_out`;
- `phy_power_out`;
- `parent_runtime_suspend_out`; and
- `parent_suspend_out`.

Thus registration was complete `27/27`. No symbol or instruction offset was
rejected. The failure was solely a readback representation bug.

## Cleanup and health

The first cleanup pass used the same bad expression. It removed the 19 `p:`
events and incorrectly reported zero. A prefix-independent
`grep p284stock` then found the eight `r16:` events. Exact-name deletion
removed all eight.

Final authoritative checks proved:

- actual `p284stock` lines in `kprobe_events`: 0;
- `instances/p284stock`: absent;
- `/data/local/tmp/p284stock-v1`: absent after host evidence capture;
- parent mode: `peripheral`;
- parent runtime status: `active`;
- child runtime status: `active`;
- Android boot complete;
- boot animation stopped; and
- root UID 0.

No reboot or recovery contingency was needed.

## Permanent correction

The attachment-name gate now has a separate kernel-readback audit. It accepts
entry prefix `p:` and return prefix `rN:`, normalizes decimal readback offsets,
and still requires exact event name, entry/return kind, module, symbol, and
offset. A regression fixture reproduces the exact `19` false legacy count
versus `27` normalized count and proves that a missing `r16:` return event
fails closed.

The private runner now uses `^(p|r[0-9]*):p284stock/` for setup, precondition,
cleanup, and final cardinality, and propagates setup exit status explicitly.
Its corrected SHA256 is
`e9bf998fb8a419a812e57404e86d38586d0fc9693ba11da267c52299ca1d3cf7`.
It passed host syntax and exact-definition checks but was not executed.

This is another input-spelling-versus-readback-invariant defect. Future
tracefs live gates must validate the kernel's normalized readback, not count
the submitted textual prefix.

## Validation

- 43 combined P2.80/P2.82/P2.84 trace/name-gate tests pass;
- eight P2.84 source-contract tests pass;
- all 60 frozen P2.84 source receipts remain exact;
- the corrected runner retains all 27 committed definitions byte-for-byte;
- three recorded private-evidence hashes revalidate; and
- `git diff --check` passes.

## Authority

The approved D1 stopped during setup and is closed. Neither its unexecuted
control nor challenge may be retried under the same approval. Any later stock
D1 requires the corrected committed gate/runner closure, a clean connected
D0, and a fresh approval. No F1 authority exists.
