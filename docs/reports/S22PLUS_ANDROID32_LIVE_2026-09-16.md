# S22+ Android32 live result and minimal Android cleanup

**P398 completed the 32 GiB userdata / 191.4580078125 GiB native layout and
returned to rooted Android with changed-boot GPT/capacity persistence.**
The native partition is unformatted. The G2 grant is closed. The separate app
profile removed 26 optional packages for user 0 and ended with proved healthy
rooted Android after one read-only reconciliation. Its formal result remains
`INCOMPLETE` because USB disappeared during the first final-health check.
A90 and S20+ were untouched.

The additional mode is also closed `INCOMPLETE / ANDROID_CLOSED_HEALTHY`:
25 newly selected packages remain absent after its reboot and four navigation
overlays reappeared. Smart Switch reappeared between the two runs, so the current
system-package count is 415 versus the original 465, or 50 currently absent.

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
sources independently checked. The subsequent fresh preparation and effects
are recorded below.

## Additional cleanup live result

The separately claimed additional run used source commit
`10419a84e6730c3999ab1b2b45ed1b053d23cb1f`, the actual new operator request and
a fresh 900-second window. Fresh metadata selected 29 of the historical 38;
five APEX-contained packages and four other system/shared-UID packages were
excluded. All 29 version-bound user-0 uninstalls returned success and each
immediate post-state proved absence. No prior uninstall was replayed.

One ordinary reboot had its unique intent, successful request and bounded USB
departure. All six full health brackets across inventory, pre-reboot and final
snapshots rederive. The final state has numeric UID/GID 0, exact original-A and
supporting digests, changed boot, unchanged GPT and total capacity, unchanged
home/input owners and all 118 initially present system keep packages. The
additional safe-mode property was empty. No transport failure occurred in this
run's final snapshot.

Four selected navigation overlays were present again after reboot:

- `com.android.internal.systemui.navbar.transparent`
- `com.samsung.internal.systemui.navbar.gestural_no_hint`
- `com.samsung.internal.systemui.navbar.sec_gestural`
- `com.samsung.internal.systemui.navbar.sec_gestural_no_hint`

Thus 25 selected removals persisted. The runner stopped on its required empty
remaining-set assertion after publishing the complete final snapshot. Its
62-row journal contains 30 intent/completion pairs, one start and one stop.
The stop occurred 182.333 seconds after open. This is an observed negative
persistence result, not an uncertain uninstall or failed Android health check.
The re-registration mechanism was not traced; those effects were not repeated.

The already complete final evidence permitted H0-only incomplete closure.
Independent review verified the private publisher with device-acquisition and
USB functions made unavailable. It rederived the exact raw uninstall/reboot
results, journal joins, complete final health and package-set change before
publishing `INCOMPLETE / ANDROID_CLOSED_HEALTHY`, four remaining names,
`cleanup_replay_permitted=false` and conservatively `reboot_verified=false`.
No read-only reconciliation window or additional device command was opened.
The terminal retains the H0 publisher's source pin and original run snapshot.

Smart Switch (`com.sec.android.easyMover`) was the sole package to reappear
between the first cleanup's reconciliation and this run's initial inventory.
The additional run therefore started with 440 system packages, reached 411
immediately, and ended at 415. Exactly 25 names were lost during this run and
none were newly added relative to its own start. Compared with the original
465-name inventory, exactly 50 names are now absent. The original run's
point-in-time 26-removal evidence and terminal remain unchanged.

| Additional-run `/data` observation | Bytes |
| --- | ---: |
| Available before cleanup | 31,475,748,864 |
| Available after reboot | 31,510,704,128 |
| Free after reboot | 31,644,921,856 |
| Available change | +34,955,264 |

This is an observed change across cleanup and reboot, without causal allocation
accounting. The 32 GiB userdata geometry and unformatted 191.4580078125 GiB native
partition remain unchanged.

