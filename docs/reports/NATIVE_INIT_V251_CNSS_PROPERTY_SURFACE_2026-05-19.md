# Native Init v251 CNSS Property Surface Report

## Summary

- status: PASS
- decision: `cnss-property-read-only-surface`
- boot image change: none
- device live command: none required
- daemon start: not executed
- output: `tmp/wifi/v251-cnss-property-surface/`
- host tool: `scripts/revalidation/wifi_cnss_property_surface.py`

v251 statically inspected the exported `cnss-daemon` ELF from the live vendor
root export. It found property read symbols and property-like strings, but no
property write/control symbols.

## Validation

Static and host-only analysis:

```bash
python3 -m py_compile scripts/revalidation/wifi_cnss_property_surface.py
git diff --check
python3 scripts/revalidation/wifi_cnss_property_surface.py \
  --out-dir tmp/wifi/v251-cnss-property-surface
```

Result:

```text
decision: cnss-property-read-only-surface
pass: True
```

Input binary:

```text
tmp/wifi/v226-vendor-root-live-export/vendor-source/bin/cnss-daemon
```

## Findings

| Item | Result |
| --- | --- |
| property read symbols | `property_get`, `property_get_int32` |
| property write/control symbols | none detected |
| host file/readelf/strings | PASS |
| v250 prerequisite | PASS |

Property-like strings detected:

```text
persist.vendor.cnss-daemon.debug_level
persist.vendor.cnss-daemon.hw_trc_disable_override
persist.vendor.cnss-daemon.kmsg_logging
ro.baseband
ro.board.platform
ro.vendor.extension_library
```

Other CNSS/Wi-Fi adjacent strings include `cnss_nl80211_init`,
`cnss_user_socket_init`, `cnss-genl`, and `/data/vendor/wifi/sockets/...` hints.

## Interpretation

- The property surface appears read-only from static ELF evidence.
- Missing Android property service/property area may affect defaults or runtime
  branching, but v251 did not find a property write/control surface.
- This reduces property-service risk for a bounded start-only attempt, but does
  not prove the daemon will run correctly without Android property service.
- The `/data/vendor/wifi/sockets/...` strings are a separate runtime filesystem
  surface and should not be treated as property-service evidence.

## References

- <https://android.googlesource.com/platform/system/core/+/refs/heads/android11-release/init/property_service.cpp>
- <https://android.googlesource.com/platform/bionic/+/cc9b100/libc/system_properties/system_properties.cpp>

## Guardrails Preserved

- host-only static analysis
- no `cnss-daemon` execution
- no property service emulation or property area write
- no rfkill unblock, `wlan*` link-up, scan/connect, credentials, DHCP, or routing
- no ICNSS bind/unbind, firmware mutation, Android partition write, or reboot

## Next Step

The first bounded live start-only attempt remains approval-gated. If approval is
still withheld, the next safe no-start candidate is `/data/vendor/wifi` socket
path/runtime filesystem surface analysis or QRTR nameservice visibility without
Wi-Fi control traffic.
