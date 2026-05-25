# Native Init V829 Service-Locator Domain-List Probe Plan

## Goal

Send exactly one bounded service-locator QMI `GET_DOMAIN_LIST` request for
`wlan/fw` to the live service-locator endpoint discovered in V826/V828, parse
the response TLVs, and keep the test below service-manager, Wi-Fi HAL,
scan/connect, credentials, DHCP/routes, external ping, boot image writes,
partition writes, and custom kernel flashing.

## Scope

- Helper:
  - `stage3/linux_init/helpers/a90_android_execns_probe.c`
  - version marker: `a90_android_execns_probe v126`
  - new gate: `--allow-servloc-domain-list-probe`
- Deploy wrapper:
  - `scripts/revalidation/wifi_execns_helper_v126_deploy_preflight.py`
- Runner:
  - `scripts/revalidation/native_wifi_servloc_domain_list_probe_v829.py`
- Input evidence:
  - `tmp/wifi/v828-servloc-domain-list-payload/manifest.json`
- Live base:
  - stock v724 native init
  - existing V817 lower companion window

## Hard Gates

- The QMI payload is limited to the V828 request:
  `00 01 00 21 00 11 00 01 07 00 77 6c 61 6e 2f 66 77 10 04 00 00 00 00 00`.
- No service-manager, Wi-Fi HAL, wificond, supplicant, scan/connect/link-up,
  credential use, DHCP, route change, or external ping.
- No `esoc0` open, qcwlanstate write, bind/unbind, driver override, or module
  load/unload.
- No boot image write, partition write, bootloader handoff, or custom kernel
  flash.
- Cleanup must reboot back to healthy v724 and verify status/selftest.

## Success Criteria

- Helper v126 builds as static aarch64 and contains both `--qrtr-readback-matrix`
  and `--allow-servloc-domain-list-probe` markers.
- V829 preflight confirms V828 input and helper readiness.
- Live run reaches V817 lower window, discovers service-locator `64/257`, sends
  one 24-byte request, and parses the response.
- Guardrails remain false for HAL/connect/credential/network/flash actions.
- Result classification records either successful domain list, QMI error, or
  bounded no-response.

## Validation

```bash
python3 -m py_compile \
  scripts/revalidation/wifi_execns_helper_v126_deploy_preflight.py \
  scripts/revalidation/native_wifi_servloc_domain_list_probe_v829.py

bash scripts/revalidation/build_android_execns_probe_helper.sh \
  tmp/wifi/v829-execns-helper-v126-build/a90_android_execns_probe

python3 scripts/revalidation/native_wifi_servloc_domain_list_probe_v829.py \
  --out-dir tmp/wifi/v829-servloc-domain-list-probe-plan-check \
  plan

python3 scripts/revalidation/native_wifi_servloc_domain_list_probe_v829.py \
  --out-dir tmp/wifi/v829-servloc-domain-list-probe-preflight \
  --transfer-method auto \
  preflight

python3 scripts/revalidation/native_wifi_servloc_domain_list_probe_v829.py \
  --out-dir tmp/wifi/v829-servloc-domain-list-probe \
  --transfer-method auto \
  run
```

## Next

If the domain list returns the WLAN process domain, V830 should derive the
bounded service-notifier `REGISTER_LISTENER` request for that returned domain
and prove whether the WLAN-PD state indication can be received below HAL,
scan/connect, credentials, DHCP/routes, and external ping.
