# Native Init V1220 cnss-daemon SDX50M Patch Candidate Report

Date: `2026-05-31`

## Result

- Decision: `v1220-private-cnss-daemon-sdx50m-patch-ready`
- Pass: `true`
- Runner: `scripts/revalidation/native_wifi_cnss_daemon_sdx50m_patch_v1220.py`
- Evidence: `tmp/wifi/v1220-cnss-daemon-sdx50m-patch/manifest.json`
- Artifact: `tmp/wifi/v1220-cnss-daemon-sdx50m-patch/artifacts/cnss-daemon.sdx50m`

## Summary

V1220 created a private host-only `cnss-daemon` artifact for the next live gate.
It does not modify the vendor export, device filesystem, boot image, or
partition state.

The patch changes only the runtime selection C string used by `cnss-daemon`
after `get_system_info()`:

```text
SDXPRAIRIE\0 -> SDX50M\0RIE\0
```

The trailing `RIE\0` bytes remain in the file, but the C string consumed by
`strcmp()` becomes `SDX50M`.  This matches the real eSoC name that
`libmdmdetect.so` accepts, instead of faking sysfs `esoc_name` to a value that
is filtered out before the type-0 output entry is filled.

## Evidence

| item | value |
| --- | --- |
| input | `tmp/wifi/v226-vendor-root-live-export/vendor-source/bin/cnss-daemon` |
| input size | `95112` |
| output size | `95112` |
| patch offset | `0x6cd4` |
| literal occurrence count | `1` |
| byte delta count | `4` |
| input SHA256 | `bced9853a77cfb02252571196584efa535be14f8f3fd9ce32712ddee224ba4bc` |
| output SHA256 | `784fd7bd9b602d8e1f94c9ceef977845909f452611025c40fda589d0e57de5fd` |
| output mode | `0700` |

Changed bytes:

| offset | before | after |
| --- | --- | --- |
| `0x6cd7` | `0x50` (`P`) | `0x35` (`5`) |
| `0x6cd8` | `0x52` (`R`) | `0x30` (`0`) |
| `0x6cd9` | `0x41` (`A`) | `0x4d` (`M`) |
| `0x6cda` | `0x49` (`I`) | `0x00` (`NUL`) |

Patched string check:

```text
0x6cd4: SDX50M
window: SDX50M\0RIE\0Wait 
```

## Safety

- Host-only: no device command.
- No daemon execution.
- No tracefs write.
- No vendor partition write.
- No boot image or partition write.
- No Wi-Fi HAL, scan/connect, credentials, DHCP/routes, or external ping.

## Next Gate

V1221 should add a helper live gate that uses this private patched binary only
inside the bounded PM/CNSS namespace.  The live gate should:

1. copy or bind the private artifact over `/vendor/bin/cnss-daemon` inside the
   helper-private namespace only;
2. keep `libmdmdetect` reading the real `SDX50M` sysfs name;
3. require `pm_client_register_entry peripheral="SDX50M"` or equivalent
   successful type-0 registration evidence;
4. require `per_mgr` `/dev/subsys_esoc0` evidence before extending toward
   MDM/WLFW/`wlan0`;
5. continue blocking Wi-Fi HAL, scan/connect, credentials, DHCP/routes, external
   ping, vendor writes, boot image writes, and partition writes.
