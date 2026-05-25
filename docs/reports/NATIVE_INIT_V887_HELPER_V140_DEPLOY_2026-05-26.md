# V887 Helper v140 Deploy-only Report

## Result

| Unit | Evidence | Decision |
| --- | --- | --- |
| helper v140 deploy | `tmp/wifi/v887-execns-helper-v140-deploy-preflight-retry1850/manifest.json` | `execns-helper-v140-deploy-pass` |

V887 deployed helper `v140` to `/cache/bin/a90_android_execns_probe`.

## Attempts

The first approved run used `--serial-chunk-size 3000` and stopped before any
device write:

- evidence: `tmp/wifi/v887-execns-helper-v140-deploy-preflight/manifest.json`
- result: `execns-helper-v140-deploy-failed`
- reason: serial line-safety check failed
- chunks written: `0`
- max line bytes: `6190`
- safe line limit: `3968`

The retry used `--serial-chunk-size 1850` and passed:

- evidence:
  `tmp/wifi/v887-execns-helper-v140-deploy-preflight-retry1850/manifest.json`
- result: `execns-helper-v140-deploy-pass`
- serial chunks: `788`
- max line bytes: `3890`
- safe line limit: `3968`
- transfer method: `serial`

## Remote Verification

- remote path: `/cache/bin/a90_android_execns_probe`
- sha256:
  `894fdd753cb6567b2abbb3c94f332ce63cf959b7d1708768cf3bcdc10b2b53e0`
- helper marker: `a90_android_execns_probe v140`
- mode token:
  `wifi-companion-esoc-req-registered-subsys-hold-preflight`
- post-deploy `version`, `status`, `selftest`, `netservice-status`,
  `stat-helper`, `sha-helper`, `ps`, and `proc-net-dev` were read-only and
  passed.
- no-argument helper usage returned rc `2`, which is expected for usage output;
  the output included the v140 marker.

## Guardrails

- no live eSoC ioctl
- no `/dev/subsys_esoc0` open
- no `ESOC_NOTIFY`
- no Android actor start
- no service-manager start
- no Wi-Fi HAL, scan/connect, credentials, DHCP/routes, or external ping
- no boot image write, partition write, firmware mutation, GPIO/sysfs/debugfs
  write, module load/unload, or reboot

## Notes

NCM was not active, so V887 used serial transfer. The failed `3000` chunk-size
attempt is useful evidence: cmdv1x transport still has a practical line limit,
and `1850` remains the safe serial deploy size for this helper.

## Next

V888 should be a host-only response-gate plan/classifier before any live
`ESOC_NOTIFY`. It should decide whether the first bounded response proof should
send `ESOC_IMG_XFER_DONE`, `ESOC_BOOT_DONE`, or a two-step sequence, and it must
define timeout and reboot-cleanup criteria.
