# Native Init v251 CNSS Property Surface Plan

## Summary

- target: v251 host-only CNSS property surface classifier
- baseline: v250 `qrtr-socket-local-bind-pass`
- new host tool: `scripts/revalidation/wifi_cnss_property_surface.py`
- boot image change: none
- device live command: none required
- daemon start: not executed

v249 classified Android property service/property area as runtime gaps. v251
statically inspects the exported `cnss-daemon` ELF to determine whether it has a
property read-only surface or any property write/control surface before live
start-only approval is discussed.

## Inputs

- v250 manifest: `tmp/wifi/v250-qrtr-socket-probe/manifest.json`
- exported binary: `tmp/wifi/v226-vendor-root-live-export/vendor-source/bin/cnss-daemon`

## Method

Host-only commands:

- `file <cnss-daemon>`
- `readelf -Ws <cnss-daemon>`
- `strings -a <cnss-daemon>`

Classify:

- imported property read symbols: `property_get`, `property_get_int32`,
  `__system_property_get`, etc.
- imported property write/control symbols: `property_set`,
  `__system_property_set`, `android::base::SetProperty`, etc.
- property-like strings: `ro.*`, `persist.*`, `vendor.*`, `wlan.*`, `wifi.*`,
  and CNSS-specific keys.

## Non-Goals

- do not execute `cnss-daemon`
- do not query or create Android property service
- do not write `/dev/__properties__`
- do not run live device commands except optional post-checks outside this tool
- do not scan/connect/link-up Wi-Fi

## Output

```text
tmp/wifi/v251-cnss-property-surface/
├── manifest.json
├── property-surface.json
├── strings-property-lines.txt
├── readelf-symbols.txt
└── summary.md
```

Decision labels:

- `cnss-property-read-only-surface`: read symbols/strings present and no write
  symbols detected.
- `cnss-property-write-surface-review`: property write/control symbols detected.
- `cnss-property-surface-blocked`: required input missing or analysis command
  failed.

## Validation Plan

```bash
python3 -m py_compile scripts/revalidation/wifi_cnss_property_surface.py
git diff --check
python3 scripts/revalidation/wifi_cnss_property_surface.py \
  --out-dir tmp/wifi/v251-cnss-property-surface
```

Acceptance:

- v250 prerequisite remains PASS
- exported `cnss-daemon` exists
- analysis completes using host-only static commands
- no daemon execution and no device Wi-Fi action occurs
