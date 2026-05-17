# Native Init v236 Bounded Linker Crash Context Capture

## Summary

- Goal: capture bounded process crash context for the reproducible Android
  linker `SIGSEGV(11)` found in v233-v235.
- Result: PASS / `android-linker-crash-context-captured`.
- Reason: all selected linker runs crashed with `SIGSEGV(11)` and ptrace-lite
  captured exec-stop and crash-stop context.
- Device baseline: `A90 Linux init 0.9.59 (v159)`.
- No Wi-Fi daemon entrypoint, `cnss_diag`, scan, connect, credential, DHCP,
  routing, global bind mount, or persistent Android partition write was used.

## Implementation

Updated helper:

- source: `stage3/linux_init/helpers/a90_android_execns_probe.c`
- helper version: `a90_android_execns_probe v5`
- local helper SHA256: `4dccd09666900434609062c755559d7608484536ff6d26528cf9d089820b25d4`
- deployed helper path: `/cache/bin/a90_android_execns_probe`

Added host wrapper:

- `scripts/revalidation/wifi_linker_crash_capture_probe.py`
- live evidence: `tmp/wifi/v236-linker-crash-capture-live`

v5 helper changes:

- `--capture-mode none|ptrace-lite`
- `ptrace-lite` only traces the helper's own child process
- bounded capture at exec-stop and crash-stop:
  - `/proc/<pid>/auxv`
  - `/proc/<pid>/maps`
  - `/proc/<pid>/mountinfo`
  - `/proc/<pid>/exe`
  - `/proc/<pid>/cwd`
  - `PTRACE_GETSIGINFO`
  - `PTRACE_GETREGSET NT_PRSTATUS`

## Inputs

Real Android generated linkerconfig captured during v233 and redeployed
transiently under `/cache/bin`:

| temporary native path | SHA256 |
| --- | --- |
| `/cache/bin/a90_real_ld.config.txt` | `1ab340f0ee1e5f6d7c43e372dfe3bc9164d34b348dd9c716ded1b4e56e079f1a` |
| `/cache/bin/a90_real_apex.libraries.config.txt` | `5419adf6ed8f74c480d79096681a19a8570470ab8359c6e8c0be110da434f16e` |

Both temporary files were removed after probing and verified absent with `stat`
returning `ENOENT`.

## Commands

Deploy helper and inputs:

```bash
python3 scripts/revalidation/tcpctl_host.py \
  --device-binary /cache/bin/a90_android_execns_probe \
  --toybox /cache/bin/toybox \
  install \
  --local-binary stage3/linux_init/helpers/a90_android_execns_probe \
  --transfer-timeout 120

python3 scripts/revalidation/tcpctl_host.py \
  --device-binary /cache/bin/a90_real_ld.config.txt \
  --toybox /cache/bin/toybox \
  install \
  --local-binary tmp/wifi/v233-android-linkerconfig-source-live/files/linkerconfig__ld.config.txt \
  --transfer-timeout 120

python3 scripts/revalidation/tcpctl_host.py \
  --device-binary /cache/bin/a90_real_apex.libraries.config.txt \
  --toybox /cache/bin/toybox \
  install \
  --local-binary tmp/wifi/v233-android-linkerconfig-source-live/files/linkerconfig__apex.libraries.config.txt \
  --transfer-timeout 120
```

Run bounded capture matrix:

```bash
python3 scripts/revalidation/wifi_linker_crash_capture_probe.py \
  --out-dir tmp/wifi/v236-linker-crash-capture-live \
  --linkerconfig-mode copy-real \
  --linkerconfig-source /cache/bin/a90_real_ld.config.txt \
  --apex-libraries-source /cache/bin/a90_real_apex.libraries.config.txt \
  --linker-profiles system-linker,apex-linker \
  --target-profiles system-toybox,apex-linker64-self,cnss-daemon \
  --env-modes clean \
  probe
```

Cleanup:

```bash
python3 scripts/revalidation/a90ctl.py --timeout 20 run /cache/bin/toybox rm -f \
  /cache/bin/a90_real_ld.config.txt \
  /cache/bin/a90_real_apex.libraries.config.txt
```

## Matrix Result

| linker | target profile | signal | siginfo | regset bytes | exec captured | crash captured |
| --- | --- | ---: | ---: | ---: | --- | --- |
| `system-linker` | `system-toybox` | 11 | 11 | 272 | true | true |
| `system-linker` | `apex-linker64-self` | 11 | 11 | 272 | true | true |
| `system-linker` | `cnss-daemon` | 11 | 11 | 272 | true | true |
| `apex-linker` | `system-toybox` | 11 | 11 | 272 | true | true |
| `apex-linker` | `apex-linker64-self` | 11 | 11 | 272 | true | true |
| `apex-linker` | `cnss-daemon` | 11 | 11 | 272 | true | true |

Decision:

```text
android-linker-crash-context-captured
```

Reason:

```text
all selected linker runs crashed with SIGSEGV and ptrace-lite crash context was captured
```

## Crash Context Pattern

Across all six selected cases:

- `capture.crash.siginfo.signo=11`
- `capture.crash.siginfo.code=1`
- `capture.crash.siginfo.addr=0xa1`
- `capture.crash.regset.nt_prstatus.bytes=272`
- `capture.exec.exe` and `capture.crash.exe` resolve to the private namespace
  APEX linker path under `/tmp/a90-v231-*/root/apex/com.android.runtime/bin/linker64`.
- `capture.exec.auxv.count=19` and `capture.crash.auxv.count=19`.
- crash PC is consistently inside linker64 at file offset `0x1002f4`:

| linker | target profile | fault addr | PC file offset |
| --- | --- | --- | --- |
| `system-linker` | `system-toybox` | `0xa1` | `0x1002f4` |
| `system-linker` | `apex-linker64-self` | `0xa1` | `0x1002f4` |
| `system-linker` | `cnss-daemon` | `0xa1` | `0x1002f4` |
| `apex-linker` | `system-toybox` | `0xa1` | `0x1002f4` |
| `apex-linker` | `apex-linker64-self` | `0xa1` | `0x1002f4` |
| `apex-linker` | `cnss-daemon` | `0xa1` | `0x1002f4` |

Representative crash lines:

```text
capture.crash.siginfo.signo=11
capture.crash.siginfo.code=1
capture.crash.siginfo.addr=0xa1
capture.crash.regset.nt_prstatus.bytes=272
capture.crash.regset.word32=0x...512f4
```

## Postflight

- `/cache/bin/a90_real_ld.config.txt`: removed, `stat` returned `ENOENT`.
- `/cache/bin/a90_real_apex.libraries.config.txt`: removed, `stat` returned `ENOENT`.
- final `selftest verbose`: `pass=11 warn=1 fail=0`.
- wrapper postflight `selftest` and `/proc/mounts`: PASS.

## Interpretation

v236 provides enough evidence to stop broad path/linkerconfig guesses.  The crash
is consistent across linker path and target profile, faults at address `0xa1`,
and reaches the same linker64 file offset `0x1002f4`.  Next work should compare
that offset against a symbolized or disassembled linker binary and compare the
Android process context that may feed the crashing linker code path.

Recommended v237 direction:

1. export or inspect the matching linker64 ELF and compute symbol/section context
   for file offset `0x1002f4`;
2. compare native private-namespace auxv/exe/cwd/mountinfo against stock Android
   linker invocation context if obtainable;
3. keep Wi-Fi daemon start blocked until this linker crash cause is understood or
   a safer execution path is found.
