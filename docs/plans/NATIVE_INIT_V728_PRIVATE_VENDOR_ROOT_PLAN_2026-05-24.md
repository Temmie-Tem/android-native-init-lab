# Native Init V728 Private Vendor Root Plan

- date: `2026-05-24 KST`
- cycle: `v728`
- runner: `scripts/revalidation/native_wifi_private_vendor_root_v728.py`
- evidence target: `tmp/wifi/v728-private-vendor-root/`
- gate: private exec namespace vendor root layout proof before modem ONLINE

## Goal

V727 proved two facts:

```text
current /vendor -> /mnt/system/vendor has no Wi-Fi firmware
isolated sda29 vendor has wlanmdsp.mbn, bdwlan.bin, regdb.bin
```

V728 verifies that the already-deployed exec namespace helper uses the same real
`sda29` vendor partition as `/vendor` in its private Android-like root. This is
the layout the later companion/modem proof will rely on.

## Scope

Allowed:

- read native baseline with `version`, `status`, and `selftest`;
- verify remote helper marker with `a90_android_execns_probe --help`;
- run helper `identity-probe` only:
  - `--system-root /mnt/system/system`;
  - `--vendor-block /dev/block/sda29`;
  - `--vendor-fstype ext4`;
  - `--target-profile cnss-daemon`;
  - `--mode identity-probe`;
- read helper output for `helper_status=namespace-ready`,
  `vendor_mount_source`, and `/vendor/bin/cnss-daemon` context;
- independently mount `sda29` under `/tmp/a90-v728-*/vendor` with
  `ext4 ro,noload` to prove required Wi-Fi firmware still exists;
- cleanup and verify no `/tmp/a90-v231-*` or `/tmp/a90-v728-*` mounts remain;
- write private host-side evidence.

Blocked:

- helper deployment or replacement;
- opening `subsys_modem` or `esoc0`;
- subsystem state writes;
- module load/unload;
- CNSS daemon start, service-manager start, Wi-Fi HAL start, supplicant,
  hostapd, or `qcwlanstate`;
- scan/connect/link-up, credentials, DHCP, route changes, or external ping;
- boot image or partition writes.

## Success Criteria

V728 passes if it records:

- expected native baseline is healthy;
- helper `v121` is present;
- helper `identity-probe` reaches `namespace-ready`;
- helper private `/vendor` target contains executable `/vendor/bin/cnss-daemon`;
- the same `sda29` isolated proof exposes `wlanmdsp.mbn`, `bdwlan.bin`,
  `regdb.bin`, and `WCNSS_qcom_cfg.ini`;
- helper and isolated proof cleanup leave no proof mounts;
- guardrail booleans show no modem trigger, daemon/HAL start, Wi-Fi bring-up, or
  external ping.

Expected current decision:

```text
v728-private-execns-vendor-root-layout-proof-pass
```

## Validation Plan

```bash
python3 -m py_compile scripts/revalidation/native_wifi_private_vendor_root_v728.py

python3 scripts/revalidation/native_wifi_private_vendor_root_v728.py \
  --out-dir tmp/wifi/v728-private-vendor-root-plan plan

python3 scripts/revalidation/native_wifi_private_vendor_root_v728.py \
  --out-dir tmp/wifi/v728-private-vendor-root run

python3 scripts/revalidation/a90ctl.py --timeout 20 cat /proc/mounts \
  | rg '/tmp/a90-v231|/tmp/a90-v728|/vendor '

git diff --check
```

## Next Gate

If V728 passes, V729 should test the smallest safe modem ONLINE trigger proof.
That proof must still avoid `esoc0`, keep daemon/HAL/scan/connect blocked, and
observe whether modem ONLINE creates QRTR/sysmon/MHI/WLFW movement.
