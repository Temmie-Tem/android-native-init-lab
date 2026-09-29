# S22+ P410 installed-Debian handoff: preparation

Date: 2026-09-30 KST. Target: `SM-S906N/g0q/S906NKSS7FYG8` only.
Bounded unit: actual installed Debian PID1 and basic access, following the
[proved P409 readonly transition](S22PLUS_SWITCH_ROOT_P409_FIRST_RUN_2026-09-30.md).
The operator requested work through the point immediately before a physical
experiment. This preparation opens no experimental grant or transfer.

## Current result

P410 `v0.4.0-rc.10` implements the separate
[native-first handoff scope](../operations/S22PLUS_DEBIAN_HANDOFF_V1.md).
Final artifact qualification and independent source-bound review are
**PASS_GO**, with no findings. Fixed foreground D0 preparation completed;
the concrete task is **READY_PRELIVE_ONLY** for `debian-handoff`, one attended
operation and 3600 seconds. No experimental grant, transfer or device control
has occurred. The candidate remains unclaimed and the F1 owner is absent.

The native-first path preserves the existing working UFS/ACM startup and fixed
authenticated health. Real native PID1 retires its workers and performs the
same protected checker, exact root/GPT/marker admission as P409. It closes the
inspector descriptors, ordinarily unmounts the protected root, clears only
entry-41 RAM RO once and mounts a fresh normal RW ext4 filesystem. It never
carries `noload` into a writable remount.

The distinct RAM witness proves the actual writable root transition. Fixed
request 39 then prepares bounded `/run`, devpts, `/dev/shm`, the sole native
block alias and read-only RAM overlays for inittab and the forced SSH command.
Installed `/sbin/init` replaces the witness. Its first synchronous sysinit
hook authenticates current boot/state, verifies actual PID1/root/init and
native-fd retirement, then emits its own proof. Only after the host retains
that proof and sends fixed release 40 may the hook retire native ACM and
allow Debian rcS/NCM/services to start. Failed hooks park instead of returning
an error code that SysVinit would ignore.

## Host ownership and return

One original compound intent owns the native preparation/RW/init/ACM phases.
Neither internal continuation renews the operation or 300-second native
deadline. Host CLOCAL and device raw tty readback cover the deliberate
close/reopen interval. Partial records preserve only independently verified
proof; missing ACKs never permit another request or native connection.

The V3 owner selects exact physical NCM descriptors and MAC, creates only its
bounded local host connection and uses the retained pinned SSH identity.
SSH health must join the same kernel boot already authenticated by the native
observer. The only subsequent remote control is a separately journaled fixed
shutdown. Its ACK and NCM departure are not presented as proof of clean
physical ext4. Normal work then pauses for attended physical Download under
the original window, before one exact original-A transfer and full rooted
Android32/GPT health. Uncertainty retains the owner for original recovery;
proved A with failed final reads permits health-only continuation.

Host connection cleanup checks the original UUID/name/MAC/interface before
deletion, also on stop/recovery. Missing or malformed cleanup evidence cannot
block Android recovery. Raw scientific-proof parsing errors likewise produce
bounded NO_PROOF/evidence-error fields after proved Android closure, without
repeating a transition or retaining the owner merely for a report failure.

## H0 validation

Real ARM64 system-QEMU ran the production parent/helper/witness and retained
installed SysVinit root. Virtual block discovery, console and NCM transport
substitutions are explicit; no result below is Samsung Debian-boot proof.

| Case | Observed result |
| --- | --- |
| Complete path | Actual installed PID1 proof, same-boot pinned SSH, fixed shutdown, clean virtual ext4 and `e2fsck -fn` success |
| Dirty or mismatched root | No writable transition and complete backing disk unchanged |
| Failed first hook or UDC retirement | Hook remains parked; rcS boot-count and SSH absent |
| Corrupt HMAC or stale boot state | No installed-PID1 promotion or rcS/SSH |
| Inherited ACM or state descriptor | PID1 proof rejected; rcS/SSH absent |
| Bad or missing release | Reached PID1 proof retained; rcS/SSH remain blocked |

