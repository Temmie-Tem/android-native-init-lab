# Native Init V666 Repaired Private CNSS Retry Plan

- date: `2026-05-24 KST`
- cycle: `v666`
- gate: bounded live `start-only`
- objective: rerun the V660/V655 fresh `cnss-daemon` retry path with the
  V665-repaired private property/runtime surface

## Background

V660 proved that service `74` plus `vndservicemanager` readiness can be reached
before a fresh `cnss-daemon` retry, but the retry still stopped in a Binder
transaction loop. V662/V664/V665 then showed that the private namespace needed
explicit property/runtime materialization and that the registry snapshot had to
capture the helper private temp-root paths rather than host/global `/dev`.

V666 tests the next narrow question:

```text
Does the same fresh cnss-daemon retry behave differently when --property-root
and the private property_service shim are active in helper v109?
```

## Scope

Allowed:

- current-boot preflight checks;
- helper v109 contract verification;
- V317 private property root visibility check;
- modem holder, QRTR companion stack, service `74` gate;
- bounded `servicemanager`/`hwservicemanager`/`vndservicemanager` start-only;
- bounded initial `cnss-daemon` cleanup and one retry `cnss-daemon`;
- reboot cleanup after live proof.

Forbidden:

- ADSP/CDSP/SLPI boot-node writes;
- `esoc0` open/hold;
- `qcwlanstate` or driver-state writes;
- Wi-Fi HAL, `wificond`, supplicant, or hostapd start;
- scan/connect/link-up, credentials, DHCP, route changes, or external ping;
- boot image changes or partition writes.

## Implementation

Add `scripts/revalidation/native_wifi_repaired_private_cnss_retry_v666.py`.
The runner reuses V655 and changes only:

1. helper contract: `a90_android_execns_probe v109`;
2. helper SHA: `eda3e88405d15cfa2b12ef3252cef3ff25ba23aae69aeb5075700fa147150030`;
3. V490 manifest path: `tmp/wifi/v666-v490-current-run/manifest.json`;
4. command contract: append
   `--property-root /mnt/sdext/a90/private-property-v317/dev/__properties__`;
5. private runtime classification from helper stdout/stderr:
   `context.dev_properties.*` and
   `wifi_hal_composite_start.property_service_shim.*`.

The command must remain at or below the current native argv budget:

```text
V655 argc: 28
V666 argc with --property-root: 30
max safe args: 30
```

## Success Labels

- `v666-repaired-private-cnss-retry-plan-ready`
- `v666-vndservicemanager-cnss-retry-preflight-ready`
- `v666-service74-gate-timeout`
- `v666-private-runtime-surface-missing`
- `v666-repaired-private-cnss-retry-binder-loop-persists`
- `v666-repaired-private-cnss-retry-wlfw-advanced`
- inherited cleanup/review labels rewritten from V655 to V666

## Interpretation

- If private runtime is missing, repair property materialization before retrying.
- If private runtime is ready and Binder `-22` persists, the blocker is no
  longer the V665 snapshot/property path; move to dynamic vendor Binder
  registration or service context analysis.
- If WLFW/BDF/`wlan0` advances, stop before Wi-Fi HAL/scan/connect and classify
  the new lower-surface state first.
- A pass does not mean Wi-Fi is connected. The final goal still requires native
  Wi-Fi connection and external ping in later gates.

## Validation

Static validation:

```bash
python3 -m py_compile scripts/revalidation/native_wifi_repaired_private_cnss_retry_v666.py
python3 scripts/revalidation/native_wifi_repaired_private_cnss_retry_v666.py \
  --out-dir tmp/wifi/v666-repaired-private-cnss-retry-plan-check plan
git diff --check
```

Live prerequisite sequence:

1. refresh V641 clean-DSP one-shot state;
2. mount SELinuxfs with V401 if needed;
3. run `mountsystem ro`;
4. run V490 current-boot policy-load proof using helper v109 SHA;
5. ensure V641 temporary firmware mounts are not left globally mounted;
6. run V666 preflight;
7. run V666 live only with the exact approval phrase.

Exact live approval phrase:

```text
approve v666 repaired private cnss-daemon retry proof only; no Wi-Fi HAL start, no scan/connect/link-up and no external ping
```
