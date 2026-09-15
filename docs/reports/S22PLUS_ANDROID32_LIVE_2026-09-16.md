# S22+ Android32 live result and minimal Android cleanup

**P398 completed the 32 GiB userdata / 191.4580078125 GiB native layout and
returned to rooted Android with changed-boot GPT/capacity persistence.**
The native partition is unformatted. The G2 grant is closed. The separate app
profile removed 26 optional packages for user 0 and ended with proved healthy
rooted Android after one read-only reconciliation. Its formal result remains
`INCOMPLETE` because USB disappeared during the first final-health check.
A90 and S20+ were untouched.

## G2 result and canonical timeline

The actual operator returned the exact 7200-second/two-operation approval and
confirmed physical attendance. Fresh P398 `v0.3.0-rc.2` passed two installations,
four native sessions and a complete actual original-GPT read. One apply wrote
four GPT blocks and verified the complete proposed pair. A physical restart
proved the new kernel extents; one stock factory reset produced the expected
F2FS geometry. Original Magisk A was installed once.

Android initial and final health both prove numeric UID/GID 0 and exact
original-A/supporting partition digests. One ordinary reboot has its unique
intent, successful raw request, bounded departure and different final boot.
Complete GPT and total `/data` capacity agree across both boots. The feature
is `RESERVED_ANDROID_REBOOT_VERIFIED` with
`PASS_CHANGED_BOOT_GPT_CAPACITY_AND_ROOT`; terminal state is
`ANDROID_CLOSED_HEALTHY`, `recovered=false`.

| Event | Seconds after grant open |
| --- | ---: |
| First P398 installed | 71.095 |
| Second P398 installed | 96.934 |
| Admission and actual original-GPT read | 121.335 |
| One GPT apply complete | 165.894 |
| Physical restart complete | 260.580 |
| Fresh proposed GPT/kernel geometry | 270.874 |
| Stock reset and native return complete | 365.762 |
| Post-reset GPT/F2FS geometry | 376.153 |
| Original Magisk A installed | 387.102 |
| Initial rooted Android GPT/statfs | 821.656 |
| Sole ordinary reboot departure | 825.519 |
| Final rooted Android GPT/statfs | 867.240 |
| Task closed with no F1 owner | 896.104 |

Both operations are consumed. Counts are two bootstrap N transfers, one GPT
apply/four writes, one stock reset, one original-A transfer and one verification
reboot. There was no GPT restoration, restorative reset or recovery transfer.
The prospective missing-su setup exception was not needed. One outer capture
wrapper rejected a 7320-second timeout before creating a writer or child
process; its corrected 7200-second invocation was the first actual bootstrap
launch. That H0 rejection consumed no device action.

The actual post-reset F2FS copies agree on block count 8,388,604, segment0 512
and 16,382 segments. Final statfs reports total **34,357,624,832 bytes**,
free **31,816,380,416 bytes** and available **31,682,162,688 bytes**.
Total minus free is 2,541,244,416 bytes used; these are point-in-time filesystem
observations, not predictions of long-term usage.

Private evidence is under
`workspace/private/runs/s22plus-native-session-v3/p398-native-android32-20260916-1/`.
The immutable task close is 5,427 bytes, SHA-256
`4b8ad693a122ffec9db244fa373fad70c519ff53057bd590afc0d36b498b3347`.
It retains both operation terminals/journal tails, source commit `8e2cab3056`
and the original source snapshot. The [H0 report](S22PLUS_ANDROID32_AND_MINIMAL_ANDROID_H0_2026-09-16.md)
records the qualified image and authority. Consumed P397/P398 identities remain unchanged.

## Device Care's 64 GB presentation

The operator photo shows 64 GB total, 32.2 GB used and 31.8 GB free. The
photo is private; its separate observation receipt joins it to the retained
G2 result without editing that result. The displayed free value is consistent
with the measured 31.816 GB filesystem free value. It does not imply that
`/data` is a 64 GB partition or actually contains 32.2 GB of used data.

