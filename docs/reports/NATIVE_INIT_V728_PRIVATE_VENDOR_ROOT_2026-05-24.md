# Native Init V728 Private Vendor Root Report

- date: `2026-05-24 KST`
- runner: `scripts/revalidation/native_wifi_private_vendor_root_v728.py`
- evidence: `tmp/wifi/v728-private-vendor-root/`
- latest pointer: `tmp/wifi/latest-v728-private-vendor-root.txt`
- decision: `v728-private-execns-vendor-root-layout-proof-pass`
- status: `pass`

## Scope Result

V728 used the already-deployed helper `a90_android_execns_probe v121` in
`identity-probe` mode only. This mode created the helper private mount namespace
and chroot-style root, mounted `sda29` as private `/vendor`, and printed context
for `/vendor/bin/cnss-daemon`.

V728 also mounted `sda29` only under an isolated `/tmp/a90-v728-*/vendor` proof
path with `ext4 ro,noload`, then unmounted and removed the temporary node and
directories.

It did not deploy or replace the helper, open `subsys_modem`, open `esoc0`,
write subsystem state, load/unload modules, start CNSS daemon, start
service-manager, start Wi-Fi HAL, run `qcwlanstate`, scan/connect, use
credentials, run DHCP, change routes, external ping, write a boot image, or
write a partition.

Post-run mount readback returned no `/tmp/a90-v231`, `/tmp/a90-v728`, or
`/vendor` proof mount.

## Key Results

| check | result |
| --- | --- |
| native baseline | V724 healthy |
| helper marker | pass; `a90_android_execns_probe v121` present |
| helper private namespace | pass; `helper_status=namespace-ready` |
| helper private `/vendor` | pass; `/vendor/bin/cnss-daemon` exists and is executable in helper root |
| helper cleanup | pass; no `/tmp/a90-v231-*` mount remained |
| current `/vendor` firmware | pass as absence proof; current global `/vendor` still has no Wi-Fi firmware |
| isolated `sda29` firmware | pass; `wlanmdsp.mbn`, `bdwlan.bin`, `regdb.bin`, and `WCNSS_qcom_cfg.ini` visible |
| isolated cleanup | pass; no `/tmp/a90-v728-*` mount remained |
| identity child runtime | review; helper child ended with signal `11`, not used as a V728 layout criterion |

## Evidence Summary

Helper private namespace:

```text
helper_status=namespace-ready
vendor_mount_source=/tmp/a90-v231-753/vendor-block-sda29
context.target.path=/vendor/bin/cnss-daemon
context.target.exists=1
context.target.access_x=1
```

Current native vendor view remains incomplete:

```text
/vendor -> /mnt/system/vendor
/system/vendor -> /vendor
current /vendor Wi-Fi firmware hits: 0
```

The same `sda29` vendor partition contains the required Wi-Fi firmware:

```text
/vendor/firmware/wlanmdsp.mbn
/vendor/firmware/wlan/qca_cld/bdwlan.bin
/vendor/firmware/wlan/qca_cld/regdb.bin
/vendor/firmware/wlan/qca_cld/WCNSS_qcom_cfg.ini
```

Runtime caveat:

```text
identity_probe.preexec_status=pass
child_exit_code=-1
child_signal=11
```

That caveat means V728 should not be interpreted as Android userspace runtime
readiness. It proves the private vendor root layout only.

## Interpretation

V728 proves that the later lower companion/modem work can rely on the existing
exec namespace helper to expose the real vendor partition as private `/vendor`.
The remaining blocker has moved from “where is the Wi-Fi firmware?” to “can the
modem be brought ONLINE safely with this namespace contract available?”

```text
helper private /vendor layout works
  + real sda29 vendor has required Wi-Fi firmware
  + global /vendor remains incomplete
  + no daemon/HAL/scan/connect was attempted
  => next gate is smallest safe modem ONLINE trigger proof
```

## Validation

Executed:

```bash
python3 -m py_compile scripts/revalidation/native_wifi_private_vendor_root_v728.py

python3 scripts/revalidation/native_wifi_private_vendor_root_v728.py \
  --out-dir tmp/wifi/v728-private-vendor-root-plan plan

python3 scripts/revalidation/native_wifi_private_vendor_root_v728.py \
  --out-dir tmp/wifi/v728-private-vendor-root run
```

Cleanup check:

```bash
python3 scripts/revalidation/a90ctl.py --timeout 20 cat /proc/mounts \
  | rg '/tmp/a90-v231|/tmp/a90-v728|/vendor '
```

No leftover proof mount was returned.

Additional host checks:

```bash
git diff --check
```

Result: pass.

## Next Gate

V729 should test the smallest safe modem ONLINE trigger proof:

1. do not touch `esoc0`;
2. use `subsys_modem`/`mss` only if the proof can be bounded and cleaned up;
3. keep CNSS daemon, service-manager, Wi-Fi HAL, scan/connect, credentials,
   DHCP, routes, and external ping blocked;
4. observe only modem state, QRTR/sysmon, MHI/QCA6390, WLFW, BDF, and `wlan0`
   markers.
