# V1248 PMIC Soft-reset Preflight Helper Build

- report: `docs/reports/NATIVE_INIT_V1248_PMIC_SOFT_RESET_PREFLIGHT_BUILD_2026-05-31.md`
- helper source: `stage3/linux_init/helpers/a90_android_execns_probe.c`
- helper binary: `stage3/linux_init/helpers/a90_android_execns_probe_v260`
- verifier: `scripts/revalidation/native_wifi_pmic_soft_reset_preflight_support_v1248.py`
- evidence: `tmp/wifi/v1248-execns-helper-v260-build/manifest.json`
- result: `v1248-pmic-soft-reset-preflight-build-pass`
- pass: `true`
- helper marker: `a90_android_execns_probe v260`
- helper sha256: `0313d613d95c56af5681871062b7fceb47ede3c3ef8fcff534d0eea3338eaa2f`

## Scope

V1248 is source/build-only. It adds a fail-closed PMIC soft-reset preflight mode
to `a90_android_execns_probe` and builds a static aarch64 helper. It does not
deploy the helper, execute a device command, perform a PMIC/GPIO/debugfs/GDSC
write, execute an eSoC ioctl, start PM/CNSS actors, start Wi-Fi HAL, scan,
connect, use credentials, run DHCP/routes, or ping externally.

## Implementation

The new mode is `wifi-companion-pmic-soft-reset-preflight` and requires
`--allow-pmic-soft-reset-preflight`. Without that explicit preflight flag it
fails argument validation.

The reserved `--allow-pmic-soft-reset-write` flag is intentionally rejected in
v260. It exists only as a visible fail-closed boundary for a later cycle; v260
does not implement a PMIC mutation path.

When eventually deployed and run in preflight mode, the helper reports:

- expected DTS contract: `qcom,ext-sdx50m` and `qcom,ap2mdm-soft-reset-gpio = <0x3d 0x9 0x0>`
- expected Android contract: relevant GPIO class nodes absent and PM8150L GPIO9
  in the PMIC gpiochip range
- current native PMIC soft-reset pinctrl line and PCIe GDSC lines
- GPIO142 IRQ snapshot, `mdm3` state, and explicit zero-action markers
- `write_gate_implemented=0`, `mutation_attempted=0`, `esoc_ioctl_executed=0`

## Validation

| Check | Result |
| --- | --- |
| V1247 input manifest | pass |
| source required strings | pass |
| static aarch64 build | pass |
| built helper has no `INTERP` | pass |
| built helper has no dynamic section | pass |
| binary required strings | pass |
| stage3 helper SHA matches build output | pass |

## Commands

| Command | Result |
| --- | --- |
| `python3 -m py_compile scripts/revalidation/native_wifi_pmic_soft_reset_preflight_support_v1248.py` | pass |
| `scripts/revalidation/build_android_execns_probe_helper.sh stage3/linux_init/helpers/a90_android_execns_probe_v260` | pass |
| `python3 scripts/revalidation/native_wifi_pmic_soft_reset_preflight_support_v1248.py plan` | pass |
| `python3 scripts/revalidation/native_wifi_pmic_soft_reset_preflight_support_v1248.py run` | pass |

## Next

V1249 should be deploy-only for helper v260. V1250 should run only the
read-only PMIC soft-reset preflight and parse whether the native surface is a
valid reproduction candidate. A bounded write gate remains out of scope until a
later cycle explicitly implements and validates one.

## Safety

- source/build-only; no deploy and no device command executed
- no PMIC/GPIO/debugfs/regulator write
- no eSoC ioctl, PM actor, CNSS actor, Wi-Fi HAL, scan/connect, credentials,
  DHCP/routes, external ping, reboot, flash, boot image write, or partition write
