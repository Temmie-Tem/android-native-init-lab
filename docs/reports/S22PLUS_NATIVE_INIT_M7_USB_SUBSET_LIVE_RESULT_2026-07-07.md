# S22+ Native-Init M7 USB-Subset Live Result - 2026-07-07

## Verdict

M7 did not achieve the USB-ACM control-channel milestone.

Safety result passed: the exact SHA-pinned M7 boot-only AP flashed, the
operator observed a boot loop and manually entered Samsung download mode, the
helper detected exactly one Odin endpoint, the pinned Magisk boot-only rollback
AP flashed successfully, and Android returned to the rooted Magisk baseline.

Native-init result failed: no M7 ACM gadget, ADB transport, or M7 marker was
observed before rollback.

## Candidate

```text
AP.tar.md5             be0e1e34ec9452a14b7cfac66cc7ac57a0b29e92343945c35c1f836282563c4d
boot.img               7e58de4cfbf50eabef73f62ed1c30a1b4bc83089307cca083c304b9a9b360206
M7 /init               530ff86247270c5a48db22f009e5f659d4403643a90486842938200c8192514d
M7 subset list         b630d318d1a95f596cbd97699d04d2bf60a53e634f35c00bbabc8000fb3315b7
base boot              2e541703951dc725bad35850faf7028c2d910dd5f21166449b63f1248c29967e
kernel                 bceca73edbfca3499148e16741c939779157925949ef6bc8a8e31d6b68fc2cff
runtime                freestanding-raw-syscall
```

The AP contained exactly one Odin member:

```text
boot.img.lz4
```

## Preflight

The no-flash dry-run passed immediately before live flashing:

```text
dry-run ok: M7 candidate, rollback APs, AGENTS exception, Android stability, and boot hash verified
```

The helper verified the exact M7 subset gates:

```text
dependency closure       54
final subset             53
subset bytes             802
watchdogs in subset        0
blocked closure entry     qc_usb_audio.ko
module binary injection   false
```

## Live Timeline

Private run log:

```text
workspace/private/runs/s22plus_m7_usb_subset_live_gate_20260707T101542Z/s22plus_m7_usb_subset_live_gate.txt
```

Key events:

```text
10:15:42Z  live helper start
10:15:53Z  rooted Android dry-run snapshot complete
10:15:53Z  adb reboot download requested
10:16:04Z  Odin/download device appeared for candidate flash
10:16:04Z  M7 candidate AP flash started
10:16:06Z  candidate Odin flash rc=0
10:16:06Z  M7 ACM/Odin/ADB observation started
10:16:45Z  one Odin/download endpoint observed after operator manual download-mode entry
10:16:45Z  Magisk boot-only rollback started
10:16:46Z  rollback Odin rc=0
10:17:31Z  Android returned with boot_completed=1 and Magisk root
```

Observed during the M7 candidate window:

```text
M7 ACM devices       none
ADB transports       none
M7 marker            not retained
```

The helper saw Odin only after the operator manually entered download mode, not
as a proven candidate self-return path.

## Post-Rollback Verification

Independent host check after helper completion:

```text
sys.boot_completed       1
init.svc.bootanim        stopped
model/device             SM-S906N / g0q
bootloader               S906NKSS7FYG8
verifiedbootstate        orange
Magisk root              available
boot hash                2e541703951dc725bad35850faf7028c2d910dd5f21166449b63f1248c29967e
```

Retained evidence:

```text
pstore files             none
/proc/last_kmsg bytes    2097136
M7 marker in retained    no
```

## Interpretation

M7 falsifies the narrow "M6 bootloop was caused only by full-recovery watchdog
modules" hypothesis. M7 excluded the explicit watchdog modules and still
boot-looped.

The result does not prove whether M7 reached the module loop, because retained
markers are still absent. It does prove that simply shrinking M6 from 446
modules to the 53-module USB dependency subset is not enough.

The useful differential is now M5 vs M7:

```text
M5 v0.4: 26 injected USB-first modules, no ACM, no operator-observed bootloop
M7:      53 stock-vendor USB dependency modules, no ACM, bootloop
```

M7 adds 36 modules not present in M5, mostly early substrate/debug/GLINK/PMIC
support:

```text
abc.ko, clk-rpmh.ko, gcc-waipio.ko, icc-rpmh.ko, qcom_ipc_logging.ko,
rpmh-regulator.ko, clk-dummy.ko, clk-qcom.ko, cmd-db.ko, debug-regulator.ko,
gdsc-regulator.ko, icc-bcm-voter.ko, icc-debug.ko, minidump.ko, phy-generic.ko,
proxy-consumer.ko, qcom_rpmh.ko, qcom-scm.ko, sec_class.ko, sec_debug.ko,
smem.ko, socinfo.ko, msm-geni-se.ko, gpi.ko, pdr_interface.ko, qmi_helpers.ko,
pmic_glink.ko, altmode-glink.ko, eud.ko, phy-msm-snps-hs.ko, ucsi_glink.ko,
i2c-msm-geni.ko, rproc_qcom_common.ko, qcom_glink.ko, qcom_glink_smem.ko,
qcom_smd.ko
```

These are the next root-cause surface. Do not repeat M7 as-is.

## Next

Do a host-only M8 design/build before any more live flash. The strongest next
candidate is a module-bisect/timed-download probe rather than another USB-ACM
milestone attempt:

1. Preserve the M7 freestanding runtime and stock vendor_boot module source.
2. Load a deliberately smaller M5-to-M7 delta batch.
3. After the bounded module batch, request download mode automatically before
   any long park.
4. Treat the result as a behavioral discriminator:
   - self-download returns: PID1 survived that module batch;
   - bootloop/no self-download: culprit is inside or before that batch.

Any M8 live use still needs a fresh SHA-pinned S22+ boot-only `AGENTS.md`
exception and attended rollback path.
