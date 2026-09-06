# P346 H0 adjacent failure audit

Scope: S22+ FYG8 retained candidate and its reachable BusyBox/filter/supervisor/
Python result path. No connected device action, candidate preparation, source
activation or repair. This follows the sleep diagnosis in
[S22+ P346 close and H0 report](S22PLUS_FYG8_P346_PREPARATION_AND_D1_RETURN_STOP_2026-09-06.md).
P346 remains consumed and NO_PROOF. A90 and S20+ received no command.

The audit found an additional output-integrity defect and further unsupported
applet false-success behavior. The original sleep problem extends to usleep.
Shell pipeline/command-substitution status masking is an additional semantic
limitation, not a newly discovered shell implementation defect.

## 1. Output below the limit can be lost with outcome `ok`

Priority: fix before qualifying a general read-only command capability.

The actual retained C creates the output pipe with `O_NONBLOCK` on both ends,
then duplicates its write end onto child stdout and stderr without clearing
that flag. The source is inherited from
[`s22plus_fyg8_p327_framed_exec_runtime.py:296`](../../workspace/public/src/scripts/revalidation/s22plus_fyg8_p327_framed_exec_runtime.py#L296)
through the P328 and later transformations. The retained generated P346 source
has the pipe call at line 13095 and stdout/stderr duplication at 13113–13115.
When the child fills the pipe, its writes return `EAGAIN`. An applet that ignores
that error can exit zero. The supervisor's truncation flag counts only bytes it
actually reads; it cannot detect bytes the applet has already dropped.

Actual native-host filter + real C supervisor + Python exchange reproduction:

| Case | Expected output | Received | Status / flags / outcome |
| --- | ---: | ---: | --- |
| BusyBox awk, 10,000 `x` lines | 20,000 bytes | 20,000 bytes | 0 / 0 / ok |
| BusyBox awk, 60,000 `x` lines | 120,000 bytes | 65,536 bytes | 0 / 0 / ok |
| Following substitution/pipeline | `NEXT` | `NEXT` | 0 / 0 / ok |

The failing 120,000-byte result is below the unchanged 131,072-byte output cap.
All sessions reached DONE on the same descriptor. This was independently
reproduced, then persisted in the parent's `join_probe.py` and immutable raw
captures. The host fixture uses the historical filter with host syscall-number
mapping, the target's 100-ms poll cadence, and the existing fixture parent
witnesses; it does not reproduce mounts, UID drop or USB.

The exact extracted AArch64 BusyBox also reproduced the applet failure under
QEMU: with a blocking pipe, the same awk program produced all 120,000 bytes;
with a 65,536-byte nonblocking pipe, it produced 65,536 bytes, encountered guest
write `EAGAIN`, and exited zero. The latter fixture deliberately lets the pipe
fill before reading. It is an applet/backpressure test, not guest seccomp or
new on-device evidence. Combined with the real-supervisor reproduction, this
establishes a concrete H0 output-integrity defect.

The narrow repair direction is to retain nonblocking parent reads while giving
the child blocking stdout/stderr, so the pipe supplies backpressure. Any repair
must still exercise output-cap truncation, timeout, cancellation and descendant
cleanup. No such production change was applied in this audit.

## 2. Unsupported read applets can print invalid values and exit zero

The consumed filter does not allow `prlimit64` or `sysinfo`; its final default
returns `EPERM`. These are different calls from the explicitly allowed
`clock_gettime` and `nanosleep` in
[`s22plus_fyg8_p345_readonly_child.inc.c`](../../workspace/public/src/native-init/s22plus_fyg8_p345_readonly_child.inc.c).

| Command | Required denied call | Reproduced behavior |
| --- | --- | --- |
| ash `ulimit -n` | `prlimit64` query | Prints an incorrect limit with exit 0 |
| BusyBox `uptime` | `sysinfo` | Prints untrusted uptime/load fields with exit 0 |
| BusyBox `free` | `sysinfo` | Prints untrusted memory/swap fields with exit 0 |

All three were first exercised under the native actual filter. The exact
candidate BusyBox was then tested under QEMU with the corresponding syscall
error explicitly injected. Trace receipts prove the denial and zero exit.
For `ulimit`, a separate fixture binds the spawned process's NOFILE soft/hard
limits to 32: the normal query prints 32, while the denied query prints a
different value but still exits zero. This is not merely timing drift between
two valid measurements. Denied uptime/free outputs were also visibly invalid;
some fields may still come from proc reads, so the audit does not claim that
every output field is wrong or establish the internal origin of each value.

This finding concerns these applets under the new child filter. P346's accepted
canary reads the finite `/proc/uptime` snapshot using `cat`, not the `uptime`
applet. It does not invalidate that preserved successful canary or P344's
separate named-command evidence.

Do not resolve this by blanket syscall allowance. `prlimit64` also accepts a
new limit, and direct sysinfo broadens the declared finite snapshot interface.
Use checked reads of the intended snapshot and explicit output invariants for
research evidence; any proposed additional query capability needs its own
narrow argument and scope review. No filter allowance was added here.

## 3. usleep shares the original sleep defect

Exact BusyBox `usleep 200000` normally waits approximately 200 ms. With
`clock_nanosleep` denied, it returns zero in about 19 ms under QEMU, without
applet output. The native actual filter also reproduces immediate zero exit.
This is another exposed applet of the already identified root cause, not a
separate reason to broaden unrelated filter permissions.

## 4. A successful shell status does not prove every subcommand succeeded

Under the actual filter:

- `cat missing-file | wc -c` emits an open error and `0`, but exits zero.
- `printf '<%s>\n' "$(cat missing-file)"` emits the error and an empty value,
  but exits zero.
- The pipeline with `set -o pipefail` exits nonzero in the same fixture.

The real C/Python join also labels the failing pipeline `ok` and retains its
error text in the combined output. The
[exchange outcome classifier](../../workspace/public/src/scripts/revalidation/s22plus_fyg8_research_shell_exchange.py#L217)
uses the shell's final status and framing flags; this is consistent with shell
semantics. It is not proof that the upstream operation succeeded. The current
five-session qualification has additional canary and exact pipeline-output
checks, which prevent simply accepting an arbitrary final marker there.

Future research commands should check the particular producer's status and
expected content. `pipefail` covers pipelines but does not alone make command
substitution inside a successful printf reliable. Unconditionally enabling
`set -e` is not a substitute for checking these cases and could change the
intentional denial canary. No blanket shell-option change was made.

## Evidence and limits

Private evidence root:
`workspace/private/outputs/s22plus_fyg8_p346/h0-adjacent-audit-20260906-01`.

- `probe.py` / `native-results.json`: 15 bounded native actual-filter probes.
- `exact_probe.py` / `exact-results.json`: normal/denied exact BusyBox pairs for
  ulimit, usleep, uptime and free.
- `exact_pipe_probe.py`: exact BusyBox pipe comparison and known-NOFILE-32 query
  control; results in `exact-awk-results.json` and `exact-ulimit32-results.json`.
- `join_probe.py` / `joined-results.json` / `joined-rx-*`: four same-FD real
  C/Python cases, with raw receipt bytes independently reopened and compared.

Exact binary scripts verify the retained BusyBox SHA-256
`d4e1ca8235fd5c47a7dfca5c9c60ad2243f5d17d3c43d58a7c42355f10fa2cba`.
The source fixture remains the byte-identical consumed child fragment
`a053e6796a83767e5de97ed714080a10888e2c9a9ef99dbb06e3aabf1633ae29`.
Raw syscall traces and generated host programs stay private. Traces containing
addresses and invalid numeric values are not copied into this report.

Native date, file listing, bounded cat/wc and small output/pipeline controls
completed; statfs, supplementary-group lookup and kill-zero probes surfaced
failure rather than silently passing. These probes are not a complete BusyBox
compatibility census. Cancellation, timeout, wait-error and descendant cleanup
review found no additional false-success defect. A partial CANCEL at child
exit deliberately stops with protocol failure, and a complete late CANCEL is
explicitly handled; neither was relabeled a new defect.

Independent review reproduced the native output loss, reviewed the exact-binary
and known-limit controls, and agreed on output-integrity-first prioritization.
No new claim of device isolation, complete qualification or automatic recovery
is made. Production code, consumed bindings, journals and formal results remain
unchanged. The prior H0 sleep patch remains unapplied.

The separately authorized implementation and preparation are recorded in the
[P347 report](S22PLUS_FYG8_P347_OUTPUT_TIMING_PREPARED_2026-09-06.md).
