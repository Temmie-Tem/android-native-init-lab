# Native Init V641 Firmware-Backed Boot-Window Armed Live Report

- date: `2026-05-23 KST`
- cycle: `v641`
- status: `classified`; Wi-Fi external ping is **not** complete
- evidence: `tmp/wifi/v641-armed-proof-20260523-063620/`
- prep commit: `ee578f1`
- disabled-smoke commit: `bb051f1`

## Scope

This live gate ran the V641 one-shot proof once. It mounted firmware surfaces
read-only, wrote the ADSP/CDSP/SLPI sibling SSCTL boot nodes with per-node
child timeout/reap handling, collected boot/timeline/proof/dmesg evidence, and
cleaned up the read-only firmware mounts.

No service-manager start, Wi-Fi HAL start, scan/connect/link-up, credential
handling, DHCP, route change, or external ping was executed.

## Arm Note

`writefile` does not create new files, so the first arm attempt did not create
the one-shot flag. The successful arm used BusyBox shell redirection to create
`/cache/native-init-sibling-fwssctl-v641`, verified it with `stat`, and then
rebooted into the same V641 image.

## Runtime Result

`bootstatus`:

```text
boot: BOOT OK shell 4.6s
selftest: pass=11 warn=1 fail=0
pid1guard: pass=11 warn=1 fail=0
runtime: backend=sd root=/mnt/sdext/a90 fallback=no writable=yes
timeline_entries: 28/32
```

V641 timeline:

```text
17 wifi-v641-fwssctl rc=0 errno=0 armed one-shot
18 wifi-v641-fwssctl rc=0 errno=0 firmware mounts ready
19 wifi-v641-fwssctl rc=0 errno=0 adsp start
20 wifi-v641-fwssctl rc=0 errno=0 adsp status=0x0
21 wifi-v641-fwssctl rc=0 errno=0 cdsp start
22 wifi-v641-fwssctl rc=0 errno=0 cdsp status=0x0
23 wifi-v641-fwssctl rc=0 errno=0 slpi start
24 wifi-v641-fwssctl rc=0 errno=0 slpi status=0x0
25 wifi-v641-fwssctl rc=0 errno=0 complete failures=0 timeouts=0
```

Proof log:

```text
firmware apnhlos mounted source=/dev/block/sda20 target=/vendor/firmware_mnt
firmware modem mounted source=/dev/block/sda21 target=/vendor/firmware-modem
firmware stat firmware_mnt_image path=/vendor/firmware_mnt/image mode=0755 size=16384
firmware stat firmware_modem_image path=/vendor/firmware-modem/image mode=0755 size=16384
firmware stat modem_b00 path=/vendor/firmware-modem/image/modem.b00 mode=0755 size=1108
firmware stat cdsp_mdt missing path=/vendor/firmware-modem/image/cdsp.mdt errno=2 error=No such file or directory
firmware mounts ready
node adsp write rc=0
node adsp parent rc=0 status=0x0 reaped=1
node cdsp write rc=0
node cdsp parent rc=0 status=0x0 reaped=1
node slpi write rc=0
node slpi parent rc=0 status=0x0 reaped=1
```

DSP PIL dmesg:

```text
adsp: loading
adsp: Brought out of reset
adsp: Power/Clock ready interrupt received
cdsp: loading
cdsp: Brought out of reset
cdsp: Power/Clock ready interrupt received
slpi: loading
slpi: Brought out of reset
slpi: Power/Clock ready interrupt received
```

Advancement query:

```text
grep 'pm_qos_add_request|service-notifier|sysmon-qmi|wlan_pd|WLAN FW|wlan0|BDF'
exit 1
```

The V638-specific `pm_qos_add_request()` warning did not recur. Generic early
kernel warnings that are present before proof execution still appear in dmesg,
so they are not treated as this proof's blocking marker.

Cleanup:

```text
umount /vendor/firmware-modem: ok
umount /vendor/firmware_mnt: ok
post-cleanup mounts: no /vendor/firmware_mnt or /vendor/firmware-modem entries
```

## Decision

```text
decision: v641-dsp-pil-clean-no-service74
pass: True
reason: firmware-backed ADSP/CDSP/SLPI writes all returned with rc=0 and produced DSP PIL reset/power-clock readiness without timeout, unreaped child, or pm_qos blocker; service-notifier, sysmon-qmi, WLAN-PD, WLFW/BDF, firmware-ready, and wlan0 did not advance.
next: V642 should combine this clean DSP-PIL state with a bounded lower companion/QRTR observer instead of retrying raw sibling writes or moving to HAL/connect.
```

## Current Device State

The device is still running `A90 Linux init 0.9.67 (v641)`. The one-shot arm
flag was removed by PID1 before proof execution, and read-only firmware mounts
were unmounted after evidence collection.

## Next Gate

Proceed to V642 as a bounded lower companion observer from the clean V641
DSP-PIL state:

1. start only the lower modem/QRTR companion set needed for QMI publication;
2. keep service-manager, CNSS/HAL, scan/connect, credentials, DHCP, route
   changes, and external ping blocked;
3. observe whether `sysmon-qmi`, service-notifier `180/74`, WLAN-PD, WLFW/BDF,
   firmware-ready, or `wlan0` appears;
4. stop/cleanup companion processes and verify no firmware mounts or process
   residue remain.
