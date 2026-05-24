# Native Init V804 PLD/ICNSS Register/Probe Prerequisite Classifier Report

## Result

- decision: `v804-icnss-fw-ready-probe-gate-selected`
- pass: `true`
- runner: `scripts/revalidation/native_wifi_pld_icnss_register_probe_prereq_classifier_v804.py`
- evidence: `tmp/wifi/v804-pld-icnss-register-probe-prereq-classifier/`

## What Ran

```bash
python3 -m py_compile scripts/revalidation/native_wifi_pld_icnss_register_probe_prereq_classifier_v804.py

python3 scripts/revalidation/native_wifi_pld_icnss_register_probe_prereq_classifier_v804.py \
  --out-dir tmp/wifi/v804-pld-icnss-register-probe-prereq-plan-check \
  plan

python3 scripts/revalidation/native_wifi_pld_icnss_register_probe_prereq_classifier_v804.py run
```

V804 was host-only. It did not execute any device command.

## Evidence Summary

| Signal | Result |
| --- | --- |
| V775 custom-kernel flash pause | pass |
| V803 register boundary input | pass |
| stock route | `CONFIG_ICNSS=y`, `CONFIG_ICNSS_QMI=y`, `CONFIG_CNSS2=n` |
| PLD/SNOC source prerequisites | pass |
| ICNSS register semantics | non-sync event, FW-ready gated probe |
| V802 `wlan: Loading driver` | `1` |
| V802 `qcwlanstate` after boot | `OFF` |
| V802 `/sys/class/wlan_dev` after boot | `478:0` |
| V802 FW-ready / WLFW / BDF / wiphy / `wlan0` | `0 / 0 / 0 / 0 / 0` |
| explicit PLD/register failure logs | absent |

## Classification

V804 refines the V803 boundary. The source path shows:

```text
hdd_driver_load()
  -> pld_init()
  -> wlan_hdd_register_driver()
  -> pld_register_driver()
  -> pld_snoc_register_driver()
  -> icnss_register_driver()
  -> ICNSS_DRIVER_EVENT_REGISTER_DRIVER, flags=0
  -> if !ICNSS_FW_READY: store ops and return
  -> later FW_READY indication calls icnss_call_driver_probe()
```

That means `icnss_register_driver()` is not expected to wait for WLFW. It posts a
non-sync event and stores HDD/PLD ops until `ICNSS_FW_READY` arrives. Therefore
V802 `qcwlanstate=OFF` and repeated `Modules not initialized just return` are
better interpreted as post-startup readback still before `hdd_wlan_startup()`
completion, not as proof that PLD registration itself is blocked.

The useful next blocker is the ICNSS `FW_READY`/WLFW service-arrival gate:

```text
missing WLFW/service69
  -> missing ICNSS FW_READY indication
    -> missing icnss_call_driver_probe()
      -> missing hdd_wlan_startup()
        -> qcwlanstate remains OFF
```

## Safety

- Host-only classifier; no device command executed.
- No custom kernel flash, boot image write, partition write, or reboot.
- No Wi-Fi HAL, `wificond`, supplicant, hostapd, scan/connect, credential use,
  DHCP, route change, or external ping.
- No `boot_wlan`, `qcwlanstate`, `esoc0`, bind/unbind, module load/unload, or
  driver override.
- No Wi-Fi secret material was written to tracked output.

## Next

V805 should classify ICNSS `FW_READY`/WLFW service arrival using stock-kernel
observability only. The next live action, if any, should remain bounded and
read-only or control-surface-only, and should not revive custom-kernel flashing
until the V773/V774 boot incompatibility is solved.
