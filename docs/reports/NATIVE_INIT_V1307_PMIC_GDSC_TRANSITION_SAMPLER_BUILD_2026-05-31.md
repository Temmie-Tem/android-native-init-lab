# Native Init V1307 PMIC/GDSC Transition Sampler Build

## Summary

- Cycle: `V1307`
- Type: source/build-only helper support
- Decision: `v1307-pmic-gdsc-transition-sampler-build-pass`
- Result: PASS
- Evidence:
  - `tmp/wifi/v1307-execns-helper-v274-build/manifest.json`
  - `tmp/wifi/v1307-execns-helper-v274-build/summary.md`
- Script: `scripts/revalidation/native_wifi_pmic_gdsc_transition_sampler_support_v1307.py`
- Helper: `a90_android_execns_probe v274`
- Built artifact: `stage3/linux_init/helpers/a90_android_execns_probe_v274`
- SHA256: `eb96072631ca38c3296f5da1756a93765e198e8fdd4dc010d087bc4b3b5fc180`
- Size: `1319408`

V1307 adds helper-side support for a focused no-write PMIC/GDSC transition sampler. It is not deployed and does not run on the device in this cycle.

## Added Helper Surface

| surface | value |
| --- | --- |
| helper marker | `a90_android_execns_probe v274` |
| new flag | `--pm-observer-late-per-proxy-pmic-gdsc-transition-sampler` |
| response mode | `late-per-proxy-focused-pmic-gdsc-transition` |
| intended cadence | `80` samples at `50ms` |
| output marker | `pmic_gdsc_focus=1` |

The focused sampler keeps the existing bounded late-`per_proxy` route, but reduces per-sample output to the lower surfaces needed after V1306:

- `powerup_marker` for `/dev/subsys_esoc0` / `mdm_subsys_powerup`;
- AP2MDM/MDM2AP target debugfs GPIO lines;
- PM8150L soft-reset source and line;
- PCIe0/PCIe1 GDSC source and line;
- PCI/MHI counts, MHI pipe, `ks`, and `wlan0`;
- safety markers proving no GPIO line request, PMIC write, or direct eSoC ioctl.

## Validation

```bash
python3 -m py_compile scripts/revalidation/native_wifi_pmic_gdsc_transition_sampler_support_v1307.py
python3 scripts/revalidation/native_wifi_pmic_gdsc_transition_sampler_support_v1307.py run
file stage3/linux_init/helpers/a90_android_execns_probe_v274
sha256sum stage3/linux_init/helpers/a90_android_execns_probe_v274
aarch64-linux-gnu-readelf -d stage3/linux_init/helpers/a90_android_execns_probe_v274
```

Build output is static aarch64 and has no dynamic section. The build log contains existing truncation warnings in old observer code, but the build returned `rc=0`.

## Next

V1308 should deploy helper `v274` only. V1309 should run a bounded no-write PMIC/GDSC transition sampler live and decide whether the missing prerequisite is visible at runtime without PMIC/GPIO mutation.

## Safety

- Source/build-only; no deploy or device command.
- No PMIC write, userspace GPIO request/hold, direct eSoC ioctl, PM/CNSS actor start, Wi-Fi HAL, scan/connect, credential use, DHCP/routes, external ping, flash, boot image write, or partition write occurred.
