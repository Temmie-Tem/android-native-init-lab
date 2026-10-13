# S22+ Debian storage-first file evidence V1

Status: **REVIEW_GATED_CAPABILITY**. Select only `SM-S906N/g0q/S906NKSS7FYG8`,
the retained Android32 GPT and native_data entry 41. This separately reviewed
sibling uses profile `debian-file-first-v1` and V3's existing `debian-early`
owner. It grants no effect through H0 definition, build or qualification.

All lifecycle, target, clean-only full-root admission, 16 KiB exclusive-file,
absolute 300-second BOOTTIME write bound, checked cleanup, physical original-A
recovery, no-replay and separate-retrieval conditions of
[file pilot V1](S22PLUS_DEBIAN_FILE_PILOT_V1.md) apply unchanged, except for the
explicit preparation and record changes below. Its original 73+8 preparation
and eight-record format remain selected only by the old profile.

## Fixed preparation before the record

The initial Debian shell PID1 launches one fixed storage helper. Its sealed
module order is the stock `sec_log_buf`, the original platform prefix through
`qcom_spmi_pmic` (68 modules including the logger), then the same eight UFS
modules. The 76-module prefix retains the corrected exact stock logger binding
and SPMI/PM8350c/GPIO barrier from the integrated boot capability. Actual module
bytes, parameters, kernel ABI and earlier symbol suppliers are checked in the
new order. Presence, module fd contents and insertion results are checked at
each effect; no unload, retry, alternative parameter or ambient loader exists.

Checked bounded RAM records and stock kernel retention cover this prefix.
This explicitly adopts the integrated profile's fixed `/dev/kmsg` record and
readback mechanism, stock logger and same-returned-Android-boot bounded
`last_kmsg` retrieval. No reserved-memory mapping or arbitrary dump is added.
The prefix includes existing USB drivers, but never creates a gadget, publishes
a UDC, opens ACM or waits for a host request. Physical storage readiness is an
experimental result, not a consequence of static supplier compatibility.

The second fixed child measures actual initial PID1, run, current kernel boot,
source hashes and the complete storage-prefix RAM log, then performs the
unchanged clean-only protected checker and complete root comparison. Only an
exact settled checker and successful admission allow the one native_data RW
mount and fixed exclusive file. No installed Debian init or service executes.

## Checked records before deferred clients

The same root-owned 0600 single-link `var/lib/lab/s22-evidence-<sealed-run>` is
created once. Its version-2 magic and separate authentication domain
`S22PLUS-FYG8-DEBIAN-FILE-FIRST-v1` prevent reinterpretation as the older pilot.
The 256-byte authenticated header, complete bounded prefix log and 14 chained
128-byte records must fit the unchanged 16384-byte maximum. A record contains
fixed sequence, kind, phase, elapsed time and errno, with no free-form command.

Header, log and READY each require one checked write, file synchronization and
exact bounded readback; directory/file creation also checks parent sync.
Only then may the writer process the six sealed clients, in this order:
`msm_geni_se`, `gpi`, `i2c_msm_geni`, `spu_verify`, `mfd_max77705`, `pdic_max77705`.
It checks the complete client set first and reopens/revalidates the exact module
fd at each effect. For each client, one synchronized/read-back BEGIN precedes
the direct fixed `finit_module(fd,"",0)` and one checked result follows its
return, fd close and module-presence check. No extra child, IPC, general command
or descriptor handoff is added. A BEGIN proves intent, not syscall entry; a
successful result proves insertion/presence, not every asynchronous driver
probe or a usable USB endpoint.

A write/sync/readback failure admits no later record or module attempt. A module
error can be recorded once only while the same original deadline remains valid;
it stops all later clients. A blocked kernel call can outlive the userspace
deadline and leave RW mounted. Only attended physical recovery addresses that
case. It is never described as automatic recovery or safe quiescence.

The final in-file record remains `UNMOUNT_NEXT`. Close, one ordinary unmount,
partition RO restoration and clean/GPT checks retain separate outcomes. No
remount is allowed to add a later success record. No overwriting, rotation,
journal replay, repair, reinstall or other-partition write is admitted.

## Fixed supervised diagnostic variant

The separately reviewed `debian-failure-observer-v1` variant retains every
storage/file/module/deadline/return boundary above. For this variant only, each
of the two existing helpers contains one fixed supervisor and one forked worker
running that same executable's fixed function. Both supervisors measure the
exact initial Debian shell and init before fork; workers validate their known
supervisor. Anonymous shared RAM and exact-child wait replace the old direct-
child/no-extra-child restriction only for this closed observer structure.
There is no selectable command, general IPC, descriptor handoff or new service.

Stable atomic snapshots separate immediate module return/errno, subsequent
close/presence, primary evidence result and worker outcome. At most two bounded
independent authenticated `S22DIAG1` records per helper use the existing checked
kernel-log carrier. Worker primary-evidence failure still stops later module/file
work; the parent may then publish its bounded diagnostic. Loss of that optional
parent diagnostic alone adds no new gate. Missing or unstable evidence remains UNKNOWN. A call-armed
record is not syscall-entry proof. Exit/reap does not prove checker descendants,
filesystem cleanup or recovery. Parent-death signaling does not establish
cancellation of an uninterruptible kernel call. At the original absolute
300-second bound the supervisor parks before releasing the shell to another
helper; the worker rejects later module/storage effects if it returns late.

The persistent layout differs only by version-3 magic/domain and explicit
supervised ancestry. The same 256-byte header, bounded preparation log and
14 chained records fit the unchanged 16 KiB maximum. No new persistent record,
replay, repair or post-unmount remount is permitted. Returned-boot D0 decodes
both primary and diagnostic record kinds from the same fixed raw capture before
a separate exact-run mountless reader. Each retained observation, pre-unmount
file history and current Android health remains a separate fact.

## Host owner and later evidence

One returned attended 1800-second/one-operation grant, one fresh N intent, the
original fixed 360-second host opportunity window, one physical original A and
complete Android32 health retain the existing owner semantics. N intent consumes
all automatic module and storage effects, including partial and absent records.
No legacy grant, old candidate or empty record opens another attempt.

After complete original-A closure, the separately bound mountless reader may
select this writer's exact run file. It authenticates exact raw bytes with the
writer's retained key, source measurements and format. Partial records and
client errors remain partial; a missing home-block record does not establish
non-execution, particularly on a dirty filesystem. Journal recovery, if needed,
is a separate reviewed owner, never an implicit part of this writer or reader.
The fixed returned-boot RAM capture is optional complementary evidence and has
the same absence/partial limits. Neither later Android health nor a complete
pre-unmount file proves the writer's successful unmount or current cleanliness.

Independent review covers the changed common/target specialization, producer,
decoder, actual artifacts and reachable owner. Qualification includes the real
ARM64 writer and separate reader without USB, failed pre-client synchronization,
module error, partial records, checked readback, child settlement and one-shot
cleanup. A90, S20+ and all consumed histories remain outside this scope.
