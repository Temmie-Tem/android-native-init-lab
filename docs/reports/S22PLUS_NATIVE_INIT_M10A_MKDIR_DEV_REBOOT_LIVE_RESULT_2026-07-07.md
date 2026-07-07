# S22+ Native-Init M10A Mkdir-Dev Reboot Live Result - 2026-07-07

## Verdict

M10A did not prove automatic self-download.

The exact SHA-pinned M10A boot-only AP flashed and the original Samsung download
endpoint disconnected. The helper later observed a Samsung download endpoint
inside its 150 second window and restored the pinned Magisk boot-only rollback
AP successfully. However, the operator corrected the causal interpretation:
the device was in bootloop-like behavior and the later download-mode endpoint
was produced by manual download-mode entry, not by the M10A candidate returning
to download mode on its own.

Safety result passed: rollback completed, Android returned to the rooted Magisk
baseline, `sys.boot_completed=1`, `init.svc.bootanim=stopped`, Magisk root was
available, and uptime increased across post-rollback samples.

Interpretation: M10A is a recovered bootloop/no-automatic-self-download result.
The first added M8A-style side effect, `mkdirat("/dev", 0755)`, is now the
current suspect boundary. Do not treat `/dev` mkdir or basic pathname VFS access
as proven survivable.

## Candidate

```text
AP.tar.md5             d71c8c82d2703892802228dd61ded561a9b4f90c678db15452014f2477170105
boot.img               c62fce5e444bad47e2b934f6e9e82bc731058a0c9494629f0eb9044ff92e8b24
M10A /init             8f954dfcd5d5887f8c1659e7e658617561627d9c7fecc518972a795ac20422b3
source                 c12b710f93b957313ad1018de40ebe2dec53883c5de6d018c9d5577b1a426cf0
base Magisk boot       2e541703951dc725bad35850faf7028c2d910dd5f21166449b63f1248c29967e
kernel                 bceca73edbfca3499148e16741c939779157925949ef6bc8a8e31d6b68fc2cff
runtime                freestanding-c-raw-syscall
```

M10A intended runtime:

```text
direct PID1
freestanding C
first side effect = mkdirat("/dev", 0755)
then reboot("download")
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
workspace/private/runs/s22plus_m10a_mkdir_dev_reboot_live_gate_20260707T115408Z/s22plus_m10a_mkdir_dev_reboot_live_gate.txt
```

Key helper events:

```text
11:54:08Z  live helper start
11:54:31Z  Samsung download endpoint appeared for candidate flash
candidate_odin_rc=0
11:54:34Z  original Odin endpoint absent; disconnect proof acquired
11:54:34Z  self-download observation window started
11:55:35Z  Samsung download endpoint observed by helper
m10a_self_download_seen=1
magisk_rollback_odin_rc=0
11:56:11Z  Android returned with boot_completed=1 and Magisk root
```

Operator correction:

```text
The device was bootlooping.
The operator manually entered download mode.
Therefore the 11:55:35Z endpoint is not an automatic M10A self-download proof.
```

## Post-Rollback Verification

Helper post-rollback result:

```text
sys.boot_completed       1
Magisk root              available
pstore files             none
/proc/last_kmsg bytes    2097136
M10A marker in retained  no
```

The retained-marker result is expected: M10A intentionally has no marker and no
kmsg write.

Independent host check after the operator reported bootloop-like behavior:

```text
ADB state                Android device attached
sys.boot_completed       1
init.svc.bootanim        stopped
boot reason              reboot,download
Magisk root              available
uptime samples           increasing over four samples
visible focus            Android lock/notification/MTP surface, not boot animation
```

## Interpretation

Updated live boundary:

```text
M4T3 raw assembly first-action reboot("download")          in-window PASS, about 44 s
M9A freestanding C first-action reboot("download")         delayed download, about 106 s
M10A freestanding C mkdirat("/dev") then reboot            BOOTLOOP, manual-download rollback
M8A freestanding C minimal-fs setup before reboot          NO SELF-DOWNLOAD in prior run
```

This moves the suspect boundary to the first VFS/pathname side effect, not
downstream of it.

Do not proceed to a larger mkdir batch. The next unit should be host-only and
should split M10A more narrowly, for example:

```text
read-only pathname probe:
  newfstatat(AT_FDCWD, "/dev", ...), then reboot("download")

branch:
  reaches download without manual entry:
    pathname lookup/VFS read is survivable; mkdir mutation or directory create path is suspect.
  bootloops:
    pathname VFS access itself is suspect before Samsung reboot.
```

Any live use still requires a fresh SHA-pinned `AGENTS.md` exception, guarded
helper, offline check, dry-run, and attended rollback path.

## Stop Rule

M10A is recovered. Do not repeat M10A unchanged and do not extend it to M10B
until the manual-download ambiguity and first-VFS boundary are split by a
narrower host-only candidate.
