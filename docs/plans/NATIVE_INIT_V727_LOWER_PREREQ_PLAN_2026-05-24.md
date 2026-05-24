# Native Init V727 Lower Prerequisite Plan

- date: `2026-05-24 KST`
- cycle: `v727`
- runner: `scripts/revalidation/native_wifi_lower_prereq_v727.py`
- evidence target: `tmp/wifi/v727-lower-prereq/`
- gate: read-only lower prerequisite classifier before modem ONLINE or CNSS daemon retry

## Goal

V726 corrected the SM8250 model:

```text
cnss2 probe -> QCA6390 PCIe/MHI power-up -> WLFW service 69 -> BDF -> wlan0
```

The next useful question is not HAL or scan/connect. V727 narrows the lower
preconditions:

1. whether current native `/vendor` exposes the real Android vendor Wi-Fi
   firmware view;
2. whether an isolated read-only `sda29` vendor mount exposes
   `wlanmdsp.mbn`, `bdwlan.bin`, and `regdb.bin`;
3. whether `/sys/module/wlan` without a `/proc/modules` entry means built-in
   static WLAN support rather than a missing loadable `wlan.ko`;
4. whether modem/MDM3 and MHI/WLFW/`wlan0` are still absent.

## Scope

Allowed:

- read native baseline with `version`, `status`, and `selftest`;
- read `/vendor` symlink state, `firmware_class.path`, `/proc/modules`,
  `/sys/module/wlan`, modem subsystem state, and dmesg;
- resolve current `sda29` major/minor from sysfs;
- create a temporary block node under `/tmp/a90-v727-*`;
- mount `sda29` only under `/tmp/a90-v727-*/vendor` with `ext4 ro,noload`;
- stat/list only bounded firmware and module paths;
- unmount and remove temporary proof paths;
- write private host-side evidence.

Blocked:

- mounting over `/vendor`, `/system`, `/mnt/system`, or `/dev/block`;
- opening `subsys_modem` or `esoc0`;
- subsystem state writes such as `echo online > state`;
- `insmod`, `rmmod`, or `modprobe`;
- CNSS daemon, service-manager, Wi-Fi HAL, supplicant, hostapd, or `qcwlanstate`;
- scan/connect/link-up, credentials, DHCP, route changes, or external ping;
- boot image or partition writes.

## Success Criteria

V727 passes as a classifier if it safely records:

- expected native baseline is healthy;
- isolated `sda29` read-only mount succeeds and is cleaned up;
- current `/vendor` firmware visibility;
- isolated vendor firmware visibility;
- `wlan` `/proc/modules` versus `/sys/module/wlan` semantics;
- modem state and MHI/WLFW/`wlan0` marker counts;
- explicit guardrail booleans showing no Wi-Fi bring-up or external ping.

Expected current decision:

```text
v727-vendor-root-alias-gap-and-static-wlan-surface-classified
```

## Validation Plan

```bash
python3 -m py_compile scripts/revalidation/native_wifi_lower_prereq_v727.py

python3 scripts/revalidation/native_wifi_lower_prereq_v727.py \
  --out-dir tmp/wifi/v727-lower-prereq-plan plan

python3 scripts/revalidation/native_wifi_lower_prereq_v727.py \
  --out-dir tmp/wifi/v727-lower-prereq run

python3 scripts/revalidation/a90ctl.py --timeout 20 cat /proc/mounts \
  | rg '/tmp/a90-v727|/vendor '

git diff --check
```

## Next Gate

If V727 confirms that the real vendor firmware is visible only through isolated
`sda29`, V728 should test a bounded private vendor root layout before modem
ONLINE or CNSS daemon retry. Modem ONLINE remains necessary, but doing it before
the vendor firmware namespace is correct is not the shortest path to WLFW.
