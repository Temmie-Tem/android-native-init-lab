# Native Init V819 mdm3/esoc0 Registration Catalogue Plan

## Goal

Run the V818-selected bounded live registration catalogue inside the existing
lower window without widening to service-manager, Wi-Fi HAL, scan/connect,
credentials, DHCP, or external ping.

## Scope

- Target script:
  - `scripts/revalidation/native_wifi_mdm3_esoc_registration_catalogue_v819.py`
- Approach:
  - Reuse the V817 lower-window harness.
  - Inject read-only registration catalogue commands at before-holder,
    after-holder, and after-companion checkpoints.
  - Keep V817 firmware mount, `subsys_modem` holder, lower companion/CNSS
    diagnostic stack, and cleanup semantics unchanged.

## Hard Gates

- Stock v724 only; no custom kernel flash or boot image write.
- No partition write outside temporary runtime/evidence paths.
- No `esoc0` open, `qcwlanstate on/off`, bind/unbind, driver override, or
  module load/unload.
- No service-manager start, Wi-Fi HAL start, wificond, scan/connect/link-up,
  credential use, DHCP, route change, or external ping.
- Catalogue commands must be short read-only commands and must not invalidate
  the V817 snapshot contract.

## Success Criteria

- V819 compiles and plan-only manifest passes.
- V818 manifest is present and passed.
- Wrapped V817 lower window still passes.
- Registration catalogue files are captured at before-holder, after-holder, and
  after-companion.
- Catalogue confirms mdm3/esoc0 surfaces and registration hints without opening
  `esoc0`.
- Cleanup reboot restores healthy stock v724.

## Validation

```bash
python3 -m py_compile scripts/revalidation/native_wifi_mdm3_esoc_registration_catalogue_v819.py

python3 scripts/revalidation/native_wifi_mdm3_esoc_registration_catalogue_v819.py \
  --out-dir tmp/wifi/v819-mdm3-esoc-registration-catalogue-plan-check \
  plan

python3 scripts/revalidation/native_wifi_mdm3_esoc_registration_catalogue_v819.py run

git diff --check
```
