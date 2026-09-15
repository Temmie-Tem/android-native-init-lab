# S22+ native GPT reservation and Android initialization V1

Status: **REVIEW_GATED_CAPABILITY**

This capability is restricted to the operator-owned
`SM-S906N/g0q/S906NKSS7FYG8`. The common G2 exception and exact target adoption
specialize their ordinary boot-only, no-GPT/format and A-only recovery rules
only through this policy. Independent source-bound review and an actual
separately returned finite attended grant are mandatory before any effect.
Definition/review opens no grant and renews no consumed authority.
Two fixed transitions are named; this is not a caller-sized partition tool:

| Transition | Original userdata / native | Proposed userdata / native |
| --- | --- | --- |
| Historical P397 reservation, consumed and closed | Stock extent / absent | 95.4580078125 GiB / 128 GiB |
| Prospective Android32 successor | 95.4580078125 GiB / 128 GiB | 32 GiB / 191.4580078125 GiB |

For the successor, "original" always means the completed P397 pair, not the
pre-reservation stock pair. It preserves native entry 41's GUID, type, name,
attributes and end while moving only its start from LBA 28,750,592 to
12,115,456. Userdata stays at LBA 3,726,848 and ends at 12,115,455. Its exact
private proposal derives from the closed P397 rooted Android/reboot proof and
must be freshly read back through the successor native endpoint before apply.
The native entry remains unformatted. The operator permits loss of Android apps, settings and
data and requires root to be retained/reestablished. The final environment is
Android. Correct Android-reported storage capacity, unchanged GPT and numeric
root must be checked before and after one ordinary Android reboot.

## Fixed metadata and recovery model

Only LU0 GPT LBAs 1, 3, 62,305,272 and 62,305,279 may change, using the sealed
original and proposed 61,440-byte private captures. The reservation changes
entry 40's ending LBA and creates entry 41; the Android32 successor changes
only entry 40's end and the existing entry 41's start. Both update the matching
table/header CRCs. All other
39 entries, PMBR, disk identity, padding and existing duplicate GUIDs remain
exactly original. No PIT, bootloader, fuse, EDL or unrelated partition rewrite
is part of this design. Generic census `NO_PROOF` remains unchanged.

The native endpoint binds the FYG8 UFS controller, LU0 ancestry, userdata
index/start/allowed size, block size, whole-disk capacity and held block node.
It must first be qualified read-only on the new admitted native image. Each
effect requires a host durable intent before its authenticated EXEC and the
native exclusive marker. The native runtime is the sole partition writer.
The fixed endpoint creates only its own mode-0400/0600 LU0 alias in `/dev`
tmpfs, verifies it, opens the exact held block device exclusively and removes
that alias before I/O. Apply/restore also create distinct exclusive markers
in `/s22-root-work` tmpfs. An existing alias/marker fails closed. These RAM
objects never replace the durable host target/proposal claim or effect intent.
Effects use one aligned direct/synchronous write per selected block, a sync,
complete readback and an exact surviving copy check. Failed or uncertain
writes and syncs are never retried.

The native and Android readers derive both userdata and native extents from
the selected sealed pair. The successor's original/recovery map contains the
128 GiB native entry; absence is invalid there. The short interval after apply
uses the original kernel map, while fresh boots must publish the proposed map.
The four-block core, write ordering and serial partial-write restoration model
are unchanged. Restoring the successor returns P397's GPT and, after a reset
intent, requires a distinct 95.4580078125 GiB restorative stock reset.

Apply begins only from the complete original pair and writes backup array,
backup header, primary array, primary header. Restore repairs the side opposite
the sole exact surviving copy first and requires a fresh complete original
readback to finish. The reviewed stock PE model supports native reentry for
the declared serial partial-write states; arbitrary media corruption and
physical restoration are unproved. Status or child publication alone cannot
prove a valid GPT because stock copy repair can ignore a write failure.

Original Magisk A can recover boot only. After a GPT intent, an A transfer must
be blocked until either exact original GPT restoration is proved or the
reduced layout has been initialized and accepted through the reviewed path.
This guard addresses Android mounting the old larger filesystem and an A
fallback leaving modified GPT behind. Its retirement evidence is one of those
two exact outcomes; review it when the initialization or recovery path changes.