Private evidence is under
`workspace/private/runs/s22plus-android-minimal-v1/p398-additional38-20260916-1/`.
The 33,206-byte source manifest has SHA-256
`aa68ba81b3887e1128ab96e4cfe44ae0576532b4ff13b4a3d492e18b442ce958`.
The 1,323-byte final snapshot has SHA-256
`1d8904f8ff6a49dd53f9af0721daf4916e2b5937854985caa0fa9e255bdf9a7b`.
The 1,178-byte terminal has SHA-256
`ef114b0551a9aa43f8fea64a5195faa91ac80e7e7a3972b30ac664f8fee856a3`.
Its 5,195-byte H0 publisher has SHA-256
`ef96d44b8d2a7566a9d3222cd04b6e2bc37a8807fbfc60995d21503c8ff3e1a4`.
The additional claim grants no descendant, replay, raw APK deletion, new GPT
action or Debian staging. A90 and S20+ remained untouched.

## User-app successor preparation

The operator explicitly named YouTube, Play Store, Contacts and Clock for
further removal. The prior optional declaration omitted several UI apps and
excluded YouTube's ordinary explicit `enabled=1` state. The new `user-apps`
mode adopts 31 fixed consumer names. Only Play Store is excepted from historical
KEEP; Contacts provider, GMS/GSF, DocumentsUI and management services retain
protection. UI-mode metadata accepts ordinary enabled states 0/1 while the old
mode projections remain unchanged. Historical A90 UI removal evidence informed
the declaration only; it supplies no S22 effect authority.

All 55 previously attempted names from the original and additional runs are
excluded, including any restored packages. The actual retained additional
closure and its original ancestor rederive in H0 with device functions
unavailable; the old incomplete terminals are unchanged. The only new child
is typed from additional to user-apps, binds both ancestor journals/claims and
has no descendant. The existing finite windows and attendance remain.
A complete retained final persistence stop may close as incomplete in H0
without adding a device read. Shared/system UIDs, APEX, persistent components,
home/input and disabled/hidden/suspended states still cannot be selected.

All 33 focused tests pass, including the new UI claim/load/second-child checks,
both effectful-ancestor journal checks, explicit-enabled Play Store removal,
mode-specific KEEP behavior, and incomplete H0 closure when an app reappears
at reboot. Python compilation and the repository boundary check pass; the
12 boundary regression tests also pass. Fresh inventory and the actual terminal
result are recorded separately below.

Independent review returned `PASS_GO` with no blocking findings and confirmed
that both old effectful terminals remain unchanged. The live app review
SHA-256 is `3a97691b85d8ff9761b4b8a05a083e2524180f45436ccef5216e0ba08fd6447a`
(60 sources), and V3 is
`d167ff39373318f7eab0e371db6d1d7478fa16c9bd78277e6026ee40fd07a6b8`
(54 execution and 156 unchanged native sources). Both consumers accept them.
The app source SHA-256 is
`2e9b303949997331605e7c31c4e97a4d03f2795eba7d29a55a76f5ccba6d5871`.
Independently checked publication reviews bind only the staged root-contract
variant, excluding preexisting unrelated S20+ changes: app
`7d6005d96ec19cc2f5a8afa4da16fbc56d92a2b5e45d15b7406fe81642c7c646`
and V3 `2b46639caf1b29de902ab22111e3b41933fd6b7a7c292454eec9562420828f56`.
These publication identities do not repin the live run.

## User-app cleanup live result

Fresh preparation of `p398-user-apps-20260916-1` used one new claim under the
closed additional run, the actual user request, attendance and a 900-second
window. Of the 31 declared names, Gmail and Duo were excluded as previously
attempted, leaving a 29-name declaration. Sixteen were currently installed.
Fresh metadata selected 15; Samsung Video (`com.samsung.android.video`) was
excluded because its active metadata declared a shared UID, despite its
list-level UID being unique in the installed-system census.

All 15 user-0 uninstalls returned success and each immediate post-state proved
absence. The complete pre-reboot snapshot had none of the selected names,
healthy original-A root, unchanged home/input/GPT/capacity and all 117 initially
present KEEP packages for this mode. One ordinary reboot had a successful
request and bounded USB departure. During final readiness, the fixed
boot-completed read `wait-080-boot` returned exit 1, empty stdout and ADB
`error: closed` on stderr. The runner stopped with `RawCaptureError`; there was
no final snapshot aggregate. The 34-row journal contains one start, 16 ordered
intent/completion pairs and one stop. No effect was uncertain or replayed.
The initiating transport cause remains unproved.

