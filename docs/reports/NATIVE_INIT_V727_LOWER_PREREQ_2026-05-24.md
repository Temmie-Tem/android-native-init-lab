# Native Init V727 Lower Prerequisite Report

- date: `2026-05-24 KST`
- runner: `scripts/revalidation/native_wifi_lower_prereq_v727.py`
- evidence: `tmp/wifi/v727-lower-prereq/`
- latest pointer: `tmp/wifi/latest-v727-lower-prereq.txt`
- decision: `v727-vendor-root-alias-gap-and-static-wlan-surface-classified`
- status: `pass`

## Scope Result

V727 was a lower prerequisite classifier. It mounted `sda29` only under an
isolated `/tmp/a90-v727-*/vendor` proof directory with `ext4 ro,noload`, then
unmounted and removed the temporary node/directories.

It did not mount over `/vendor`, `/system`, `/mnt/system`, or `/dev/block`. It
did not open `subsys_modem` or `esoc0`, write subsystem state, load/unload
modules, start CNSS daemon, start service-manager, start Wi-Fi HAL, run
`qcwlanstate`, scan/connect, use credentials, run DHCP, change routes, external
ping, write a boot image, or write a partition.

Post-run mount readback returned no `/tmp/a90-v727` or `/vendor` proof mount.

## Key Results

| check | result |
| --- | --- |
| native baseline | V724 healthy |
| isolated vendor mount | pass; current `sda29` resolved as `259:13` and cleanup passed |
| current `/vendor` firmware | finding; no Wi-Fi firmware files visible |
| isolated `sda29` firmware | pass; `wlanmdsp.mbn`, `bdwlan.bin`, `regdb.bin`, and `WCNSS_qcom_cfg.ini` visible |
| `wlan` module semantics | pass; `/sys/module/wlan` exists, `/proc/modules` lacks `wlan`, no `initstate`/`refcnt`, parameter files exist |
| modem state | finding; `mss=OFFLINING`, `mdm3=OFFLINING` |
| MHI/WLFW progression | finding; MHI/QCA6390/WLFW/BDF/`wlan0` markers absent |

## Evidence Summary

Current native vendor view:

```text
/vendor -> /mnt/system/vendor
/system/vendor -> /vendor
```

Current native `/vendor` did not expose:

```text
/vendor/firmware/wlanmdsp.mbn
/vendor/firmware/wlan/qca_cld/bdwlan.bin
/vendor/firmware/wlan/qca_cld/regdb.bin
/vendor/firmware/wlan/qca_cld/WCNSS_qcom_cfg.ini
```

The isolated read-only `sda29` vendor proof did expose:

```text
/vendor/firmware/wlanmdsp.mbn
/vendor/firmware/wlan/qca_cld/bdwlan.bin
/vendor/firmware/wlan/qca_cld/regdb.bin
/vendor/firmware/wlan/qca_cld/WCNSS_qcom_cfg.ini
```

`wlan` load-state evidence:

```text
/proc/modules has wlan: False
/sys/module/wlan exists: True
/sys/module/wlan/initstate exists: False
/sys/module/wlan/refcnt exists: False
vendor lib/modules WLAN-like hits: 0
```

This supports treating `wlan` as a built-in/static parameter surface unless a
later Android reference proves a loadable `wlan.ko` path.

## Interpretation

V727 changes the immediate next step:

```text
current /vendor lacks Android vendor Wi-Fi firmware
  + isolated sda29 vendor contains required Wi-Fi firmware
  + wlan looks static/built-in, not missing loadable module
  + modem/MDM3 still OFFLINING
  + no MHI/WLFW/BDF/wlan0
  => fix runtime vendor namespace before modem ONLINE or CNSS daemon retry
```

The shorter path is not `insmod`, CNSS daemon retry, HAL, or scan/connect. The
next gate should prove a private vendor root layout that exposes the real
`sda29` vendor assets in the namespace used by the lower companion stack.

## Validation

Executed:

```bash
python3 -m py_compile scripts/revalidation/native_wifi_lower_prereq_v727.py

python3 scripts/revalidation/native_wifi_lower_prereq_v727.py \
  --out-dir tmp/wifi/v727-lower-prereq-plan plan

python3 scripts/revalidation/native_wifi_lower_prereq_v727.py \
  --out-dir tmp/wifi/v727-lower-prereq run
```

Cleanup check:

```bash
python3 scripts/revalidation/a90ctl.py --timeout 20 cat /proc/mounts \
  | rg '/tmp/a90-v727|/vendor '
```

No leftover proof mount was returned.

Additional host checks:

```bash
git diff --check
```

Result: pass.

## Next Gate

V728 should stay below daemon/HAL/scan/connect and test a bounded private vendor
root layout:

1. mount actual `sda29` vendor read-only in an isolated namespace or proof root;
2. prove `wlanmdsp.mbn`, `bdwlan.bin`, and `regdb.bin` resolve through the paths
   companion services expect;
3. keep modem ONLINE trigger separate until vendor namespace correctness is
   proven;
4. keep credentials, DHCP, routes, external ping, and Wi-Fi bring-up blocked.
