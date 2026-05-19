# Native Init v396 Frame ELF Symbolization

## Summary

V396 adds a read-only frame ELF puller for the V392 `servicemanager` crash backchain and uses the pulled Android system ELFs to rerun the framechain analyzer.

The result is a clean symbolization pass for the previously missing `liblog.so`, `libbase.so`, and `servicemanager` frame objects. This was not Wi-Fi bring-up. It did not deploy helpers, start Android daemons, start Wi-Fi HAL, scan, connect, or mutate Android partitions.

## Added Tooling

- tool: `scripts/revalidation/wifi_service_manager_frame_elf_pull.py`
- plan: `docs/plans/NATIVE_INIT_V396_FRAME_ELF_SYMBOLIZATION_PLAN_2026-05-20.md`

The tool performs:

- narrow remote path allowlisting for the three V392 frame ELFs.
- `mountsystem ro` only.
- read-only `stat` plus `toybox base64 -w 0` transfer.
- private host evidence writes through the shared evidence store.
- automatic rerun of `wifi_service_manager_framechain_analyze.py` with the pulled `system-root`.

## Evidence

Primary evidence:

- live pull/analyze: `tmp/wifi/v396-frame-elf-pull-20260520-073940/`
- manifest: `tmp/wifi/v396-frame-elf-pull-20260520-073940/manifest.json`
- summary: `tmp/wifi/v396-frame-elf-pull-20260520-073940/summary.md`
- rerun framechain manifest: `tmp/wifi/v396-frame-elf-pull-20260520-073940/framechain/manifest.json`

Top-level result:

```text
decision: service-manager-frame-elf-symbolization-pass
pass: True
reason: read-only frame ELF pull and framechain analyzer completed
device_commands_executed: True
device_mutations: False
daemon_start_executed: False
wifi_bringup_executed: False
```

Pulled ELFs:

| remote | size | sha256 | local |
| --- | ---: | --- | --- |
| `/mnt/system/system/bin/servicemanager` | 96344 | `506a61cd825490c181e2ca5171b65f8b5f9b10db91ef3d367423308c1f6a9b65` | `system-root/system/bin/servicemanager` |
| `/mnt/system/system/lib64/libbase.so` | 251280 | `6b25a2135bf470280888b977706a8ce6b65e33aefc1b318f94ba40883ce836f6` | `system-root/system/lib64/libbase.so` |
| `/mnt/system/system/lib64/liblog.so` | 66408 | `6f71de4b9311ed6b996c1ddd63eab2893af88bdf3908da56a014fdeb8746eb37` | `system-root/system/lib64/liblog.so` |

Guardrails:

- allowlisted `/mnt/system/system` frame ELF paths only.
- `mountsystem ro` only.
- no helper deploy.
- no daemon start.
- no Wi-Fi HAL/start/scan/connect.

## Framechain Result

Rerun framechain analyzer:

```text
decision: service-manager-framechain-symbolization-pass
pass: True
symbols_present: True
remaining_blockers: []
```

Frames after V396:

| frame | mapped object | relative offset | symbol/result |
| --- | --- | --- | --- |
| 0 | `/system/lib64/liblog.so` | `0x63bc` | `__android_log_set_aborter` |
| 1 | `/system/lib64/libbase.so` | `0x16188` | `android::base::LogMessage::~LogMessage()` |
| 2 | `/system/bin/servicemanager` | `0x8294` | no symbol table name; disassembly shows fatal `android::base::LogMessage` path |
| 3 | `/system/bin/servicemanager` | `0x13b14` | symbolized into libc++ tree-remove area; disassembly is service-manager setup/main path |
| 4 | `bionic/libc.so` | `0x84378` | `__libc_init` |
| 5 | `/system/bin/servicemanager` | `0x8058` | no symbol table name; entry/init area |
| 6 | none | none | framechain end / maprow not found |

## Interpretation

V396 removes the missing-ELF blocker. The crash path is now clearly a `LOG(FATAL)`/abort path rather than a raw segmentation fault:

- frame0 and frame1 are Android logging/base fatal-log cleanup.
- frame2 points at `servicemanager` offset `0x8294` immediately after `android::base::LogMessage::~LogMessage()`.
- nearby disassembly passes file `frameworks/native/cmds/servicemanager/Access.cpp`, line-immediate `441`, and severity `6` into `android::base::LogMessage`.
- pulled `servicemanager` strings include these relevant checks:
  - `Check failed: selinux_status_open(true ) >= 0`
  - `Check failed: gSehandle != nullptr`
  - `Check failed: getcon(&mThisProcessContext) == 0`
  - `/dev/binder`
  - `frameworks/native/cmds/servicemanager/Access.cpp`

The strongest current candidate is therefore a missing or invisible SELinux runtime/status surface inside the private Android namespace, not Wi-Fi itself. This is still a candidate, not final proof; V397 should verify SELinux status/context visibility before any repair or HAL start-only attempt.

## Validation

Static validation:

```text
python3 -m py_compile scripts/revalidation/wifi_service_manager_frame_elf_pull.py
```

Plan-only validation:

```text
python3 scripts/revalidation/wifi_service_manager_frame_elf_pull.py \
  --out-dir tmp/wifi/v396-frame-elf-pull-plan \
  --run-log tmp/wifi/v392-approved-full-20260520-072551/live/native/run-system-servicemanager.txt \
  plan
```

Plan result:

```text
decision: service-manager-frame-elf-pull-plan-ready
pass: True
device_commands_executed: False
device_mutations: False
daemon_start_executed: False
wifi_bringup_executed: False
```

Read-only live pull/analyze:

```text
python3 scripts/revalidation/wifi_service_manager_frame_elf_pull.py \
  --out-dir tmp/wifi/v396-frame-elf-pull-20260520-073940 \
  --run-log tmp/wifi/v392-approved-full-20260520-072551/live/native/run-system-servicemanager.txt \
  --timeout 300 \
  pull
```

Live result: PASS with no mutation, no daemon start, and no Wi-Fi bring-up.

## Next Target

Proceed to V397: SELinux status/runtime surface proof.

V397 should verify, read-only first:

- whether `/sys/fs/selinux` is visible inside the private namespace.
- whether `/sys/fs/selinux/status` and related SELinux runtime files are present and readable.
- whether `getcon`, service context files, and SELinux handles have the expected runtime inputs.
- whether the private-root bind/mount plan needs a minimal SELinux surface before `servicemanager` can start cleanly.

Wi-Fi HAL/start/scan/connect remains blocked until the `servicemanager` runtime gap is resolved or explicitly classified as non-blocking with stronger evidence.