The existing sole 300-second close-only reconciliation completed. Its full raw
snapshot proves numeric UID/GID 0 with exact original-A/supporting digests,
a changed Android boot, unchanged full GPT, 32 GiB userdata capacity and native
extent, unchanged home/input and all 117 initial mode-specific KEEP entries.
The safe-mode property was empty. Four selected apps were present again:

| Restored after reboot | Package |
| --- | --- |
| Samsung My Files | `com.sec.android.app.myfiles` |
| Galaxy Store | `com.sec.android.app.samsungapps` |
| Samsung Weather | `com.sec.android.daemonapp` |
| Samsung Dictionary | `com.diotek.sec.lookup.dictionary` |

The exact final package-set difference is the other 11 selected apps, with no
new package relative to this run's initial list:

| Absent at final reconciliation | Package |
| --- | --- |
| YouTube | `com.google.android.youtube` |
| Google Play Store | `com.android.vending` |
| Google Maps | `com.google.android.apps.maps` |
| Gemini | `com.google.android.apps.bard` |
| Chrome | `com.android.chrome` |
| Samsung Contacts UI | `com.samsung.android.app.contacts` |
| Samsung Clock | `com.sec.android.app.clockpackage` |
| Samsung Calendar | `com.samsung.android.calendar` |
| Samsung Gallery | `com.sec.android.gallery3d` |
| Samsung Camera | `com.sec.android.app.camera` |
| Samsung Messages | `com.samsung.android.messaging` |

The formal terminal is `INCOMPLETE / ANDROID_CLOSED_HEALTHY`, four remaining
names, `cleanup_replay_permitted=false` and `reboot_verified=false`. The changed
boot and healthy return are distinct from the failed all-removals persistence
criterion. No causal mechanism for the four apps' return was established.
This closed user-apps claim has no child. All earlier effects and terminals
retain their original identities.

The installed-system count went **415 -> 400 immediately -> 404 at final
reconciliation**. Compared with the original 465-name list, exactly 61 names
are absent and none newly present.

| User-app run `/data` observation | Bytes |
| --- | ---: |
| Available before cleanup | 31,492,640,768 |
| Available before reboot | 31,675,535,360 |
| Available after reconciliation | 31,678,308,352 |
| Free after reconciliation | 31,812,526,080 |
| Available change | +185,667,584 |

This is measured across cleanup/reboot, without causal allocation accounting.
No system APK partition was removed or resized. The 191.4580078125 GiB native
partition remains unformatted. No further reboot, F1/GPT operation, rootfs
staging, A90 or S20+ effect occurred.

Private evidence remains under
`workspace/private/runs/s22plus-android-minimal-v1/p398-user-apps-20260916-1/`.
The 33,023-byte source manifest has SHA-256
`9616a1e7e7b752a725b68d031ddfbe483fe9d8464840ca2623275df9fea59bf5`.
The 5,777-byte inventory result has SHA-256
`0390779fcf770d1e7935bd18575a32c9e52a4984fc5a6a08a3e85bd0677c94d1`.
The 1,243-byte reconciliation snapshot has SHA-256
`3c6542db7a027b39222bbc1dd29900ea21fbfb677cda5e9c2811a7d47bdaab87`.
The 818-byte terminal has SHA-256
`a2015f964840127d24cc47e29a9da9e4bf59d1865c2430fa402a36f56f1436a3`.

Independent terminal audit rederived all raw effects, matching journal joins,
readiness failure and complete reconciliation with live acquisition disabled.
It confirmed the exact 11-package difference, four remaining apps, retained
117 KEEP entries and unchanged prior terminals. The current incomplete verdict
and source records were preserved; no further device action was justified.

## Full checkpoint reapplication preparation

The full-checkpoint request adopts the existing same-FYG8 116-package checkpoint
with its three debug requirements and the already explicit Play Store exception.
The new declaration covers the complete current user-0 APK inventory outside
this protected set, excluding every name attempted by the three previous runs.
It includes ordinary non-system apps and does not retain the consumer modes'
blanket exclusions for shared/system UIDs, persistent flags or APKs under APEX
paths. Actual APEX modules remain excluded. All protected packages must exist,
except that an absent Magisk manager UI need not be installed while exact
original-A numeric root remains healthy; any initially present manager stays
protected. HOME/IME, hidden/suspended-state exclusions and exact per-package
identity checks remain.

