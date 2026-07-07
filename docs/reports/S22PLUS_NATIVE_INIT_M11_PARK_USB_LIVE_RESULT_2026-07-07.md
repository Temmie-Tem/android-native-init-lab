# S22+ Native-Init M11 Park USB Live Result - 2026-07-07

## Verdict

M11 did not reach the USB-ACM control-channel milestone.

The boot-only M11 candidate AP flashed successfully, but the candidate exposed
no ACM transport and no ADB transport during the observation window. The
operator observed a boot loop and manually entered Samsung download mode. The
helper then detected the Odin endpoint and flashed the pinned Magisk boot-only
rollback AP successfully. Android returned with Magisk root and the expected
boot hash.

This is a live NO-GO for M11. Do not repeat M11 unchanged.

## Candidate

```text
AP.tar.md5             8b4a4fa6db3bc0b2bf5e4fd1fccf4b671fd2fbd7fbbcc08542c3be816a3f5d43
boot.img               32f2667c31f05d967529031630e5b004cf5238120ffc6ec7089dcc40a3352a3f
M11 /init              234ded5b6172a3470825a1c616e6537c3de4b2274d8c26525386f8e85d5e8d7e
M11 module list        c254be05c91199c4f69380f0488de13c7b2cde987594bc1c5d0a6657a0e8eb58
source                 ff92af817cd4564b6fd811484540e8a217ff19bbe445839981ce7818498561f6
base Magisk boot       2e541703951dc725bad35850faf7028c2d910dd5f21166449b63f1248c29967e
```

The AP contained exactly one member:

```text
boot.img.lz4
```

## Live Timeline

Private run log:

```text
workspace/private/runs/s22plus_m11_park_usb_live_gate_20260707T133607Z/s22plus_m11_park_usb_live_gate.txt
```

Key events:

```text
13:36:07Z  live helper start
13:36:18Z  Android/Magisk preflight passed; current boot hash matched baseline
13:36:18Z  adb reboot download requested for the host-controlled Odin flash
13:36:29Z  Odin/download device appeared for candidate flash
13:36:29Z  M11 candidate AP flash started
13:36:31Z  candidate Odin flash rc=0
13:36:31Z  M11 ACM/ADB/Odin observation started
13:37:14Z  Odin/download endpoint returned after operator manual download-mode entry
13:37:14Z  Magisk boot-only rollback AP flash started
13:37:15Z  rollback Odin flash rc=0
13:38:00Z  Android returned with boot_completed=1
```

Observed during the M11 window:

```text
M11 ACM devices       none
ADB transports       none
Odin transport       absent until manual download-mode entry
host new net links   none recorded
```

## Rollback

Rollback path:

```text
manual download mode entered after boot loop
Magisk boot-only AP flashed
rollback Odin rc=0
Android returned
boot_completed=1
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

The absence of retained markers means this live run does not prove whether M11
reached its `/dev/kmsg` marker. It proves only the external behavior: candidate
flash succeeded, no ACM appeared, Android did not return, the operator observed
boot looping, and rollback succeeded.

## Interpretation

M11 was intended to test a leaner, park-based USB substrate after M7. It removed
the explicit reset/debug/glink/EUD/audio blocklist entries, kept the Max77705
i2c PD chain, forced USB role device, and avoided any reboot beacon.

The result follows the M11 branch:

```text
still loops, no ACM
```

Compared to M5 v0.4, M11 commonality is limited:

```text
M5 module count       26
M11 module count      48
common modules        24
M11-only modules      24
M5-only modules       usb_notifier_qcom.ko, qc_usb_audio.ko
```

The M11-only module group is:

```text
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
qti-fixed-regulator.ko
phy-generic.ko
proxy-consumer.ko
qcom_rpmh.ko
qcom-scm.ko
sec_class.ko
i2c-gpio.ko
smem.ko
socinfo.ko
msm-geni-se.ko
gpi.ko
phy-msm-snps-hs.ko
i2c-msm-geni.ko
```

Because retained markers are absent, do not over-interpret this as a specific
module fault. The strongest current conclusion is narrower: M11 did not restore
the M5 park/no-transport floor, so the next live candidate must first recover a
non-looping floor before adding more USB substrate.

## Next

Next bounded unit should be host-only M12:

1. Keep the M11 freestanding PID1, configfs, role-force, and park loop shape.
2. Replace the 48-module M11 subset with an M5-floor subset loaded from the
   stock vendor_boot `/lib/modules`, not with injected module binaries.
3. Include the 24 M5/M11 common modules first; decide separately whether to add
   the two M5-only modules after the floor behavior is known.
4. Live-gate M12 only after a fresh SHA-pinned `AGENTS.md` exception and helper
   preflight.

Expected M12 decision tree:

```text
M12 parks/no ACM:
  M11-only substrate caused the loop; add M11-only modules back in small groups.

M12 loops:
  the difference is not only the M11-only substrate; inspect vendor_boot module
  source path, M11 loader/runtime order, configfs timing, and retained logging.

M12 parks + ACM:
  USB control channel is reached; move to ACM command handling and recovery.
```

Keep the same constraints: boot-only AP, no forbidden partitions, no raw host
`dd`, no fastboot, attended live ack, and pinned Magisk boot-only rollback.