Android 15's [primary-capacity API](https://raw.githubusercontent.com/aosp-mirror/platform_frameworks_base/android-15.0.0_r1/core/java/android/os/storage/StorageManager.java) adds data and system filesystem
sizes and applies [storage-size rounding](https://raw.githubusercontent.com/aosp-mirror/platform_frameworks_base/android-15.0.0_r1/core/java/android/os/FileUtils.java) to decimal product-size
steps. Our 32 GiB partition is about 34.36 decimal GB and exceeds the 32 GB
step even before adding the system filesystem. This is consistent with the
observed 64 GB label. The exact Samsung Device Care call path was not traced,
so this is an explanation supported by the upstream calculation and measured
values, not proof of the proprietary app's implementation. The photo does
not establish a minimum supported partition size; this run proves exactly
32 GiB, not arbitrary smaller sizes.

## App inventory preparation correction

The first fixed inventory captured 465 system-package rows successfully, with
empty stderr and no timeout, overflow or producer fault. Its host parser
rejected 26 valid `/apex/` APK paths and the framework package `android`.
Before/after exact rooted Android health passed on the same boot, current
user was 0 and the journal stayed empty. No app uninstall or app-profile
reboot was intended or performed.

The first correction includes those rows in inventory/UID accounting and
explicitly excludes framework/APEX packages from removal. The second inventory
then captured identical `flags` and `pkgFlags` aliases for its first optional
package. Both aliases contain the same flags; the host parser incorrectly
required just one. Its 20 raw commands succeeded with empty stderr, both exact
rooted health brackets passed on the same boot, and its journal stayed empty.
The corrected parser accepts one of each alias only when the sets agree;
contradictory aliases or repeated keys still fail. Metadata captures now all
complete before interpretation, allowing pure H0 repair from retained bytes.

The parser retirement binds these two known old source hashes and
rederives complete successful raw stages, full health and no execution. Each
proved retired preparation can have one immutable child under the original
foreground request. The chain preserves all prior claims/records and permits
only one effectful cleanup. Any ancestor execution start, effect intent,
unsuccessful/uncertain read, missing journal, duplicate open or cycle blocks it.
The first immutable retirement remains byte-identical.

The operator pointed to the existing same-FYG8 cleanup evidence. The fixed
declaration now combines its original optional names with the successful
package block in [Pass1](S22PLUS_ANDROID_DEBLOAT_PASS1_2026-07-06.md), excluding
the [116-package keep list](../plans/S22PLUS_ANDROID_116_PACKAGE_ALLOWLIST_2026-07-06.txt)
and [three debug packages](../plans/S22PLUS_ANDROID_DEBUG_CHANNEL_REQUIRED_PACKAGES_2026-07-08.txt).
This yields 66 consumer candidates with 119 mandatory exclusions. It does not
replay the historical complement or claim an exact remaining-package count.
All three data inputs are part of the 59-file app review closure.

All 16 focused app tests pass, including alias conflicts, every historical
keep entry, aggregate-free projection, linked claims/cycle rejection, raw
retirement, and uncertain uninstall/reboot no-replay. Independent review has
no unresolved findings. Revision 20 incorporates only this preparation/profile
change; no G2 authority or consumed result changes.

The third preparation reached a different, explained host acquisition stop:
Reminder's metadata exceeded the 128 KiB stdout allowance. Its failed receipt
retains exactly 131,072 bytes, return code -15 and output-exceeded, with no
timeout, producer fault or stderr. The raw producer detects bytes beyond its
bound before sending SIGTERM. All earlier reads succeeded; full exact rooted
health before/after passed on the same boot and the journal stayed empty.
There were 25 captures, including six optional metadata captures from 41
installed candidates. The truncated metadata remains failed/unproved.

The metadata-only bound is now 1 MiB for inventory and fresh pre-effect reads,
with the same 20-second timeout; pure projections use the same bound. Other
read limits are unchanged. Upstream Android 15's
[DumpHelper](https://raw.githubusercontent.com/aosp-mirror/platform_frameworks_base/android-15.0.0_r1/services/core/java/com/android/server/pm/DumpHelper.java)
includes filter details for a named package; its `packages` command dumps all
packages, so it is not a narrower named-package replacement.
Revision 21 admits only this third known source's exact host-limit result to
H0 no-effect retirement. All prior captures and health must succeed, all
ancestor journals remain empty, and the unique child claim rules still apply.
Timeouts, other command failures and unexplained transport errors remain stops.
Old retirements rederive byte-identically; no overflow becomes a successful
metadata observation and a fresh complete capture is required before selection.
All 19 focused tests pass, including complete metadata above 128 KiB through
uninstall/terminal reconstruction, a 1 MiB overflow stopping before effects,
and real subprocess SIGTERM with timeout/transport-failure rejection.

The fourth preparation captured 45 successful reads, including 26 complete
metadata records. Its next fixed candidate, `com.sec.android.easyMover`, could
not be used as a raw capture label because the shared writer permits lowercase
labels only. The writer rejected it before stream creation or command launch.
Both exact rooted health brackets passed on the same boot; no execution began.
Current labels use `pkg-` plus the full SHA-256 of the unchanged package name.
All 66 labels are unique and accepted by the actual writer rule.

H0 inspection of those retained records also found seven shared-UID packages
whose later shared-user sections repeated `appId`/`User 0` fields. The parser
now confines fields to the unique active `Packages:` section, preserving
duplicate rejection within that section and exclusion of shared-UID packages.
All 26 actual records now parse. Revision 22 adds only the exact known
prelaunch-label case to retirement; the pending invalid name must have no
capture/stream, every earlier read must succeed and all no-effect/health/claim
conditions still apply. All three earlier retirement values remain unchanged.
All 22 focused tests pass, including real uppercase-name acquisition through
uninstall/terminal proof, section scoping and first-invalid-label retirement.

The four preparations remain private under
`workspace/private/runs/s22plus-android-minimal-v1/p398-android32-20260916-{1,2,3,4}/`.
One outer wrapper initially rejected a missing capture directory before Popen;
the corrected invocation was the first actual third preparation. No device
command was repeated by that H0 wrapper correction.

## Cleanup result and reconciled final health

The fifth preparation captured all 41 installed candidates from the fixed 66
names. Selection retained the 119 mandatory exclusions and rejected ten
system/shared-UID candidates plus five customized/disabled user states.
All 26 selected user-0 uninstalls returned success and each package was absent
in its immediate post-state. The installed system-package list went from 465
to 439; this is not a reconstruction of the historical 116-package checkpoint.
Independent raw-evidence review confirms those are the only package-set
changes: all initially present keep entries remain. Twenty-five selected names
come from the historical successful Pass1 block; Gmail comes from the reviewed
original optional declaration. No concrete selection/execution defect was found.

One ordinary reboot was requested once and its USB departure was observed.
The device returned with `sys.boot_completed=1`, but the first final-health
sequence then captured an empty root response and a selector with no devices.
The runner stopped. It issued no further uninstall, reinstall, reboot, transfer
or GPT write. The journal contains 27 intents and 27 completions (26 removals
and one reboot), followed by the semantic health stop.

The existing 300-second read-only reconciliation completed. Both rooted health
brackets rederive numeric UID/GID 0 and exact original-A/supporting digests.
All selected packages remain absent. Home/input owners are unchanged, full GPT
matches the pre-reboot proposed pair, and total filesystem capacity remains
34,357,624,832 bytes. The final boot differs from the pre-reboot boot and exactly
matches the briefly observed post-reboot properties; no extra reboot was
observed. The operator subsequently reported Android state.

A bounded host-kernel read around the failed health check independently shows
the exact target port disconnecting and enumerating again. This supports a
temporary USB re-enumeration; its initiating cause is unproved. No device read
or effect was added for that host-log diagnosis. The interrupted result remains
`INCOMPLETE`, `reboot_verified=false`, with `ANDROID_CLOSED_HEALTHY` and no
remaining selected packages. Reconciliation does not relabel the original
execution or permit replay. Any prospective device effect must first resolve
the applicable session stop; this task supplies no new authority.

| `/data` observation | Bytes |
| --- | ---: |
| Available before cleanup | 31,700,729,856 |
| Available after reconciliation | 31,645,573,120 |
| Free after reconciliation | 31,779,790,848 |
| Available change | -55,156,736 |

No reclaimed-space gain was proved. These are point-in-time measurements across
app removal and a reboot; they do not identify which activity caused the change.
User-scoped removal leaves factory APKs in their existing system partitions.

The actual cleanup source commit is `3574a2bb7f460969a8ca099c992ca35b5cff16d7`.
Its private run is
`workspace/private/runs/s22plus-android-minimal-v1/p398-android32-20260916-5/`.
The 32,505-byte preserved source manifest has SHA-256
`7d372bd21440daa59fabb750fded21806cbf684254510f3e0fe4f9cab0c0d228`.
The 692-byte terminal has SHA-256
`a81914af3b16443a08b01a309ced1f36395d76156ad8c025e22155a534a222e5`;
the 1,093-byte reconciliation result has SHA-256
`851ce9e329d9126cdd17128aca907952d3fa6a904ed91dfabe47f8a041e9d36c`.
The four retired preparations, their claims/source snapshots, and all G2
results remain unchanged. No Debian filesystem or rootfs was installed.

## Prospective additional cleanup preparation

The operator requested additional cleanup after reviewing the remaining scope.
Pure H0 comparison found 321 current system-package names outside the 119-entry
keep/debug declaration, including all 38 explicitly removed in the four
successful batches of the [extra report](S22PLUS_SYSTEM_APP_EXTRA_DEBLOAT_2026-07-06.md).
This comparison does not make all 321 eligible for removal. The selected new
mode uses only those 38 historical resources/overlays/platform utilities and
retains every existing keep, APEX, UID, persistence and user-state exclusion.
Current retained path/UID data yields 29 preliminary candidates and nine
exclusions; fresh complete metadata is still required for selection.

The new `additional-known` mode reuses the existing effect and reconciliation
machinery with a separate one-child claim. Its predecessor proof rederives all
prior intents/completions and raw effects, changed-boot GPT/root/capacity and
the exact final package set. The known read-only USB disappearance is qualified
only when the existing healthy reconciliation matches the briefly observed
post-reboot boot. The old `INCOMPLETE` terminal remains byte-identical. Uncertain
effects, missing completions, changed parent activity or another additional
child fail before device effects. The direct new request supplies foreground
scope; effects remain attended and use a fresh finite window.

The four historical data inputs are bound in the app source closure. Per-mode
declarations flow through collection, selection and raw reconstruction. Packages
already excluded by APEX path or system/shared UID need no metadata read.
Additional-mode inventory and final snapshots also read `persist.sys.safemode`,
accepting empty or zero as a limited historical health signal. Original-mode
records and projections retain their existing meaning.

All 28 focused tests pass, including real additional-package effect/terminal
flow, the known read-only disappearance with healthy reconciliation, rejection
of uncertain reboot despite later health, one-child ownership, changed parent
journal rejection, the safe-mode property guard, and an unexpected keep-package
loss stopping the batch before its planned reboot. Every additional-mode
snapshot checks the initially present keep set using the retained census.
Independent changed-closure review passed with no blocking findings. The app
closure has 60 sources, with 54 V3 execution and 156 unchanged native-runtime
sources independently checked. Fresh preparation is still required before
this new scope's effects.
