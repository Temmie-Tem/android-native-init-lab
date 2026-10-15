# S22+ P430/P431: Debian early PID1 and preparation persist across recovery

Status: **PASS_PERSISTED_EARLY_PID1_PRE_UNMOUNT;
ANDROID_CLOSED_HEALTHY**. Both attended operations are consumed and closed.
Execution date: 2026-10-16 (Asia/Seoul). No F1 owner remains.

P430 produced a 10,972-byte authenticated file which P431 retrieved after the
writer's original-A recovery. Its measured parent is Debian initial PID1;
the source-bound preparation log proves all 76 storage-prefix module completions,
and the 14 chained file records cover READY, six later client BEGIN/return pairs
and UNMOUNT_NEXT. Every client returned zero. The full file and returned-RAM
records join the same writer kernel boot and identical preparation bytes.

This establishes the physical Debian-owned early preparation and recoverable
storage-recording capability. Installed Debian init/services, same-boot SSH,
writer live USB and the unmount syscall's successful return remain unproved.
The later reader's clean filesystem view and both Android health closures are
separate positive observations.

## Scope, authority and unchanged inputs

The operator returned both exact attended grants prepared by the
[P430/P431 H0 qualification](S22PLUS_DEBIAN_ARGV_SUCCESSOR_P430_H0_2026-10-15.md)
and explicitly confirmed physical presence and usable manual Download recovery.
Each grant permits one operation and 1800 original BOOTTIME seconds. The reader
grant opened only after complete writer closure and same-returned-boot RAM capture.

Before execution, the exact tasks, source/review closures, qualified boot-only
packages, readable original A, prior P429 closure and unconsumed claims were
revalidated. Each owner then performed fresh Android/root/GPT/Android32 health
checks before its Download transition. The incorporated common details retained
their AGENTS-pinned digest. Execution used commit
`aaa215964ff67abfc86552c38fae87ddbef8295b` plus the unchanged reviewed working-tree
inputs: 131 host paths and 204/165 writer/reader runtime paths. No execution
source, review, artifact or policy was changed during either operation.

P430 retained the supervised storage-first flow, 16 KiB exclusive-file limit,
absolute 300-second write bound and 360-second host window. The host window
performed no device query or control and made no internal-progress claim.
After it ended, the operator confirmed starting manual Download; the existing
owner verified exact arrival before one original-A transfer. P431 used its
separately approved partition-RO mountless reader, sealed to P430's exact file,
then its normal authenticated return CONTROL and one original-A transfer.
No mount, journal replay, repair or data write occurred in the reader.

A90 and S20+ were untouched. All 46 preexisting working-tree entries were
preserved; this reporting unit changes only GOAL and this report.

## Canonical execution timeline

Times are seconds from each operation's own grant opening. P431 boot-ready
means the authenticated native reader boundary. The writer host window and
later file proof retain their separate meanings. Close includes the H0 audit.

| Event | P430 writer | P431 reader |
| --- | ---: | ---: |
| Live session start | 0.000 | 0.000 |
| Candidate transfer intent | 30.341 | 14.916 |
| Candidate transfer complete | 31.884 | 16.408 |
| Live candidate boot ready | Unobserved | 28.790 |
| Writer host window complete | 392.046 | Not applicable |
| Original-A transfer intent | 427.495 | 40.989 |
| Original-A transfer complete | 428.913 | 42.541 |
| Final Android health complete | 494.826 | 90.079 |
| Live session close | 539.836 | 94.151 |

Each operation consumed exactly one N and one A transfer, with zero additional
recovery transfers. P431's fixed reader completed at 32.631 seconds and its
normal return CONTROL completed at 34.756 seconds.

## Joined physical evidence

The fixed same-returned-Android-boot RAM capture acquired 2,097,136 bytes with
complete before/after health brackets. Production decoders authenticate 158
primary records and three diagnostic records, with no parser error or mixed
boot. The primary sequence reaches `ufs_qcom` DONE and
`TERMINAL result=STORAGE_READY error=0`. The first helper's diagnostic terminal
reports collected exit 0, 76 returned calls, `semantic_done=1`, result 0 and
measured initial PID1. The second helper has an authenticated START with the
same initial-PID1 measurement, but no returned-RAM terminal in the captured view.
Its worker collection and post-file cleanup therefore remain unproved there.

P431 returns **PASS_ROOT_EVIDENCE_OBSERVED**. It keeps partition RO, uses no
mount or persistent write, and observes `state=1`, `recover=0`, `orphan=0`.
The exact P430 file is a regular root-owned mode-0600 single-link file with all
10,972 bytes captured. The H0 collector revalidates both closed owners, original
claims, captured reader bytes, exact writer run/key and measured source closure.
It returns **PASS_PERSISTED_EARLY_PID1_PRE_UNMOUNT** without a device command or
any change to journals or terminal records.

The file contains the measured Debian shell/init/helper header, 8,924 bytes of
complete preparation log and all 14 version-3 chained records. Those records
include six successful pairs for `msm_geni_se`, `gpi`, `i2c_msm_geni`,
`spu_verify`, `mfd_max77705` and `pdic_max77705`. The imported log covers the
preceding 76 modules, including the stock logger and eight UFS modules. The
fixed loading sequence has physical completion evidence for all 82 modules;
individual peripheral functionality remains outside this proof.

The final file record's authenticated time is 3,599 ms from kernel BOOTTIME
origin (1,066 ms helper origin plus 2,533 ms record elapsed). Production decoding
finds no partial tail or client error. An additional H0 join verifies that
both RAM channels name the same boot as the file and that every embedded
preparation line equals the returned primary sequence. Thus the file survives
the writer's physical Android return and the separate native reader boot.

The measured producer reaches this file only after its fixed clean protected
root admission, settled checker and native_data-only writable mount. The
records establish the admitted write path and pre-unmount sequence. They end
before file close, unmount and post-unmount checks; neither their completeness
nor the later clean read retroactively proves those syscall returns. The missing
second-helper terminal does not erase the independently authenticated file.

## Recovery, preservation and bounded completion

Both original-A transfers completed before one post-return ADB read failed with
`error: closed`. P430's failure was in `before/02-health`; P431's was in the
bounded readiness poll `before/wait-076-boot`. The existing recovery owner
continued health only, without another transfer, reboot or native command.
Both final terminals prove changed Android boot, original boot/root and full
GPT/Android32 health: **ANDROID_CLOSED_HEALTHY**, `recovered=true`,
`research_closed=true`.

H0 closure rederives 509 captures and 292 frozen source entries for P430, and
643 captures and 283 entries for P431. The original 16/20-row journals and
terminal records are unchanged; each retains its one classified transient read
failure. Source snapshots and first raw acquisition remain private under
`workspace/private/outputs/s22plus-debian-argv-successor-p430-h0-20261015-1/`,
alongside the returned authorization, grants, claims, closure audits, retained
projection, raw file, collector result and cross-channel evidence join.

The corrected entry now has physical initial-PID1 and persistent-evidence
support; this does not assign a historical physical exit to consumed P428.
P430/P431 are closed and have no replay authority. The next functional unit is
installed Debian init/services and access using this proved early preparation
and storage-evidence path, with any new effects separately qualified and bound.
This physical unit ends with reporting and a scoped commit; no push is selected.
