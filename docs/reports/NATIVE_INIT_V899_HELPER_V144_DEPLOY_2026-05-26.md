# V899 Helper v144 Deploy-only Report

## Result

| Unit | Evidence | Decision |
| --- | --- | --- |
| deploy run | `tmp/wifi/v899-execns-helper-v144-deploy-preflight/manifest.json` | `execns-helper-v144-deploy-pass` |
| post-deploy parity | `tmp/wifi/v899-execns-helper-v144-postdeploy-preflight/manifest.json` | `execns-helper-v144-deploy-preflight-ready` |

V899 deployed helper `v144` to `/cache/bin/a90_android_execns_probe` and proved
remote checksum/mode parity. No live eSoC, `mdm_helper`, `ks`, Wi-Fi HAL, or
Wi-Fi bring-up action occurred.

## Implementation

- Added deploy wrapper:
  `scripts/revalidation/wifi_execns_helper_v144_deploy_preflight.py`
- Local artifact:
  `tmp/wifi/v898-mdm-helper-ks-contract-helper-build/a90_android_execns_probe`
- Expected sha256:
  `c7b02320f143f57a837b5f1cf8af17258307439be3b8969dc33000735116ce4e`
- Mode token:
  `wifi-companion-mdm-helper-ks-image-contract-preflight`

## Deploy

- transfer method: `serial`
- chunks written: `788`
- encoded bytes: `1456699`
- chunk size: `1850`
- max cmdv1 line bytes: `3890`
- safe line limit: `3968`
- line check: pass

The host NCM path was not active, so the wrapper used the conservative serial
appendfile/uudecode path.

## Post-deploy Proof

- Remote sha:
  `c7b02320f143f57a837b5f1cf8af17258307439be3b8969dc33000735116ce4e`
- Remote marker/mode check: pass
- Native health: `selftest fail=0`
- Service-manager process surface: clean
- Wi-Fi link surface: clean
- Extra manual health check after deploy: `selftest fail=0`, `bootstatus` OK.

## Interpretation

The device now has helper `v144`, so the V900 live gate can use the
`mdm_helper`/`ks` contract mode without another deploy step. This still does
not prove Wi-Fi bring-up. It only removes the deploy/parity blocker between
V898 source/build and a bounded live contract proof.

## Guardrails

- The only intentional device mutation was replacing
  `/cache/bin/a90_android_execns_probe`.
- No live eSoC ioctl, `/dev/subsys_esoc0` open, `REG_REQ_ENG`,
  `ESOC_NOTIFY`, `BOOT_DONE`, `mdm_helper` start, `ks` start,
  service-manager, CNSS daemon, Wi-Fi HAL, scan/connect, credentials,
  DHCP/routes, external ping, boot image write, partition write, firmware
  mutation, GPIO/sysfs/debugfs write, module load/unload, reboot, or Wi-Fi
  link-up occurred.

## Next

V900 should run a bounded live `mdm_helper`/`ks` contract proof:

1. start `/vendor/bin/mdm_helper`;
2. open `/dev/subsys_esoc0` only after `mdm_helper` is observable;
3. observe whether `ks`, MHI pipe, GPIO 142 IRQ, `mdm3=ONLINE`, WLFW/BDF, and
   `wlan0` advance;
4. classify cleanup as pass or reboot-required.

Wi-Fi HAL, scan/connect, credentials, DHCP/routes, and external ping remain
blocked until the lower contract proves readiness.
