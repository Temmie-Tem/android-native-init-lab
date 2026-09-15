# S22+ native UFS: P395 incident and P396 result

**P396 `v0.2.2-rc.2` completed bootstrap and the full fixed native UFS read,
then closed `NATIVE_CLOSED_HEALTHY` without Android recovery.** All 44 KiB of
captured LU0 storage bytes match the saved Android bytes. Strict GPT remains
`NO_PROOF` because the original backup array is outside the fixed tail-five
range. Both operations and the grant are permanently closed, with no F1 owner.
No partition split or format occurred. The earlier P395 failure and one-A
recovery remain recorded below with their original evidence.

## Bounded purpose

The [captured layout](S22PLUS_ANDROID_STORAGE_CENSUS_H0_2026-09-15.md)
supports a numerical 159.458 GiB userdata plus 64 GiB native proposal, with all
39 non-userdata entries preserved. Strict GPT qualification remains `NO_PROOF`
because eleven existing entries share a GUID; the original bytes and verdict
are preserved. Exact modified-GPT restoration is still unqualified.

P393 does not initialize Qualcomm UFS. The smallest useful next capability is
storage access independent of Android userdata, retaining authenticated native
control. P395 addresses that prerequisite. It adds no GPT writer, formatter,
filesystem mount or user-key request. Its
[F1 profile](../operations/S22PLUS_NATIVE_UFS_V1.md) separately describes
ordinary driver initialization, discovery, internal device-feature changes and
shutdown behavior. It does not claim zero hardware writes or automatic recovery
from a kernel/SCM/storage stall.

## Implementation and static evidence

Eight fixed stock modules are loaded after existing E3/display initialization
and before the supervised renderer drops privilege. Their exact sealed FYG8
vendor-ramdisk files supply the PHY, UFS host and required crypto dependencies.
The loader follows no directory/file symlink, checks ownership/mode/link count
and size, and uses one empty-parameter, zero-flag `finit_module` per file.
There is no insertion retry or unload. Module insertion alone is not a storage
readiness proof. Newly loaded files are excluded from the unselected-file
memory census.

The actual kernel executable code, E3 module plan and boot-ramdisk inventory
remain unchanged; only existing declared image identity spans, native identity
and the supervised renderer change. All original 144 native source inputs are
unchanged. Four new inputs form the 148-source UFS composition. The separate
48-source host capability includes the profile-routing factory code while
keeping declarative candidate rows separate.

All eight actual module import CRCs resolve against the fixed kernel and
preceding module exports in order. Their FYG8 vermagic and vendor-file digests
match. This is ABI/linkage evidence, not live driver-probe evidence. Source
review distinguishes ordinary UFS/ICE configuration, multi-LU discovery,
conditional HPB buffer commands and shutdown handling from unrequested key
programming or partition-data writes.

Actual A/B packaging produces the same 31,303,721-byte AP with SHA-256
`05ec20c6a350679d24f48cba5e81f94b8d04f74bab3390857137965385312b49`.
Both 96 MiB boot images, their compressed members and the AP's actual contents
are joined by the retained package auditor. The dedicated UFS exporter
qualifies the new profile and leaves the historical exporter bytes untouched.
The live validator checks that exporter and the producer's UFS profile.

## Original H0 qualification

All **75 focused tests pass** in 5.419 seconds. A real static ARM64 harness
under QEMU exercises directory/open flags, symlink/hardlink/type/size/mode and
ownership failures, ordered insertion calls and failure without retry. File
syscalls are real; fixture root ownership and module insertion are substituted.
It never inserts a host module. The first composition fixture incorrectly
provided an empty memory census; a valid nonempty fixture corrected that H0
test error without changing the existing source assertion.

Tests also cover exporter/profile joins, actual bootstrap admission before
census, consumed tails, raw observation and existing recovery/no-replay paths.
Nine touched Python files compile. The original Android-return close and both
Android census terminals rederive unchanged under the new host code.

The actual returned grant covered 1,800 seconds and two attended operations:
the existing two-installation/four-authentication bootstrap, then one fixed
native census. Bootstrap completed both installs and all four authenticated
health observations and published admission. The following census ran once.
The existing native census keeps its original six-initial/five-final-block
bounds. Its output can establish native access by comparison with saved Android
bytes while its stricter full-GPT result remains separately `NO_PROOF`.
A later partition mutation still requires a reviewed restoration method for
its declared failure cases and applicable authority.

Private build, ABI, test and review evidence is under
`workspace/private/outputs/s22plus-native-ufs-h0-20260915-1/`; the A/B package is
under `workspace/private/outputs/s22plus-native-ufs-v1/p395/build-1/`.
A90 and S20+ were untouched.

