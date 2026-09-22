# S22+ P403: fixed Debian userspace proved, healthy Android return

Date: 2026-09-23 KST (2026-09-22 UTC). Target: `SM-S906N/g0q/S906NKSS7FYG8`.

The attended P403 `v0.4.0-rc.3` operation proved its fixed installed-Debian
workload on the actual Samsung device: `PASS_PROBE_COMPLETED` and
`PROVED_FIXED_DEBIAN_USERSPACE`. The protected root comparison matched all
8,969 expected entries before one unprivileged child executed the installed
shell, numeric identity tools, external libc program and nested shell/exit
workload. Expected output, setup/exec evidence and process settlement agreed.

The operation returned normally to original Android with
`ANDROID_CLOSED_HEALTHY`, `recovered=false`. Rooted health, original boot and
supporting partition hashes, unchanged complete GPT and Android32 statfs total
34,357,624,832 bytes all passed. The final Android boot differs from the entry
boot. The F1 owner is retired and the one-operation grant is consumed and closed.
This diagnostic chroot proves neither Debian host PID 1 nor networking/SSH.

## Actual workload and protected storage

The exact native partition received RAM block-RO protection before mounting.
The ext4 superblock was clean with no RECOVER bit or orphan head. Start and
completion records, the witness and the expected archive closure matched;
only the three records and empty root-owned `lost+found` existed beyond that
closure. No missing, metadata or content mismatches were observed.

| Observation | Actual result |
| --- | --- |
| Expected archive / boot-input subset | 8,969 matched / 8,175 matched |
| Known regular-file content hashed | 199,362,324 bytes |
| Bounded root tree | 8,973 entries; no unexpected node types |
| Child setup | Private readonly executable mount, chroot, all UIDs/GIDs 65534, zero capabilities and `no_new_privs` verified |
| Installed programs | `/bin/sh`, numeric `id`, external `printf`, synchronous nested shell |
| Expected nested exit | 23, observed and checked by the workload |
| Child output | Exact 100-byte stdout; empty stderr |
| Direct child / descendants | Exit 0, reaped, no adopted descendants, settled to `ECHILD` |
| Parent protection / cleanup | Readonly, noexec and partition block RO rechecked; ordinary unmount completed |
| Final native storage guards | Complete superblock and GPT readbacks unchanged |
| Outer probe capture | 1,262-byte stdout; empty stderr; authenticated completion and DETACH |

The exact child output was:

```text
UP_WORK shell uid=65534 gid=65534
UP_WORK libc external
UP_WORK fork child
UP_WORK exit observed=23
```

The observed SHA-256 is
`1b968a668eb78a2484c93e3b520e178f2058f192ee51694101defc247f5e6577`,
matching the compiled workload's expected output. The setup pipe contained the
complete ready record without an exec-error record. Exit zero alone was not
the success criterion. No filesystem data write, repair, installation, service,
network operation or PID 1 handoff was part of this probe.

This establishes the installed dynamic loader and libraries used by the fixed
programs under the FYG8 kernel. It does not qualify every Debian program,
Debian init, hotplug, USB networking, or the P401 bootstrap/handoff path. P401's
consumed NO_PROOF result remains unchanged.

## Canonical journal-derived timeline

Times are seconds from the original 1800-second grant opening. The grant
retains the operator's actual returned start statement; its clock was never
renewed. Intent and completion are separate observations.

| Elapsed | Event | Evidence boundary |
| ---: | --- | --- |
| Before operation selection | First host launch could not acquire the shared session lock | No operation directory, device command or capacity consumption |
| 49.332 | Fresh execution preflight complete | Exact rooted original-A health |
| 49.425–53.024 | Android Download request and departure | One control intent/result |
| 62.112–63.609 | P403 transfer | One candidate claim and completed Odin capture |
| 76.079–78.997 | Protected root and fixed userspace probe | One pre-EXEC intent; complete authenticated result and DETACH |
| 80.418–81.138 | Same-boot native Download return | Fresh health, CONTROL and measured departure |
| 87.186–88.742 | Original-A transfer | One exact completed transfer |
| 137.185 | Final Android health complete | Full root/hash/GPT/Android32 brackets passed |
| 182.363 | Finite grant closed after H0 audit | Raw evidence rederived; owner absent |

The initial lock acquisition returned `BlockingIOError`/`RegistryUnavailable`
before operation creation. Subsequent host inspection found no retained
operation, F1 owner or pending D1 intent, and successfully acquired/released
the unchanged lock. The exact competing holder was not established. The next
launch used the same grant and deadline; it did not replay a device action.
The host failure summary is retained separately from the operation journal.

There were one N transfer, one probe execution, one original-A transfer and
zero additional recovery transfers or health continuations. No physical
Download intervention was needed. P403 received no reusable native admission.
No A90 or S20+ target command was issued by this task.

## Retained evidence and next boundary

The private run is
`s22plus-debian-userspace-probe-h0-20260923-1/prepared-1/task/operation-0001`.
Its task directory retains the raw-rederived closure audit, closed grant and
220-file source snapshot joined to the independent review. The six completed
steps and all five effect intents were rederived without another device action.

| Record | Bytes | SHA-256 |
| --- | ---: | --- |
| Immutable terminal | 3,135 | `5a567a34ff3262a3dfafc516a4f6d264db1f526b7f384546cf570b5d95f76136` |
| Raw-rederived closure audit | 1,769 | `5ff50e06fc5f8b41ddad91be077061dca0cd53542aa80b112a3fd440cadf8133` |
| Finite task close | 2,954 | `56e28886e2c22c02158dc3ad28be1224a715d8a5543bf810c637c7eb0606918f` |
| Source snapshot manifest | 124,202 | `f62a1c336e3be5ee3d2f1b08678827699db7149736bb3bfa45f99f9b57a92f5e` |

Source commit at execution was `0da3de4eceb699b7992939de93d6180a412437a4`.
The snapshot preserves the actual reviewed bytes, including preexisting
working-tree contract content. The [H0 qualification](S22PLUS_NATIVE_USERSPACE_PROBE_H0_2026-09-23.md),
[fixed probe policy](../operations/S22PLUS_NATIVE_USERSPACE_PROBE_V1.md) and
[P402 inspection](S22PLUS_NATIVE_ROOT_INSPECTION_P402_FIRST_RUN_2026-09-23.md)
remain separate evidence inputs.

Stage 3 is complete. The next useful bounded work is H0 preparation of the
full Debian init handoff and its post-handoff observation/recovery path, using
the installed root and this functional evidence. A new live candidate requires
its own reviewed scope and current authority. This closed grant authorizes no
P403 replay, further chroot, rootfs reinstall or PID 1 handoff.