## Intended initialization order

The V3 task selects only optional bootstrap and one `gpt-reserve`, attended
recovery, at most two operations and 60–7200 original BOOTTIME seconds. It
selects no E, HUD, extra reconnect experiment or deferred recovery. The exact
new N binds the private original/proposed vectors and fixed command bodies;
no caller chooses an LBA, path, byte count or write payload. A remains the
original Magisk boot-only archive. A healthy admitted predecessor N may supply
bootstrap's starting health/CONTROL when its closed tail and unchanged ancestor
source closure are bound. Two new-N installations and four healthy sessions
still qualify the new N; the final session also reads complete original GPT.
Only a rederived `PASS_EXACT_GPT` for that actual endpoint permits apply.
The Android32 successor starts bootstrap from healthy original Android A;
changed sources never relax an old native candidate's ancestor binding.

| Phase | Required outcome before continuing |
| --- | --- |
| `gpt-apply` | One claimed/journaled authenticated EXEC; all changed blocks synchronized/read back and complete proposed GPT proved; DETACH/close |
| `gpt-restart` | Attended physical restart, original USB generation absent, then different native boot at ordinal one |
| `gpt-proposed` | Complete proposed GPT and new userdata/native-entry sysfs geometry |
| `factory-reset` | One attended ordinary reset in the unchanged stock recovery, followed by reboot to still-installed N |
| `gpt-after-reset` | Different native boot, preserved proposed GPT and both fixed F2FS geometry prefixes |
| `gpt-android-start`, `install-android` | Fresh native CONTROL, timely exact Download, one exact A transfer after initialization proof |
| `android-initial` | Attended Android/Magisk/ADB setup; fresh exact rooted health, full GPT and reported filesystem capacity |
| `android-reboot`, `android-final` | One exact ordinary ADB reboot, bounded departure, different Android boot with the same GPT/capacity and numeric root |

Physical phases retain an intent, original native USB snapshot and deadline
before the operator acts. Completion requires the operator's actual statement,
departure within that deadline, and the subsequent authenticated new native
boot/ordinal. Reporting reconstruction never repeats the physical action.
The same owner and original task deadline remain held during physical setup.
Android initialization is followed by full GPT and statfs reads between rooted
health brackets, one journaled ordinary Android reboot, and the same checks on
a different Android boot. Free space may change; reported total capacity and
the complete GPT metadata must remain equal.
Android must not boot the old filesystem between GPT reduction and reset.
An Android setup requiring physical input is a real operator action.

Only Android32 adopts a prospective `android-setup-pending` result when the
first initial-health root command completes with rc127, empty stdout, and
exact `/system/bin/sh: su: inaccessible or not found` stderr after successful
exact-target inventory/devpath/properties. Preserve that failed raw attempt
and append its pin. A new actual operator setup-completion statement permits
a fresh full read attempt within the original grant, with the owner retained.
No reboot is intended until full initial GPT/statfs/root health passes. Other
errors still stop normal work. This neither changes P397's recorded stop nor
reuses its separate incident completion. After a completed ordinary reboot,
the existing health-only recovery may provide final proof without another
reboot, native installation, A transfer or GPT effect.

The exact stock recovery obtains the current block-device size with
`BLKGETSIZE64` and reserves the fstab's final 16 KiB before userdata format.
Its exact formatter receives the reduced block count in 4096-byte units with
the stock Android/project-quota/casefold/compression options. Its normal wipe
also reaches cache and metadata. MDF writes the same 64-byte region at param
end minus 2048 twice: zeroing it and writing its mode-4 record. Conditional UCM
maintenance updates `/efs/sec_efs/ucm_ode_mode` and `odeConfig` and removes the
failure reboot count; the traced product-conditional post-wipe marker is
`/efs/recovery/postwipedata`. FinishRecovery clears the first 2048 misc bytes.
Cache recovery logs can be preserved/restored and a stock cache backup can
cause cache formatting to be skipped. These exact stock side effects are
covered by the common exception; no general raw param/EFS/misc access follows.
The traced ordinary wipe contains no GPT/PIT rewrite. Recovery configuration
declares a non-A/B build; this static fact does not prove runtime OTA state or
all bootloader behavior. The closed P397 result proves that exact stock reset
at 95.4580078125 GiB; Android32 must prove its new geometry and health separately.

