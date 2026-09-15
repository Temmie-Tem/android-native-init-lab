# S22+ storage census and Android return

**The device is in healthy original-A Android, and both complete GPT copies
have been captured.** Strict metadata remains `NO_PROOF` because existing
partition GUIDs are duplicated. The numerical 64 GiB layout has independent
review; no partition split or formatting occurred. The goal retains Android
and allows resetting user data; it is not yet achieved.

## Actual native result

The 600-second deferred-recovery task executed one authenticated P393 session.
Fixed native health passed. The 759-byte census command was accepted and
returned terminal `[5,0,256,0,0,0,0]`: normal child exit code 1, with zero
stdout and stderr bytes. DETACH and actual descriptor close completed.

| Event | Seconds after grant open |
| --- | ---: |
| Host preflight completed | 12.383 |
| Native observation started | 12.402 |
| Raw-proved observation completed | 14.799 |
| H0 rederivation, source preservation and task close | 164.630 |

The execution subprocess completed in 3.824 seconds. No CONTROL, image
transfer, module load or recovery was performed. One of one operations is
consumed, the shared F1 owner is absent, and the old prior tail is consumed.
The healthy native tail from this census was later consumed by Android exit. Its raw result
rederives without another device action. The original source closure and
review bytes were copied into the task's private source snapshot before any
successor edits.

The empty streams place the observed failure before the script's first
geometry output, but do not identify which guard failed. No/duplicate userdata,
ancestry, device-number read and block-size/capacity guards remain possible.
Alias creation precedes some guards, so its creation/removal is **unproved**.
The negative metadata result does not invalidate proved native health.

## Storage producer and selected successor

The concrete P393 kernel matches its builder's 41,490,944-byte input and
SHA-256 `d648303da3697fce2897440a316b882b7943793573ffe9a68a9135c610486e81`.
Its embedded configuration has no built-in `CONFIG_SCSI_UFS_QCOM`, and the
boot ramdisk's 22 module entries contain no UFS driver. This supports missing
native UFS initialization as a likely cause; it is not a live syscall trace or
proof of the exact failing guard. The unchanged native read will not be repeated.
The renderer separately inventories UFS module files in the vendor ramdisk;
this does not mean the fixed native startup loads them. File availability and
driver activation remain separate facts.

The selected path returned through the existing reviewed original-A V3 exit,
then used the [fixed Android D0 profile](../operations/S22PLUS_ANDROID_STORAGE_CENSUS_V1.md)
in a storage-capable environment. This does not add storage drivers to P393.
The Android-return transition needs its own actual finite grant; the adopted
foreground D0 profile needs no repeated approval after its reviewed entry
conditions pass. The completed return and read are recorded below.

The initial D0 uses existing Android nodes, verifies exact LU0 identity before
reading, and preserves matching seven-command Android health brackets around
one fixed 44 KiB metadata read. Failure emits a fixed stage label. Raw output,
metadata qualification and final health remain separate. The command creates
no node, loads no module, reads no user files or keys, and writes no partition.

## Initial Android H0 qualification

Independent review of the changed common/target adoption and both 45-source
current/publication closures returned **`PASS_GO`**. All **63 focused tests pass**, including ten new Android
tests for actual subprocess binary transport, complete negative results,
same-boot health joins, pending-owner/native-close rejection, failed health,
no retry, and H0 raw reconstruction. The first run exposed missing registry
setup in the new fixture; the fixture now initializes its isolated registry.
No production exclusion rule was changed for that correction.

Independent review caught an ADB transport mismatch: `exec-out` does not
preserve separate remote stderr and the remote child exit status. The final
command uses `shell -T` after a fixed feature query proves `shell_v2`; legacy
fallback is refused. Tests exercise unsupported features and actual subprocess
exit-1/separate-stderr handling, with final health still separate from metadata.
The feature parser and fixtures use the CLI's one-feature-per-line output;
the earlier comma-list assumption was corrected during review. All ten new
Android tests passed again after that correction, retaining the 63-test run.

