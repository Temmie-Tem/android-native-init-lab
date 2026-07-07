# S22+ Native-Init M13 No-Module Configfs Live Result - 2026-07-07

## Verdict

M13 did not reach the USB-ACM control-channel milestone.

The boot-only M13 candidate AP flashed successfully, but the candidate exposed
no ACM transport, no ADB transport, and no Odin/download transport during the
120 second observation window. The live helper therefore stopped with rc=4 and
required download-mode rollback. The operator visually confirmed this was not
a boot loop. A later manually entered Odin endpoint was detected, the rollback-
only helper flashed the pinned Magisk boot-only rollback AP successfully, and
Android returned with Magisk root and the expected boot hash.

This is a partial M13 success: it recovered a non-boot-looping no-module floor,
but did not reach ACM. Do not repeat M13 unchanged.

## Candidate

```text
AP.tar.md5             5e959f0dd7c55d8e6a9363cde0c0fcc72876639bdc46ccdc826186cfc43134fa
boot.img               21808217d6cf698217e25cf35caf3a271a7f55451cad85ba576d54a40010441b
M13 /init              6b2d229217d83c7f36032c37291bebbebe7c8c5782d006fedcc538649d99f5d3
source                 4e3a88336c6a6e0b1ed6e25f572ed0ec26c2e8d177942598a6e32aa1b2a762e8
base Magisk boot       2e541703951dc725bad35850faf7028c2d910dd5f21166449b63f1248c29967e
```

The AP contained exactly one member:

```text
boot.img.lz4
```

## Live Timeline

Private candidate run log:

```text
workspace/private/runs/s22plus_m13_nomodule_configfs_live_gate_20260707T142110Z/s22plus_m13_nomodule_configfs_live_gate.txt
```

Private rollback run log:

```text
workspace/private/runs/s22plus_m13_nomodule_configfs_live_gate_20260707T142517Z/s22plus_m13_nomodule_configfs_live_gate.txt
```

Key events:

```text
14:21:10Z  live helper start
14:21:21Z  Android/Magisk preflight passed; current boot hash matched baseline
14:21:21Z  adb reboot download requested for the host-controlled Odin flash
14:21:32Z  Odin/download device appeared for candidate flash
14:21:32Z  M13 candidate AP flash started
14:21:33Z  candidate Odin flash rc=0
14:21:34Z  M13 ACM/ADB/Odin observation started
14:23:33Z  observation ended with no ACM, no ADB, and no Odin endpoint
14:25:17Z  rollback-only helper started after Odin endpoint was detected
14:25:17Z  Magisk boot-only rollback AP flash started
14:25:18Z  rollback Odin flash rc=0
14:26:03Z  Android returned with boot_completed=1
```

Observed during the M13 window:

```text
M13 ACM devices       none
ADB transports       none
Odin transport       absent during the 120 second observation window
operator visual      no boot loop
```

The live helper exited with rc=4 and requested download-mode rollback because
M13 deliberately has no reboot beacon and no ACM command path.

## Rollback

Rollback path:

```text
manual download mode entered after the no-transport/non-looping result
Magisk boot-only AP flashed
rollback Odin rc=0
Android returned
boot_completed=1
bootanim=stopped
Magisk root available
pstore_files=[]
```

Post-rollback boot hash:

```text
2e541703951dc725bad35850faf7028c2d910dd5f21166449b63f1248c29967e
```

Independent post-run verification also confirmed:

```text
boot_completed=1
bootanim=stopped
build=S906NKSS7FYG8
current boot hash=2e541703951dc725bad35850faf7028c2d910dd5f21166449b63f1248c29967e
/sys/fs/pstore empty
```

Retained marker evidence:

```text
post_rollback_pstore_marker_found=0
post_rollback_last_kmsg_marker_found=0
post_rollback_retained_marker_found=0
```

The absence of retained markers means this live run does not prove whether M13
reached its `/dev/kmsg` marker. It proves only the external behavior: candidate
flash succeeded, no ACM appeared, Android did not return during the observation
window, no Odin endpoint appeared during that window, the operator observed no
boot loop, and rollback succeeded after download mode was available.

## Interpretation

M13 was intended to distinguish whether M12's boot failure was caused by
runtime module insertion. It kept the M12 freestanding PID1, minimal mounts,
configfs `ss_acm.0` attempt, USB role-force, `a600000.dwc3`-only bind policy,
and no-reboot park loop, but removed all module insertion and injected no
boot-ramdisk module list.

The result follows the M13 parks/no-transport branch:

```text
no boot loop, no ACM, no ADB, no Odin during observation
```

This recovers the non-looping floor below M12. It strongly points at the removed
module work as the source of the M12 boot-loop behavior, but it does not prove a
specific module fault. M13 still performs minimal mounts, configfs setup,
role-force writes, UDC enumeration/bind attempts, ttyGS0 probing, and kmsg
logging before parking, and none of that produced ACM without module insertion.

Because retained markers are absent, do not over-interpret the outcome as proof
that the M13 `/init` reached each internal phase. The strongest current
conclusion is: M13 produced a non-looping, no-transport floor; ACM still needs
some module or lower-level USB substrate to be reintroduced safely.

## Next

Next bounded unit should be host-only M14:

1. Start from the stable M13 no-module floor.
2. Reintroduce module work in a much smaller, bounded group than M12, preserving
   the no-reboot park model.
3. Keep configfs/role-force unchanged so the next result isolates the small
   module add-back.
4. Add a live gate only after a fresh SHA-pinned `AGENTS.md` exception and
   helper preflight.

If the first small module add-back loops, bisect inside that group. If it stays
non-looping but no ACM appears, add the next dependency group instead of
changing configfs at the same time.
