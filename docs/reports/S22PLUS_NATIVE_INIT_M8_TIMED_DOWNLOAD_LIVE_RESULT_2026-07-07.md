# S22+ Native-Init M8 Timed-Download Live Result - 2026-07-07

## Verdict

M8 did not survive to its timed Samsung download-mode request.

Safety result passed after manual recovery: the exact SHA-pinned M8 boot-only
AP flashed, the original Odin endpoint disconnected, no self-download appeared
within the bounded wait, the operator manually returned the device to Samsung
download mode, the pinned Magisk boot-only rollback AP flashed successfully,
and Android returned to the rooted Magisk baseline.

Native-init result is a useful negative discriminator: M8 excluded ACM,
configfs, UDC binding, USB role forcing, and host serial I/O, so the failure is
upstream of the M7 USB gadget path.

## Candidate

```text
AP.tar.md5             59433518e7bea2d16f5efb62ee226c190f6a3af8673336310a2ef0fff7bee36b
boot.img               3c10c9232b8579b552d791d24e65b7b4dd8ec3625941766894a08725a7abae52
M8 /init               5c8591023d0ad801155535e9b535993fb3122c4d3e4c86139d36a819ee72c3b2
M8 delta batch         6831a24ac12ddf0bfdb9b5695dcd3aada7f200aa4a998864874c207efa31bc9d
base boot              2e541703951dc725bad35850faf7028c2d910dd5f21166449b63f1248c29967e
kernel                 bceca73edbfca3499148e16741c939779157925949ef6bc8a8e31d6b68fc2cff
runtime                freestanding-raw-syscall
```

The AP contained exactly one Odin member:

```text
boot.img.lz4
```

M8 batch:

```text
abc.ko
clk-rpmh.ko
gcc-waipio.ko
icc-rpmh.ko
qcom_ipc_logging.ko
rpmh-regulator.ko
clk-dummy.ko
clk-qcom.ko
cmd-db.ko
debug-regulator.ko
gdsc-regulator.ko
icc-bcm-voter.ko
icc-debug.ko
minidump.ko
phy-generic.ko
proxy-consumer.ko
qcom_rpmh.ko
qcom-scm.ko
```

## Preflight

The no-flash dry-run passed immediately before live flashing:

```text
agents_exception_missing=[]
android_stability_result=ok samples=4
current_boot_hash=2e541703951dc725bad35850faf7028c2d910dd5f21166449b63f1248c29967e
```

Manifest gates verified by the helper:

```text
boot_only=true
live_flash_authorized=false
module_binary_injection=false
module_files_injected_into_boot_ramdisk=0
module_list_files_injected_into_boot_ramdisk=1
batch_count=18
batch_bytes=255
m7_only_count=36
tar_members=["boot.img.lz4"]
nochange_repack_boot == base_boot
```

## Live Timeline

Private live run log:

```text
workspace/private/runs/s22plus_m8_timed_download_live_gate_20260707T103906Z/s22plus_m8_timed_download_live_gate.txt
```

Key events:

```text
10:39:06Z  live helper start
10:39:17Z  rooted Android dry-run snapshot complete
10:39:17Z  adb reboot download requested
10:39:29Z  Odin/download device appeared for candidate flash
10:39:29Z  M8 candidate AP flash started
candidate_odin_rc=0
10:39:31Z  original Odin endpoint still visible
10:39:32Z  original Odin endpoint absent; disconnect proof acquired
10:40:31Z  self-download observation ended, m8_self_download_seen=0
```

Post-failure host checks before manual recovery:

```text
adb devices -l      no devices
odin4 -l            no devices
lsusb Samsung scan  no matching Samsung/Odin device
```

Private rollback run log:

```text
workspace/private/runs/s22plus_m8_timed_download_live_gate_20260707T104739Z/s22plus_m8_timed_download_live_gate.txt
```

Rollback events:

```text
10:47:39Z  rollback helper start from manual Samsung download mode
magisk_rollback_odin_rc=0
10:48:25Z  Android returned with boot_completed=1 and Magisk root
```

The operator observed bootloop behavior during the failed candidate/recovery
window. Host-side rollback verification ultimately returned clean.

## Post-Rollback Verification

Independent host check after helper completion:

```text
sample count            4
sys.boot_completed      1
init.svc.bootanim       stopped
model/device            SM-S906N / g0q
Magisk root             available
boot hash               2e541703951dc725bad35850faf7028c2d910dd5f21166449b63f1248c29967e
```

Retained evidence:

```text
pstore files             none
/proc/last_kmsg bytes    2097136
M8 marker in retained    no
```

## Interpretation

M8 narrowed the failure upstream of M7's USB gadget work. It never touched:

```text
ACM
configfs
UDC binding
USB role force
ttyGS0
host serial command handling
```

Therefore repeating M7 or adding more USB role/configfs logic is the wrong next
move. The failure is in one of these earlier surfaces:

```text
minimal native PID1 setup
boot-ramdisk module-list parsing
opening /lib/modules from the stock vendor_boot runtime
one of the first 18 M7-only modules
```

The strongest next split is host-only:

```text
M8A: no-module timed-download after minimal fs
M8B: first 9 M8 modules
M8C: second 9 M8 modules only if M8B survives
```

Any live use of those candidates must again use a fresh SHA-pinned boot-only
exception and a guarded dry-run/live helper. No new device flash should happen
until the next host-only candidate and live gate are built and reviewed.