All eleven VM cases preserved bytes outside native_data. Virtual post-shutdown
cleanliness is reported only for the successful VM, not inferred for a future
physical run. Existing P409 readonly physical raw evidence rederives to the
same proof under the updated default parser.

The real C/PTTY fixture exercises native admission, independent HMAC phases,
pre-send continuation receipts and closed-descriptor raw rederivation. It
separates terminal effects from the ARM64 VM's actual PID1 proof. Focused
tests cover stale/wrong PID/root/init/FD records, partial captures, same-boot
SSH, exact scope, one compound effect, physical pause, uncertain shutdown/A,
health-only recovery and host-only cleanup failures.

H0 caught and repaired two concrete runtime issues: the VM's Linux 5.10 kernel rejects
`CLOSE_RANGE_CLOEXEC`, so the helper closes fd4+ directly and marks only ACM
close-on-exec; a reopened nonblocking tty with VMIN=0 can return zero before
data, so the hook now verifies VMIN=1/VTIME=0. A host fixture extraction bug
mixed buffered I/O with SEEK_DATA/SEEK_HOLE; unbuffered extraction fixed that
audit and the earlier failed captures were preserved. The final runtime VM
results were then checked using the corrected filesystem reader.

The independent review also removed an accidental static dependency on the
historical first-boot owner: the live profile reads only three regular files
from the hash-pinned retained archive. The separate full H0 archive admission
remains unchanged. This changes source provenance, not installed payload bytes.

The first fixed Android preparation completed its health/GPT/statfs reads,
but H0 task publication stopped because the host NetworkManager CLI had been
updated since P401. Credentials, known-hosts and SSH still matched. Host-only
input selection now pins current `nmcli` for a fresh task; later drift rejects
that immutable task. It is checked before connected preparation, and no
access tool is needed to finish original-A recovery. The preserved first
attempt opened no grant and performed no control, transfer or filesystem write.

The refreshed independent review verified all 257 unique frozen source files,
the actual identical A/B/AP bytes and the retained validation joins. All 82
focused tests and Python compilation of 27 touched modules passed. Current
physical helper bytes and generated assets matched the validated VM inputs;
eleven helper/header/physical-build rejection cases also passed. The default
P409 helpers remained byte-identical to their retained predecessors.

Fresh `prepared-2` completed all fixed Android reads. Its 19 raw captures
rederive healthy rooted original Android, exact boot/supporting partition
hashes, unchanged before/after boot, full GPT and Android32 capacity. The
prepared task then passed current live-binding validation without opening a
grant. Its directory contains only the immutable task and proposal; no
operation has been created. This is preparation evidence, not a physical
Debian PID1 or access result.

| Final binding | SHA-256 |
| --- | --- |
| Source closure 2 | `d9abc1ccf626fe290c3b2cdbe492dbfb65b3c950fd65bbe5825f38a5c767afdd` |
| Qualified image receipt | `15c4c5887944cce182d7f2bf95858d96b581612af55b83d5e5b87dd5b9cae390` |
| Boot-only AP bytes | `e408becedd9e913ac6a478c0f212f8437dbcbded59e10226ec0c67ae9e3e4aeb` |
| Independent capability review | `e7a420ad7ed151706a013f1d4bc4bb9d8630debeb4e0b76a1dbb2ef3e94999e2` |
| Prepared task | `cd4731b594bdffddd8581d43ae1cfe35f5f2665ec8c7e307137fc82fa30aebe4` |
| Final prelive audit | `a68a8c156869b0822b81e59bae4dadaabe76dc9da08aaddbc952da20866c7896` |

## Evidence and limits

Private build, raw VM/test, source snapshot, artifact qualification and
preparation evidence are retained under
`workspace/private/outputs/s22plus-debian-handoff-h0-20260930-1/`.
The fresh physical package is under
`workspace/private/outputs/s22plus-debian-handoff-v1/p410/`.
No credentials, device identifiers, firmware, executable payloads or raw
captures are tracked.

P409's readonly result and all earlier consumed journals/grants stay unchanged.
The proposed P410 run introduces a writable Debian lifetime. A forced return
can leave native_data dirty; Android health alone cannot prove its integrity.
Persistence, package workload and ordinary Debian reboot are later bounded
units. A90 and S20+ receive no action from this work.
