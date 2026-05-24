# Native Init V729 Modem-only Hold Plan

- date: `2026-05-24 KST`
- cycle: `v729`
- runner: `scripts/revalidation/native_wifi_modem_only_hold_v729.py`
- evidence target: `tmp/wifi/v729-modem-only-hold/`
- gate: smallest safe modem-readiness trigger proof before companion/daemon work

## Goal

V728 proved the private exec namespace can expose the real `sda29` vendor
partition as `/vendor`, and that the required Wi-Fi firmware exists there.
V729 tests the next lower prerequisite: whether opening only the
`subsys_modem` subsystem character device can create an observable modem
readiness window.

The proof is intentionally narrower than earlier modem/esoc experiments:

```text
create private /tmp char node from /sys/class/subsys/subsys_modem/dev
  -> open only that node in a bounded background holder
    -> observe mss/mdm3 state, crash counts, QRTR/sysmon/MHI/WLFW/BDF/wlan0
```

## Scope

Allowed:

- read native baseline with `version`, `status`, and `selftest`;
- read `/sys/class/subsys/subsys_modem/dev`;
- create a temporary private `/tmp/a90-v729-*` character node for
  `subsys_modem`;
- open only that temporary `subsys_modem` node from a bounded background holder;
- observe `mss` and `mdm3` state/crash counts before, during, and after the
  holder window;
- capture bounded `dmesg` marker counts for QRTR, sysmon, rpmsg, MHI, QCA6390,
  WLFW, BDF, and `wlan0`;
- cleanup holder process, temporary node, and temporary directory;
- write private host-side evidence.

Blocked:

- creating or opening any `esoc0` node;
- subsystem state writes such as `echo online`;
- module load/unload;
- CNSS daemon start, service-manager start, Wi-Fi HAL start, supplicant,
  hostapd, or `qcwlanstate`;
- scan/connect/link-up, credentials, DHCP, route changes, or external ping;
- boot image or partition writes.

## Success Criteria

V729 passes if it safely classifies the modem-only trigger attempt:

- expected native baseline is healthy;
- the `subsys_modem` cdev major/minor is read successfully;
- the temporary node is created with private proof scope;
- the holder starts and either:
  - opens successfully and records whether a modem readiness window appears; or
  - remains pending/blocking and records that as a valid blocker;
- crash counts remain stable;
- cleanup removes the proof node/directory;
- guardrail booleans show no `esoc0`, daemon/HAL, Wi-Fi bring-up, or external
  ping action.

Expected current decision if the open blocks:

```text
v729-subsys-modem-open-pending-no-online-window
```

## Validation Plan

```bash
python3 -m py_compile scripts/revalidation/native_wifi_modem_only_hold_v729.py

python3 scripts/revalidation/native_wifi_modem_only_hold_v729.py \
  --out-dir tmp/wifi/v729-modem-only-hold-plan plan

python3 scripts/revalidation/native_wifi_modem_only_hold_v729.py \
  --out-dir tmp/wifi/v729-modem-only-hold run

python3 scripts/revalidation/a90ctl.py --timeout 20 status

git diff --check
```

## Next Gate

If V729 shows that `subsys_modem` open alone stays pending or does not create an
ONLINE window, V730 should compare the Android `mdm_helper`/subsystem trigger
path before trying broader native actions. The next proof should still avoid
Wi-Fi HAL, scan/connect, credentials, DHCP, routes, and external ping.
