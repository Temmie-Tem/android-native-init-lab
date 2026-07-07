# S22+ Native-Init M15 PHY-Split Live Result - 2026-07-08

## Verdict

M15 did not reach the USB-ACM control-channel milestone.

The boot-only M15 candidate AP flashed successfully, but no ACM transport and
no ADB transport appeared. The operator observed a boot loop. The live helper
detected the Odin endpoint during the observation window, flashed the pinned
Magisk boot-only rollback AP successfully, and Android returned with Magisk
root and the expected boot hash.

This is a live NO-GO for M15. Do not repeat M15 unchanged.

## Candidate

```text
AP.tar.md5       16a4d526bbc0cb09bc63d61f4743d17dddb26c34047127fe610b1f677bddced2
boot.img         adaee20d490748aa1be555cdc7aa6828b9bc553185355a60183bd722119b5812
M15 /init        5897fee141921dffc2848fb3eb3515a9b2d75d41e0c286448c4f0add06ab8558
M15 module list  f3afe268a05c47492107227b224185c65f7757c004806c4c24d23231bd19e217
source           ac57cb1ece2dcc65bf5a8cbfc3fa0a077b006c757a4615298ee00d115b1fdd13
base boot        2e541703951dc725bad35850faf7028c2d910dd5f21166449b63f1248c29967e
kernel           bceca73edbfca3499148e16741c939779157925949ef6bc8a8e31d6b68fc2cff
```

The AP contained exactly one member:

```text
boot.img.lz4
```

M15 loaded only the two PHY-side modules from the failed M14 core group:

```text
phy-msm-ssusb-qmp.ko
phy-msm-snps-eusb2.ko
```

M15 withheld the other two M14 modules:

```text
dwc3-msm.ko
usb_f_ss_acm.ko
```

## Live Timeline

Private candidate run log:

```text
workspace/private/runs/s22plus_m15_phy_split_live_gate_20260707T150428Z/s22plus_m15_phy_split_live_gate.txt
```

Key events:

```text
15:04:28Z  live helper start
15:04:39Z  Android/Magisk preflight passed; current boot hash matched baseline
15:04:39Z  adb reboot download requested for the host-controlled Odin flash
15:04:51Z  Odin/download device appeared for candidate flash
15:04:52Z  M15 candidate AP flash rc=0
15:04:53Z  M15 ACM/ADB/Odin observation started
15:05:46Z  Odin endpoint detected after operator-observed boot loop
15:05:46Z  Magisk boot-only rollback AP flash started
15:05:47Z  rollback Odin flash rc=0
15:06:22Z  Android returned with boot_completed=1
```

Observed during the M15 window:

```text
M15 ACM devices       none
ADB transports       none
Odin transport       returned during observation window
operator visual      boot loop
```

The helper completed with rc=0 because it detected the Odin endpoint and
performed rollback in the same live run.

## Rollback

Rollback path:

```text
Magisk boot-only AP flashed
rollback Odin rc=0
Android returned
boot_completed=1
bootanim=stopped
verified boot state=orange
boot_recovery=0
Magisk root available
pstore file count=0
```

Post-rollback boot hash:

```text
2e541703951dc725bad35850faf7028c2d910dd5f21166449b63f1248c29967e
```

Retained marker evidence:

```text
post_rollback_pstore_marker_found=0
post_rollback_last_kmsg_marker_found=0
post_rollback_retained_marker_found=0
```

The absence of retained markers means this live run does not prove whether the
M15 marker or per-module kmsg lines executed before reset. It proves only the
external behavior: candidate flash succeeded, no ACM appeared, Android did not
return before rollback, the operator observed boot looping, Odin became
available during the observation window, and rollback succeeded.

## Interpretation

M14 showed that the four-module core USB/ACM add-back loops:

```text
phy-msm-ssusb-qmp.ko
phy-msm-snps-eusb2.ko
dwc3-msm.ko
usb_f_ss_acm.ko
```

M15 removed `dwc3-msm.ko` and `usb_f_ss_acm.ko` but still looped:

```text
phy-msm-ssusb-qmp.ko
phy-msm-snps-eusb2.ko
```

This moves the fault boundary earlier than dwc3/ACM gadget function load. The
current live evidence says the loop is at or below the PHY-side module load or
the act of entering the runtime `finit_module` path under native-init.

Because retained markers are absent, do not claim a specific PHY module fault
yet.

## Next

Next bounded unit should be host-only M16:

1. Split M15 to one PHY module at a time, starting with
   `phy-msm-ssusb-qmp.ko` only.
2. If that loops, build the complementary `phy-msm-snps-eusb2.ko`-only
   candidate.
3. If either single-module candidate loops before retained markers, add an
   open-only/no-finit control to separate module file access and parser
   mechanics from module init side effects.

Keep the same constraints: boot-only AP, no forbidden partitions, no raw host
`dd`, no fastboot, attended live ack, and pinned Magisk boot-only rollback.
