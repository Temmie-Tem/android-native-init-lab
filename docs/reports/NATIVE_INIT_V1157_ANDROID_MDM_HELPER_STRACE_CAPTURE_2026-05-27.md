# Native Init V1157 Android `mdm_helper` Strace Capture Report

Date: `2026-05-27`

## Result

- Decision: `v1149-android-mdm-helper-strace-captured-rollback-complete`
- Pass: `true`
- Live out dir: `tmp/wifi/v1157-vendor-original-live-20260527-184309`
- Trace file: `tmp/wifi/v1157-vendor-original-live-20260527-184309/android-trace/extracted/a90-wifi/mdm_helper.strace.txt`
- Native rollback image: `stage3/boot_linux_v724.img`
- Native rollback verified: `A90 Linux init 0.9.68 (v724)`, `selftest: pass=11 warn=1 fail=0`

## What Changed

V1153 through V1156 narrowed the wrapper failures step by step:

| version | finding | fix |
| --- | --- | --- |
| V1153 | ELF wrapper still exited `127`; module context was captured | added broader context proof |
| V1154 | `strace` became executable, but module policy install was skipped by `customize.sh exit 0` | removed installer early exit |
| V1155 | wrapper started; `/data/adb/modules/.../strace` failed with `errno=13` | moved strace to a vendor overlay path |
| V1156 | `/vendor/bin/a90_strace` executed, but original `mdm_helper` mirror/fallback was inaccessible | copied original to `mdm_helper.real` at install time |
| V1157 | wrapper selected `/vendor/bin/mdm_helper.real` and captured strace | pass |

The final V1157 module overlays:

```text
/vendor/bin/mdm_helper        -> static wrapper, vendor_mdm_helper_exec
/vendor/bin/mdm_helper.real   -> install-time copy of stock original, vendor_file
/vendor/bin/a90_strace        -> static strace, vendor_file
```

## Live Evidence

Wrapper log:

```text
a90_mdm_helper_strace_wrapper v1157
wrapper_start=2026-05-27T09:44:59+0000
pid=1190 uid=0 gid=1000
argv[0]=/vendor/bin/mdm_helper
selinux_context=u:r:vendor_mdm_helper:s0
original_candidate_selected=/vendor/bin/mdm_helper.real
exec_strace=/vendor/bin/a90_strace original=/vendor/bin/mdm_helper.real out=/data/local/tmp/a90-wifi/mdm_helper.strace.txt filter=trace=openat,ioctl,read,write,execve
```

Strace key sequence:

```text
execve("/vendor/bin/mdm_helper.real", ["/vendor/bin/mdm_helper.real"], ...) = 0
read("SDX50M") from /sys/bus/esoc/devices/esoc0/esoc_name
read("PCIe") from /sys/bus/esoc/devices/esoc0/esoc_link
read("0305_01.01.00") from /sys/bus/esoc/devices/esoc0/esoc_link_info
read("esoc0") from /sys/bus/msm_subsys/devices/subsys9/name
openat(AT_FDCWD, "/dev/esoc-0", O_RDONLY|O_NONBLOCK) = 5
ioctl(5, _IOC(_IOC_NONE, 0xcc, 0x7, 0), 0x800) = 0
ioctl(5, _IOC(_IOC_READ, 0xcc, 0x2, 0x4), 0x7ad3fbebc4) = 4
openat(AT_FDCWD, "/sys/power/wake_lock", O_WRONLY|O_APPEND) = 6
write(6, "mdm_helper\0", 11) = 11
```

Android dmesg later proves the lower Wi-Fi path completed in the same boot:

```text
icnss: WLAN FW is ready: 0xd87
wma_wait_for_ready_event: FW ready event received
dev : wlan0 : event : 16
dev : swlan0 : event : 16
dev : p2p0 : event : 16
dev : wifi-aware0 : event : 16
```

Trace classification from the live manifest:

```text
wrapper_log_present=True
strace_log_present=True
wrapper_started=True
strace_executed=True
original_selected=True
strace_has_esoc0=True
strace_has_ioctl=True
strace_has_execve=True
strace_has_mhi_pipe=False
strace_size=54758
```

## Interpretation

V1157 proves the Android-positive `mdm_helper` path starts by reading the
SDX50M/PCIe/MHI identity, confirming `esoc_link_info=0305_01.01.00` and
`subsys9=esoc0`, then opens `/dev/esoc-0`, registers the command engine
(`0xcc07`, rc 0), waits for an image request (`0xcc02`, rc 4), and takes the
`mdm_helper` wakelock.

That matches V1143/V1144 native post-PM observations but also sharpens the
missing piece: native can place `mdm_helper` in the same wait state, while
Android later receives enough lower eSoC/firmware progress for FW ready and
`wlan0`. The next capture should not stop at boot-complete/capture-settle; it
should keep the wrapper installed until `wlan0` or FW-ready appears, then pull
the longer trace so the post-wakelock image-transfer and possible `ks` sequence
are visible.

The original V1157 generated manifest still reported `strace_has_ks=True` due a
broad substring match in linker namespace text. The handoff classifier has been
patched after this run to require an actual `ks` exec/open or `ks` PID. In this
evidence, `pids.txt` has no `ks` PID and no `execve(".../ks")` appears in the
captured strace.

## Validation

Executed:

```bash
python3 -m py_compile \
  scripts/revalidation/native_wifi_android_mdm_helper_strace_module_v1147.py \
  scripts/revalidation/android_mdm_helper_strace_handoff_v1149.py

python3 scripts/revalidation/native_wifi_android_mdm_helper_strace_module_v1147.py \
  --strace-binary external_tools/userland/bin/strace-aarch64-static-7.0 \
  --wrapper-binary external_tools/userland/bin/a90_mdm_helper_strace_wrapper-aarch64-static

python3 scripts/revalidation/android_mdm_helper_strace_handoff_v1149.py \
  --out-dir tmp/wifi/v1157-vendor-original-dryrun \
  --native-image stage3/boot_linux_v724.img \
  --native-expect-version 'A90 Linux init 0.9.68 (v724)' \
  --allow-android-boot-flash \
  --assume-yes \
  --i-understand-native-rollback \
  dry-run

python3 scripts/revalidation/android_mdm_helper_strace_handoff_v1149.py \
  --out-dir tmp/wifi/v1157-vendor-original-live-20260527-184309 \
  --native-image stage3/boot_linux_v724.img \
  --native-expect-version 'A90 Linux init 0.9.68 (v724)' \
  --allow-android-boot-flash \
  --assume-yes \
  --i-understand-native-rollback \
  run
```

Post-run native checks:

```text
A90 Linux init 0.9.68 (v724)
selftest: pass=11 warn=1 fail=0
```

## Guardrails

- Magisk module only; no direct vendor partition mutation.
- Temporary Android boot handoff only, with automatic native v724 rollback.
- No native `/dev/subsys_esoc0` retry or native eSoC ioctl.
- No Wi-Fi credentials, scan/connect, DHCP/routes, or external ping.

## Next

Use V1158 to extend this same Android capture instead of changing the native
gate yet:

1. Keep the V1157 vendor-overlay wrapper/original/strace layout.
2. Replace fixed `capture_settle_sleep` as the primary discriminator with a bounded wait for FW ready, `wlan0`, `swlan0`, `p2p0`, or `wifi-aware0`.
3. Pull `mdm_helper.strace.txt` only after that marker appears, with a timeout fallback that still preserves fail-closed evidence.
4. Use the longer trace to identify the request producer and any post-wakelock `ks`/MHI image-link sequence before designing the next native gate.
