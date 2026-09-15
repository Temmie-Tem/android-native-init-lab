# S22+ Android32 layout and minimal Android preparation

The prospective P398 unit shrinks Android userdata to **32 GiB** and expands
the existing unformatted native entry to **191.4580078125 GiB**. It starts
from the [closed P397 result](S22PLUS_NATIVE_GPT_128G_LIVE_2026-09-15.md),
whose actual GPT and rooted Android reboot evidence rederive. This report
records H0 preparation; no new grant, device command or device effect has occurred.

## Exact layout and recovery

| Entry | Current size | Proposed size | Proposed first / last LBA |
| --- | ---: | ---: | --- |
| 40 userdata | 95.4580078125 GiB | 32 GiB | 3,726,848 / 12,115,455 |
| 41 native_data | 128 GiB | 191.4580078125 GiB | 12,115,456 / 62,305,023 |

The constructor changes userdata end, existing native start and matching CRCs.
The native GUID/type/name/attributes/end, other 39 entries, disk identity,
padding and historical duplicate GUIDs are preserved. Only GPT LBAs 1, 3,
62,305,272 and 62,305,279 change. The sealed original vectors join P397's
actual final metadata to its proposed vectors; pre-reservation stock metadata
is not the successor's restoration target.

The unchanged four-block core retains its serial partial-write model and
single apply/restore roles. Host and native geometry checks admit only the
historical reservation or this exact successor. Independent review caught an
old parent-level size guard; actual ARM64 tests now cover both exact pairs,
invalid pairs, original/proposed sysfs maps, direct/synchronous I/O and faulted
restoration. These host tests do not prove physical media durability.

The [common-incorporated G2 policy](../operations/S22PLUS_NATIVE_GPT_RESERVATION_V1.md)
requires fresh native admission, a complete actual original-GPT read, one apply,
physical restart, proposed GPT proof, one unchanged stock recovery reset,
fresh GPT/F2FS geometry, one original Magisk A transfer, and rooted Android
GPT/statfs checks before and after one ordinary reboot. Android apps, settings
and data are erased by reset. If restoration is needed after reset intent,
its separate restorative reset uses the original 95.4580078125 GiB userdata.
Layout restoration cannot recover erased data. An uncertain effect never replays.

## Formatter and fresh image

The hash-verified stock ARM64 formatter ran exactly once under QEMU against
one private 32 GiB sparse regular file, without block devices or network.
The exact Android options and final 16 KiB exclusion produced block count
8,388,604, segment0 512 and segment count 16,382 in both geometry copies.
The footer sentinel stayed intact; allocated host space was 77,709,312 bytes.
Expected Android statfs total is 34,357,624,832 bytes, subject to actual live
geometry and mounted health proof. Native storage remains unformatted.

The initial postprocessor rejected nonempty stderr despite formatter exit 0.
Its 205-byte linker warning exactly matched the previously accepted H0 capture.
Only interpretation resumed from retained raw bytes; the formatter did not run
again. The result retains that warning and the distinction between formatter
geometry and complete filesystem health. The disposable model file was retired.

Fresh P398 **v0.3.0-rc.2** passes byte-identical A/B building and actual AP/member
qualification. The boot-only AP is 31,354,921 bytes, SHA-256
`0dfcba4eab71b328a687d78a240a68dbc61938b8e71acb73b69e4ab0e603a388`.
All 156 actual runtime source inputs still match. The later risk-tier and
app-runner corrections change host authority/observation sources, not the
qualified native runtime. Old candidates and consumed images retain their identities.

Only this successor recognizes the exact completed initial-health missing-su
rc127 as setup pending. It preserves the failed raw attempt and original grant,
requires an actual new setup-completion statement, and repeats only full reads
before the still-unconsumed ordinary reboot. Unknown or incomplete attempts
remain stopped. Publication cuts are reconstructed without replay; P397's
historic incident and health-only recovery remain unchanged.

## Separate optional-app cleanup

The [Android-minimal profile](../operations/S22PLUS_ANDROID_MINIMAL_V1.md) runs
only after the closed Android32 GPT, capacity, changed-boot and root proof
rederive. It records the existing explicit minimal-management request and
actual attendance. Fixed Package Manager inventory selects from 35 optional
consumer apps, excluding required, shared-UID, persistent and customized
primary-user packages. Settings, launcher, input, files, networking, ADB and
Magisk are outside its removal declaration.