## P395 live result, incident and recovery

The census completed fresh authenticated health and accepted EXEC sequence 5.
It returned 21 stdout frames containing 16,128 bytes, then an authenticated
EXIT with `CLEANUP|OUTPUT_INCOMPLETE` (`0x88`), wait status zero, exec errno zero
and dropped-byte count zero. The host transmitted DETACH sequence 6; its ACK
is the first missing final stage. RX ends at a complete frame boundary.

After the 134-byte geometry prefix, 15,994 LU0 bytes exactly match the previous
Android capture prefix (SHA-256
`a1889a4643bd531591184dcd21735dab24279bfb65e808690233419492415090`).
The complete primary GPT header and 5,632-byte entry array are present and
both CRCs validate. This is observed native UFS access. Backup bytes, final
geometry and `END` are absent; complete census and alias cleanup are unproved.
No complete module-insertion trace was captured. Neither the partial bytes
nor successful native bootstrap upgrades strict GPT qualification.

The packaged console polls every 100 ms and sends bounded 768-byte output
chunks. Main-child reap starts a two-second descendant-cleanup timer; its
old completion predicate also requires pipe EOF. Buffered output alone can
therefore trigger `0x88`. The old H0 console fixture polls every 1 ms and
missed this condition. The observed frame count supports this diagnosis;
the live transcript does not expose every internal cleanup predicate.

The initial recovery wait found no usable Download endpoint and sent no A.
After the operator's physical Download action, one exact A transfer completed.
Its first health attempt failed target/authorization binding during Android
return. The existing health-only recovery resumed without another transfer
and passed exact rooted FYG8 health and boot/supporting partition hashes.
The census remains consumed and cannot be replayed.

### Canonical timeline

Times below are elapsed host BOOTTIME seconds from the original grant, derived
from immutable operation journals. They include host suspend.

| Elapsed seconds | Durable event |
| ---: | --- |
| 2.275 | Android preflight complete |
| 17.725 / 19.231 | First P395 transfer intent / completion |
| 44.583 / 46.816 | First-boot authenticated sessions complete |
| 55.200 / 56.728 | Same-P395 qualification transfer intent / completion |
| 82.132 / 83.867 | Second-boot sessions complete; native bootstrap qualified |
| 154.742 | One native census observation starts |
| 215.232 | Observation stops after missing DETACH ACK |
| 215.268 | Recovery starts; initial endpoint wait has no A intent |
| 464.131 / 465.545 | One original-A intent / transfer completion after physical action |
| 651.264 / 653.093 | Health-only resumption / final Android health complete |
| 742.898 | Task permanently closed, two operations consumed, no owner |

Private live evidence and the frozen host source snapshot are under
`workspace/private/runs/s22plus-native-session-v3/p395-ufs-bootstrap-20260915-1/`.
The original source commit is `385b9797ca18721211963c0d5028ae59c0c9bfd3`.
The operator also reported the missing `rc.1` display suffix. Consumed P395
continues to identify as `v0.2.2`; its intended `rc.1` is historical. The
output-fix successor correctly declares `v0.2.2-rc.2`.

## Bounded successor

P396 retains UFS initialization and uses a separate console source composer.
It distinguishes process-group settlement from buffered pipe EOF. After
settlement, buffered output drains within the original command deadline;
unsettled groups and explicit cancellation/timeout keep the original cleanup
bound. Stream fairness, queue credits, byte/frame limits and CONTROL are
unchanged. Clean completion still requires EOF. Host DETACH now rejects
terminal flags or dropped bytes before writing; a nonzero child status with
zero flags remains a completed negative command.

This correction addresses incomplete console delivery and mismatched DETACH
admission. Its review trigger is any change to these predicates, original
limits or their producer/host composition. No extra live gate or new recovery
mechanism is introduced. P396 requires actual A/B qualification, representative
100 ms ARM64 behavior and current independent review before a fresh grant.
It creates no GPT writer, restoration qualification or permission to reuse the
closed P395 grant. A90 and S20+ were untouched.

The successor passes **60 focused tests**: 23 producer/protocol/artifact/census
tests in 32.416 seconds and 37 cleanup/adapter/session/target-I/O tests in
2.448 seconds. At the actual 100 ms cadence, a static ARM64 supervisor and
explicitly selected packaged ARM64 BusyBox reproduce the old `0x88` failure;
the corrected composition delivers all 49,152 binary stdout bytes and stderr.
Real pipes, process groups and socket backpressure are exercised. Separate
coverage retains cancellation, timeout, CONTROL and background-child cleanup;
a controlled unkillable-group fixture preserves the exact two-second failure
stop. Kernel/USB behavior and a live P396 result remain unproved.

