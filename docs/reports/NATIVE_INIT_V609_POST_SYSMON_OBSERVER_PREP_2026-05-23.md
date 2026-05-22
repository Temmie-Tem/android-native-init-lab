# Native Init V609 Post-Sysmon Observer Prep Report

- date: `2026-05-23 KST`
- status: `prepared`; live observer is **not** executed yet
- helper source: `stage3/linux_init/helpers/a90_android_execns_probe.c`
- runner: `scripts/revalidation/native_wifi_post_sysmon_observer_v609.py`
- deploy wrapper: `scripts/revalidation/wifi_execns_helper_v103_deploy_preflight.py`
- build evidence: `tmp/wifi/v609-execns-helper-v103-build/`
- deploy preflight evidence: `tmp/wifi/v609-execns-helper-v103-preflight/`
- runner plan evidence: `tmp/wifi/v609-post-sysmon-observer-plan-static/`

## Scope

V609 prep adds a helper mode and host runner for a no-CNSS post-sysmon observer
window. The prep validation built the static helper and ran plan/preflight only.

It did not deploy helper v103, start CNSS, start service-manager, start Wi-Fi
HAL, write `qcwlanstate`, scan/connect/link-up, use credentials, run DHCP,
change routes, ping externally, flash boot images, or write partitions.

## Helper V103

```text
marker: a90_android_execns_probe v103
sha256: a63758a4cd10a4d0b227e2b85516ecc65575cca30fe863d332b802fabae4f57e
mode: wifi-companion-post-sysmon-observer-start-only
```

The helper is static and has no dynamic section. The usage surface includes the
new mode and rejects `--allow-cnss-start-only` for that observer mode.

## Observer Contract

Allowed child order:

```text
qrtr_ns,rmt_storage,tftp_server,pd_mapper
```

Blocked in the primary observer window:

```text
cnss_diag
cnss_daemon
servicemanager
hwservicemanager
vndservicemanager
Wi-Fi HAL
wificond
supplicant
hostapd
```

The host runner reuses the existing V598 modem-holder/firmware-mount path and
replaces only the companion command. It still keeps `esoc0` unopened and uses
reboot cleanup.

## Static Validation

```text
py_compile(native_wifi_post_sysmon_observer_v609.py): pass
py_compile(wifi_execns_helper_v103_deploy_preflight.py): pass
v609_runner_plan: v609-post-sysmon-observer-plan-ready
v103_deploy_preflight: execns-helper-v103-deploy-preflight-ready
```

Expected preflight state:

```text
remote_helper: v100 currently installed after V608
remote_helper_v103: needs-deploy
NCM: absent; serial transfer explicitly selected
```

## Next Gate

Recommended live sequence:

1. Deploy helper v103.
2. Refresh current-boot V401/V490 prerequisites.
3. Run V609 preflight.
4. Run V609 bounded live observer.
5. Classify as `v609-service-notifier-pre-cnss-visible`,
   `v609-service-notifier-pre-cnss-missing`, or `v609-qrtr-sysmon-not-reached`.

No Wi-Fi HAL or connection attempt should happen until the pre-CNSS
service-notifier boundary is understood.
