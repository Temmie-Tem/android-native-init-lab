# V1254 Execns Helper v261 Deploy

- report: `docs/reports/NATIVE_INIT_V1254_EXECNS_HELPER_V261_DEPLOY_2026-05-31.md`
- wrapper: `scripts/revalidation/wifi_execns_helper_v261_deploy_preflight_v1254.py`
- local helper: `stage3/linux_init/helpers/a90_android_execns_probe_v261`
- remote helper: `/cache/bin/a90_android_execns_probe`
- evidence: `tmp/wifi/v1254-execns-helper-v261-deploy/manifest.json`
- result: `execns-helper-v261-deploy-pass`
- pass: `true`

## Scope

V1254 deployed helper v261 only. It did not run the new PMIC/power-surface
preflight, request a GPIO line, write PMIC/GPIO/debugfs or regulator state, open
`/dev/subsys_esoc0`, start PM/CNSS/HAL actors, scan/connect, use credentials,
DHCP/routes, external ping, reboot, flash, boot image write, or partition write.

## Deployment

| Field | Value |
| --- | --- |
| transfer method | serial fallback |
| serial chunk size | `1800` |
| chunks written | `1010` |
| encoded bytes | `1817918` |
| max cmdv1 line bytes | `3788` |
| line limit check | pass |
| remote SHA-256 | `37947e378f4743a6661a03ee36dfc95ddf5ce9cd79acec0862a28a4564573a7c` |
| helper marker | `a90_android_execns_probe v261` |
| new mode marker | `wifi-companion-pmic-power-surface-write-gate-preflight` |

NCM was not reachable during preflight, so the wrapper used the existing safe
serial appendfile + uudecode deployment path.

## Validation

| Check | Result |
| --- | --- |
| local helper SHA/marker/mode | pass |
| native version | `A90 Linux init 0.9.68 (v724)` |
| native selftest | `fail=0` |
| service-manager process surface | clean |
| Wi-Fi link surface | clean |
| remote helper SHA after deploy | pass |
| staging cleanup | pass |

The generic preflight check initially reported `remote-helper-v261=needs-deploy`
because `/cache/bin/a90_android_execns_probe` was still v260 before the approved
run. The deploy log then shows the v261 SHA on the remote helper after install.

## Safety

- helper deployment was the only device mutation
- no PMIC/GPIO/debugfs/regulator write
- no eSoC ioctl, PM actor, CNSS actor, Wi-Fi HAL, scan/connect, credentials,
  DHCP/routes, external ping, reboot, flash, boot image write, or partition write

## Next

V1255 should run the temporary-debugfs read-only mapping preflight with the
deployed helper v261. It should only classify PM8150L `gpiochip` identity,
global line `1270`, and offset `7`; it must still print
`gpio_line_request_executed=0`, `esoc_ioctl_executed=0`, and
`pm_actor_executed=0`.
