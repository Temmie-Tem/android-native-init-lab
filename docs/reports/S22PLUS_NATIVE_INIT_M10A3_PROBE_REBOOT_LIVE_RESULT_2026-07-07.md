# S22+ Native-Init M10A3 Probe Reboot Live Result - 2026-07-07

## Verdict

M10A3 did not prove automatic download-mode return.

The exact SHA-pinned M10A3 boot-only AP flashed, the original Samsung download
endpoint disconnected, and the helper later observed Samsung download mode and
restored the pinned Magisk boot-only rollback AP. The operator confirmed the
device was bootlooping and manually entered download mode, so the later endpoint
is not an automatic M10A3 self-download proof.

Safety result passed: rollback completed, Android returned to the rooted Magisk
baseline, `sys.boot_completed=1`, `init.svc.bootanim=stopped`, Magisk root was
available, and the live boot partition SHA256 matched the known-booting Magisk
baseline.

Interpretation: M10A3 is a recovered bootloop/manual-download result. Since
M10A3 removed the M10A2 pre-reboot `getpid()` syscall and kept only a no-syscall
pre-reboot stack-probe helper, the failure is broader than prior-syscall side
effects. The Samsung download reboot path appears sensitive to any work before
the reboot helper in this early PID1 context.

## Candidate

```text
AP.tar.md5             7415538ac9cbfdf4af27f294927c3c81d2656412a7f779fce515138ec28e7e3b
boot.img               eb2d1cfc278e63cdfe009379f05139e5299b49859a2b247d4e6996be5f24959c
M10A3 /init            4c7908026430658250a0999fad2d47c7e5d99c212dc8daa3ba8fbafb0f4a8371
source                 9b5e3669a7a790a369bf8ed4beb662cb5262189e5d8f22011c731fc827955856
base Magisk boot       2e541703951dc725bad35850faf7028c2d910dd5f21166449b63f1248c29967e
kernel                 bceca73edbfca3499148e16741c939779157925949ef6bc8a8e31d6b68fc2cff
runtime                freestanding-c-raw-syscall
```

M10A3 intended runtime:

```text
direct PID1
freestanding C
first side effect = none before reboot
pre-reboot helper = stack probe, no syscall
then reboot("download")
no getpid
no pathname access
no VFS
no mkdirat
no marker
no /dev/kmsg
no mknodat
no mount
no sleep
no modules
no configfs or USB gadget
park if reboot returns
```

## Live Timeline

Private live run log:

```text
workspace/private/runs/s22plus_m10a3_probe_reboot_live_gate_20260707T125618Z/s22plus_m10a3_probe_reboot_live_gate.txt
```

Key helper events:

```text
12:56:18Z  live helper start
12:56:40Z  Samsung download endpoint appeared for candidate flash
candidate_odin_rc=0
12:56:43Z  original Odin endpoint absent; disconnect proof acquired
12:56:43Z  download observation window started
12:57:29Z  Samsung download endpoint observed by helper
m10a3_download_endpoint_seen=1
m10a3_manual_download_ambiguity=operator-confirmation-required
magisk_rollback_odin_rc=0
12:58:05Z  Android returned with boot_completed=1 and Magisk root
```

Operator correction:

```text
The device was bootlooping.
The operator manually entered download mode.
Therefore the 12:57:29Z endpoint is not an automatic M10A3 self-download proof.
```

Approximate elapsed time from original endpoint disconnect to the manually
confirmed download endpoint: 46 seconds.

## Post-Rollback Verification

Helper post-rollback result:

```text
sys.boot_completed       1
Magisk root              available
pstore files             none
/proc/last_kmsg bytes    2097136
M10A3 marker in retained no
```

The retained-marker result is expected: M10A3 intentionally has no marker and
no kmsg write.

Independent host check after helper completion:

```text
ADB state                Android device attached
sys.boot_completed       1
init.svc.bootanim        stopped
boot reason              reboot,download
Magisk root              available
boot partition SHA256    2e541703951dc725bad35850faf7028c2d910dd5f21166449b63f1248c29967e
```

## Interpretation

Updated live boundary:

```text
M4T3 raw assembly first-action reboot("download")          in-window PASS, about 44 s
M9A freestanding C first-action reboot("download")         delayed download, about 106 s
M10A3 freestanding C no-syscall helper then reboot         BOOTLOOP, manual-download rollback
M10A2 freestanding C getpid() then reboot                  BOOTLOOP, manual-download rollback
M10A1 freestanding C newfstatat("/dev") then reboot        BOOTLOOP, manual-download rollback
M10A freestanding C mkdirat("/dev") then reboot            BOOTLOOP, manual-download rollback
M8A freestanding C minimal-fs setup before reboot          NO SELF-DOWNLOAD in prior run
```

M10A3 narrows the failure below prior-syscall behavior. The remaining ambiguity
is now:

```text
path A: any extra helper call/return before reboot changes early PID1 state enough to lose self-download.
path B: any stack work or extra instructions before reboot, even inline, are enough to lose self-download.
```

Do not proceed to filesystem, module, configfs, or USB work. The next unit
should stay below filesystem work and split the M9A-to-M10A3 delta with one
changed factor:

```text
M10A4 candidate idea:
  inline stack-probe in _start, no pre-reboot helper call, then reboot helper.

M10A4 reaches download without manual entry:
  the function call/return boundary is the sensitive factor.

M10A4 bootloops / requires manual download:
  any pre-reboot stack work/instruction delay before the reboot helper is suspect.
```

## Stop Rule

M10A3 is recovered. Do not repeat it unchanged and do not extend to larger
native-init bring-up until the M9A-to-M10A3 pre-reboot helper/stack boundary is
split.