The single new claim binds the rederived closed UI run and its two ancestors,
including the exact readiness read failure and healthy existing reconciliation.
All 70 prior attempted identities and three incomplete terminals remain
unchanged. The new batch has 3600 seconds and one ordinary reboot. Its full
plan is checked against the 2052-row journal capacity before any effect;
legacy journals retain the 256-row default. Complete explicit PM refusals and
unchanged retained-package outcomes consume their attempts and permit the rest
of the original batch to continue. Unknown or contradictory outcomes stop.
No effect retries, disable fallback, partition action or permission change
are added. Both pre-reboot and final package-set differences must rederive.
Residual packages outside KEEP are reported even when no new candidate remains.

Independent review passed with 43 focused app tests, four journal/record tests,
and two additional subprocess cases for transport-loss stop and unexpected
package changes before reboot. Python compilation, the repository boundary
check and its 12 regression tests passed. The app source SHA-256 is
`d3763aaaf31a09b5df404f902eff91466adf19ac67b8e48b9ce11875289fd872`;
the shared record source SHA-256 is
`111611417233cd9c3a793ec754bdf9ae8b98c864d405d273083301a2e78ea0e4`.
The app review covers 61 sources, V3 covers 54 execution sources, and all 156
native runtime sources remain unchanged. No native image rebuild is involved.
All-user-0 counts from this scope are distinct from the earlier system-only
465/404 package counts.

Both working capability consumers accept the full-checkpoint receipts: app
`020aaf44c6521c791a7875c31bd91ac41d5848a0a51983daf034bdeacf2e1ffc`
and V3 `68986beccf5968ac53042e6545f834464b8da6a1438d92bf9601597c11fcd390`.
Independently verified publication copies bind the staged root without unrelated
S20+ working changes: app
`ee8a65e6636a9cd897e1e5b52e76ac499f01f09973a04dd21082713d192c8c95`
and V3 `4c2eef79a95dd1e79e867ad51397e2418b120c087bd7cd986b4581067b956282`.
These do not repin any live or consumed record.

Fresh inventory for `p398-checkpoint-full-20260916-1` found **406 installed user-0
APK packages**. The full 118-entry effective KEEP set, including Magisk manager,
was present. Nine previously attempted packages remained and were excluded.
All **279 new candidates** passed the declared metadata checks; no additional
candidate was excluded. They include 112 declared shared-UID packages, nine
persistent packages and 18 APKs inside APEX paths; one selected package is
non-system. These categories can overlap. Compared with the prior system-only
404-name list, the all-package inventory adds Magisk manager and Samsung Tips;
none of that prior list was absent at entry. Tips is the non-system candidate.
The initial available space was 31,671,635,968 bytes. Inventory SHA-256 is
`f0e900e617b7ee3ad9017a8d3639858b6eb8faba90f426d964e4bdb2a4d83e32`
(88,416 bytes). Fresh bracketed original-A root and empty safe-mode property
were confirmed before the batch began.

## Full checkpoint batch live result

All **279** selected packages returned `Success` and each immediate post-state
proved absence. No explicit refusal or retained-package outcome occurred. The
complete pre-reboot snapshot contained exactly **127** installed user-0 APKs:
all **118 protected entries** plus the **nine prior residuals**. The exact set
change matched the selected 279 names; no unrelated package was lost or added.
Root, HOME/IME, complete GPT and capacity remained healthy. The safe-mode
property was empty. No previously attempted package was retried.

The sole ordinary reboot request and bounded USB departure completed 462.513
seconds after open. Its first final health sequence obtained the exact selector
and physical lane. The `02-health` properties read returned exit 0 but only 15
stdout bytes containing the model field; the other eight required properties,
including boot ID, were absent. This truncated response does not establish a
complete post-reboot identity. The root-health read `final/before/03-health`
then returned exit 1, empty stdout and the ADB target-not-found diagnostic. There was
no timeout, overflow or producer fault. No final health/result aggregate was
published. The runner stopped at 506.490 seconds; the journal contains 562 rows:
one start, 280 ordered intent/completion pairs and one `RawCaptureError` stop.
All package/reboot effects had completed before this failed read. The initiating
USB/device cause remains unproved, and no transition was repeated.

