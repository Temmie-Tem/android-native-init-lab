# Native Init V729 Modem-only Hold Report

- date: `2026-05-24 KST`
- runner: `scripts/revalidation/native_wifi_modem_only_hold_v729.py`
- evidence: `tmp/wifi/v729-modem-only-hold/`
- latest pointer: `tmp/wifi/latest-v729-modem-only-hold.txt`
- decision: `v729-subsys-modem-open-pending-no-online-window`
- status: `pass`

## Scope Result

V729 created a temporary private character node for `subsys_modem` from the
live `/sys/class/subsys/subsys_modem/dev` value `236:0`, started a bounded
background holder against that node, and observed subsystem state and kernel
markers before cleanup.

The holder process started, but the open attempt remained pending/blocking:

```text
holder_pid_during=794
holder_alive_during=true
holder_log_exists_during=false
holder_pid_after=794
holder_alive_after=true
holder_log_exists_after=false
holder_open_pending_during=true
holder_open_pending_after=true
holder_open_rc_after=
```

That means the holder entered the open path but never reached the logging line
after `exec 3<subsys_modem` during the bounded window.

V729 did not create or open `esoc0`, write subsystem state, load/unload modules,
start CNSS daemon, start service-manager, start Wi-Fi HAL, run `qcwlanstate`,
scan/connect, use credentials, run DHCP, change routes, external ping, write a
boot image, or write a partition.

Cleanup terminated the pending holder and removed the temporary node/directory.

## Key Results

| check | result |
| --- | --- |
| native baseline | V724 healthy |
| `subsys_modem` cdev | pass; `236:0` |
| holder start | pass; pid `794` |
| holder open outcome | finding; open stayed pending/blocking |
| `mss` state | `OFFLINING -> OFFLINING -> OFFLINING` |
| `mdm3` state | `OFFLINING -> OFFLINING -> OFFLINING` |
| `mss` crash count | stable `0 -> 0` |
| `mdm3` crash count | stable `0 -> 0` |
| QRTR/sysmon movement | none |
| MHI/QCA6390/WLFW/BDF/`wlan0` movement | none |
| postflight safety | pass; cleanup ok, crash counts stable, warning marker count `0` |

## Evidence Summary

State timeline:

```text
mss:  before=OFFLINING hold=OFFLINING after=OFFLINING
mdm3: before=OFFLINING hold=OFFLINING after=OFFLINING
```

Dmesg marker counts:

```text
qrtr_rx=0 qrtr_tx=0 sysmon=0 rpmsg=0
mhi=0 qca6390=0 wlfw=0 bdf=0 wlan0=0
```

Guardrails:

```text
subsys_modem_open_attempted=True
subsys_modem_open_executed=False
esoc0_open_executed=False
subsystem_writes_executed=False
wifi_bringup_executed=False
external_ping_executed=False
```

Post-run status remained healthy:

```text
boot: BOOT OK shell 4.2s
selftest: pass=11 warn=1 fail=0
exposure: guard=ok warn=0 fail=0 ncm=absent tcpctl=stopped rshell=stopped
```

## Interpretation

`subsys_modem` open by itself is not a sufficient native trigger for the current
Wi-Fi path. It does not move `mss` or `mdm3` out of `OFFLINING`, does not produce
QRTR/sysmon movement, and does not progress toward MHI/QCA6390/WLFW/BDF/`wlan0`.

The meaningful new result is that the read-only open path itself can remain
pending. That points away from blindly retrying CNSS daemon, service-manager,
Wi-Fi HAL, or scan/connect, and toward understanding Android's lower modem
bring-up path: `mdm_helper`, subsystem ioctl/property sequencing, and any
required modem firmware/SSCTL handoff.

## Validation

Executed:

```bash
python3 -m py_compile scripts/revalidation/native_wifi_modem_only_hold_v729.py

python3 scripts/revalidation/native_wifi_modem_only_hold_v729.py \
  --out-dir tmp/wifi/v729-modem-only-hold-plan plan

python3 scripts/revalidation/native_wifi_modem_only_hold_v729.py \
  --out-dir tmp/wifi/v729-modem-only-hold run

python3 scripts/revalidation/a90ctl.py --timeout 20 status
```

Result: pass.

## Next Gate

V730 should be an Android-vs-native lower modem trigger comparison before any
broader live action:

1. identify how Android invokes `mdm_helper` for `mdm3`/modem readiness;
2. classify whether it uses subsystem cdev ioctl, properties, or another
   control path rather than a plain blocking open;
3. keep `esoc0`, subsystem writes, daemon/HAL, scan/connect, credentials, DHCP,
   routes, and external ping blocked until the lower modem window is understood.
