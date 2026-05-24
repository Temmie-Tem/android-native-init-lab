# Native Init V782 BPF Counter Boot WLAN Report

## Result

- decision: `v782-bpf-counter-boot-wlan-counted-control-surface-only`
- pass: `true`
- runner: `scripts/revalidation/native_wifi_bpf_counter_boot_wlan_v782.py`
- evidence: `tmp/wifi/v782-bpf-counter-boot-wlan/`

## What Ran

Prerequisites were refreshed first because the recovered v724 boot did not have
SELinuxfs mounted:

```bash
python3 scripts/revalidation/wifi_selinuxfs_toybox_mount_live_executor.py \
  --out-dir tmp/wifi/v782-v401-current-run \
  --approval-phrase 'approve v401 toybox mount selinuxfs runtime surface only; no daemon start and no Wi-Fi bring-up' \
  --apply --assume-yes run

python3 scripts/revalidation/native_selinux_policy_load_proof_v490.py \
  --out-dir tmp/wifi/v782-v490-current-run \
  --expect-version 'A90 Linux init 0.9.68 (v724)' \
  --helper-sha256 d44cbb538db11a280aa789ccafb008476ac541ec08bb96f549670ae28db7cec6 \
  --approval-phrase 'approve v490 native SELinux policy-load proof only; no init reexec, no daemon start and no Wi-Fi bring-up' \
  --apply --assume-yes run
```

Then V782 ran:

```bash
python3 -m py_compile scripts/revalidation/native_wifi_bpf_counter_boot_wlan_v782.py

python3 scripts/revalidation/native_wifi_bpf_counter_boot_wlan_v782.py \
  --allow-bpf-counter-deploy \
  --allow-tracefs-mount \
  --allow-bpf-attach \
  --allow-lower-window-boot-wlan \
  --assume-yes \
  run
```

## Evidence Summary

| Signal | Value |
| --- | --- |
| BPF helper | `a90_bpf_trace_counter v782` |
| BPF helper sha256 | `c09c419cae6ca0d58075970543e84ef4a51e89a94c1d7c27dc6a034e6de6ce1b` |
| BPF deploy | `existing` remote helper reused after sha match |
| tracepoint | `msm_pil_event:pil_notif` |
| tracepoint id | `595` |
| BPF result | `attach-count-pass` |
| BPF event count | `8` |
| `mss` state | `OFFLINING -> ONLINE -> ONLINE` |
| `mdm3` state | `OFFLINING -> OFFLINING -> OFFLINING` |
| QRTR readiness | RX `1`, TX `1`, `sysmon-qmi` `1` |
| QRTR service `69/74/180` | `0/0/0` |
| qcwlanstate markers | `15` |
| WLFW/BDF/wiphy/`wlan0` | `0/0/false/false` |
| cleanup | rebooted back to healthy v724; tracefs unmounted |

The BPF counter captured events during the lower-window transition:

```text
a90_bpf_trace_counter v782
target=msm_pil_event:pil_notif
tracepoint_id=595
bpf_prog_fd=4
perf_fd=5
attach_attempted=1
observe_begin=1
observe_end=1
event_count=8
result=attach-count-pass
```

The bounded `boot_wlan` write still reached only the control surface:

```text
wlanboot.result=boot-write-executed
wlanboot.after.qcwlanstate.value=OFF
wlanboot.after.sys_class_wlan_dev.value=478:0
wlanboot.after.dev_wlan.exists=0
wlanboot.after.sys_class_net_wlan0.exists=0
wlanboot.after.sys_class_ieee80211.count=0
```

## Interpretation

V782 proves the stock v724 BPF observer can count real PIL notification events
during the lower modem/WLAN window. The count is not zero: `8` PIL notification
events occurred while the firmware mounts, `subsys_modem` holder, QRTR
readiness, lower companion stack, and bounded `boot_wlan` write executed.

The blocker is now sharper:

```text
PIL notifications happen
  -> mss reaches ONLINE
  -> QRTR RX/TX and sysmon-qmi happen
  -> qcwlanstate control surface appears
  -> mdm3 stays OFFLINING
  -> service 69/74/180, WLFW, BDF, wiphy, wlan0 remain absent
```

This means the missing edge is not "no PIL notification at all" and not a
generic inability to observe the transition. The remaining gap is the mdm3 /
WLAN-PD / WLFW publication path after modem/sysmon readiness and before
ICNSS/QCACLD can finish.

## Safety

- Wi-Fi HAL/service-manager start: not executed
- Wi-Fi scan/connect/link-up: not executed
- credential use: not executed
- DHCP/routes/external ping: not executed
- `qcwlanstate ON`: not executed
- module load/unload: not executed
- sysfs bind/unbind or `driver_override`: not executed
- `esoc0` access: not executed
- boot image or partition write: not executed
- runtime cleanup: rebooted back to healthy v724

## Next

V783 should use the new BPF counter plus existing dmesg/QRTR evidence to compare
which PIL notification names/codes are missing or different from Android. The
most direct next step is a host-only classifier over Android reference logs and
V782 `pil_notif` evidence, followed by a bounded live gate only if it identifies
a specific missing mdm3/WLAN-PD trigger. Do not repeat blind `boot_wlan`,
`qcwlanstate`, CNSS daemon ordering, or HAL/scan/connect.
