# Native Init V1526 Android Initial RC1 Trigger Capture Design

## Summary

- Cycle: `V1526`
- Type: host-only capture design
- Decision: `v1526-android-initial-rc1-trigger-capture-design-ready`
- Result: PASS
- Reason: existing evidence proves first-L0 trigger attribution is missing, and V1521 handoff can be extended with raw kmsg plus high-cadence IRQ/GPIO capture

## Inputs

| input | path |
| --- | --- |
| v1525 | tmp/wifi/v1525-mhi-pm-resume-position-classifier/manifest.json |
| v852_dmesg | tmp/wifi/v852-android-ext-mdm-provider-surface-handoff/v852-android-ext-mdm-provider-surface-run/android/commands/dmesg-focus.txt |
| v1521_samples | tmp/wifi/v1521-android-rc1-magisk-postfs-handoff/android-postfs-evidence/a90-v1521-rc1-postfs-sampler/samples.log |
| v1517_native_dmesg | tmp/wifi/v1517-wifi-critical-source-pre-l0-handoff/test-v1393-dmesg.stdout.txt |
| v1521_handoff_script | scripts/revalidation/android_rc1_magisk_postfs_sampler_handoff_v1521.py |

## Checks

| check | status | detail |
| --- | --- | --- |
| v1525-fixed-point | pass | V1525 closes MHI PM-resume as the first-L0 trigger |
| android-v852-initial-l0-reference | pass | V852 has Android esoc0 -> RC1 assert -> L0 timing |
| android-v852-not-test11 | pass | V852 first L0 has no pci-msm TEST/debugfs marker |
| native-v1517-test11-fail-reference | pass | V1517 has native explicit TEST:11 fail before L0 |
| v1521-postfs-handoff-reusable | pass | V1521 already provides rollbackable temporary Magisk post-fs-data handoff mechanics |
| v1521-irq-samples-insufficient | pass | V1521 reached Android-good lower markers but sampled IRQ totals stayed zero, so V1527 needs raw kmsg plus higher-cadence IRQ samples |

## Timing Fixed Point

| field | value |
| --- | --- |
| Android first esoc0 | 8.54144 |
| Android first RC1 assert | 8.796369 |
| Android first L0 | 8.820231 |
| Android esoc0 -> assert ms | 254.929 |
| Android assert -> L0 ms | 23.862 |
| Native V1517 link failed | 9.341767 |
| V1521 GPIO104 IRQ range | {'sample_count': 90, 'min': 0, 'max': 0, 'last': 0, 'all_zero': True} |
| V1521 GPIO142 IRQ range | {'sample_count': 90, 'min': 0, 'max': 0, 'last': 0, 'all_zero': True} |

## V1527 Capture Contract

| contract | value |
| --- | --- |
| mechanism | temporary Magisk post-fs-data module, rollbackable Android handoff copied from V1521 |
| remote evidence dir | /data/local/tmp/a90-v1527-rc1-trigger-sampler |
| required files | kmsg-stream.txt, irq-gpio-samples.log, dmesg-filtered.txt, done |
| must start before | Android first RC1 assert (~8.796s in V852); post-fs-data starts early enough in V1521 at uptime 5.72s |
| sample window | 320 samples at 25ms target cadence, covering about 8s with usleep available |
| fallback | V1528 tracefs-only Android read-only/dynamic event design; do not mutate native RC1 again first |

## Classification Labels

| label | meaning |
| --- | --- |
| raw-kmsg-caller-found | raw kmsg includes current task/comm for first msm_pcie_enable lines |
| endpoint-wake-before-l0 | GPIO104 IRQ count increases before first L0 |
| mdm-status-before-l0 | GPIO142 IRQ count increases before or during first L0 |
| kernel-caller-still-opaque-tracefs-needed | raw kmsg and IRQ samples still do not identify the first-L0 trigger |

## Module Script Preview

```sh
#!/system/bin/sh
OUT=/data/local/tmp/a90-v1527-rc1-trigger-sampler
mkdir -p "$OUT"
chmod 755 "$OUT"

# Background raw kernel-log capture. Prefer non-destructive /dev/kmsg over
# /proc/kmsg, and fall back to dmesg snapshots if neither stream works.
(
  echo "A90_V1527_KMSG_BEGIN uptime=$(cat /proc/uptime 2>/dev/null | awk '{print $1}')"
  if [ -r /dev/kmsg ]; then
    cat /dev/kmsg 2>/dev/null
  elif command -v dmesg >/dev/null 2>&1; then
    dmesg -w 2>/dev/null
  else
    echo "kmsg_stream_unavailable=1"
  fi
) > "$OUT/kmsg-stream.txt" 2>&1 &
KMSG_PID=$!

# High-cadence IRQ/read-only snapshots around first RC1. The important window
# is Android esoc0 -> RC1 assert -> L0, about 8.5s..8.9s in V852.
(
  i=0
  while [ "$i" -lt 320 ]; do
    uptime="$(cat /proc/uptime 2>/dev/null | awk '{print $1}')"
    echo "A90_V1527_SAMPLE_BEGIN index=$i uptime=$uptime"
    cat /proc/interrupts 2>/dev/null | grep -Ei 'msmgpio-dc +104|msmgpio-dc +142|msm_pcie_wake|mdm status|mhi|pcie' || true
    if [ -r /sys/kernel/debug/gpio ]; then grep -Ei 'gpio102|gpio103|gpio104|gpio135|gpio142' /sys/kernel/debug/gpio || true; fi
    echo "A90_V1527_SAMPLE_END index=$i uptime=$uptime"
    i=$((i + 1))
    if command -v usleep >/dev/null 2>&1; then usleep 25000; else sleep 1; fi
  done
) > "$OUT/irq-gpio-samples.log" 2>&1

kill "$KMSG_PID" 2>/dev/null || true
dmesg 2>&1 | grep -Ei 'subsys-restart|__subsystem_get|esoc0|msm_pcie|PCIe|RC1|LTSSM|mhi|wlfw|BDF|wlan0' > "$OUT/dmesg-filtered.txt" 2>&1 || true
touch "$OUT/done"
chmod 644 "$OUT"/* 2>/dev/null || true
exit 0
```

## Interpretation

V1526 does not start Wi-Fi or mutate native RC1. It defines the next bounded Android-good capture needed to explain the first-L0 trigger. V852 proves Android gets first L0 without a debugfs TEST marker. V1517 proves native explicit TEST:11 fails before L0. V1525 proves MHI PM-resume is post-enumeration and cannot create first L0. Therefore V1527 should capture raw kernel log context and high-cadence GPIO104/GPIO142 IRQ samples from early Android boot using the already proven V1521 temporary Magisk/rollback pattern.

If raw kmsg includes task context for the first `msm_pcie_enable` lines, V1527 can attribute the Android-only caller. If it does not, the next step should be tracefs/dynamic event design, not another blind native TEST:11 timing retry.

## Safety Scope

This cycle is host-only. It performs no device command, flash, reboot, partition write, Wi-Fi HAL start, scan/connect, credential handling, DHCP/routes, external ping, PMIC/GPIO/GDSC write, eSoC notify/`BOOT_DONE` spoof, pci-msm debugfs write, global PCI rescan, or platform bind/unbind.

## Next

- V1527 should implement and run the rollbackable Android trigger capture handoff using this contract.
