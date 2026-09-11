# S22+ native resident adoption H0 — P386 / v0.2.0-rc.4

Result: **PASS_RESIDENT_ADOPTION_H0; independent PASS_GO for H0 only**.
Target: **SM-S906N / g0q / S906NKSS7FYG8**.

This unit packages the qualified resident runtime and connects four authenticated
checkpoints to the existing ordinary one-candidate/one-Android-return F1 owner.
The [adoption specification](../operations/S22PLUS_NATIVE_RESIDENT_ADOPTION_V1.md)
defines the prospective thirty-minute observation. No device contact, transfer,
live prepared run, public READY activation or grant occurred.

## Artifacts and source identity

The packager reopens both copies of the previously qualified static AArch64 init,
renderer and gauge module, all 118 retained build inputs, the toolchain/kernel
pins and exact module import CRCs. Those native bytes were reused without a
rebuild. Deterministic boot/AP packaging replaces exactly three ramdisk payloads:
`init`, `s22-display` and `s22-display-modules/s22plus_max77705_telemetry.ko`.
All 45 entry identities and metadata are checked; the remaining payloads match
the reference. The kernel uses the existing reversible two-span identity-only
transform, with unchanged size and bytes outside those spans.

Both actual AP archives decode to the recorded boot bytes. The archive contains
only `boot.img.lz4`; the exact Android rollback archive is independently reopened.

| Final A/B artifact | Bytes | SHA-256 |
| --- | ---: | --- |
| Boot image | 100,663,296 | `67ff1e4403e18a6e8dc95a313e5c2957eb72a8ebd23baede25a67285c31b0960` |
| AP archive | 31,150,121 | `32983bada2b7384484ace22d6971b1b248d7d2a7866625ef75b54dfe85635f58` |

The unchanged native ELF/module identities and prior target-ABI qualification are
in the [resident runtime report](S22PLUS_NATIVE_RESIDENT_H0_V1_2026-09-11.md).
Candidate-static reuses the existing shared producer, binds the dynamic codec
reader chain, and exercises actual Process-v2 bundle/closure validation with a
private `draft-host-only` manifest. It selects ordinary candidate/rollback roles,
with neither baseline admission nor same-N restoration.

## Observation and return

Each of four sessions has a 60-second bound. The first three end with authenticated
DETACH and actual descriptor close. Subsequent opens require the same endpoint
and kernel boot, a fresh nonce and the next authentication ordinal. Dwell starts
after the first successful close; later opens are no earlier than 620, 920 and
1820 seconds from that point. One original 2100-second host budget covers the
observation. Existing guard arithmetic derives 3000 seconds without changing
other candidate timeout limits or renewing any session.

Each checkpoint executes fixed native health and exports bounded HUD records.
Authenticated native BOOTTIME checkpoints must span at least 1,800,000 ms, with
system, hardware and valid gauge sequences exceeding 601 and advancing between
checkpoints. Source age includes elapsed time since the frame and the procfs
clock's 10-ms truncation bound. CPU temperature and available sensor coverage
remain separate observations. A valid-to-unavailable gauge transition is retained.

Only the fourth checkpoint issues the existing exact CONTROL return. Complete
wire evidence and an accepted CONTROL survive a later semantic NO_PROOF result.
The ordinary owner retains one candidate and one exact Android return, final
health and durable recovery after an interruption. Uncertain close/reopen or
authentication stops further observation; cleanup addresses only its currently
owned descriptor. No command or transfer is replayed.

## H0 validation and limits

The new suite passed **11 tests in 105.373 seconds**. It exercises actual generated
C, renderer/collector IPC, PTYs and authenticated raw replay with explicitly
accelerated clocks and hardware/USB/guard fixtures. Cases cover four clean opens
and closes, malformed or truncated evidence, stale data, failed health, short
native span after CONTROL, descriptor/guard/endpoint faults, and interrupted
ordinary-owner recovery. The complete proof remains within the existing journal
and terminal JSON bounds; its command rows are stored once and reconstructed by
the reader.

The existing shared-core, P384 and P385 regression suites passed **47 tests in
60.183 seconds**, including exact Android exit, owner consumption and failure
recovery. After the final preparation repair, all **4 binding tests** passed
in 0.400 seconds. Touched Python passed `py_compile`. The unchanged native artifact inputs
allow reuse of the preceding AArch64 A/B and target-ABI checks.
The subsequent generic full/large preparation, P384 binding and P385 owner
regression passed **13 tests in 45.010 seconds** after the closure change.

Final independent review found a full-preparation integration defect: a compact
67,952-byte record exceeded the existing 65,536-byte writer limit even with short
fixture receipt paths. The small lifecycle fixture had not included that closure.
P386 now records each unique execution source once, preferring semantic names
over duplicate static aliases. All 176 unique file identities and required named
readers remain bound; other profiles and the core static map retain their original
form. The new test exercises actual `prepare_connected`, binding, writer and
`load_prepared`, replacing connected D0/Type-C and AP verification with explicit
fixtures. Its complete record is 63,880 bytes and reopens exactly. Restoring the
duplicate map still fails the unchanged writer limit before publishing a file.

P385's 112 native inputs still match the historical review. Exactly three shared
host files changed, so its original 160-input review no longer matches current
execution. The existing owner correctly refuses a new request with that stale
binding. Independent review includes preservation of the P385 exact-A behavior;
future exit still needs its existing prospective source/static/request/grant
binding and current attended physical recovery conditions. This unit modifies no
historical review activation, admission, consumed record or P385 artifact.

Private artifacts and evidence are retained under
`workspace/private/outputs/s22plus-fyg8-v0.2.0-rc.4/`, including
`candidate-build-final/`, `h0-review-final-2/` and `adoption-qualification/`.
The final qualification record binds source maps, build/static results, test
logs, compatibility checks and the independent review. Earlier H0 outputs remain
separate. One captured test log is labelled as tool-returned output; the remaining
test/build logs were redirected directly by the host commands.
A private snapshot retains all 176 reviewed execution source files with verified
readback, including preexisting local contract bytes outside this scoped commit.

Independent review closed with no unresolved findings. It covers archive/native
identity, authentication and descriptor ownership, observation/CONTROL evidence,
preparation serialization, ordinary N1/A1 recovery and P385 exact-A compatibility.
The final bundle result SHA-256 is
`f10fb9c9a22b9ecf0e6bccd7c8a5b5052513f854f95fba1a84f5f0215bce7698`;
its 157 static inputs and recomputed 176-source execution closure match. This
review creates no activated binding or device grant.
The private qualification record SHA-256 is
`7c7cdf35db89e9e26086ed9d024c56ad938658a7faf39b54c3e741aab45276e8`.

This is H0 capability evidence. Actual thirty-minute native operation, CPU sensor
exposure, physical pixels, uninterrupted service between checkpoints, thermal
accuracy, lossless lifetime history and recovery after kernel/DRM stalls remain
**UNPROVED**. P385's prior healthy native terminal is only the last observed
snapshot. Its fresh exact Android exit and rooted FYG8 health must precede P386
installation. A90 and S20+ were not contacted.
