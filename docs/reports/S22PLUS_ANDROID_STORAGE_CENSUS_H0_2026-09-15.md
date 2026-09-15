# S22+ storage census result and Android successor

The approved one-operation native census is consumed and closed:
**metadata `NO_PROOF`, terminal `NATIVE_CLOSED_HEALTHY`**. No GPT was obtained,
and no partition split or formatting occurred. The current 64 GiB goal still
retains Android and allows resetting user data; it is not yet achieved.

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
The latest healthy native tail is this census terminal. Its raw result
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

The selected path returns through the existing reviewed original-A V3 exit,
then uses the [fixed Android D0 profile](../operations/S22PLUS_ANDROID_STORAGE_CENSUS_V1.md)
in a storage-capable environment. This does not add storage drivers to P393.
The Android-return transition needs its own actual finite grant; the adopted
foreground D0 profile needs no repeated approval after its reviewed entry
conditions pass. No successor grant or Android device command has occurred.

The new D0 uses existing Android nodes, verifies exact LU0 identity before
reading, and preserves matching seven-command Android health brackets around
one fixed 44 KiB metadata read. Failure emits a fixed stage label. Raw output,
metadata qualification and final health remain separate. The command creates
no node, loads no module, reads no user files or keys, and writes no partition.

## H0 qualification

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
execution is not yet observed. Its `dd status=none` option is covered by the
[AOSP Toybox tests](https://android.googlesource.com/platform/external/toybox/%2B/dc973f12b2fe4086165b8df1552f7dcb3929e8d1/tests/dd.test).
The native image/runtime and its 144 source inputs remain unchanged.

The prepared return request selects only original-A `android-exit`, 900 seconds,
one operation and deferred physical recovery. Its P393 admission, latest native
tail and original A evidence rederive; the five installed host files, current
readiness and expected native endpoint with no holder were checked without a
device command. The actual returned transition grant is still pending. The
subsequent adopted Android D0 is separate foreground read authority.

Private native evidence is under
`workspace/private/runs/s22plus-native-session-v3/storage-census-20260915-1/`.
The producer diagnosis and embedded config are under the original native
census H0 output. Android successor review/tests are under
`workspace/private/outputs/s22plus-android-storage-census-h0-20260915-1/`.
GPT modification/restoration remains unqualified. A90 and S20+ were untouched.