The existing single 300-second read-only reconciliation opened 581.856 seconds
after the original open and completed successfully. It proves numeric UID/GID
0 with exact original-A/supporting digests, a changed boot, unchanged full GPT,
32 GiB userdata and the 191.4580078125 GiB native extent, unchanged HOME/IME,
and all 118 protected entries including Magisk manager. The safe-mode property
was empty; this remains a limited health signal.

**All 279 selected packages remained absent after reboot.** The final all-user-0
APK count stayed **127**, with no package additions relative to the batch's
initial 406-name list. The only names outside effective KEEP are the same nine
previously attempted packages, excluded from this batch:

| Residual | Package |
| --- | --- |
| Smart Switch | `com.sec.android.easyMover` |
| My Files | `com.sec.android.app.myfiles` |
| Galaxy Store | `com.sec.android.app.samsungapps` |
| Weather | `com.sec.android.daemonapp` |
| Dictionary | `com.diotek.sec.lookup.dictionary` |
| Transparent navigation overlay | `com.android.internal.systemui.navbar.transparent` |
| Gestural no-hint overlay | `com.samsung.internal.systemui.navbar.gestural_no_hint` |
| Samsung gestural overlay | `com.samsung.internal.systemui.navbar.sec_gestural` |
| Samsung gestural no-hint overlay | `com.samsung.internal.systemui.navbar.sec_gestural_no_hint` |

The formal terminal remains `INCOMPLETE / ANDROID_CLOSED_HEALTHY`, with
`remaining=[]`, all nine `remaining_outside_keep` names,
`checkpoint_reached=false`, `cleanup_replay_permitted=false` and conservatively
`reboot_verified=false`. Observed persistence of all new removals is separate
from that unchanged close-only terminal verdict and the unmet exact checkpoint.
All three earlier incomplete terminals retain their original identities.
This closed full-checkpoint claim has no descendant.

| Full-batch `/data` observation | Bytes |
| --- | ---: |
| Available before cleanup | 31,671,635,968 |
| Available before reboot | 31,634,427,904 |
| Available after reconciliation | 31,675,633,664 |
| Free after reconciliation | 31,809,851,392 |
| Available change from entry | +3,997,696 |

These are measured allocations across cleanup/reboot, without per-package
attribution. User-0 removal does not shrink the system APK partitions. No raw
APK deletion, formatting, native partition write, rootfs staging, additional
reboot, F1 transfer, A90 or S20+ effect occurred.

Private evidence is under
`workspace/private/runs/s22plus-android-minimal-v1/p398-checkpoint-full-20260916-1/`.
The 33,923-byte source manifest has SHA-256
`b177b1f518de7e3a0d6b0d1d1654e53507f1b83a5d447bfc4a6a45a8cbbaf238`.
The 1,572-byte pre-reboot snapshot has SHA-256
`5e3628c3eac3de2b1b0092e96f88a07bbe5ac4ff111260842abf47f2a68bfc6b`.
The 1,574-byte reconciliation snapshot has SHA-256
`d29cc363d12cde2d61214c459a179dbde74cb6c437f0b822712545fffef229e4`.
The 1,228-byte terminal has SHA-256
`b5187e77f70d02ce20d33c34676da839b84729d5ab003836f235cd2d71e6beb4`.
The 27,088-byte checkpoint claim has SHA-256
`39d16cf61921eaf9f1c6fd220a75dec0b664c33c1727c860885370165d469d18`.

Independent H0 terminal audit, with live I/O disabled, rederived all 279
identity-bound uninstall/post-state joins, the sole reboot/departure, the exact
562-row journal, both package-set differences and the complete reconciliation.
It confirmed all 118 KEEP entries, no new-candidate remainder, the same nine
prior residuals, and unchanged prior terminals/source snapshots. The partial
properties response and subsequent target-not-found failure are preserved;
no verdict was promoted and no additional device read or effect was performed.
