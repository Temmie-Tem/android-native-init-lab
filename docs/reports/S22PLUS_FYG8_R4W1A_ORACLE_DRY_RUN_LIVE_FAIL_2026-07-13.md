# S22+ FYG8 R4W1-A Oracle Dry-Run Live Fail

Date: 2026-07-13 KST
Target: `SM-S906N/g0q/S906NKSS7FYG8`
Scope: one attended zero-flash `bugreportz -s` oracle rehearsal

## Verdict

`FAIL_R4W1A_ORACLE_DRY_RUN_CLEANUP_OR_SHAPE`

The one-shot was consumed and is retired. It must not be retried. The helper
failed closed because its reviewed contract required exactly one durable new
file under `/bugreports`, but the exact FYG8 streaming path left no direct file
after returning. No oracle PASS record exists and the retained-PID1 candidate
policy remains inactive.

This was not a bad-ZIP, device-health, reboot, or flash failure. The stream was
complete and later passed the pinned parser host-only. That forensic result
does not retroactively change the live verdict.

## Exact Run Evidence

- helper SHA256:
  `d541397c823b7c6311dbec950dd3a82dc6a5881984b45838c99ffedebc2d3d14`;
- source-ready commit: `6f78610b`;
- active-policy commit: `3ddfee1e`;
- private run:
  `workspace/private/runs/s22plus_fyg8_r4w1a_oracle_dry_run_20260713T095754Z`;
- result SHA256:
  `3d0e470d457241808dbcf5b24ba9bde37710905a7feb20943f21605230fe2af4`;
- canonical timeline SHA256:
  `a8e575090827a72d7732e34cc568f06229e5205ac2d3bb55481973f0959dd581`;
- consumed-state SHA256:
  `61b613c87ebadcd1694d6c61f1b3569a7506902f3b257bc9965e25a1ef02da77`;
- oracle PASS record: absent;
- candidate consumed record: absent.

The timeline contains exactly the eight canonical event names. The one-shot
was consumed at `2026-07-13T09:57:55.901663Z` immediately before capture.

## Connected Baseline And Final Health

Pre-capture gates passed:

- exact FYG8 model/device/build and completed Android boot;
- stopped boot animation and orange verified-boot state;
- Magisk `uid=0(root)`;
- exact known Magisk boot, stock DTBO, and stock recovery;
- no Odin endpoint;
- `sec_log_buf` Live and exact platform bind;
- complete 2,097,136-byte `/proc/ap_klog` and `/proc/last_kmsg` reads;
- R4W1 marker family absent from both baseline observers;
- pstore console paths absent.

Final Android revalidation reproduced exact model/device/build, Magisk root,
boot, DTBO, recovery, boot completion, stopped boot animation, orange state,
and no Odin endpoint. No reboot, Download transition, Odin transfer, candidate
or rollback flash, partition write, panic, or SysRq occurred.

## Capture Result

The single command was `adb exec-out bugreportz -s` through the redacted exact
target. It returned:

- return code: `0`;
- EOF-complete stdout: `14,461,892` bytes;
- stream SHA256:
  `0935e3215ea39c5c9113f71a1de71e7a63de60f947878527a9926ba86aa071b1`;
- stderr: `0` bytes;
- `/bugreports` before inventory: empty;
- `/bugreports` after inventory: empty;
- preexisting inventory unchanged: true;
- added durable files: zero;
- cleanup attempted: false;
- cleanup needed for a durable direct file: false in observed live state.

The helper was intentionally stricter than the observed platform behavior. It
required exactly one added file, so it stopped before parser invocation and did
not manufacture `cleanup_verified=true` from an empty delta.

## Host-Only Forensic Parse

The immutable captured stream was parsed only after the live helper had ended.
This analysis contacted no device and created no live promotion state.

- forensic parser result SHA256:
  `ff5a229a0c1ebb93b71bf8ec589a80b15488773bcd7bf9b3b01ec23c40d28a1f`;
- verdict: `PASS_R4W1A_BUGREPORT_ORACLE_PARSED_HOST_ONLY`;
- same-file pre/post SHA256: true;
- ZIP entries: `315`;
- all entry CRCs checked: true;
- ZIP version: `2.0`;
- `main_entry.txt`: unique and selects `dumpstate.txt`;
- main entry size: `91,074,058` bytes;
- exact `LAST KMSG (/proc/last_kmsg)` section: one, complete;
- last-kmsg section size: `2,097,136` bytes;
- following section boundary: complete;
- dump read error: false;
- archive and last-kmsg marker-family counts: zero.

This proves the FYG8 stream and parser shape selected by A0. It does not prove
the remote/stream identity condition required by the consumed policy, because
the platform exposed no durable remote copy after stream completion.

## Root Cause

The static audit correctly identified that dumpstate builds a ZIP locally
before copying it to the control socket, but incorrectly promoted that internal
temporary file into a durable post-return `/bugreports` identity oracle. Exact
live evidence disproved durability.

AOSP corroborates the distinction: `-s` selects `stream_to_socket`, and
`FinishZipFile` copies the generated path to the control-socket fd. Temporary
paths are separately subject to cleanup. These references are corroborative;
the exact FYG8 before/after inventory and captured bytes are load-bearing.

- <https://android.googlesource.com/platform/frameworks/native/+/android16-release/cmds/dumpstate/dumpstate.cpp#2559>
- <https://android.googlesource.com/platform/frameworks/native/+/android16-release/cmds/dumpstate/dumpstate.cpp#2666>
- <https://android.googlesource.com/platform/frameworks/native/+/android16-release/cmds/dumpstate/dumpstate.cpp#3231>

## What Is And Is Not Proved

Proved:

- exact FYG8 shell can trigger one bounded zipped dumpstate stream;
- stream EOF, rc, stderr, ZIP, CRC, and parser shape are valid;
- dumpstate includes exact `/proc/last_kmsg` when both pstore console paths are
  absent;
- marker-absent baseline classification works;
- no durable direct `/bugreports` side effect remained after completion;
- Android/Magisk health remained exact.

Not proved:

- the consumed remote/stream identity and cleanup contract;
- an oracle PASS promotion record;
- the candidate marker-positive path;
- direct-PID1 execution;
- candidate boot viability or rollback in this unit.

## Next Gate

The next unit is host-only A4 contract correction, not another live run. It
must decide whether this immutable stream proof is sufficient to replace a
second baseline oracle or whether a new v2 one-shot is irreducible. Any
successor must use the EOF-complete host stream as the canonical artifact,
require same-file pre/post SHA256 and size, parse that exact file, require
unchanged `/bugreports` inventory for `-s`, perform no remote deletion when no
new file exists, and remain fail-closed on any changed or added entry.

No successor helper, ACTIVE clause, acknowledgement, candidate transfer, or
flash is authorized by this report.

Post-A4 close: the host-only successor validator independently pinned and
revalidated every retained raw input and returned
`PASS_R4W1A_STREAM_ORACLE_EVIDENCE_QUALIFIED_HOST_ONLY`. It concluded that the
existing stream contains the complete corrected baseline evidence and a second
device-side baseline is not required. The historical live FAIL and retired
policy remain unchanged. See
`docs/reports/S22PLUS_FYG8_R4W1A_A4_STREAM_ORACLE_QUALIFICATION_2026-07-13.md`.