Both actual P396 AP packages are identical, 31,303,721 bytes, SHA-256
`d0027e5ba54e75c2b06179746df74499b98d4ca65d29ff412211120d0ea08903`.
Actual member/boot/package joins pass. Its 150 native inputs consist of the
unchanged old 148 plus the new composer and builder. The UFS loader/renderer
behavior is unchanged. The separate exporter leaves old qualification receipts
valid. Nine touched Python files compile; all nine completed P395 bootstrap
and recovery steps rederive under the updated host code without device I/O.
Private build, tests and review inputs are under
`workspace/private/outputs/s22plus-native-output-drain-h0-20260915-1/`.

Independent review returned **`PASS_GO`** for both 49-source host closures and
all 150 native inputs, with no blocking findings. The reviewed public and local
root variants preserve the unrelated S20+ working changes. The fresh request
is 1,800 seconds and two attended operations: P396 bootstrap, then one fixed
native census after actual admission. Its exact A artifact, retained recovery
evidence, five installed host files and noninteractive host readiness validate.
The subsequently returned grant and completed P396 task are at
`workspace/private/runs/s22plus-native-session-v3/p396-drain-rc2-bootstrap-20260915-1/`.
This is the concrete next action under the
[V3 actual-returned-grant requirement](../operations/S22PLUS_NATIVE_SESSION_V3.md);
it neither renews P395 nor changes the outstanding GPT-restoration requirement.

The initial P396 H0 package/request incorrectly repeated `rc.1`; it was
retired before grant opening, with no device effect or candidate consumption.
The corrected `rc.2` rebuild has byte-identical kernel and init, and each
renderer differs only in the single version character. All 49 host and 150
native source inputs are unchanged, so the existing tests and independent
capability review are reused. Fresh A/B package qualification and version-byte
evidence are under
`workspace/private/outputs/s22plus-native-output-drain-rc2-h0-20260915-1/`;
the immutable build directory is
`workspace/private/outputs/s22plus-native-output-drain-v1/p396/build-rc2-1/`.

## P396 rc.2 live result

The actual 1,800-second/two-operation attended grant completed both planned
operations. Bootstrap installed P396 twice and passed all four authenticated
native health observations, with actual N admission. The subsequent census
used that admission and the unused final native tail exactly once.

Census EXEC sequence 5 returned 45,328 stdout bytes in 60 frames, no stderr,
zero flags/wait status/exec errno and no dropped bytes. It includes both equal
geometry brackets, all 45,056 declared storage bytes and the final `END`
marker. DETACH sequence 6 was acknowledged and the descriptor actually closed.
The fixed script's successful completion retains its alias-cleanup condition.
The old post-reap output cutoff did not recur in this run.

Both the 24,576-byte primary region and 20,480-byte final region exactly match
the corresponding original Android capture. The primary header and entry-array
CRCs pass. The original full Android backup table still matches that primary;
the new native read did not capture that entire backup array. The unchanged
canonical parser reports `GPT entry array is outside its capture or overlaps
its header`. This remains `NO_PROOF`, separate from the proved bounded read
and native health/close. The earlier duplicate-GUID observation is unchanged.

### P396 canonical timeline

Elapsed host BOOTTIME seconds from this grant, including host suspend:

| Elapsed seconds | Durable event |
| ---: | --- |
| 14.757 | Exact Android preflight complete |
| 30.552 / 32.103 | First P396 transfer intent / completion |
| 45.144 / 47.399 | First-boot authenticated sessions complete |
| 55.980 / 57.503 | Same-N qualification transfer intent / completion |
| 82.812 / 84.674 | Second-boot sessions complete; native admission earned |
| 109.110 / 117.485 | Fixed census observation starts / closes healthy native |
| 233.198 | Task permanently closed, two operations consumed, no owner |

Original A was not transferred. P396 remains admitted with the new healthy
native tail; this is a past health snapshot, not automatic recovery or future
responsiveness. The five installed host files remain verified external
configuration. A90 and S20+ were untouched. The census does not capture a complete module-insertion syscall trace;
the complete LU0 read is direct functional storage evidence.

The immutable task close has SHA-256
`f52e61d9b72d6f3de2f3fa84c13f184122a0b163c66fcbda9a22b159238c3b97`.
Its source snapshot binds commit `8ed15cb14007ec4624a746256189902a4380cf03`,
the 49 actual host inputs and capability, plus the 150 native source identities.
The authenticated extraction and byte comparison are under that task's
`analysis/`, with comparison receipt SHA-256
`eecd5504af0d4962ac9871368e92a11bc4e2781f73826c8e49e88c5ce585d456`.
Storage access removes one prerequisite; exact GPT write/restoration machinery
and reachability for its declared interruption cases remain unqualified.
