# S22+ native UFS prerequisite: P395 H0

**P395 `v0.2.2` has matching A/B boot packages, 75 passing focused tests and
independent `PASS_GO` for both host closures and its native source closure.** No P395 transfer or native
UFS device experiment has occurred. The device last closed healthy original-A
Android after the complete GPT capture. No partition split or format occurred.

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

## Validation and next execution

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

The prepared task is 1,800 seconds and two attended operations: the existing
two-installation/four-authentication P395 bootstrap, then one fixed native
storage census. No E, HUD, extra reconnect or Android-exit operation is selected.
Census preparation remains blocked until actual N admission and an unused
healthy tail exist. Any source review, prepared request or H0 build is not a
returned grant; no grant has opened. Exact task binding, original A/recovery
evidence, the five installed host files and noninteractive host readiness pass.
The request is under
`workspace/private/runs/s22plus-native-session-v3/p395-ufs-bootstrap-20260915-1/`.
Host readiness is not a fresh device-health observation; the runner performs
its fixed Android preflight when the actual grant is used.

The existing native census keeps its original six-initial/five-final-block
bounds. Its output can establish native access by comparison with saved Android
bytes while its stricter full-GPT result remains separately `NO_PROOF`.
A later partition mutation still requires a reviewed restoration method for
its declared failure cases and applicable authority.

Private build, ABI, test and review evidence is under
`workspace/private/outputs/s22plus-native-ufs-h0-20260915-1/`; the A/B package is
under `workspace/private/outputs/s22plus-native-ufs-v1/p395/build-1/`.
A90 and S20+ were untouched.
