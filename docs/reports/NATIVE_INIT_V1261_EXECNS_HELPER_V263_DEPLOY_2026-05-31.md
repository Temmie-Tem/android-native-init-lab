# V1261 Execns Helper v263 Deploy

- report: `docs/reports/NATIVE_INIT_V1261_EXECNS_HELPER_V263_DEPLOY_2026-05-31.md`
- runner: `scripts/revalidation/wifi_execns_helper_v263_deploy_preflight_v1261.py`
- evidence: `tmp/wifi/v1261-execns-helper-v263-deploy/manifest.json`
- result: `execns-helper-v263-deploy-pass`
- pass: `true`

## Scope

V1261 is deploy-only for `a90_android_execns_probe v263`. It installs and verifies
`/cache/bin/a90_android_execns_probe`, then runs read-only postflight checks. It
does not execute the new gpiochip line-info mode, create a live device node,
request a GPIO line, write PMIC/GPIO/debugfs or regulator state, open
`/dev/subsys_esoc0`, start PM/CNSS/HAL actors, scan/connect, use credentials,
DHCP/routes, external ping, reboot, flash, boot image write, or partition write.

## Deploy Result

| Field | Value |
| --- | --- |
| helper marker | `a90_android_execns_probe v263` |
| local helper | `stage3/linux_init/helpers/a90_android_execns_probe_v263` |
| remote helper | `/cache/bin/a90_android_execns_probe` |
| SHA-256 | `32ac877a165a266d96589387d9974dfea38c81d0adb368bf17ff15de77a9f9fb` |
| transfer method | serial fallback |
| serial chunks | `1010` |
| serial chunk size | `1800` |
| max cmdv1 line bytes | `3788` / safe limit `3968` |
| postflight selftest | `fail=0` |

The host NCM address was not present during this run, so `auto` transfer fell
back to serial. The serial line-limit preflight passed before any append chunks
were written.

## Validation

| Check | Result |
| --- | --- |
| `python3 -m py_compile scripts/revalidation/wifi_execns_helper_v263_deploy_preflight_v1261.py` | pass |
| `git diff --check` | pass |
| local helper SHA/marker/mode | pass |
| remote helper SHA after deploy | pass |
| service-manager process surface | clean |
| Wi-Fi link surface | clean |
| V373 post-deploy preflight | `service-manager-start-only-smoke-approval-required`, pass |

## Interpretation

V1261 closes the deploy gate for helper v263. The device now has the helper needed
for the next bounded live proof:
`wifi-companion-pmic-gpiochip-line-info-preflight` with
`--allow-pmic-gpiochip-line-info-preflight`.

## Safety

- deploy-only; no execution of the new gpiochip line-info mode
- no live `mknod`, GPIO line request, PMIC/GPIO/debugfs/regulator write
- no eSoC ioctl, PM actor, CNSS actor, Wi-Fi HAL, scan/connect, credentials,
  DHCP/routes, external ping, reboot, flash, boot image write, or partition write
