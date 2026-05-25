# V901 Helper v145 Allowlist Repair and Deploy Report

## Result

| Unit | Evidence | Decision |
| --- | --- | --- |
| build | `tmp/wifi/v901-execns-helper-v145-build/a90_android_execns_probe` | static ARM64 build pass |
| deploy | `tmp/wifi/v901-execns-helper-v145-deploy-preflight/manifest.json` | `execns-helper-v145-deploy-pass` |

V901 repaired the helper allowlist bug that blocked the first V900 attempt.
Helper `v145` is now deployed to `/cache/bin/a90_android_execns_probe`.

## Repair

- source: `stage3/linux_init/helpers/a90_android_execns_probe.c`
- marker: `a90_android_execns_probe v145`
- change: added `wifi-companion-mdm-helper-ks-image-contract-preflight` to the
  global v235 mode allowlist
- usage now advertises `--allow-mdm-helper-ks-contract-preflight`
- artifact:
  `tmp/wifi/v901-execns-helper-v145-build/a90_android_execns_probe`
- sha256:
  `30c042376ac89f211f597c5a3a17da1e33ce208cfe3b1b839221789a983399c1`
- build: static ARM64, no dynamic section

## Deploy Verification

- transfer method: `serial`
- chunks written: `788`
- remote path: `/cache/bin/a90_android_execns_probe`
- remote helper marker: `a90_android_execns_probe v145`
- remote mode token:
  `wifi-companion-mdm-helper-ks-image-contract-preflight`
- native post-deploy checks remained within deploy-only scope.

## Guardrails

- The only intentional device mutation was replacing
  `/cache/bin/a90_android_execns_probe`.
- No live eSoC ioctl, `/dev/subsys_esoc0` open, `REG_REQ_ENG`,
  `ESOC_NOTIFY`, `BOOT_DONE`, `mdm_helper` start, `ks` start,
  service-manager, CNSS daemon, Wi-Fi HAL, scan/connect, credentials,
  DHCP/routes, external ping, boot image write, partition write, firmware
  mutation, GPIO/sysfs/debugfs write, module load/unload, reboot, or Wi-Fi
  link-up occurred in V901.

## Next

Rerun V900 bounded `mdm_helper`/`ks` contract proof with the repaired helper.