The existing exact A archive contains only patched `boot.img.lz4`. Factory
reset does not establish post-reset root by itself: Magisk app/setup and
actual numeric-root execution must be verified after Android initialization.
Prior modules and per-application root permissions may be lost with userdata.

The post-reset native reader reads only the first two 4096-byte userdata
blocks, exporting 108 geometry bytes at offset 1024 in each. The 216 exported
bytes end before the filesystem UUID. Both copies must agree and establish
the expected magic, logarithms, block count and segment bounds. This is
`PASS_GEOMETRY_ONLY`, not mounted filesystem health. No file, key, UUID or
userdata footer is exported. The Android reader reuses the fixed full tail9
GPT script plus one fixed native-entry/statfs script between exact same-boot
numeric-root/partition-health brackets. Its total block count must equal the
proved F2FS block count minus segment0, following the exact FYG8 statfs code.
This proves Android's reported filesystem capacity; no Settings screenshot or
UI observation is inferred. The full metadata, raw framing and filesystem
geometry remain private. Existing strict census `NO_PROOF` is not promoted.

## Failure and recovery

The prospective recovery scope includes one original-GPT restoration. If a
candidate factory reset was already intended, original-layout Android recovery
also requires at most one separate restorative factory reset at the original
userdata size and its fresh geometry proof. An uncertain restoration is never
replayed. Once an A transfer has an intent, it cannot be overwritten by another
N recovery transfer or repeated; only its original proof and final health may
be recovered. The shared F1 owner remains held through unresolved recovery.

Before any GPT intent, failure retains the unchanged V3 one-A recovery. After
GPT intent and before proved new-layout initialization, recovery selects one
attended exact Download/N installation, one fixed original-GPT restoration,
the original-size restorative reset when candidate reset was intended, then
fresh original geometry/CONTROL, one A and rooted Android health. If initialized
proposed GPT is already proved, recovery may use A directly and preserve the
reservation. Every A launch rechecks that exact basis. An uncertain write,
reset, CONTROL or transfer is never retried; recovery does not renew research
time or capacity. Recovery physical phases are bounded by 900 seconds each
and remain restricted to the original host boot, as in V3.

Complete raw evidence takes priority over recovery effects. H0 reconstruction
may publish a missing result, including after a physical or Android reboot,
without replay. After proved A transfer, fresh rooted Android health may close
an uncertain ordinary reboot with explicit `NO_PROOF` reboot persistence; that
is recovery health, not normal task success. Original-layout recovery after a
reset does not recover erased user data. Arbitrary corruption, unusable physical
Download and uncertain GPT restoration retain the owner and stop new effects.

The pre-A guard blocks mounting an old larger filesystem or silently retaining
uninitialized modified GPT. Its scope ends only with the exact initialized
proposal or proved original-layout recovery. Review it when writer, reset,
initialization or recovery inputs change. Other identity, no-replay and privacy
checks remain permanent common boundaries; this policy creates no blanket
formatting or future partition authority.

## Review, activation and reporting

The source-bound independent review covers common/target/G2/V3 interactions,
the reachable owner, fixed native endpoint and immutable vector joins. Fresh
A/B image and AP/member qualification plus actual read-only endpoint proof
remain separate from the reviewed capability. Before the first effect, the
operator receives the exact finite task, including this GPT/reset scope and
the original-layout recovery limits, and returns its bound approval statement.

One structured terminal, the append-only V3 journal and bounded private raw
evidence report proposal, initialization, Android return, reboot persistence,
root and recovery separately. Normal completion requires all ten phases and
`PASS_CHANGED_BOOT_GPT_CAPACITY_AND_ROOT`. A health-only recovered terminal may
separately prove that feature only when the actual initial health, sole reboot
request/departure and fresh final health all validate; it retains `recovered=true`
and is not relabelled normal completion. Partial or unproved results cannot
claim the user's completed reservation/reboot goal. Consumed claims, old
artifacts and earlier source reviews keep their original provenance.
