# NATIVE_INIT V2507 — audio ACDB dependency closure live

Date: 2026-06-16

## Decision

`v2507-local-closure-reaches-bionic-tls-loader-block`

V2507 ran the V2506 private ACDB dependency closure through one checked Android
handoff and rolled back to V2321. The V2505 `libdiag.so` missing-library blocker
is closed: `libdiag.so` was staged locally beside `libaudcal.so`.

The new blocker is not another missing ACDB vendor library. Plain local
`dlopen()` of the staged `libaudcal.so` now fails while resolving bionic runtime
dependencies:

```text
TLS symbol "(null)" in dlopened "/apex/com.android.runtime/lib/bionic/libc.so"
referenced from "/apex/com.android.runtime/lib/bionic/libc.so" using IE access model
```

No ACDB GET call was reached. No raw ACDB payload was captured.

## Live Run

Private run directory, not committed:

```text
workspace/private/runs/audio/v2507-acdb-ownprocess-closure-live-20260616-031140
```

Runner decision:

```text
v2490-namespace-visible-load-failed-before-rollback-rollback-pass
```

The runner name/build tag remains the reused V2490 live handoff harness; the
iteration/result identity for this report is V2507.

Helper artifact used:

```text
path: workspace/private/builds/audio/v2489-acdb-ownprocess-get-host-only/bin/a90_acdb_ownprocess_get_v2489
sha256: 4fe262f5ef57390c306656ce6693ca57430b67479efac16c4b87f0ef75321834
```

Staged V2506 dependency closure:

```text
libaudcal.so      sha256=3f214dc18758d360cbc39d8a5323ff76baf6b5eb6c247de141bd6d5e91f4295d
libdiag.so        sha256=771920e96bbc1796288a430c315d93ddfb14941432baeca000c4e79292819d22
libacdb-fts.so    sha256=800eaf98197debbb6191172b6f22df3dbb09a0d80f6a471363c925a320f1b4db
libacdbrtac.so    sha256=2cef5b0f7444c3c94076f273f6b5841dad57d7ccb48da78f497338ded43ae6a4
libadiertac.so    sha256=a5abcac1573133c36f0575f6dd8b3e221daab07f889c13e83fdd6b730fb4c121
libacdbloader.so  sha256=25ae25afda6f52fc75d9b72e7f9df22094c7e3b243efb7257654ec9445bcd0a1
```

Sealed Android boot copy:

```text
sha256=c15ce425abb8da41f0b1696d19d05a625fd7cec949b4ae50651a5f1e7293057b
mode=0600
```

## Observed Events

First local load attempt:

```text
plain-local load /data/local/tmp/a90-acdb-ownget/libaudcal.so:
  failed: TLS symbol "(null)" in dlopened "/apex/com.android.runtime/lib/bionic/libc.so"
          referenced from "/apex/com.android.runtime/lib/bionic/libc.so"
          using IE access model
```

Namespace fallback remained unchanged:

```text
symbol_probe libdl:android_get_exported_namespace             found=false
symbol_probe default:android_get_exported_namespace           found=false
symbol_probe default:__loader_android_get_exported_namespace  found=true
symbol_probe libdl:android_dlopen_ext                         found=true

sphal   visible=true   load libaudcal.so: failed, not found
sphal   visible=true   load /vendor/lib/libaudcal.so: failed, not found
vendor  visible=false
default visible=true   load libaudcal.so: failed with bionic TLS error
default visible=true   load /vendor/lib/libaudcal.so: failed, not found
vndk    visible=true   load libaudcal.so: failed, not found
vndk    visible=true   load /vendor/lib/libaudcal.so: failed, not found
```

Final helper error:

```text
stage: namespace-visible-load-failed-libaudcal
code: -5
```

Artifact summary:

```text
acdb_ioctl row_count: 0
raw_file_count: 0
target_4916_count: 0
namespace_event_count: 11
symbol_event_count: 4
ownget stdout/stderr: empty
```

## Interpretation

V2507 is a real forward step because it distinguishes two failure classes:

1. V2505's missing `libdiag.so` dependency is solved by the V2506 closure.
2. The current blocker is the process/linker model for loading vendor blobs from
   a standalone shell/su process, specifically bionic TLS/initial-exec handling
   while resolving `libaudcal.so`'s runtime dependencies.

Host ELF inspection confirms the staged helper itself is minimal:

```text
helper NEEDED: libdl.so
interpreter: /system/bin/linker
```

The staged vendor libraries are `BIND_NOW` and depend on normal Android runtime
libraries such as `libc.so`, `libc++.so`, `libutils.so`, `libcutils.so`, and
`liblog.so`; `libacdbloader.so` additionally depends on `libtinyalsa.so` and
`libion.so`. The V2507 error appears before `libacdbloader.so` is attempted.

Therefore the next useful unit should not add more ACDB vendor libraries or
retry in-HAL injection. It should be host-only design for a loader-compatible
own-process variant, for example:

- run the helper through an Android runtime entry point that already has bionic
  runtime libraries loaded in a compatible way;
- or build a small Android app/process wrapper around the same pure-read helper
  logic;
- or adjust the helper link/load model so bionic runtime libraries are not
  re-dlopened as a duplicate TLS provider.

The boundary remains measurement-only and pure-read.

## Boundary Check

The live unit stayed inside the own-process pure-read boundary:

- no in-HAL `LD_PRELOAD` or wrapper-exec injection;
- no Magisk module install;
- no HAL restart;
- no AudioTrack/playback;
- no native speaker write;
- no `/dev/msm_audio_cal` open or SET ioctl;
- no `0xC00461CB` path;
- no `acdb_loader_send_common_custom_topology`;
- no raw payload committed.

## Rollback / Health

The checked handoff booted Android, staged and ran the helper, pulled the private
artifact directory, cleaned `/data/local/tmp/a90-acdb-ownget`, rebooted recovery,
and flashed V2321 through `native_init_flash.py`.

Post-rollback native health was verified:

```text
version: 0.9.285 build=v2321-usb-clean-identity-rodata
selftest: fail=0
```

## Validation

Commands/results:

```text
preflight rollback images: v2321/v2237/v48 present; v2321 and v2237 SHA matched
preflight native health: version 0.9.285, selftest fail=0
preflight dry-run: live_ready=true, command_safety.ok=true, source_kind=v2506-vendor-ext4-closure
live runner: completed
artifact pull: completed
rollback to V2321: completed
post-rollback selftest: fail=0
git diff --check: pending at report creation
```

## Next Unit

Host-only first:

1. design a loader-compatible own-process variant for the V2507 bionic TLS
   failure;
2. keep the same direct GET matrix and the same hard ban on `/dev/msm_audio_cal`
   and `0xC00461CB`;
3. run a dry-run/source-scan unit before any new live attempt.

Do not return to in-HAL injection or wrapper-exec.