Each selected uninstall binds user 0, the same Android boot, current package
metadata and version, then records an intent before dispatch. One final
ordinary reboot proves retained root, required home/input components, full GPT
and capacity. Actual available-space change is measured; removing a primary-user
system app does not imply deletion or resizing of its system APK partition.

An immutable claim permits only one cleanup open per closed G2 task. This closes
the independent review finding that a new output folder could otherwise renew
the clock and retry an uncertain uninstall. After failure, only one bounded
read-only reconciliation remains; partial cleanup stays incomplete even when
Android health passes. Complete raw results can be republished without I/O.
The original 900-second cleanup window and 300-second reconciliation limit
cannot authorize another uninstall or reboot. No package inventory or cleanup
has yet occurred on the device, so selected apps and reclaimed space are unknown.

## Evidence and activation

Private proposal, formatter, build, qualification and focused-test evidence
are under `workspace/private/outputs/s22plus-native-android32-gpt-proposal-h0-20260916-1/`.
The proposal result SHA-256 is
`1acf0147026ca4dcc07008ba61f32660b65c9a455dc2ee640a554acde179362c`;
the formatter result SHA-256 is
`015dba0cabcc9f87de1c1dd73a337341b4c56c1177ae0025d58b609ac2464467`;
the qualified image receipt SHA-256 is
`bd0c1931e28a3dabf69313eeb4d9e0f4a3f22003305b777a09e0db0ef1294409`.

Independent review covers the exact layout, reachable native/host paths,
common/target/risk-tier interactions, setup publication cuts, cleanup claims,
raw proof reconstruction and unchanged recovery limits. Capability review is
separate from the actual finite grant and live qualification. The immediate
completion criterion is the new layout, initialized rooted Android, reboot
persistence and a terminal scoped cleanup result. Debian formatting, rootfs
staging and runtime execution remain subsequent units. A90 and S20+ are untouched.

The final focused run passes **67 tests**, including actual ARM64 execution,
raw subprocess evidence and failure/publication paths; all 15 touched Python
source/test files compile. The test postprocessor initially applied a
zero-stderr producer rule to unittest's ordinary stderr report. Its retained
exit-zero, complete 67-test `OK` output was interpreted in H0 without rerunning
the suite. No device-result success rule was changed.

Both independent capability consumers accept their final receipts:

| Review | Bound sources | SHA-256 |
| --- | --- | --- |
| V3 capability | 54 execution / 156 native | `98495345afb0cd8a5f5305d9104656f742dec207f31a8ec7254c8fd6ca934769` |
| Android-minimal | 56 execution | `9faab73b7d1a0f7316b88b950958a0b1b4fc147618670fb91a9fc3f336de9844` |

The concrete task `p398-native-android32-20260916-1` is prepared for 7200 seconds,
two operations (fresh bootstrap and G2), attended recovery and final Android.
Its task SHA-256 is
`7fffbee7fad599bbe70cf5c4c6919b96e1ab27f05b2217ec0487e68d45b65927`.
Exact current host source bytes and the capability receipt are preserved in
its private source snapshot. Original A and demonstrated recovery inputs pass
the task's actual validator. Fixed host installation/readiness and holder
census pass, no F1 owner exists, and no grant has been opened. The actual
returned finite approval remains required; these preparation checks do not
establish fresh live target health or qualify the new endpoint on the device.

The hashes above identify the task's live working-source reviews, preserved
with its exact private snapshot. Independently checked publication copies
instead bind the staged root contract, excluding only the preexisting unrelated
S20+ status row and closed-exception paragraph. No S22+ semantics or other
execution/runtime source differs. Publication receipt SHA-256 values are
`5a9b3f6fe4df09e436d516f7be0e8e8f10a1c3f4f9696806294731e324e82eb0`
(V3) and `b1afca18f2f4009ca12143a8c93414ab164808993461bec58a011bf963162159`
(Android-minimal). Publishing these copies does not repin the prepared task.
