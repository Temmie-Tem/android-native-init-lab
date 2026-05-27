# Native Init V1146 Android `mdm_helper` / `ks` strace Capture Plan

Date: `2026-05-27`

## Purpose

V1145 selected a native post-PM eSoC request verifier as the next build
direction. New research changes the immediate priority: before adding another
native `/dev/subsys_esoc0` trigger path, capture Android's real
`mdm_helper`/`ks` image-link sequence with syscall-level evidence.

Target question:

```text
When Android reaches mdm3 ONLINE and WLFW/FW-ready/wlan0, what exactly do
mdm_helper and ks do around /dev/esoc-0, ESOC_WAIT_FOR_REQ, /dev/subsys_esoc0,
/dev/mhi_0305_01.01.00_pipe_10, and image paths?
```

## Current Evidence Basis

- V1143/V1144: native post-PM `mdm_helper` holds `/dev/esoc-0` and waits in
  `ESOC_WAIT_FOR_REQ`; no subsystem trigger, `ks`, MHI pipe, WLFW, or `wlan0`.
- V1145: Android-positive PM fd + `mdm_helper`/`ks`/MHI/WLFW chain exists, but
  current helper modes are split between post-PM observer and older
  `mdm_helper` before subsystem-trigger mode.
- V900/V1020: repeating older native subsystem-trigger attempts can create
  unkillable lower-kernel waits and require reboot cleanup.

## Selected V1146 Gate

V1146 should be Android read-only instrumentation planning and module
scaffolding, not a native live retry.

Scope:

- temporarily boot Android only for read-only syscall/dmesg/fd capture;
- use Magisk module timing hooks if available;
- capture `mdm_helper` and `ks` syscall sequence;
- rollback to native boot after capture;
- do not use Wi-Fi credentials;
- do not initiate native Wi-Fi scan/connect/DHCP/external ping.

## Capture Options

| option | value | risk | decision |
| --- | --- | --- | --- |
| passive `strace -p` attach from `service.sh` | low implementation risk | can miss early `openat`/`ioctl` before attach | fallback |
| Magisk overlay wrapper for `/vendor/bin/mdm_helper` | best syscall coverage | wrapper recursion/path/SELinux mistakes can break boot service | preferred after dry-run |
| dmesg/fd sampler only | safest | insufficient for image transfer details | baseline always-on |

## Preferred Wrapper Design

The wrapper must not recursively execute itself.

Required design:

```text
/vendor/bin/mdm_helper    -> Magisk overlay wrapper
original mdm_helper       -> call through Magisk mirror or copied original path
/data/local/tmp/a90-wifi/ -> trace output directory
```

Wrapper contract:

```sh
exec /data/adb/modules/a90_mdm_trace/bin/strace \
  -f -tt -s 256 \
  -e trace=execve,fork,vfork,clone,openat,ioctl,read,write,close,poll,ppoll,select,pselect6 \
  -o /data/local/tmp/a90-wifi/mdm_helper.strace.txt \
  <original-mdm_helper_path> "$@"
```

Important constraints:

- prefer static aarch64 `strace`;
- verify wrapper can find the original binary before enabling overlay;
- avoid long work in `post-fs-data.sh` because it is blocking;
- do not modify vendor partition directly; use Magisk overlay only;
- always preserve rollback path to native boot.

## Baseline Sampler

Even if wrapper mode is not enabled yet, collect:

```sh
dmesg > /data/local/tmp/a90-wifi/boot_dmesg.txt
ps -AZef > /data/local/tmp/a90-wifi/ps_azef.txt
for p in $(pidof mdm_helper ks pm-service pm_proxy_helper cnss-daemon); do
  ls -l /proc/$p/fd > /data/local/tmp/a90-wifi/fd_$p.txt
  cat /proc/$p/cmdline > /data/local/tmp/a90-wifi/cmdline_$p.txt
  cat /proc/$p/attr/current > /data/local/tmp/a90-wifi/attr_$p.txt
done
cat /proc/interrupts > /data/local/tmp/a90-wifi/interrupts.txt
cat /sys/kernel/debug/gpio > /data/local/tmp/a90-wifi/gpio.txt 2>/dev/null || true
```

## Success Criteria

V1146 planning/scaffold success:

- module layout documented;
- original-binary path problem explicitly handled;
- capture outputs and rollback path defined;
- no credential, scan/connect, DHCP, route, external ping, or native eSoC retry.

Future V1147 live success:

- `mdm_helper.strace.txt` captures at least one `/dev/esoc-0` ioctl sequence;
- `ks` execve and args are captured, or absence is proven;
- MHI pipe open/write/read sequence is captured, or absence is proven;
- dmesg includes WLFW/FW-ready/`wlan0` positive Android chain;
- native rollback is verified after collection.

## Failure Classification

| failure | meaning | next |
| --- | --- | --- |
| wrapper does not start original | wrapper path/mirror issue | disable overlay, use passive attach |
| Android boot/service breaks | overlay too invasive | rollback, switch to passive attach + fd sampler |
| no `ks` in strace but Android Wi-Fi succeeds | `ks` is transient or different argv/path | widen exec/fd sampler |
| `ks` captured but no MHI write details | strace filter too narrow | include `sendmsg`, `recvmsg`, `mmap`, `ioctl` detail |
| no WLFW positive chain | Android capture window failed | rerun Android baseline before changing native path |

## Guardrails

- No native `/dev/subsys_esoc0` retry in V1146.
- No native eSoC ioctl.
- No Wi-Fi credentials, scan/connect, DHCP/routes, or external ping.
- No direct vendor partition mutation.
- No boot image change unless the handoff/rollback runner explicitly flashes
  known Android/native images and verifies readback.

## Next

V1147 should create the Magisk module scaffold and dry-run verifier:

1. verify static `strace` availability or vendor a bundled binary;
2. resolve the non-recursive original `mdm_helper` path;
3. generate module files without installing them;
4. add a host-side checker for expected output paths and rollback steps.
