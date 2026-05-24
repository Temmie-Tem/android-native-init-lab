# Native Init V733 Holder Lower Companion Report

- date: `2026-05-24 KST`
- runner: `scripts/revalidation/native_wifi_holder_lower_companion_v733.py`
- evidence: `tmp/wifi/v733-holder-lower-companion/`
- latest pointer: `tmp/wifi/latest-v733-holder-lower-companion.txt`
- prerequisite evidence:
  - V401: `tmp/wifi/v733-v401-current-run/`
  - V490: `tmp/wifi/v733-v490-current-run/`
- decision: `v733-holder-lower-companion-sysmon-advance`
- status: `pass`

## Scope Result

V733 ran the current-build lower companion observer inside the V731/V732
firmware-mounted `subsys_modem` holder window.

It started only:

```text
qrtr_ns,rmt_storage,tftp_server,pd_mapper
```

It did not start `cnss_diag`, `cnss-daemon`, service-manager, Wi-Fi HAL,
`wificond`, supplicant, hostapd, scan/connect, credential use, DHCP, route
changes, external ping, boot image writes, partition writes, module load/unload,
subsystem state writes, or `esoc0`.

Post-run reboot cleanup returned to `A90 Linux init 0.9.68 (v724)` with
`selftest fail=0`; follow-up mount grep returned no V733 firmware/proof mount
leftovers.

## Preconditions

| item | result |
| --- | --- |
| helper | `a90_android_execns_probe v121`, SHA `547232ddb352740bb7a7f1d0f9116162584e34a536b9d9b77869ed8d838e7c89` |
| V401 SELinuxfs | `toybox-selinuxfs-mount-live-executor-run-pass` |
| V490 policy load | `v490-selinux-policy-load-proof-pass` |
| V731 reference | `v731-firmware-mounted-modem-holder-qrtr-rx-pass` |
| V732 reference | `v732-cnss2-mhi-holder-window-cnss2-gap-classified` |

## Key Results

| item | result |
| --- | --- |
| firmware mounts | pass; `/vendor/firmware_mnt` and `/vendor/firmware-modem` mounted read-only during proof |
| `subsys_modem` holder | pass; holder opened |
| `mss` state | `OFFLINING -> ONLINE -> ONLINE` |
| `mdm3` state | `OFFLINING -> OFFLINING -> OFFLINING` |
| lower companion order | `qrtr_ns,rmt_storage,tftp_server,pd_mapper` |
| lower companion cleanup | `all_observable=1`, `all_postflight_safe=1` |
| forbidden helper actions | CNSS/service-manager/HAL/wificond/scan/connect/external ping/QMI payload all `0` |
| QRTR RX/TX/sysmon | advanced: `qrtr_rx=1`, `qrtr_tx=1`, `sysmon_qmi=1` |
| QRTR service `69/74/180` | all `0` |
| MHI/QCA6390/WLFW/BDF/`wlan0` | all `0` |
| kernel warning markers | `0` |

Marker counts from the proof window:

| marker | count |
| --- | ---: |
| `qrtr_rx` | `1` |
| `qrtr_tx` | `1` |
| `sysmon_qmi` | `1` |
| `rpmsg` | `0` |
| `service_notifier` | `0` |
| `wlan_pd` | `0` |
| `mhi` | `0` |
| `qca6390` | `0` |
| `wlfw` | `0` |
| `bdf` | `0` |
| `wlan0` | `0` |
| `kernel_warning` | `0` |

## Interpretation

V733 restores the V609-safe lower companion effect on the current V724 build:

```text
firmware mounts + subsys_modem holder
  -> mss ONLINE
  -> QRTR RX
  -> lower companion/TFTP stack
  -> QRTR TX + modem sysmon-qmi
  -> no service-notifier, no service 69, no MHI/QCA6390/WLFW/BDF/wlan0
```

This moves the current blocker forward from V732's `post-QRTR-RX` gap to a
post-sysmon publication gap. Starting more Wi-Fi userspace remains premature
until the path after modem `sysmon-qmi` publishes WLAN-PD/service `180/74` or
WLFW/service `69`.

`mdm3` remained `OFFLINING`, so the next gate should focus on the Android/native
delta that changes `mdm3` or publishes post-sysmon services, not on HAL or
scan/connect.

## Validation

Executed:

```bash
python3 -m py_compile scripts/revalidation/native_wifi_holder_lower_companion_v733.py

python3 scripts/revalidation/native_wifi_holder_lower_companion_v733.py \
  --out-dir tmp/wifi/v733-holder-lower-companion-plan plan

python3 scripts/revalidation/a90ctl.py --timeout 60 mountsystem ro

python3 scripts/revalidation/wifi_selinuxfs_toybox_mount_live_executor.py \
  --out-dir tmp/wifi/v733-v401-current-run \
  --approval-phrase 'approve v401 toybox mount selinuxfs runtime surface only; no daemon start and no Wi-Fi bring-up' \
  --apply --assume-yes run

python3 scripts/revalidation/native_selinux_policy_load_proof_v490.py \
  --out-dir tmp/wifi/v733-v490-current-run \
  --expect-version 'A90 Linux init 0.9.68 (v724)' \
  --helper-sha256 547232ddb352740bb7a7f1d0f9116162584e34a536b9d9b77869ed8d838e7c89 \
  --approval-phrase 'approve v490 native SELinux policy-load proof only; no init reexec, no daemon start and no Wi-Fi bring-up' \
  --apply --assume-yes run

python3 scripts/revalidation/native_wifi_holder_lower_companion_v733.py \
  --out-dir tmp/wifi/v733-holder-lower-companion run
```

Post-run spot checks:

```bash
python3 scripts/revalidation/a90ctl.py --timeout 20 status

python3 scripts/revalidation/a90ctl.py --timeout 20 cat /proc/mounts \
  | rg '/vendor/firmware_mnt|/vendor/firmware-modem|/tmp/a90-v733| /sys/fs/selinux'
```

The status check returned native V724 healthy, and the mount grep returned no
leftover V733 firmware/proof mount.

## Next Gate

V734 should remain below CNSS daemon, service-manager, HAL, scan/connect, and
credentials. The next useful unit is a host-only classifier over Android
reference evidence and V733 native evidence focused on:

1. `mdm3` transition timing and trigger source;
2. events immediately after modem `sysmon-qmi`;
3. service-notifier/service `180/74` publication prerequisites;
4. whether a safe, non-DSP-boot-node live trigger exists for the missing
   post-sysmon publication edge.
