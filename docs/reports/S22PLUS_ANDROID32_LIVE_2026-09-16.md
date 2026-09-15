# S22+ Android32 live result and minimal Android cleanup

**P398 completed the 32 GiB userdata / 191.4580078125 GiB native layout and
returned to rooted Android with changed-boot GPT/capacity persistence.**
The native partition is unformatted. The G2 grant is closed; app cleanup is a
separate foreground profile whose first inventory stopped before any effect.
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

The corrected parser includes these rows in inventory/UID accounting and
explicitly excludes framework/APEX packages from removal. A separately reviewed
H0 retirement proves the known original source, exact successful raw stage,
full health and absence of execution. It preserves the old open/claim and
permits one replacement claim/preparation under the original foreground
request. Any execution start, effect intent, unsuccessful/uncertain raw read,
missing journal or previous replacement rejects that exception.

All 13 focused app tests pass, including raw no-effect retirement, one successor,
no replay after an uncertain uninstall/reboot, no missing-journal reconstruction,
failed-read rejection and current-user/source/claim guards. Independent review
has no unresolved findings. The actual retained failure rederives 465 rows,
27 known parser rejections and zero effects. Root revision 19 incorporates
this preparation-only correction; no GPT authority or consumed record changes.

The first preparation remains private at
`workspace/private/runs/s22plus-android-minimal-v1/p398-android32-20260916-1/`.
Cleanup selection, removals and post-cleanup reboot/space results remain pending
until the one repaired preparation and its reviewed execution complete.