Host shell and actual ARM64 BusyBox validate the new shell syntax; the fixed
failure-stage trap is exercised without device paths. Actual Android Toybox
execution was unobserved at initial qualification. Its `dd status=none` option is covered by the
[AOSP Toybox tests](https://android.googlesource.com/platform/external/toybox/%2B/dc973f12b2fe4086165b8df1552f7dcb3929e8d1/tests/dd.test).
The native image/runtime and its 144 source inputs remain unchanged.

The return request selected only original-A `android-exit`, 900 seconds,
one operation and deferred physical recovery. Its P393 admission, latest native
tail and original A evidence rederive; the five installed host files, current
readiness and expected native endpoint with no holder were checked without a
device command. The actual returned transition grant was consumed once. The
subsequent adopted Android D0 is separate foreground read authority.

## Actual Android return and first D0

The 900-second grant returned the device through one native CONTROL and one
original-A transfer. Final health encountered ADB `error: closed`. The runner
stopped for deferred attended recovery. The operator confirmed physical
attendance; durable transfer evidence allowed health-only recovery, with no
second transfer. Exact rooted original-A health passed. The transport failure's
cause remains unproved.

| Event | Seconds after grant open |
| --- | ---: |
| Native CONTROL and observation completed | 3.625 |
| Original-A transfer completed | 13.640 |
| Initial Android health stopped | 55.453 |
| Attended health-only recovery completed | 301.543 |
| Source preservation and task close | 379.322 |

The task is permanently closed `ANDROID_CLOSED_HEALTHY`, with one consumed
operation, one total A transfer and no pending F1 owner. Its original raw
results and saved source closure rederive.

The first foreground Android census completed its fixed shell-v2/Toybox
command and fresh same-boot health brackets. Both GPT header CRCs and the
primary entry-array CRC validate, but the backup array begins nine blocks from
the end, outside the captured last-five-block range. The terminal correctly
remains metadata `NO_PROOF`, `ANDROID_CLOSED_HEALTHY`. Its bytes are retained;
H0 parsing does not invent the missing backup data.

## Tail9 successor qualification

The fixed `lu0-tail9-v2` profile reads six initial and nine final blocks:
61,440 block bytes, within the existing 65,536-byte stdout bound. Before any
block read, checked start/size reads establish that userdata ends before the
tail range. Independent review caught lost read errors inside arithmetic
substitution; separate checked assignments and bounded numeric validation now
reject missing, empty, malformed and overlong fields before reading blocks.

Both 45-source closures received independent `PASS_GO`; all 68 selected tests
passed in 5.394 seconds, and four changed Python files compile. The 144 native
source inputs are unchanged. Historical tail5/native results rederive exactly.
The old Android-return CAP is verified through its saved source snapshot;
current D0 source approval and its own snapshot are separate. A read-profile
update therefore needs no repeated Android transition. No partition-write or
formatting authority was added.

## Actual tail9 result and proposed layout

The new foreground D0 ran once after qualification. Its 61,712-byte stdout
contains the complete 61,440-byte block capture and matching geometry framing.
The raw command and same-boot before/after rooted Android health passed.
Both header CRCs and both 5,632-byte table CRCs validate; the tables are identical.
All 40 occupied extents are nonoverlapping and userdata agrees with sysfs.

Eleven existing entries share one nonzero partition GUID. The strict decoder
therefore returns `NO_PROOF` with `GPT partition name or GUID is missing or
ambiguous`. This result is preserved and rederives exactly. H0 analysis records
complete observations separately; it does not relax the decoder, normalize old
GUIDs, relabel the consumed terminal or acquire another capture.

| Region | Current size | Proposed size |
| --- | ---: | ---: |
| Android userdata | 223.458950 GiB | 159.458008 GiB |
| Native entry 41 | Absent | 64 GiB |
| Alignment gap after native | Part of userdata | 988 KiB |

The proposed native boundaries are 1 MiB-aligned and fit inside current
userdata. The table has four unused entries; entry 41 is the first. The other
39 entries retain their original bytes and extents, including their existing
GUIDs. An independent H0 review checked the raw joins, all preservation hashes
and the exact byte accounting. This establishes a layout proposal, not safe
GPT mutation or boot compatibility with that proposed table.

No retained target evidence establishes GPT restoration. Ordinary boot-only
Odin/A recovery was demonstrated under the original GPT. The upstream
[Heimdall transfer implementation](https://raw.githubusercontent.com/Benjamin-Dobell/Heimdall/master/heimdall/source/FlashAction.cpp)
also separates PIT upload from individual partition transfer; it does not prove
Samsung Qualcomm restoration behavior. A retained PIT with unspecified
userdata size is not an exact GPT restore artifact.

P396 subsequently qualified native UFS initialization and the complete fixed
44 KiB census with authenticated control; its captured bytes exactly match
the corresponding Android originals. Its independent strict metadata result
remains `NO_PROOF`, and it adds no GPT-write recovery qualification. See the
[native result](S22PLUS_NATIVE_UFS_H0_2026-09-15.md). No intentional GPT
corruption is proposed as a test.

## Exact 64 GiB byte construction

The host-only constructor validates the original protective MBR, both GPT
header/table CRCs, identical arrays, 44-entry shape, 40 occupied entries and
nonoverlapping extents. It changes only userdata's ending LBA and unused entry
41, then recomputes table/header CRCs. The new entry has a private fresh GUID,
the existing userdata type GUID and the name `native_data`. All 39 other
entries, header fields, disk identity, padding and original duplicate GUIDs
are preserved. Both generated copies validate without upgrading the strict
duplicate-GUID result.

Only four 4096-byte metadata blocks differ: LBA 1, LBA 3, the backup array's
second block and the final header. There are 61 changed bytes in each captured
region. Replacing the generated table with the original table and recalculating
the CRCs restores both entire original captures byte for byte. The constructor
uses bounded private regular files and contains no device writer or formatter.

Four focused tests pass: exact 64 GiB shape and four-block change set;
preservation of duplicate GUIDs and strict rejection; inverse restoration in
host prefix/torn-block models; and rejection of malformed originals, occupied
slots, overlapping extents or a reused new GUID. Both Python files compile.
Independent `PASS_H0_EXACT_LAYOUT_CONSTRUCTION` also reconstructs the actual
private output byte for byte. This qualifies byte construction only, with
physical restoration, execution order and GPT/PIT compatibility still unproved.

The proposal result is 3004 bytes, SHA-256
`dac9bfc854781e170444e1019a8bd0fd5ce1e22f14a9d262ca0a3b5a794631a9`;
the independent review is 3197 bytes, SHA-256
`ae7c05a35a7b02184dc606f757712c5abdcd767811ef3202045ced3f2eb3bb47`.
Both are retained under
`workspace/private/outputs/s22plus-native-64g-gpt-proposal-h0-20260915-1/`.

This construction does not resize the existing Android filesystem. Reserving
the GPT entry alone would leave its bytes untouched; using Android with the
smaller userdata would require a separately implemented reset/format path.
Original-A boot recovery alone cannot restore GPT, so it cannot serve as the
unchanged fallback for a later GPT mutation.

Private native evidence is under
`workspace/private/runs/s22plus-native-session-v3/storage-census-20260915-1/`.
The producer diagnosis and embedded config are under the original native
census H0 output. Android successor review/tests are under
`workspace/private/outputs/s22plus-android-storage-census-h0-20260915-1/`.
The actual return and first Android census are under
`workspace/private/runs/s22plus-native-session-v3/android-storage-return-20260915-1/`
and `workspace/private/runs/s22plus-android-storage-census-v1/census-20260915-1/`.
Tail9 H0 evidence is under
`workspace/private/outputs/s22plus-android-storage-tail9-h0-20260915-1/`.
The tail9 run is under
`workspace/private/runs/s22plus-android-storage-census-v1/census-tail9-20260915-1/`;
original GPT byte copies and the exact proposed layout are under
`workspace/private/outputs/s22plus-native-64g-layout-h0-20260915-1/`.
GPT modification/restoration remains unqualified. A90 and S20+ were untouched.
